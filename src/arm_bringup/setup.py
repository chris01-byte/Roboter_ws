from glob import glob
from setuptools import setup

package_name = "arm_bringup"
setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml", "README.md"]),
        ("share/" + package_name + "/config", glob("config/*.json")),
    ],
    install_requires=["setuptools"],
    tests_require=["pytest"],
    zip_safe=True,
    maintainer="QTG0900",
    maintainer_email="qtg0900@example.com",
    description="Uncalibrated arm inventory and synthetic commissioning fixtures.",
    license="MIT",
    entry_points={"console_scripts": []},
)
