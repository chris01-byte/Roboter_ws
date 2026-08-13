from setuptools import setup
import os
from glob import glob

# =====================================================================
#  setup.py - base_hardware
# =====================================================================
package_name = 'base_hardware'

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
    tests_require=['pytest'],
    zip_safe=True,
    maintainer='QTG0900',
    maintainer_email='qtg0900@example.com',
    description='Differentialantrieb Basis-Hardware-Node, zuerst als sicherer Dry-run.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'base_hardware = base_hardware.base_hardware_node:main',
        ],
    },
)
