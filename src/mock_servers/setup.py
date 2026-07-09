from setuptools import setup
import os
from glob import glob

# =====================================================================
#  setup.py  -  mock_servers (ament_python)
#  Trockenlauf-Server fuer den Behavior-Tree (WP-2).
# =====================================================================
package_name = 'mock_servers'

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
    description='Mock-Server (Dummy Actions/Services/Topics) zum Trockentest des Behavior-Trees.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'mock_servers = mock_servers.mock_servers_node:main',
        ],
    },
)
