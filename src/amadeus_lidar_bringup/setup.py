from glob import glob

from setuptools import setup

package_name = 'amadeus_lidar_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/config/udev', glob('config/udev/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Christopher',
    maintainer_email='chr.bakiera@icloud.com',
    description='Amadeus-Start des 2D-LiDARs STL-27L (Herstellertreiber bleibt unveraendert)',
    license='MIT',
    tests_require=['pytest'],
    entry_points={'console_scripts': []},
)
