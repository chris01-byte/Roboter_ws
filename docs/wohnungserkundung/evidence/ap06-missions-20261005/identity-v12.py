import hashlib, json, importlib, platform, sys, subprocess
from pathlib import Path
from ament_index_python.packages import get_package_prefix
root=Path('/evidence/ap06-repo'); install=Path('/evidence/ap06-old-product-install')
packages=['amadeus_map_identity','base_hardware','robot_interfaces','bt_orchestrator','mission_manager','robot_state_estimation','explore','robot_navigation','robot_map_manager','vl53_near_field','safety_monitor','amadeus_lidar_bringup']
records=[]
for name in packages:
 prefix=Path(get_package_prefix(name)); source=root/'src'/name
 assert prefix==install/name,(name,str(prefix))
 for folder,target in [(source/name,prefix/'lib/python3.10/site-packages'/name),(source/'config',prefix/'share'/name/'config'),(source/'launch',prefix/'share'/name/'launch'),(source/'bt_xml',prefix/'share'/name/'bt_xml'),(source/'behavior_trees',prefix/'share'/name/'behavior_trees'),(source/'msg',prefix/'share'/name/'msg'),(source/'srv',prefix/'share'/name/'srv'),(source/'action',prefix/'share'/name/'action')]:
  if not folder.exists():continue
  for file in sorted(folder.rglob('*')):
   if file.suffix not in ['.py','.yaml','.xml','.msg','.srv','.action']:continue
   counterpart=target/file.relative_to(folder)
   if not counterpart.exists():raise RuntimeError('missing '+str(counterpart))
   assert file.read_bytes()==counterpart.read_bytes(),(str(file),str(counterpart))
   records.append(dict(source=str(file.relative_to(root)),installed=str(counterpart),sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
 modules=['explore.explore_node','robot_interfaces.action._explore_area','vl53_near_field.measurement_quality','rclpy']
resolved={m:importlib.import_module(m).__file__ for m in modules}
native=[]
for package,relative in [('bt_orchestrator','lib/bt_orchestrator/bt_orchestrator'),('robot_localization','lib/robot_localization/ekf_node'),('slam_toolbox','lib/slam_toolbox/sync_slam_toolbox_node'),('nav2_planner','lib/nav2_planner/planner_server'),('nav2_controller','lib/nav2_controller/controller_server'),('nav2_bt_navigator','lib/nav2_bt_navigator/bt_navigator'),('nav2_velocity_smoother','lib/nav2_velocity_smoother/velocity_smoother'),('nav2_collision_monitor','lib/nav2_collision_monitor/collision_monitor')]:
 p=Path(get_package_prefix(package))/relative
 native.append(dict(package=package,path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
print(json.dumps(dict(platform=platform.platform(),python=sys.version,ros_packages=subprocess.check_output(['dpkg-query','-W','ros-humble-rclpy','ros-humble-rclcpp','ros-humble-rcl'],text=True),source_installed_equal=records,resolved_modules=resolved,native_binaries=native),indent=2))
