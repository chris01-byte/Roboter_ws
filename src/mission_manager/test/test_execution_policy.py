import ast
from pathlib import Path
import unittest

from mission_manager.execution_policy import (
    effective_real_types,
    execution_mode,
    go_to_room_execution_status,
    pick_and_place_room_allowed,
)


class ExecutionPolicyTests(unittest.TestCase):
    def test_go_to_room_is_removed_from_configured_real_types(self):
        self.assertEqual(
            effective_real_types(['explore', 'go_to_room']),
            {'explore'},
        )

    def test_go_to_room_remains_simulated_even_with_bad_runtime_set(self):
        self.assertEqual(execution_mode('go_to_room', {'go_to_room'}), 'sim')

    def test_room_navigation_status_requires_explicit_opt_in(self):
        self.assertEqual(
            go_to_room_execution_status(False),
            'simulation_only_no_navigation',
        )
        self.assertEqual(
            go_to_room_execution_status(True),
            'nav2_explicit_opt_in',
        )

    def test_existing_action_types_remain_real(self):
        self.assertEqual(execution_mode('explore', {'explore'}), 'real')
        self.assertEqual(execution_mode('pick_object', {'explore'}), 'sim')

    def test_simulation_path_contains_no_navigation_or_velocity_command(self):
        node_path = (
            Path(__file__).resolve().parents[1]
            / 'mission_manager' / 'mission_manager_node.py')
        source = node_path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        functions = {
            node.name: node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        sim_source = ast.get_source_segment(source, functions['_start_sim_mission'])
        self.assertNotIn('send_goal_async', sim_source)
        self.assertNotIn('_start_real_mission', sim_source)
        self.assertNotIn("'/cmd_vel", source)

    def test_real_room_navigation_is_default_off_and_separately_guarded(self):
        node_path = (
            Path(__file__).resolve().parents[1]
            / 'mission_manager' / 'mission_manager_node.py')
        source = node_path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        functions = {
            node.name: node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        init_source = ast.get_source_segment(source, functions['__init__'])
        command_source = ast.get_source_segment(source, functions['_on_command'])
        nav_source = ast.get_source_segment(
            source, functions['_start_room_navigation'])
        self.assertIn(
            "declare_parameter('enable_real_go_to_room', False)", init_source)
        self.assertIn(
            "declare_parameter('go_to_room_behavior_tree', '')", init_source)
        self.assertIn(
            "command_type == 'go_to_room' and self.enable_real_go_to_room",
            command_source)
        self.assertIn('NavigateToPose.Goal()', nav_source)
        self.assertIn('goal.behavior_tree = self.go_to_room_behavior_tree', nav_source)
        self.assertIn('send_goal_async', nav_source)
        self.assertNotIn('cmd_vel', nav_source)

    def test_semantic_rooms_do_not_expand_real_pick_and_place_allowlist(self):
        configured = ('Wohnzimmer', 'Kueche')
        self.assertTrue(pick_and_place_room_allowed('Kueche', configured))
        self.assertFalse(pick_and_place_room_allowed('Neuer Raum', configured))
        self.assertFalse(pick_and_place_room_allowed(None, configured))

    def test_semantic_snapshot_timeout_is_wired_into_timer_and_validation(self):
        node_path = (
            Path(__file__).resolve().parents[1]
            / 'mission_manager' / 'mission_manager_node.py')
        source = node_path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        functions = {
            node.name: node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        timer_source = ast.get_source_segment(source, functions['_timer_tick'])
        validation_source = ast.get_source_segment(source, functions['_validate_command'])
        self.assertIn('_expire_semantic_snapshot_if_stale()', timer_source)
        self.assertIn('_expire_semantic_snapshot_if_stale()', validation_source)
        self.assertIn('_semantic_snapshot_received_monotonic', source)


if __name__ == '__main__':
    unittest.main()
