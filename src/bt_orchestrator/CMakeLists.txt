# =====================================================================
#  CMakeLists.txt  -  bt_orchestrator (WP-2)
#  Baut das ausfuehrbare Programm 'bt_orchestrator' (Behavior-Tree-Client).
#  ------------------------------------------------------------------
#  NEUEN BT-KNOTEN HINZUFUEGEN:
#    1) Header in include/bt_orchestrator/nodes/ anlegen/ergaenzen
#    2) in src/bt_orchestrator_main.cpp registrieren
#    (Header-only -> hier in CMake meist KEINE Aenderung noetig)
# =====================================================================
cmake_minimum_required(VERSION 3.8)
project(bt_orchestrator)

# C++17 erzwingen
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
endif()
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# --- Abhaengigkeiten ---
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)         # Missions-Action-Server (K1)
find_package(behaviortree_cpp REQUIRED)      # BehaviorTree.CPP v4
find_package(behaviortree_ros2 REQUIRED)     # ROS-2-Anbindung (RosActionNode etc.)
find_package(robot_interfaces REQUIRED)      # unsere eigenen srv/action
find_package(nav2_msgs REQUIRED)
find_package(control_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)

# --- Ausfuehrbares Programm ---
add_executable(bt_orchestrator src/bt_orchestrator_main.cpp)

# Header-Verzeichnis (unsere Knoten liegen unter include/)
target_include_directories(bt_orchestrator PRIVATE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

ament_target_dependencies(bt_orchestrator
  rclcpp
  rclcpp_action
  behaviortree_cpp
  behaviortree_ros2
  robot_interfaces
  nav2_msgs
  control_msgs
  std_msgs
  geometry_msgs
  sensor_msgs
)

# --- Installation ---
install(TARGETS bt_orchestrator
  DESTINATION lib/${PROJECT_NAME})

# XML-Baum, Parameter und Launch-Dateien mit installieren
install(DIRECTORY bt_xml config launch
  DESTINATION share/${PROJECT_NAME})

ament_package()
