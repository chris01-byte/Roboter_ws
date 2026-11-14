import hashlib, importlib, json, platform, sys
from pathlib import Path
from robot_interfaces.action import ExploreArea
from ament_index_python.packages import get_package_prefix
source=Path('/evidence/ap05-repo')
modules=['explore.explore_node','explore.metric_frontier_runtime','explore.metric_frontier','explore.metric_frontier_candidates','explore.metric_progress','explore.metric_checkpoint','explore.exploration_persistence','mission_manager.mission_manager_node','robot_map_manager.robot_map_manager_node','amadeus_map_identity.fingerprint','robot_state_estimation.hwt601_imu_node','robot_state_estimation._hwt601_clock','robot_navigation.cmd_vel_mission_gate','base_hardware.encoder_shadow_node']
records=[]
for name in modules:
 m=importlib.import_module(name); installed=Path(m.__file__)
 pkg=name.split('.')[0]; relative=Path('src')/pkg/Path(*name.split('.')).with_suffix('.py')
 original=source/relative
 a=hashlib.sha256(original.read_bytes()).hexdigest(); b=hashlib.sha256(installed.read_bytes()).hexdigest()
 assert str(installed).startswith('/evidence/ap05-final-install/') and a==b,(name,a,b)
 records.append(dict(module=name,source=str(relative),installed=str(installed),sha256=a))
extras=[]
for pkg,relative in [('explore','config/metric_frontier_params.yaml'),('robot_interfaces','action/ExploreArea.action')]:
 original=source/'src'/pkg/relative; installed=Path(get_package_prefix(pkg))/'share'/pkg/relative
 a=hashlib.sha256(original.read_bytes()).hexdigest(); b=hashlib.sha256(installed.read_bytes()).hexdigest()
 assert a==b,(original,installed)
 extras.append(dict(source=str(original.relative_to(source)),installed=str(installed),sha256=a))
print(json.dumps(dict(python=sys.version,platform=platform.platform(),source=str(source),modules=records,installed_files=extras,action_fields={t.__name__:t.get_fields_and_field_types() for t in (ExploreArea.Goal,ExploreArea.Result,ExploreArea.Feedback)},ros_domain_id=230,ros_localhost_only=True,proof_scope='Actual installed ROS bindings and byte identity; no hardware or full AP-06 graph'),indent=2))
