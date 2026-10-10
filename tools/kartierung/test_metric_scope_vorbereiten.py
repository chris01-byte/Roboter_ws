"""Offline behavioral checks; all maps/poses here are synthetic fixtures."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'src/explore'), str(ROOT/'src/amadeus_map_identity')]
SPEC = importlib.util.spec_from_file_location('metric_scope_vorbereiten', Path(__file__).with_name('metric_scope_vorbereiten.py'))
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


def publisher(name, n):
    return tool.owner(name, [n]+[0]*23)


MAP_OWNER = publisher('/slam_toolbox', 1)
MANAGER_OWNER = publisher('/robot_map_manager', 2)
ODOM_OWNER = publisher('/hwt601_mapping_ekf', 3)


def grid(**changes):
    values = dict(width=4, height=4, resolution=1., frame_id='map', source_stamp_ns=99_000_000_000,
        origin=(-2., -2., 0., 0., 0., 0., 1.), cells=[0]*16)
    values.update(changes)
    return values


def document():
    return dict(schema_version=1, session_id='synthetic-session', scope_id='synthetic-lab',
        frame_id='map', map_fingerprint=tool.raw_map_portal_source_from_values(**grid()).fingerprint,
        accessible_scope_verified=True, vertices=[[-1., -1.], [1., -1.], [1., 1.], [-1., 1.]])


def status(**changes):
    payload = dict(schema_version=1, time=99.5,
        map=dict(available=True, snapshot_available=True, age_seconds=.2,
            summary=dict(fingerprint=document()['map_fingerprint'], frame_id='map', source_stamp_ns=99_000_000_000)),
        counters=dict(accepted_maps=2, observed_maps=3))
    payload.update(changes)
    return payload


def pose(child='base_link', **changes):
    value = dict(parent='map', child=child, stamp_ns=99_500_000_000,
        translation=[0., 0., 0.], rotation=[0., 0., 0., 1.])
    value.update(changes)
    return value


def ready():
    binding = tool.ScopeBinding(document())
    binding.accept_map(grid(), 10., MAP_OWNER)
    binding.accept_status(json.dumps(status(time=99.4)), 10., MANAGER_OWNER)
    binding.accept_status(json.dumps(status()), 10.1, MANAGER_OWNER)
    return binding


def snapshot(binding, **changes):
    values = dict(ros_now_ns=100_000_000_000, monotonic_now=10.2, pose=pose(), reference=pose('odom'),
        tf_owners=dict(map_odom=MAP_OWNER, odom_base=ODOM_OWNER))
    values.update(changes)
    return binding.snapshot(**values)


class ScopeDocumentTests(unittest.TestCase):
    def test_capacity_is_explicit_bounded_and_preserves_actual_grid(self):
        values = grid(width=8, height=8, cells=[-1]*63+[100])
        doc = document()
        doc['map_fingerprint'] = tool.raw_map_portal_source_from_values(**values).fingerprint
        with self.assertRaisesRegex(ValueError, 'evidence limit'):
            tool.ScopeBinding(doc, maximum_cells=16).accept_map(values, 10., MAP_OWNER)
        binding = tool.ScopeBinding(doc, maximum_cells=64)
        binding.accept_map(values, 10., MAP_OWNER)
        params = binding.parameters({'explore_node': {'ros__parameters': {}}})['explore_node']['ros__parameters']
        self.assertEqual(params['wohnungserkundung_evidence_max_cells'], 64)
        self.assertEqual(params['metric_scope_map_fingerprint'], doc['map_fingerprint'])
        self.assertEqual(values['cells'], [-1]*63+[100])
        for invalid in (True, 0, -1, 4_000_001, 64.):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                tool.ScopeBinding(doc, maximum_cells=invalid)

    def test_exact_existing_scope_and_context_contract(self):
        value, scope = tool.scope_document(json.dumps(document()))
        self.assertEqual(scope.context.session_id, value['session_id'])
        self.assertEqual(scope.context.map_id, 'map-'+value['map_fingerprint'])
        self.assertEqual([(p.x, p.y) for p in scope.vertices], [tuple(p) for p in value['vertices']])

    def test_malformed_scope_never_invents_permission(self):
        cases = [('accessible_scope_verified', False), ('accessible_scope_verified', 1),
            ('vertices', []), ('vertices', [[0, 0], [1, 1], [0, 1], [1, 0]]),
            ('vertices', [[0, 0], [True, 1], [0, 1]]), ('vertices', [[0, 0], [float('nan'), 1], [0, 1]]),
            ('session_id', ''), ('scope_id', 'bad/id'), ('frame_id', '/map'), ('map_fingerprint', 'bad')]
        for key, value in cases:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                tool.scope_document(json.dumps({**document(), key: value}))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            tool.scope_document('{"schema_version":1,"schema_version":1}')
        with self.assertRaises(ValueError):
            tool.scope_document(json.dumps({**document(), 'inferred_map_bounds': True}))

    def test_output_keeps_installed_metric_profile_but_uses_conservative_binding(self):
        profile = yaml.safe_load((ROOT/'src/explore/config/metric_frontier_params.yaml').read_text())
        before = copy.deepcopy(profile)
        result = ready().parameters(profile)['explore_node']['ros__parameters']
        self.assertEqual(profile, before)
        self.assertEqual(result['exploration_strategy'], 'metric_frontier')
        self.assertEqual(result['metric_session_id'], document()['session_id'])
        self.assertEqual(result['metric_scope_map_fingerprint'], document()['map_fingerprint'])
        self.assertEqual(result['wohnungserkundung_scope_polygon_xy'], [-1., -1., 1., -1., 1., 1., -1., 1.])
        self.assertEqual(result['metric_path_validation'], 'conservative')
        self.assertFalse(result['metric_resume_saved_state'])
        self.assertNotIn('nav_departure_alignment_tolerance_rad', result)


class LiveBindingTests(unittest.TestCase):
    def test_valid_exact_pair_and_real_pose_produce_no_motion_authorization(self):
        proof = snapshot(ready())
        self.assertEqual(proof['map_fingerprint'], document()['map_fingerprint'])
        self.assertEqual(proof['source_stamp_ns'], 99_000_000_000)
        self.assertEqual(proof['scope_fingerprint'], ready().scope.fingerprint)
        self.assertFalse(proof['movement_authorized'])
        self.assertEqual(proof['owners']['odom_base'], ODOM_OWNER)

    def test_only_one_status_observation_is_not_sufficient(self):
        binding = tool.ScopeBinding(document())
        binding.accept_map(grid(), 10., MAP_OWNER)
        binding.accept_status(json.dumps(status()), 10., MANAGER_OWNER)
        with self.assertRaises(tool.BindingPending):
            snapshot(binding)

    def test_equal_fingerprint_but_different_stamp_waits_for_exact_pair(self):
        binding = ready()
        binding.accept_map(grid(source_stamp_ns=99_100_000_000), 10.15, MAP_OWNER)
        with self.assertRaisesRegex(tool.BindingPending, 'exact pair'):
            snapshot(binding)
        current = status(time=99.6)
        current['map']['summary']['source_stamp_ns'] = 99_100_000_000
        current['counters']['observed_maps'] = 4
        binding.accept_status(json.dumps(current), 10.18, MANAGER_OWNER)
        self.assertEqual(snapshot(binding)['source_stamp_ns'], 99_100_000_000)

    def test_occupancy_or_scope_fingerprint_changes_reject(self):
        with self.assertRaisesRegex(ValueError, 'map changed'):
            ready().accept_map(grid(cells=[100]+[0]*15), 10.2, MAP_OWNER)
        changed = status()
        changed['map']['summary']['fingerprint'] = 'f'*64
        with self.assertRaisesRegex(ValueError, 'manager map changed'):
            ready().accept_status(json.dumps(changed), 10.2, MANAGER_OWNER)

    def test_epoch_resets_and_backwards_status_are_not_hidden_by_latest_value(self):
        for mutate in (
            lambda p: p['counters'].update(accepted_maps=1),
            lambda p: p['counters'].update(observed_maps=2),
            lambda p: p.update(time=99.3),
            lambda p: p['map']['summary'].update(source_stamp_ns=98_000_000_000),
            lambda p: p['map']['summary'].update(frame_id='other')):
            binding, value = ready(), status()
            mutate(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                binding.accept_status(json.dumps(value), 10.2, MANAGER_OWNER)

    def test_raw_zero_stamp_rejects_but_late_same_source_history_does_not_refresh(self):
        with self.assertRaises(ValueError):
            ready().accept_map(grid(source_stamp_ns=0), 10.2, MAP_OWNER)
        binding = ready()
        before = binding.raw
        binding.accept_map(grid(source_stamp_ns=98_000_000_000), 10.2, MAP_OWNER)
        self.assertEqual(binding.raw, before)
        self.assertEqual(snapshot(binding)['source_stamp_ns'], 99_000_000_000)

    def test_status_payload_age_includes_transport_time(self):
        delayed = status(time=96.)
        delayed['map']['summary']['source_stamp_ns'] = 96_000_000_000
        delayed['map']['age_seconds'] = 2.
        binding = tool.ScopeBinding(document())
        binding.accept_map(grid(source_stamp_ns=96_000_000_000), 10., MAP_OWNER)
        binding.accept_status(json.dumps(delayed), 10., MANAGER_OWNER)
        binding.accept_status(json.dumps(delayed), 10.1, MANAGER_OWNER)
        with self.assertRaisesRegex(ValueError, 'including status transport'):
            snapshot(binding)

    def test_receipt_ros_time_and_tf_freshness_are_each_required(self):
        cases = [dict(monotonic_now=16.), dict(monotonic_now=9.), dict(ros_now_ns=106_000_000_000),
            dict(ros_now_ns=99_000_000_000), dict(pose=pose(stamp_ns=99_000_000_000), reference=pose('odom', stamp_ns=99_000_000_000)),
            dict(pose=pose(stamp_ns=0), reference=pose('odom', stamp_ns=0)),
            dict(reference=pose('odom', stamp_ns=99_400_000_000)),
            dict(pose=pose(rotation=[0., .1, 0., 1.])), dict(pose=pose(rotation=[0., 0., 0., 2.])),
            dict(pose=pose(translation=[float('nan'), 0., 0.])), dict(reference=pose('other'))]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                snapshot(ready(), **changes)

    def test_pose_outside_explicit_scope_cannot_expand_it(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            snapshot(ready(), pose=pose(translation=[1.5, 0., 0.]))

    def test_old_tf_remains_pending_until_actual_fresh_sample_arrives(self):
        binding = ready()
        with self.assertRaises(tool.BindingPending):
            snapshot(binding, pose=pose(stamp_ns=99_000_000_000),
                     reference=pose('odom', stamp_ns=99_000_000_000))
        # Same unchanged limits and owners; no restamping the old sample.
        proof = snapshot(binding)
        self.assertEqual(proof['pose']['stamp_ns'], 99_500_000_000)

    def test_names_and_same_name_restarted_publishers_both_fail(self):
        for kind, actual in [('map', publisher('/other_slam', 1)), ('map', publisher('/slam_toolbox', 9)),
                            ('manager', publisher('/robot_map_manager', 9))]:
            with self.subTest(kind=kind, actual=actual), self.assertRaises(ValueError):
                ready().check_owner(kind, actual)
        binding = ready()
        snapshot(binding)
        with self.assertRaisesRegex(ValueError, 'changed'):
            snapshot(binding, tf_owners=dict(map_odom=MAP_OWNER, odom_base=publisher('/hwt601_mapping_ekf', 8)))

    def test_native_tf_gid_joins_actual_endpoint_not_guessed_name(self):
        evidence = {('map', 'odom'): {tuple(MAP_OWNER['gid'])}, ('odom', 'base_link'): {tuple(ODOM_OWNER['gid'])}}
        self.assertEqual(tool.tf_pair_owners(evidence, [MAP_OWNER, ODOM_OWNER], 'map'),
            dict(map_odom=MAP_OWNER, odom_base=ODOM_OWNER))
        with self.assertRaises(tool.BindingPending):
            tool.tf_pair_owners(evidence, [MAP_OWNER], 'map')
        evidence[('odom', 'base_link')].add(tuple(MANAGER_OWNER['gid']))
        with self.assertRaisesRegex(ValueError, 'multiple dynamic TF owners'):
            tool.tf_pair_owners(evidence, [MAP_OWNER, ODOM_OWNER, MANAGER_OWNER], 'map')

    def test_missing_and_ambiguous_graph_owners_fail(self):
        with self.assertRaises(tool.BindingPending):
            tool.single_owner([], '/map')
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            tool.single_owner([MAP_OWNER, MAP_OWNER], '/map')
        for name, gid in [('slam_toolbox', [1]*24), ('/slam_toolbox', [0]*24), ('/slam_toolbox', [1])]:
            with self.subTest(name=name, gid=gid), self.assertRaises(ValueError):
                tool.owner(name, gid)

    def test_actual_humble_discovery_placeholder_waits_then_resolves_same_gid(self):
        # Recorded device-free ROS smoke: the fresh CLI knows the /map DDS GID
        # before its ROS node metadata, while the producer graph already knows it.
        gid = [1, 15, 127, 1, 74, 200, 124, 46, 0, 0, 0, 0, 0, 0, 45, 3, 0, 0, 0, 0, 0, 0, 0, 0]
        row = SimpleNamespace(node_name='_NODE_NAME_UNKNOWN_',
            node_namespace='_NODE_NAMESPACE_UNKNOWN_', endpoint_gid=gid)
        binding = tool.ScopeBinding(document())
        with self.assertRaisesRegex(tool.BindingPending, 'name discovery pending'):
            tool.graph_owners([row], '/map', require_single=True)
        self.assertEqual(binding.owners, {})
        self.assertIsNone(binding.raw)
        row.node_name, row.node_namespace = 'slam_toolbox', '/'
        values = tool.graph_owners([row], '/map', require_single=True)
        binding.accept_map(grid(), 10., tool.single_owner(values, '/map'))
        self.assertEqual(binding.owners['map'], dict(node='/slam_toolbox', gid=gid))
        self.assertEqual(binding.raw[0].fingerprint, document()['map_fingerprint'])

    def test_unresolved_names_do_not_hide_multiple_endpoints(self):
        unknown = SimpleNamespace(node_name='_NODE_NAME_UNKNOWN_',
            node_namespace='_NODE_NAMESPACE_UNKNOWN_', endpoint_gid=MAP_OWNER['gid'])
        known = SimpleNamespace(node_name='slam_toolbox', node_namespace='/', endpoint_gid=MAP_OWNER['gid'])
        for topic in ('/map', '/robot_map_manager/status_json'):
            with self.subTest(topic=topic), self.assertRaisesRegex(ValueError, 'ambiguous') as error:
                tool.graph_owners([unknown, known], topic, require_single=True)
            self.assertNotIsInstance(error.exception, tool.BindingPending)

    def test_other_bad_names_and_known_foreign_owners_are_hard_errors(self):
        for name, namespace in [('slam_toolbox', 'bad_namespace'), ('bad-name', '/'),
                                ('/slam_toolbox', '/'), ('unknown', '/'), ('slam_toolbox', '/foreign')]:
            row = SimpleNamespace(node_name=name, node_namespace=namespace, endpoint_gid=MAP_OWNER['gid'])
            with self.subTest(name=name, namespace=namespace), self.assertRaises(ValueError) as error:
                actual = tool.single_owner(tool.graph_owners([row], '/map', require_single=True), '/map')
                ready().check_owner('map', actual)
            self.assertNotIsInstance(error.exception, tool.BindingPending)

    def test_existing_explorer_even_namespaced_or_renamed_is_rejected(self):
        for nodes, services, topics in [([('explore_node', '/robot')], [], []),
                ([], [('/robot/explore_area/_action/send_goal', [])], []),
                ([], [], [('/robot/explore_area/_action/status', [])])]:
            self.assertTrue(tool.explorer_exists(nodes, services, topics))
            with self.assertRaisesRegex(ValueError, 'already exists'):
                snapshot(ready(), explorer_present=tool.explorer_exists(nodes, services, topics))
        self.assertFalse(tool.explorer_exists([('slam_toolbox', '/')], [], []))


class PrivateOutputTests(unittest.TestCase):
    def test_new_profile_is_private_auditable_and_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'private.yaml'
            proof = snapshot(ready())
            parameters = ready().parameters(yaml.safe_load((ROOT/'src/explore/config/metric_frontier_params.yaml').read_text()))
            tool.write_private_profile(target, parameters, proof, ROOT)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertEqual(yaml.safe_load(target.read_text()), parameters)
            self.assertIn('"movement_authorized": false', target.read_text())
            before = target.read_bytes()
            with self.assertRaises(FileExistsError):
                tool.write_private_profile(target, {}, {}, ROOT)
            self.assertEqual(target.read_bytes(), before)

    def test_any_git_checkout_and_symlink_into_it_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)/'other-checkout'
            checkout.mkdir(); (checkout/'.git').write_text('gitdir: elsewhere')
            link = Path(directory)/'link'
            link.symlink_to(checkout, target_is_directory=True)
            for target in (ROOT/'private.yaml', checkout/'private.yaml', link/'private.yaml'):
                with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'outside every Git'):
                    tool.write_private_profile(target, {}, {}, ROOT)
                self.assertFalse(target.exists())

    def test_changed_scope_or_probe_bytes_cannot_receive_old_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'scope.json'
            original = json.dumps(document()).encode()
            path.write_bytes(original)
            self.assertEqual(tool.unchanged_file(path, original), hashlib.sha256(original).hexdigest())
            path.write_bytes(original+b' ')
            with self.assertRaisesRegex(ValueError, 'changed during binding'):
                tool.unchanged_file(path, original)


class InstalledIdentityTests(unittest.TestCase):
    def test_installed_profiles_are_loaded_once_and_bound_to_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root/'explore/share/explore/config'
            config.mkdir(parents=True)
            for name in ('metric_frontier_params.yaml', 'explore_params.yaml'):
                (config/name).write_bytes((ROOT/'src/explore/config'/name).read_bytes())
            runtime = root/'explore/lib/python3.10/site-packages/explore/metric_frontier_runtime.py'
            runtime.parent.mkdir(parents=True)
            runtime.write_bytes(b'# synthetic installed identity fixture\n')
            profile, base, identity, snapshots = tool.installed_inputs(root, config, {'runtime': runtime})
            self.assertEqual(profile['explore_node']['ros__parameters']['exploration_strategy'], 'metric_frontier')
            self.assertEqual(base['door_localization_timeout_s'], .8)
            self.assertEqual(identity['runtime']['path'], str(runtime))
            self.assertEqual(identity['runtime']['sha256'], hashlib.sha256(runtime.read_bytes()).hexdigest())
            path = config/'metric_frontier_params.yaml'
            path.write_bytes(path.read_bytes()+b'\n# changed during observation\n')
            with self.assertRaisesRegex(ValueError, 'changed during binding'):
                tool.unchanged_file(path, snapshots[path])

    def test_old_or_source_overlay_is_rejected_before_ros_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'outside the explicit installed release'):
                tool.installed_inputs(Path(directory), ROOT/'src/explore/config',
                    {'runtime': ROOT/'src/explore/explore/metric_frontier_runtime.py'})


if __name__ == '__main__':
    unittest.main()
