# =====================================================================
#  CMakeLists.txt - robot_description (WP-0)
#  Installiert URDF/Xacro, Launch und README in den ROS-Share-Ordner.
# =====================================================================
cmake_minimum_required(VERSION 3.8)
project(robot_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf launch
  DESTINATION share/${PROJECT_NAME})

install(FILES README.md
  DESTINATION share/${PROJECT_NAME})

ament_package()
