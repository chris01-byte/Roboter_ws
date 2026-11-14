#!/usr/bin/env python3
"""Explicitly synthetic, non-actuating ROS integration test in domain 193.

PREPARED ONLY: execute after other tests, from the existing device-free ROS
container and actual built product overlay. This starts three tiny fake source
nodes and the real read-only scope CLI/TF observer. It never starts Explorer,
navigation, a mission, a driver, or a velocity publisher.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
import traceback


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new_json(path, value):
    payload = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(payload)


def endpoint(node, topic, name):
    rows = [row for row in node.get_publishers_info_by_topic(topic)
            if row.node_namespace.rstrip('/')+'/'+row.node_name == name]
    require(len(rows) == 1, f'Expected exactly one {name} endpoint on {topic}; found {len(rows)}')
    return dict(node=name, gid=[int(v) for v in rows[0].endpoint_gid])


def spin_until(executor, predicate, limit=5.):
    end = time.monotonic()+limit
    while time.monotonic() < end:
        executor.spin_once(timeout_sec=.03)
        if predicate():
            return
    raise AssertionError('Synthetic smoke precondition/cleanup did not complete within deadline')


def own_children(pid):
    """Inspect descendants for cleanup evidence; never kill by name or graph."""
    try:
        values = Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
    except FileNotFoundError:
        # This container exposes proc status/stat but not task/children. Read
        # exact PPid instead; an empty unsupported children file is not evidence
        # that the directly owned CLI never launched its native observer.
        values = []
        for path in Path('/proc').iterdir():
            if not path.name.isdecimal():
                continue
            try:
                text = (path/'stat').read_text()
                fields = text[text.rfind(')')+2:].split()
                if int(fields[1]) == pid:  # field 4: exact parent process ID
                    values.append(path.name)
            except FileNotFoundError:
                pass
    result = {}
    for value in values:
        try:
            # field 22 starttime protects against an unrelated later PID reuse.
            text = Path(f'/proc/{value}/stat').read_text()
            result[int(value)] = text[text.rfind(')')+2:].split()[19]
        except FileNotFoundError:
            pass
    return result


def still_same_process(pid, start):
    try:
        text = Path(f'/proc/{pid}/stat').read_text()
        return text[text.rfind(')')+2:].split()[19] == start
    except FileNotFoundError:
        return False


def run_cli(executor, command, directory, label):
    """Only signal this directly owned CLI; it owns and reaps its TF probe."""
    out, err = directory/(label+'.stdout.log'), directory/(label+'.stderr.log')
    descendants = {}
    child = None
    started = time.monotonic()
    try:
        with out.open('x') as stdout, err.open('x') as stderr:
            child = subprocess.Popen(command, stdout=stdout, stderr=stderr,
                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}, start_new_session=True)
            deadline = started+25.
            while child.poll() is None and time.monotonic() < deadline:
                descendants.update(own_children(child.pid))
                executor.spin_once(timeout_sec=.03)
            require(child.poll() is not None, 'Scope CLI exceeded smoke deadline')
            code = child.wait()
    finally:
        if child is not None and child.poll() is None:
            child.send_signal(signal.SIGINT)
            try:
                child.wait(timeout=10.)  # real CLI finally reaps only its TF observer
            except subprocess.TimeoutExpired:
                child.terminate()
                try:
                    child.wait(timeout=3.)
                except subprocess.TimeoutExpired:
                    child.kill(); child.wait(timeout=3.)
    require(not any(still_same_process(pid, start) for pid, start in descendants.items()),
            'The real scope CLI left a previously observed owned child running')
    return dict(command=command, exit_code=code, duration_s=time.monotonic()-started,
        stdout=str(out), stderr=str(err), owned_cli_pid=child.pid,
        observed_owned_children=sorted(descendants), all_observed_children_reaped=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool', type=Path,
        default=Path('/evidence/ap06-repo/tools/kartierung/metric_scope_vorbereiten.py'))
    parser.add_argument('--tf-probe', type=Path,
        default=Path('/evidence/ap06-tf-probe-build/tf_ownership_probe'))
    parser.add_argument('--install-root', type=Path,
        default=Path('/evidence/ap06-old-product-install'))
    parser.add_argument('--output-root', type=Path,
        default=Path('/evidence/ap06-concept-20261008/scope-ros-smoke'))
    args = parser.parse_args()
    require(Path('/.dockerenv').exists(), 'Run only in the existing device-free container')
    require(os.environ.get('AP06_SIMULATION') == '1', 'Explicit AP06_SIMULATION=1 required')
    require(os.environ.get('ROS_DOMAIN_ID') == '193', 'Dedicated smoke domain 193 required')
    require(os.environ.get('ROS_LOCALHOST_ONLY') == '1', 'ROS_LOCALHOST_ONLY=1 required')
    require(not any(Path(p).exists() for p in (
        '/dev/ttyUSB_BASE', '/dev/ttyUSB_HWT601', '/etc/nv_tegra_release')), 'Real-device environment forbidden')
    require(args.tool.is_file() and args.tf_probe.is_file(), 'Actual tool and built TF probe are required')
    args.output_root = args.output_root.resolve()
    require(not any((p/'.git').exists() for p in (args.output_root, *args.output_root.parents)),
            'Synthetic private files must remain outside every repository')
    args.output_root.mkdir(mode=0o700, exist_ok=False)
    result = dict(schema=1, created_utc=datetime.now(timezone.utc).isoformat(),
        synthetic=True, non_actuating=True, hardware_qualified=False,
        ros_domain_id=193, tool_sha256=sha(args.tool), tf_probe_sha256=sha(args.tf_probe),
        smoke_script_sha256=sha(__file__), cases=[], passed=False)
    result['child_inspection'] = 'Exact owned CLI children via proc task/children or proc stat PPid, with starttime identity against PID reuse'

    import rclpy
    from rclpy.node import Node
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    from rclpy.action import ActionServer, GoalResponse
    from geometry_msgs.msg import TransformStamped
    from nav_msgs.msg import OccupancyGrid
    from std_msgs.msg import String
    from tf2_msgs.msg import TFMessage
    from robot_interfaces.action import ExploreArea
    from explore.portal_source_adapter import raw_map_portal_source_from_values
    import yaml

    installed = {}
    for name in ('explore.portal_source_adapter', 'explore.map_status_adapter',
                 'explore.exploration_scope', 'explore.metric_frontier_runtime',
                 'amadeus_map_identity.fingerprint', 'robot_interfaces.action._explore_area'):
        path = Path(importlib.util.find_spec(name).origin).resolve()
        require(args.install_root.resolve() in path.parents, name+' is not from the actual built install')
        installed[name] = dict(path=str(path), sha256=sha(path))
    result['installed_modules'] = installed
    rclpy.init(args=[])
    executor = SingleThreadedExecutor()
    nodes, action = [], None
    try:
        mapper = Node('slam_toolbox')
        manager = Node('robot_map_manager')
        odom = Node('hwt601_mapping_ekf')
        nodes.extend((mapper, manager, odom))
        for node in nodes:
            executor.add_node(node)
        map_pub = mapper.create_publisher(OccupancyGrid, '/map', QoSProfile(depth=2,
            reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        status_pub = manager.create_publisher(String, '/robot_map_manager/status_json', 10)
        map_tf = mapper.create_publisher(TFMessage, '/tf', 100)
        odom_tf = odom.create_publisher(TFMessage, '/tf', 100)
        # This immutable grid is a labeled unit/integration fixture, never a
        # claimed real map and never published outside isolated domain 193.
        grid = OccupancyGrid()
        grid.header.frame_id = 'map'
        grid.info.width = grid.info.height = 16
        # Exact binary fraction survives OccupancyGrid's float32 resolution
        # unchanged; the fingerprint must match the received ROS message.
        grid.info.resolution = .125
        grid.info.origin.position.x = grid.info.origin.position.y = -1.
        grid.info.origin.orientation.w = 1.
        grid.data = [0]*256
        source = raw_map_portal_source_from_values(width=16, height=16,
            resolution=grid.info.resolution, frame_id='map', source_stamp_ns=1,
            origin=(-1., -1., 0., 0., 0., 0., 1.), cells=grid.data)
        scope = dict(schema_version=1, session_id='synthetic-scope-ros-smoke',
            scope_id='synthetic-lab-scope', frame_id='map', map_fingerprint=source.fingerprint,
            accessible_scope_verified=True, vertices=[[-.6,-.6],[.6,-.6],[.6,.6],[-.6,.6]])
        scope_path = args.output_root/'explicit-synthetic-scope.json'
        write_new_json(scope_path, scope)
        sample = dict(map_stamp_ns=0, last_map=-1., last_status=-1., observed_maps=0,
                      map_messages=0, status_messages=0, tf_messages=0)

        def publish():
            now = mapper.get_clock().now()
            steady = time.monotonic()
            if steady-sample['last_map'] >= .5:
                grid.header.stamp = now.to_msg()
                map_pub.publish(grid)
                sample.update(map_stamp_ns=now.nanoseconds, last_map=steady,
                    observed_maps=sample['observed_maps']+1, map_messages=sample['map_messages']+1)
            if steady-sample['last_status'] >= .15:
                status = dict(schema_version=1, time=now.nanoseconds/1e9,
                    map=dict(available=True, snapshot_available=True,
                        age_seconds=(now.nanoseconds-sample['map_stamp_ns'])/1e9,
                        summary=dict(fingerprint=source.fingerprint, frame_id='map',
                            source_stamp_ns=sample['map_stamp_ns'])),
                    counters=dict(accepted_maps=1, observed_maps=sample['observed_maps']))
                status_pub.publish(String(data=json.dumps(status)))
                sample.update(last_status=steady, status_messages=sample['status_messages']+1)
            transforms = []
            for parent, child, x, y in (('map','odom',.1,.1), ('odom','base_link',.15,-.1)):
                transform = TransformStamped()
                transform.header.frame_id, transform.child_frame_id = parent, child
                transform.header.stamp = now.to_msg()
                transform.transform.translation.x, transform.transform.translation.y = x, y
                transform.transform.rotation.w = 1.
                transforms.append(transform)
            map_tf.publish(TFMessage(transforms=[transforms[0]]))
            odom_tf.publish(TFMessage(transforms=[transforms[1]]))
            sample['tf_messages'] += 2

        timer = mapper.create_timer(.05, publish)
        spin_until(executor, lambda: sample['status_messages'] >= 5)
        # Discovery of any unrelated actor/source makes this domain unsuitable.
        allowed = {('slam_toolbox','/'), ('robot_map_manager','/'), ('hwt601_mapping_ekf','/')}
        graph = set(mapper.get_node_names_and_namespaces())
        require(graph <= allowed, 'Domain 193 already contains unrelated nodes: '+repr(graph-allowed))
        require(len(mapper.get_publishers_info_by_topic('/map')) == 1, 'Synthetic test must have only one map owner')
        proof_owners = dict(map=endpoint(mapper,'/map','/slam_toolbox'),
            manager=endpoint(mapper,'/robot_map_manager/status_json','/robot_map_manager'),
            map_odom=endpoint(mapper,'/tf','/slam_toolbox'),
            odom_base=endpoint(mapper,'/tf','/hwt601_mapping_ekf'))
        result['publisher_graph_before_cli'] = [dict(topic=topic,
            node_name=row.node_name, node_namespace=row.node_namespace,
            endpoint_gid=[int(value) for value in row.endpoint_gid])
            for topic in ('/map', '/robot_map_manager/status_json', '/tf')
            for row in mapper.get_publishers_info_by_topic(topic)]
        positive = args.output_root/'positive-private.yaml'
        command = [sys.executable, str(args.tool), '--scope', str(scope_path),
            '--output', str(positive), '--tf-probe', str(args.tf_probe),
            '--install-root', str(args.install_root), '--timeout', '12']
        case = run_cli(executor, command, args.output_root, 'positive')
        result['cases'].append(case)
        require(case['exit_code'] == 0, 'Positive real CLI failed; inspect its stdout/stderr')
        require(positive.is_file() and stat.S_IMODE(positive.stat().st_mode) == 0o600,
                'Positive profile missing or not mode 0600')
        text = positive.read_text()
        proof = json.loads(next(line.removeprefix('# binding: ') for line in text.splitlines()
                                if line.startswith('# binding: ')))
        params = yaml.safe_load(text)['explore_node']['ros__parameters']
        require(proof['owners'] == proof_owners, 'Native per-transform DDS GIDs differ from actual synthetic peers')
        require(proof['movement_authorized'] is False and proof['snapshot_only'] is True,
                'Profile must grant no movement authority')
        require(proof['map_fingerprint'] == source.fingerprint and proof['observed_maps'] >= 1,
                'Real CLI did not bind the actual synthetic map')
        require(abs(proof['pose']['translation'][0]-.25) < 1e-8
                and abs(proof['pose']['translation'][1]) < 1e-8, 'Actual TF composition mismatch')
        require(proof['pose']['stamp_ns'] == proof['map_odom']['stamp_ns'] > 0, 'TF timestamps not bound')
        require(params['metric_path_validation'] == 'conservative'
                and params['metric_session_id'] == scope['session_id']
                and params['metric_scope_map_fingerprint'] == source.fingerprint,
                'Profile lost the conservative scoped binding')
        stdout = Path(case['stdout']).read_text()
        require('ros2 launch explore explore.launch.py' in stdout
                and 'hwt601_active_drive:=false' in stdout
                and 'keine Mission oder Bewegung gestartet' in stdout, 'Passive launch display missing')
        require(case['observed_owned_children'], 'No native TF-observer child was observed')
        case.update(passed=True, profile=str(positive), profile_sha256=sha(positive),
            profile_mode='0600', native_dds_owner_match=True, passive_start_displayed=True)
        result['positive_binding'] = proof

        # Exclusive-output behavior is checked via the actual CLI, not merely
        # by calling its helper. It must preserve the first profile byte-for-byte.
        before = positive.read_bytes()
        exclusive = run_cli(executor, command, args.output_root, 'exclusive-existing-output')
        result['cases'].append(exclusive)
        require(exclusive['exit_code'] == 1 and positive.read_bytes() == before,
                'CLI did not reject an existing output without overwriting it')
        require('new filename' in Path(exclusive['stderr']).read_text(), 'Unexpected exclusive-output failure')
        exclusive['passed'] = True

        # Negative: a renamed, non-actuating synthetic action endpoint. It is
        # not Explorer, accepts no goal and contains no navigation/driver peer.
        fake_action = Node('synthetic_reject_all_explore_endpoint')
        nodes.append(fake_action); executor.add_node(fake_action)
        goal_requests = []
        def reject_goal(_):
            goal_requests.append(time.monotonic())
            return GoalResponse.REJECT
        def never_execute(_):
            raise AssertionError('Synthetic endpoint must never execute a goal')
        action = ActionServer(fake_action, ExploreArea, '/synthetic/explore_area',
            execute_callback=never_execute, goal_callback=reject_goal)
        spin_until(executor, lambda: any(name == '/synthetic/explore_area/_action/send_goal'
                   for name, _ in mapper.get_service_names_and_types()))
        negative = args.output_root/'negative-forbidden.yaml'
        blocked_command = list(command)
        blocked_command[blocked_command.index('--output')+1] = str(negative)
        blocked = run_cli(executor, blocked_command, args.output_root, 'negative-existing-action')
        result['cases'].append(blocked)
        require(blocked['exit_code'] == 1 and not negative.exists(),
                'Existing ExploreArea endpoint did not prevent file creation')
        require('Explorer/ExploreArea owner already exists' in Path(blocked['stderr']).read_text(),
                'Negative CLI failed for an unrelated reason')
        require(not goal_requests, 'The preparation CLI unexpectedly sent an action goal')
        blocked.update(passed=True, no_profile_created=True, no_action_goal_received=True)
        action.destroy(); action = None
        executor.remove_node(fake_action); fake_action.destroy_node(); nodes.remove(fake_action)
        spin_until(executor, lambda: all(name not in ('ap06_tf_ownership_probe',)
            and not name.startswith('metric_scope_prepare_')
            for name, _ in mapper.get_node_names_and_namespaces()))
        result['producer_summary'] = dict(sample, map_publishers=1,
            map_qos=dict(depth=2, reliability='RELIABLE', durability='TRANSIENT_LOCAL'),
            test_input_only=True, velocity_publishers=0, accepted_action_goals=0)
        result['cleanup'] = dict(cli_and_native_probe_absent_from_graph=True,
                                 all_observed_owned_children_reaped=True)
        result['passed'] = True
    except BaseException as error:
        result['error'] = f'{type(error).__name__}: {error}'
        result['traceback'] = traceback.format_exc()
        raise
    finally:
        if action is not None:
            action.destroy()
        for node in reversed(nodes):
            executor.remove_node(node); node.destroy_node()
        executor.shutdown()
        if rclpy.ok():
            rclpy.shutdown()
        result['all_synthetic_nodes_destroyed'] = True
        write_new_json(args.output_root/'result.json', result)
    print(json.dumps(dict(passed=result['passed'], cases=len(result['cases']),
                         result=str(args.output_root/'result.json'))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
