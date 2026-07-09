from setuptools import setup

package_name = 'robot_face'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
        ('share/' + package_name + '/config',
         ['config/face_params.yaml', 'config/event_expression_map.yaml']),
        ('share/' + package_name + '/launch', ['launch/robot_face.launch.py']),
        # Bewusst EINE Datei (CSS+JS inline): rendert auch bei Doppelklick /
        # unvollstaendiger Kopie korrekt, keine Nachladefehler moeglich.
        ('share/' + package_name + '/web', ['web/index.html']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='QTG0900',
    maintainer_email='qtg0900@example.com',
    description='Reaktives Cartoon-Gesicht (SVG-Web-App + Ereignis-Controller) fuer den mobilen Roboter.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'face_controller = robot_face.face_controller_node:main',
            'serve_face = robot_face.serve_face:main',
        ],
    },
)
