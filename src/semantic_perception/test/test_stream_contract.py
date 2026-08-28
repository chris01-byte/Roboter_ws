import ast
from pathlib import Path
import unittest
import xml.etree.ElementTree as ElementTree

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT.parent


class SemanticStreamContractTests(unittest.TestCase):
    def test_server_defaults_use_only_compressed_semantic_topics(self):
        config = yaml.safe_load(
            (PACKAGE_ROOT / 'config' / 'semantic_perception_params.yaml')
            .read_text(encoding='utf-8'))[
                'semantic_perception']['ros__parameters']

        self.assertTrue(config['compressed_input'])
        self.assertEqual(
            config['rgb_topic'], '/oak/semantic/rgb/compressed')
        self.assertEqual(
            config['depth_topic'], '/oak/semantic/depth/compressed')
        self.assertNotIn('image_rect', config['rgb_topic'])
        self.assertLessEqual(config['max_rgb_depth_skew_s'], 0.20)
        self.assertGreaterEqual(config['input_pair_queue_size'], 2)
        self.assertLessEqual(config['input_pair_queue_size'], 120)

    def test_relay_is_started_by_oak_launch_and_can_be_disabled(self):
        launch_path = (
            SOURCE_ROOT / 'robot_bringup' / 'launch' / 'oak.launch.py')
        source = launch_path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        strings = {
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }

        self.assertIn('semantic_relay', strings)
        self.assertIn('semantic_stream_relay', strings)
        self.assertIn('semantic_stream_relay_params.yaml', strings)
        self.assertIn('oak_rectifier', strings)
        self.assertIn('external_rectifier', strings)
        self.assertIn('false', strings)
        self.assertIn("'rectify_rgb': 'false'", source)
        self.assertIn("executable='oak_rectifier'", source)

    def test_oak_profiles_set_real_isp_output_scale(self):
        main_params = yaml.safe_load(
            (SOURCE_ROOT / 'robot_bringup' / 'config' / 'oak_params.yaml')
            .read_text(encoding='utf-8'))['/oak']['ros__parameters']
        slam_params = yaml.safe_load(
            (SOURCE_ROOT / 'robot_bringup' / 'config' / 'oak_params_slam.yaml')
            .read_text(encoding='utf-8'))['/oak']['ros__parameters']

        self.assertEqual(
            (main_params['rgb']['i_isp_num'],
             main_params['rgb']['i_isp_den']),
            (1, 6))
        self.assertEqual(
            (slam_params['rgb']['i_isp_num'],
             slam_params['rgb']['i_isp_den']),
            (1, 3))
        for params in (main_params, slam_params):
            self.assertNotIn('pipeline_gen', params)
            self.assertNotIn('i_synced', params['rgb'])
            self.assertNotIn('i_synced', params['stereo'])
            self.assertEqual(params['rgb']['i_fps'], 10.0)
            self.assertEqual(params['left']['i_fps'], 10.0)
            self.assertEqual(params['right']['i_fps'], 10.0)

        relay = yaml.safe_load(
            (PACKAGE_ROOT / 'config' / 'semantic_stream_relay_params.yaml')
            .read_text(encoding='utf-8'))[
                'semantic_stream_relay']['ros__parameters']
        self.assertGreaterEqual(relay['max_input_age_s'], 2.0)
        self.assertGreaterEqual(relay['frame_queue_size'], 60)
        self.assertLessEqual(relay['input_stall_timeout_s'], 3.0)
        self.assertGreaterEqual(
            relay['subscription_restart_cooldown_s'],
            relay['input_stall_timeout_s'])

    def test_detail_profile_is_hd_bounded_and_separate(self):
        detail = yaml.safe_load(
            (SOURCE_ROOT / 'robot_bringup' / 'config' /
             'oak_params_detail.yaml').read_text(encoding='utf-8'))[
                 '/oak']['ros__parameters']
        relay = yaml.safe_load(
            (PACKAGE_ROOT / 'config' /
             'semantic_stream_relay_detail_params.yaml').read_text(
                 encoding='utf-8'))[
                     'semantic_stream_relay']['ros__parameters']
        launch_source = (
            SOURCE_ROOT / 'robot_bringup' / 'launch' /
            'oak_detail.launch.py').read_text(encoding='utf-8')

        self.assertEqual(
            (detail['rgb']['i_isp_num'], detail['rgb']['i_isp_den']),
            (2, 3))
        self.assertEqual(
            (detail['rgb']['i_width'], detail['rgb']['i_height']),
            (1280, 720))
        self.assertEqual(detail['rgb']['i_fps'], 5.0)
        self.assertEqual(detail['stereo']['i_width'], 1280)
        self.assertEqual(detail['stereo']['i_height'], 720)
        self.assertLessEqual(relay['publish_rate_hz'], 1.0)
        self.assertEqual(relay['profile_name'], 'detail_hd')
        self.assertIn('oak_params_detail.yaml', launch_source)
        self.assertIn('semantic_stream_relay_detail_params.yaml', launch_source)
        self.assertIn("'pointcloud': 'false'", launch_source)
        self.assertIn("'maximum_runtime_s'", launch_source)
        self.assertIn('TimerAction', launch_source)

    def test_bringup_declares_external_rectifier_dependencies(self):
        root = ElementTree.parse(
            SOURCE_ROOT / 'robot_bringup' / 'package.xml').getroot()
        dependencies = {
            element.text.strip()
            for element in root.findall('depend') + root.findall('exec_depend')
            if element.text
        }

        self.assertIn('depthai_ros_driver', dependencies)
        self.assertIn('depth_image_proc', dependencies)
        self.assertIn('cv_bridge', dependencies)
        self.assertIn('sensor_msgs', dependencies)
        self.assertIn('python3-opencv', dependencies)

    def test_runtime_dependencies_cover_codec_and_ros_conversion(self):
        root = ElementTree.parse(PACKAGE_ROOT / 'package.xml').getroot()
        dependencies = {
            element.text.strip()
            for element in root.findall('depend') + root.findall('exec_depend')
            if element.text
        }

        self.assertIn('cv_bridge', dependencies)
        self.assertIn('python3-opencv', dependencies)


if __name__ == '__main__':
    unittest.main()
