from setuptools import setup
import os
from glob import glob

# =====================================================================
#  setup.py - explore (WP-5 Ebene 1: autonome Frontier-Exploration)
# =====================================================================
package_name = 'explore'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'behavior_trees'),
         glob('behavior_trees/*.xml')),
    ],
    install_requires=['setuptools'],
    tests_require=['pytest'],
    zip_safe=True,
    maintainer='QTG0900',
    maintainer_email='qtg0900@example.com',
    description='Autonome Frontier-basierte Wohnungs-Erkundung ueber Nav2 (WP-5 Ebene 1).',
    license='MIT',
    entry_points={
        'console_scripts': [
            'explore = explore.explore_node:main',
        ],
    },
)
