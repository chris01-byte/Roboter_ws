from setuptools import setup
import os
from glob import glob

# =====================================================================
#  setup.py - llm_planner (WP-5 Baustein C: Sprache -> Missionsauftrag)
# =====================================================================
package_name = 'llm_planner'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='QTG0900',
    maintainer_email='qtg0900@example.com',
    description='LLM-Aufgabenplaner: natuerliche Sprache -> mission_manager command_json (WP-5 Baustein C).',
    license='MIT',
    entry_points={
        'console_scripts': [
            'llm_planner = llm_planner.llm_planner_node:main',
        ],
    },
)
