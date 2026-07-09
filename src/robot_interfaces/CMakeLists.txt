# =====================================================================
#  CMakeLists.txt  -  robot_interfaces
#  Erzeugt C++/Python-Code aus den msg/srv/action-Dateien.
#  ------------------------------------------------------------------
#  NEUE SCHNITTSTELLE HINZUFUEGEN:
#    Datei unter msg/ , srv/ oder action/ anlegen und unten in der
#    Liste rosidl_generate_interfaces(...) (ab Zeile 28) ergaenzen.
# =====================================================================
cmake_minimum_required(VERSION 3.8)
project(robot_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# --- Abhaengigkeiten finden ---
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(action_msgs REQUIRED)

# --- Schnittstellen generieren (HIER neue Dateien eintragen) ---
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/NearFieldStatus.msg"
  "srv/GetObjectPose.srv"
  "srv/RefineObjectPose.srv"
  "srv/ComputeApproachPose.srv"
  "srv/ComputeGrasp.srv"
  "action/MoveArmToPose.action"
  "action/MoveArmToNamed.action"
  "action/ExploreArea.action"
  "action/RunMission.action"
  DEPENDENCIES std_msgs geometry_msgs sensor_msgs action_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
