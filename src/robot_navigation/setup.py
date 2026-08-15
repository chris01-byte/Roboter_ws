import os
from glob import glob
from setuptools import setup

package_name = 'robot_navigation'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'maps'), glob('maps/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='QTG0900',
    maintainer_email='qtg0900@example.com',
    description='Nav2-Konfiguration + Testkarte: echte Navigation ohne Hardware (virtuelle Basis).',
    license='MIT',
    entry_points={
        'console_scripts': [
            'cmd_vel_mission_gate = '
            'robot_navigation.cmd_vel_mission_gate:main',
        ],
    },
)
