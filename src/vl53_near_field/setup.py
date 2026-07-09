from setuptools import setup
import os
from glob import glob

# =====================================================================
#  setup.py  -  vl53_near_field (ament_python, WP-1b)
#  NEUE config-/launch-Datei? -> wird durch die glob(...) unten automatisch
#  mitinstalliert. Neues Python-Modul? -> in packages=[...] ergaenzen.
# =====================================================================
package_name = 'vl53_near_field'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='QTG0900',
    maintainer_email='qtg0900@example.com',
    description='WP-1b: VL53L7CX Nahbereich-Hinderniserkennung (2 Sensoren via TCA9548A) als ROS-2-Node.',
    license='MIT',
    entry_points={
        'console_scripts': [
            # ros2 run vl53_near_field vl53_near_field
            'vl53_near_field = vl53_near_field.vl53_near_field_node:main',
        ],
    },
)
