"""Integration contract for clean Humble shutdown entry points."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ENTRYPOINTS = (
    REPO_ROOT / 'src/mission_manager/mission_manager/mission_manager_node.py',
    REPO_ROOT / (
        'src/semantic_map_manager/semantic_map_manager/'
        'semantic_map_manager_node.py'),
    REPO_ROOT / 'src/safety_monitor/safety_monitor/safety_monitor_node.py',
    REPO_ROOT / (
        'src/amadeus_lidar_bringup/amadeus_lidar_bringup/'
        'scan_vereinheitlichen.py'),
    REPO_ROOT / 'src/base_hardware/base_hardware/base_hardware_node.py',
    REPO_ROOT / (
        'src/vl53_near_field/vl53_near_field/'
        'vl53_near_field_node.py'),
)


def test_python_stack_entrypoints_only_suppress_invalid_shutdown_context():
    for path in ENTRYPOINTS:
        source = path.read_text(encoding='utf-8')
        main_source = source[source.index('\ndef main('):]
        assert 'ExternalShutdownException' in source, path
        assert (
            'except (KeyboardInterrupt, ExternalShutdownException):'
            in main_source
        ), path
        assert 'except RuntimeError:' in main_source, path
        assert 'if rclpy.ok():\n            raise' in main_source, path
        assert 'if rclpy.ok():\n            rclpy.shutdown()' in main_source, path
