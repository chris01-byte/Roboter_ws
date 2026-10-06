"""Read-only original /plan subscriber. No goal, TF, command or health publication."""
from pathlib import Path
import json,time,os
import rclpy
from rclpy.node import Node
from rclpy.serialization import serialize_message
from nav_msgs.msg import Path as NavPath
os.sched_setaffinity(0,{0})
out=Path('/evidence/ap06-missions-20261005/b76-native-plans-passive');out.mkdir(exist_ok=False)
rclpy.init();node=Node('ap06_passive_plan_diagnosis');counter=[0]
def received(msg):
 counter[0]+=1
 if counter[0]>64:return
 name='plan-'+str(counter[0]);(out/(name+'.cdr')).write_bytes(serialize_message(msg))
 row=dict(index=counter[0],received_monotonic=time.monotonic(),frame=msg.header.frame_id,stamp=[msg.header.stamp.sec,msg.header.stamp.nanosec],points=[[p.pose.position.x,p.pose.position.y] for p in msg.poses])
 (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');print(name,len(msg.poses),flush=True)
node.create_subscription(NavPath,'/plan',received,10)
deadline=time.monotonic()+400
try:
 while rclpy.ok() and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.1)
finally:node.destroy_node();rclpy.shutdown()
