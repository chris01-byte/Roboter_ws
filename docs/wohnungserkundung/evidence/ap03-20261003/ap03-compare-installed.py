import importlib,hashlib
from pathlib import Path
paths={'explore.metric_frontier':'src/explore/explore/metric_frontier.py','explore.metric_frontier_runtime':'src/explore/explore/metric_frontier_runtime.py','explore.explore_node':'src/explore/explore/explore_node.py','robot_state_estimation._hwt601_clock':'src/robot_state_estimation/robot_state_estimation/_hwt601_clock.py','robot_map_manager.robot_map_manager_node':'src/robot_map_manager/robot_map_manager/robot_map_manager_node.py','robot_navigation.cmd_vel_mission_gate':'src/robot_navigation/robot_navigation/cmd_vel_mission_gate.py'}
for name,source in paths.items():
    installed=Path(importlib.import_module(name).__file__);original=Path('/repo')/source
    assert str(installed).startswith('/evidence/ap03-current-install/')
    assert installed.read_bytes()==original.read_bytes()
    print(hashlib.sha256(installed.read_bytes()).hexdigest(),name,str(installed),'byte-identical to',source)
