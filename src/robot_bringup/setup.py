from setuptools import setup
import os
from glob import glob

# =====================================================================
#  setup.py - robot_bringup (WP-5 Baustein D: Onboard/Offboard-Start)
# =====================================================================
package_name = 'robot_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='QTG0900',
    maintainer_email='qtg0900@example.com',
    description='Onboard/Offboard-Deployment und Server-Erreichbarkeits-Monitor (WP-5 Baustein D).',
    license='MIT',
    entry_points={
        'console_scripts': [
            'link_monitor = robot_bringup.link_monitor_node:main',
        ],
    },
)
