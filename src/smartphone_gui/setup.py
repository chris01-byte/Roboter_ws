from setuptools import setup
import os
from glob import glob

# =====================================================================
#  setup.py - smartphone_gui (WP-4)
# =====================================================================
package_name = 'smartphone_gui'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'web'), glob('web/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='QTG0900',
    maintainer_email='qtg0900@example.com',
    description='Smartphone PWA fuer den mobilen Pick-and-Place-Roboter.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'serve_gui = smartphone_gui.serve_gui:main',
        ],
    },
)
