from setuptools import setup
import os
from glob import glob

# =====================================================================
#  setup.py - semantic_perception (WP-5 Baustein B: Open-Vocabulary)
# =====================================================================
package_name = 'semantic_perception'

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
    description='Open-Vocabulary-Objekterkennung (GetObjectPose) + dynamischer Katalog (WP-5 Baustein B).',
    license='MIT',
    entry_points={
        'console_scripts': [
            'semantic_perception = semantic_perception.semantic_perception_node:main',
        ],
    },
)
