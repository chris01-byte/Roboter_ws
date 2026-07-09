from setuptools import setup
import os
from glob import glob

# =====================================================================
#  setup.py - mission_manager (WP-4)
# =====================================================================
package_name = 'mission_manager'

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
    description='Mission Manager fuer Smartphone-GUI und Behavior-Tree-Auftraege.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'mission_manager = mission_manager.mission_manager_node:main',
        ],
    },
)
