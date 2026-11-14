from setuptools import setup


package_name = "amadeus_map_identity"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name],
        ),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    tests_require=["pytest"],
    zip_safe=True,
    maintainer="QTG0900",
    maintainer_email="qtg0900@example.com",
    description="Canonical ROS-independent map identity helpers for Amadeus.",
    license="MIT",
)
