from glob import glob
from setuptools import setup

package_name = "arm_hardware"
setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml", "README.md", "requirements-modbus.txt"]),
        ("share/" + package_name + "/config", glob("config/*.json")),
    ],
    install_requires=["setuptools"],
    extras_require={"serial": ["pymodbus==3.14.0", "pyserial==3.5"]},
    tests_require=["pytest"],
    zip_safe=True,
    maintainer="QTG0900",
    maintainer_email="qtg0900@example.com",
    description="Read-only ESS commissioning transport and inventory validation.",
    license="MIT",
    entry_points={"console_scripts": []},
)
