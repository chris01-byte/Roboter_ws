from glob import glob
import os

from setuptools import setup


package_name = "semantic_map_manager"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name],
        ),
        ("share/" + package_name, ["package.xml", "README.md"]),
        (
            os.path.join("share", package_name, "launch"),
            glob("launch/*.launch.py"),
        ),
        (
            os.path.join("share", package_name, "config"),
            glob("config/*.yaml"),
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="QTG0900",
    maintainer_email="qtg0900@example.com",
    description=(
        "Fail-closed semantic room overlays for versioned Amadeus maps."
    ),
    license="MIT",
    entry_points={
        "console_scripts": [
            "semantic_map_manager = "
            "semantic_map_manager.semantic_map_manager_node:main",
        ],
    },
)
