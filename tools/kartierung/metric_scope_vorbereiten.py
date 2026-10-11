#!/usr/bin/env python3
"""Bind a private, explicitly reviewed LAB polygon to the current passive stack.

Reads /map, MapManager status, TF and ROS graph ownership. Starts only the
existing native read-only TF provenance observer, never Explorer or a mission.
The printed existing Explorer launch stays passive and conservative.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import selectors
import shlex
import signal
import subprocess
import sys
import time

from explore.exploration_scope import AuthorizedExplorationScope, point_within_scope_clearance
from explore.map_status_adapter import MapManagerStatusCorrelator, decode_map_manager_status_json
from explore.portal_memory import Point2D, PortalMapContext
from explore.portal_source_adapter import (raw_map_portal_source_from_values,
    correlate_raw_map_portal_source)
from amadeus_map_identity import MAXIMUM_OCCUPANCY_CELL_COUNT


class BindingPending(ValueError):
    """An exact live pair/owner has not arrived yet; no file can be produced."""


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON field: '+key)
        result[key] = value
    return result


def scope_document(text):
    require(len(text.encode()) <= 65536, 'scope JSON exceeds 64 KiB')
    document = json.loads(text, object_pairs_hook=unique_object)
    keys = {'schema_version', 'session_id', 'scope_id', 'frame_id',
            'map_fingerprint', 'accessible_scope_verified', 'vertices'}
    require(isinstance(document, dict) and set(document) == keys, 'scope fields missing or unknown')
    require(type(document['schema_version']) is int and document['schema_version'] == 1,
            'unsupported scope schema_version')
    require(document['accessible_scope_verified'] is True, 'explicit reviewed LAB scope required')
    require(isinstance(document['map_fingerprint'], str)
        and re.fullmatch('[0-9a-f]{64}', document['map_fingerprint']) is not None,
        'scope requires the explicitly observed current map fingerprint')
    context = PortalMapContext(document['session_id'], 'map-'+document['map_fingerprint'], document['frame_id'])
    require(isinstance(document['vertices'], list) and all(isinstance(p, list) and len(p) == 2
            for p in document['vertices']), 'vertices must be explicit [x,y] pairs')
    scope = AuthorizedExplorationScope(document['scope_id'], context,
        tuple(Point2D(*p) for p in document['vertices']))
    return document, scope


def owner(node, gid):
    require(isinstance(node, str) and re.fullmatch(r'/(?:[A-Za-z_][A-Za-z_0-9]*/)*[A-Za-z_][A-Za-z_0-9]*', node),
            f'publisher name must be fully qualified: node={node!r}, gid={list(gid)!r}')
    values = tuple(gid)
    require(len(values) == 24 and all(type(v) is int and 0 <= v <= 255 for v in values) and any(values),
            'publisher GID missing or invalid')
    return dict(node=node, gid=list(values))


def private_path(path, repository):
    path, repository = Path(path).expanduser().resolve(), Path(repository).resolve()
    require(path != repository and repository not in path.parents
        and not any((parent/'.git').exists() for parent in (path.parent, *path.parents)),
        'real LAB scope/output must be outside every Git checkout')
    return path


def unchanged_file(path, expected_bytes):
    require(path.read_bytes() == expected_bytes, str(path)+' changed during binding')
    return hashlib.sha256(expected_bytes).hexdigest()


def single_owner(values, topic):
    if not values:
        raise BindingPending('publisher discovery pending: '+topic)
    require(len(values) == 1, 'ambiguous publishers: '+topic)
    return values[0]


def graph_owners(records, topic, *, require_single=False):
    """Discovery may know a DDS endpoint before its ROS name is resolved."""
    if require_single:
        single_owner(records, topic)  # Count all endpoints, including unresolved ones.
    result = []
    for record in records:
        name, namespace = record.node_name, record.node_namespace
        gid = [int(value) for value in record.endpoint_gid]
        # Humble RMW exposes these explicit placeholders during discovery.
        # Never filter the endpoint out or accept its identity on that basis.
        if name == '_NODE_NAME_UNKNOWN_' or namespace == '_NODE_NAMESPACE_UNKNOWN_':
            raise BindingPending(f'publisher name discovery pending: topic={topic!r}, '
                f'namespace={namespace!r}, name={name!r}, gid={gid!r}')
        require(isinstance(name, str) and isinstance(namespace, str), 'publisher graph name metadata invalid')
        result.append(owner(namespace.rstrip('/')+'/'+name, gid))
    return result


def tf_pair_owners(provenance, endpoints, frame):
    endpoints = {tuple(e['gid']): e for e in endpoints}
    result = {}
    for kind, pair in (('map_odom', (frame, 'odom')), ('odom_base', ('odom', 'base_link'))):
        gids = provenance.get(pair, set())
        if not gids:
            raise BindingPending('no fresh native TF provenance for '+str(pair))
        require(len(gids) == 1, 'multiple dynamic TF owners: '+str(pair))
        gid = next(iter(gids))
        if gid not in endpoints:
            raise BindingPending('TF publisher no longer discoverable')
        result[kind] = endpoints[gid]
    return result


def explorer_exists(nodes, services, topics):
    return any(name == 'explore_node' for name, _ in nodes) or any(
        re.search(r'(?:^|/)explore_area/_action/', name) for name, _ in (*services, *topics))


def installed_inputs(install_root, config, module_paths):
    """Bind actual resolved installed bytes, with no fallback to another overlay."""
    import yaml
    root = Path(install_root).expanduser().resolve()
    config = Path(config).resolve()
    paths = dict(module_paths)
    paths.update(metric_profile=config/'metric_frontier_params.yaml', base_profile=config/'explore_params.yaml')
    snapshots, identity = {}, {}
    for label, raw_path in paths.items():
        path = Path(raw_path).resolve()
        require(root in path.parents, label+' resolves outside the explicit installed release')
        content = path.read_bytes()
        snapshots[path] = content
        identity[label] = dict(path=str(path), sha256=hashlib.sha256(content).hexdigest())
    return (yaml.safe_load(snapshots[config/'metric_frontier_params.yaml']),
            yaml.safe_load(snapshots[config/'explore_params.yaml'])['explore_node']['ros__parameters'],
            identity, snapshots)


def transform_values(message):
    t, q = message.transform.translation, message.transform.rotation
    return dict(parent=message.header.frame_id, child=message.child_frame_id,
        stamp_ns=message.header.stamp.sec*10**9+message.header.stamp.nanosec,
        translation=[t.x, t.y, t.z], rotation=[q.x, q.y, q.z, q.w])


def grid_values(message):
    origin = message.info.origin
    p, q = origin.position, origin.orientation
    return dict(width=message.info.width, height=message.info.height,
        resolution=message.info.resolution, frame_id=message.header.frame_id,
        source_stamp_ns=message.header.stamp.sec*10**9+message.header.stamp.nanosec,
        origin=(p.x, p.y, p.z, q.x, q.y, q.z, q.w), cells=message.data)


class ScopeBinding:
    """Use existing pure map/scope contracts; never construct an occupancy map."""
    def __init__(self, document, *, map_owner='/slam_toolbox', manager_owner='/robot_map_manager',
                 odom_owner='/hwt601_mapping_ekf', map_timeout=5., pose_timeout=.8, maximum_cells=262144):
        self.document, self.scope = scope_document(json.dumps(document))
        self.expected = dict(map=map_owner, manager=manager_owner,
                             map_odom=map_owner, odom_base=odom_owner)
        self.correlator = MapManagerStatusCorrelator(document['session_id'], document['frame_id'])
        require(all(type(value) in (float, int) and math.isfinite(value) and value > 0
                    for value in (map_timeout, pose_timeout)), 'freshness limits must be finite and positive')
        require(type(maximum_cells) is int and 0 < maximum_cells <= MAXIMUM_OCCUPANCY_CELL_COUNT,
                'maximum_cells must be within the shared bounded map capacity')
        for expected in self.expected.values():
            owner(expected, [1]+[0]*23)
        self.map_timeout, self.pose_timeout, self.maximum_cells = map_timeout, pose_timeout, maximum_cells
        self.raw = self.status = None
        self.owners = {}
        self.status_count = 0

    def check_owner(self, kind, actual):
        actual = owner(actual['node'], actual['gid'])
        require(actual['node'] == self.expected[kind], kind+' publisher name mismatch')
        require(kind not in self.owners or self.owners[kind] == actual, kind+' publisher/source changed')
        self.owners[kind] = actual

    def accept_map(self, values, received, actual_owner):
        self.check_owner('map', actual_owner)
        require(values['width']*values['height'] <= self.maximum_cells, 'map exceeds Explorer evidence limit')
        source = raw_map_portal_source_from_values(**values)
        require(source.fingerprint == self.document['map_fingerprint'], 'map changed from reviewed scope fingerprint')
        require(source.frame_id == self.document['frame_id'], 'scope/map frame mismatch')
        require(source.source_stamp_ns > 0, 'map stamp must be positive')
        if self.raw is not None:
            if source.source_stamp_ns < self.raw[0].source_stamp_ns:
                # Same immutable map from the second QoS history can arrive late.
                # Match the product: do not treat it as new reception/freshness.
                return
        self.raw = source, received

    def accept_status(self, text, received, actual_owner):
        self.check_owner('manager', actual_owner)
        sample = decode_map_manager_status_json(text)
        require(sample.fingerprint == self.document['map_fingerprint'], 'manager map changed from reviewed scope')
        correlation = self.correlator.accept(sample)
        require(correlation.context == self.scope.context, 'scope/session/map context mismatch')
        self.status = sample, correlation, received
        self.status_count += 1

    def snapshot(self, *, ros_now_ns, monotonic_now, pose, reference, tf_owners, explorer_present=False):
        require(not explorer_present, 'an Explorer/ExploreArea owner already exists; no second start')
        if self.raw is None or self.status is None or self.status_count < 2:
            raise BindingPending('need current raw map and two MapManager status observations')
        source, map_received = self.raw
        sample, correlation, status_received = self.status
        if (source.fingerprint, source.source_stamp_ns, source.frame_id) != (
                correlation.fingerprint, correlation.source_stamp_ns, correlation.context.frame_id):
            raise BindingPending('latest raw map and manager status are not an exact pair')
        correlate_raw_map_portal_source(source, correlation)
        def fresh(age, limit, label):
            require(math.isfinite(age), label+' invalid age')
            if not 0 <= age <= limit:
                raise BindingPending(label+' missing/stale/future; age='+str(age))
        fresh(monotonic_now-map_received, self.map_timeout, 'map receipt')
        fresh(monotonic_now-status_received, self.map_timeout, 'status receipt')
        fresh(ros_now_ns/1e9-sample.status_time_seconds, self.map_timeout, 'status time')
        fresh(sample.received_age_seconds+ros_now_ns/1e9-sample.status_time_seconds,
              self.map_timeout, 'manager map age including status transport')
        fresh((ros_now_ns-source.source_stamp_ns)/1e9, self.map_timeout, 'raw map stamp')
        require(pose['parent'] == reference['parent'] == self.document['frame_id']
            and pose['child'] == 'base_link' and reference['child'] == 'odom', 'TF frames mismatch')
        require(pose['stamp_ns'] == reference['stamp_ns'] and pose['stamp_ns'] > 0, 'TF must share a positive actual timestamp')
        for transform in (pose, reference):
            fresh((ros_now_ns-transform['stamp_ns'])/1e9, self.pose_timeout, 'TF pose/reference')
            t, q = transform['translation'], transform['rotation']
            require(len(t) == 3 and len(q) == 4 and all(type(v) in (int, float) and math.isfinite(v) for v in (*t, *q)),
                    'TF values invalid')
            require(abs(q[0])+abs(q[1]) <= 1e-6 and abs(sum(v*v for v in q)-1) <= 1e-6,
                    'TF must be planar with a normalized quaternion')
        for kind in ('map_odom', 'odom_base'):
            self.check_owner(kind, tf_owners[kind])
        require(point_within_scope_clearance(self.scope, context=correlation.context,
            x_m=pose['translation'][0], y_m=pose['translation'][1], clearance_m=1e-9),
            'actual robot centre lies outside the explicitly reviewed LAB scope')
        return dict(schema_version=1, session_id=self.document['session_id'],
            processing_capacity_cells=self.maximum_cells,
            map_fingerprint=source.fingerprint, source_stamp_ns=source.source_stamp_ns,
            scope_fingerprint=self.scope.fingerprint, observed_maps=sample.observed_maps,
            bound_ros_ns=ros_now_ns, owners=copy.deepcopy(self.owners), pose=pose, map_odom=reference,
            movement_authorized=False, path_validation='conservative')

    def parameters(self, metric_profile):
        parameters = copy.deepcopy(metric_profile['explore_node']['ros__parameters'])
        parameters.update(metric_session_id=self.document['session_id'],
            wohnungserkundung_evidence_max_cells=self.maximum_cells,
            metric_scope_map_fingerprint=self.document['map_fingerprint'],
            wohnungserkundung_accessible_scope_verified=True,
            wohnungserkundung_scope_id=self.document['scope_id'],
            wohnungserkundung_scope_polygon_xy=[float(v) for p in self.document['vertices'] for v in p],
            global_frame=self.document['frame_id'], robot_base_frame='base_link',
            metric_path_validation='conservative', metric_resume_saved_state=False)
        return {'explore_node': {'ros__parameters': parameters}}


def write_private_profile(output, parameters, proof, repository):
    import yaml
    output = private_path(output, repository)
    require(output.parent.is_dir(), 'create the private output directory first')
    payload = ('# Current passive snapshot only; rebind after any stack/map restart.\n'
        '# No motion, hardware tracking or later source freshness qualification.\n'
        '# binding: '+json.dumps(proof, sort_keys=True, allow_nan=False)+'\n'
        + yaml.safe_dump(parameters, sort_keys=False)).encode()
    fd = os.open(str(output), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(payload)
        stream.flush(); os.fsync(stream.fileno())
    return output


class ScopeTfListener:
    """Receive original TF independently of map and graph validation work."""
    def __init__(self, node):
        from threading import Event, Thread
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from tf2_ros import Buffer, TransformListener
        self.node = Node(node.get_name()+'_tf', context=node.context,
                         namespace=node.get_namespace(), use_global_arguments=False,
                         enable_rosout=False, start_parameter_services=False)
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self.node, spin_thread=False)
        self.executor = SingleThreadedExecutor(context=node.context)
        self.executor.add_node(self.node)
        self.stop = Event()
        self.fault = None
        self.thread = Thread(target=self._spin, name='scope_tf_receiver')
        self.thread.start()

    def _spin(self):
        try:
            while not self.stop.is_set() and self.node.context.ok():
                self.executor.spin_once(timeout_sec=.05)
        except Exception as error:
            self.fault = error

    def close(self):
        # Humble shutdown() destroys guard handles while spin() can still be
        # constructing its wait set. End the reader before destroying handles.
        self.stop.set()
        self.executor.wake()
        self.thread.join()
        self.executor.shutdown()
        self.listener.unregister()
        self.node.destroy_node()


def collect(args, binding, metric_profile, repository):
    # ROS stays a CLI-only dependency: offline tests use actual pure contracts.
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
    from rclpy.time import Time
    from nav_msgs.msg import OccupancyGrid
    from std_msgs.msg import String
    from tf2_ros import TransformException

    require(args.tf_probe.is_file() and os.access(args.tf_probe, os.X_OK), 'built read-only TF ownership probe required')
    rclpy.init(args=[])
    node = Node('metric_scope_prepare_'+str(os.getpid()))
    tf_source = ScopeTfListener(node)
    tf_buffer = tf_source.buffer
    fault = [None]
    provenance = {}
    def endpoints(topic, *, require_single=False):
        return graph_owners(node.get_publishers_info_by_topic(topic), topic, require_single=require_single)
    def single(topic):
        return single_owner(endpoints(topic, require_single=True), topic)
    def observed(callback, topic, convert):
        def receive(message):
            try:
                callback(convert(message), time.monotonic(), single(topic))
            except BindingPending:
                pass  # discovery only; no source is fabricated or restamped
            except Exception as error:
                fault[0] = error
        return receive
    # Like MapManager, accept both durable history and live volatile publishers.
    for durability in (DurabilityPolicy.TRANSIENT_LOCAL, DurabilityPolicy.VOLATILE):
        map_qos = QoSProfile(depth=1, durability=durability, reliability=ReliabilityPolicy.RELIABLE)
        node.create_subscription(OccupancyGrid, '/map', observed(binding.accept_map, '/map', grid_values), map_qos)
    node.create_subscription(String, '/robot_map_manager/status_json', observed(binding.accept_status,
        '/robot_map_manager/status_json', lambda m: m.data), 10)
    process = None
    selector = selectors.DefaultSelector()
    pending = b''
    try:
        unchanged_file(args.tf_probe, args.tf_probe_bytes)
        process = subprocess.Popen([str(args.tf_probe)], stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, start_new_session=True)
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic()+args.timeout
        last_pending = 'waiting for live map/status/TF'
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.05)
            if tf_source.fault is not None:
                raise tf_source.fault
            if fault[0] is not None:
                raise fault[0]
            require(process.poll() is None, 'TF ownership observer exited')
            for event, _ in selector.select(timeout=0):
                pending += os.read(event.fd, 65536)
                require(len(pending) <= 1048576, 'TF provenance line exceeds limit')
                while b'\n' in pending:
                    line, pending = pending.split(b'\n', 1)
                    if not line.startswith(b'{'):
                        continue
                    item = json.loads(line)
                    key = item['parent'], item['child']
                    provenance.setdefault(key, set()).add(tuple(item['gid']))
            try:
                binding.check_owner('map', single('/map'))
                binding.check_owner('manager', single('/robot_map_manager/status_json'))
                tf_owners = tf_pair_owners(provenance, endpoints('/tf'), binding.document['frame_id'])
                explorer_present = explorer_exists(node.get_node_names_and_namespaces(),
                    node.get_service_names_and_types(), node.get_topic_names_and_types())
                pose = tf_buffer.lookup_transform(binding.document['frame_id'], 'base_link', Time())
                reference = tf_buffer.lookup_transform(binding.document['frame_id'], 'odom', Time.from_msg(pose.header.stamp))
                proof = binding.snapshot(ros_now_ns=node.get_clock().now().nanoseconds,
                    monotonic_now=time.monotonic(), pose=transform_values(pose), reference=transform_values(reference),
                    tf_owners=tf_owners, explorer_present=explorer_present)
                proof['tf_probe_sha256'] = unchanged_file(args.tf_probe, args.tf_probe_bytes)
                proof['scope_file_sha256'] = unchanged_file(args.scope, args.scope_bytes)
                for path, content in args.installed_snapshots.items():
                    unchanged_file(path, content)
                proof['installed_inputs'] = args.installed_identity
                proof['preparation_tool'] = dict(path=str(Path(__file__).resolve()),
                    sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
                proof['publisher_provenance'] = {
                    'tf': 'native per-transform DDS GID joined to current graph endpoint',
                    'map_status': 'single current graph endpoint, latched GID; Humble Python has no per-message GID'}
                proof['snapshot_only'] = True
                return write_private_profile(args.output, binding.parameters(metric_profile), proof, repository)
            except (BindingPending, TransformException) as error:
                last_pending = str(error)
        raise ValueError('binding deadline exhausted: '+last_pending)
    finally:
        try:
            if process is not None and process.poll() is None:
                process.send_signal(signal.SIGINT)  # own passive direct child only
                try:
                    process.wait(timeout=3.)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=3.)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.wait(timeout=3.)
        finally:
            selector.close()
            tf_source.close()
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, epilog='Scope JSON needs schema_version=1, session_id, scope_id, '
        'frame_id, current map_fingerprint, accessible_scope_verified=true and explicit vertices [[x,y],...]. '
        'Read the fingerprint from the current /robot_map_manager/status_json; never reuse a prior map epoch blindly.')
    parser.add_argument('--scope', type=Path, required=True, help='private explicitly reviewed LAB-scope JSON')
    parser.add_argument('--output', type=Path, required=True, help='new private YAML outside repository')
    parser.add_argument('--tf-probe', type=Path, required=True, help='built existing tools/simulation/tf_ownership_probe binary')
    parser.add_argument('--install-root', type=Path, required=True, help='explicit product-install root; reject mixed/old Python overlays')
    parser.add_argument('--timeout', type=float, default=15.)
    parser.add_argument('--unknown-space-policy', choices=('observed_only', 'sensor_guarded'),
        default='sensor_guarded', help='same policy as the running app_mapping stack; printed launch only')
    parser.add_argument('--maximum-cells', type=int, default=None,
        help='Explicit processing capacity copied into the bound profile; no resampling or geometry changes')
    parser.add_argument('--map-owner', default='/slam_toolbox')
    parser.add_argument('--manager-owner', default='/robot_map_manager')
    parser.add_argument('--odom-owner', default='/hwt601_mapping_ekf')
    args = parser.parse_args(argv)
    require(math.isfinite(args.timeout) and 0 < args.timeout <= 60., 'timeout must be within (0,60] seconds')
    repository = Path(__file__).resolve().parents[2]
    args.scope = private_path(args.scope, repository)
    args.output = private_path(args.output, repository)
    require(args.output.parent.is_dir() and not args.output.exists(), 'output needs an existing directory and a new filename')
    args.tf_probe = args.tf_probe.expanduser().resolve()
    args.scope_bytes = args.scope.read_bytes()
    args.tf_probe_bytes = args.tf_probe.read_bytes()
    document, _ = scope_document(args.scope_bytes.decode('utf-8'))
    from ament_index_python.packages import get_package_share_directory
    config = Path(get_package_share_directory('explore'))/'config'
    # Pure modules are already loaded. Runtime is resolved without importing its
    # ROS/motion implementation, and neither the Node nor a mission is created.
    module_names = ('explore.exploration_scope', 'explore.map_status_adapter', 'explore.portal_memory',
                    'explore.portal_source_adapter', 'explore.metric_frontier_runtime',
                    'amadeus_map_identity', 'amadeus_map_identity.fingerprint')
    module_paths = {name: importlib.util.find_spec(name).origin for name in module_names}
    metric_profile, base, args.installed_identity, args.installed_snapshots = installed_inputs(
        args.install_root, config, module_paths)
    binding = ScopeBinding(document, map_owner=args.map_owner, manager_owner=args.manager_owner,
        odom_owner=args.odom_owner, map_timeout=base.get('map_timeout_s', 5.),
        pose_timeout=base.get('door_localization_timeout_s', .8),
        maximum_cells=(args.maximum_cells if args.maximum_cells is not None else
                       base.get('wohnungserkundung_evidence_max_cells', 262144)))
    output = collect(args, binding, metric_profile, repository)
    print('Privates konservatives Profil gebunden: '+str(output))
    print('Nur anzeigen; keine Mission oder Bewegung gestartet. Bestehenden passiven Stack weiterlaufen lassen:')
    print('Snapshotbindung: Explorer muss beim ersten Kartenempfang denselben Fingerprint erhalten; bei Änderung neu binden.')
    print(shlex.join(['ros2', 'launch', 'explore', 'explore.launch.py', 'explore_params_overlay:='+str(output),
        'unknown_space_policy:='+args.unknown_space_policy,
        'require_hwt601_fusion:=true', 'hwt601_active_drive:=false', 'hwt_development_contract:=true']))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print('Scopebindung abgebrochen: '+str(error), file=sys.stderr)
        raise SystemExit(1)
