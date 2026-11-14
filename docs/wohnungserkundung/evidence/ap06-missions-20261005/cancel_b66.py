import time,rclpy
from rclpy.node import Node
from std_msgs.msg import String
rclpy.init();n=Node('ap06_analysis_cancel');p=n.create_publisher(String,'/mission_manager/command_json',10)
until=time.monotonic()+3.
while not p.get_subscription_count() and time.monotonic()<until:rclpy.spin_once(n,timeout_sec=.05)
assert p.get_subscription_count()>0,'No actual mission command consumer'
p.publish(String(data='{"type":"cancel"}'))
until=time.monotonic()+2.
while time.monotonic()<until:rclpy.spin_once(n,timeout_sec=.05)
n.destroy_node();rclpy.shutdown()
