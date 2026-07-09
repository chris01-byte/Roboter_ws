from setuptools import setup

package_name = 'handeye_calibration'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
        ('share/' + package_name + '/config', ['config/handeye_params.yaml']),
        ('share/' + package_name + '/launch', ['launch/handeye_recorder.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='QTG0900',
    maintainer_email='qtg0900@example.com',
    description='Hand-Auge-Kalibrierung (Eye-to-Hand) fuer den mobilen Pick-and-Place-Roboter.',
    license='MIT',
    entry_points={
        'console_scripts': [
            # ros2 run handeye_calibration handeye_recorder
            'handeye_recorder = handeye_calibration.handeye_recorder_node:main',
            # laeuft auch ohne ROS (offline am PC): handeye_solve <pairs.yaml>
            'handeye_solve = handeye_calibration.handeye_solve:main',
        ],
    },
)
