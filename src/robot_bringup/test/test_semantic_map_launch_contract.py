import ast
from pathlib import Path
import unittest
import xml.etree.ElementTree as ElementTree


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class SemanticMapLaunchContractTests(unittest.TestCase):
    def test_robot_launch_declares_passive_semantic_map_include(self):
        launch_path = PACKAGE_ROOT / 'launch' / 'robot.launch.py'
        source = launch_path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        strings = {
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertIn('start_semantic_map_manager', strings)
        self.assertIn('semantic_map_manager', strings)
        self.assertIn('semantic_map_manager.launch.py', strings)
        self.assertNotIn('/cmd_vel', strings)
        self.assertNotIn('/navigate_to_pose', strings)

    def test_package_declares_runtime_dependency(self):
        root = ElementTree.parse(PACKAGE_ROOT / 'package.xml').getroot()
        dependencies = {
            element.text.strip() for element in root.findall('exec_depend')
            if element.text
        }
        self.assertIn('semantic_map_manager', dependencies)


if __name__ == '__main__':
    unittest.main()
