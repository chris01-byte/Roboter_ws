"""Real DDS source delivery while the genuine Explorer's map lock is busy."""
import json
import threading
import time
import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
from nav_msgs.msg import OccupancyGrid, Path
from std_msgs.msg import String
from explore.explore_node import ExploreNode
from test_metric_frontier import require_isolated_ros


def test_geometry_lock_waiters_cannot_starve_original_hwt_samples():
    require_isolated_ros()
    values=dict(exploration_strategy='metric_frontier',
        wohnungserkundung_accessible_scope_verified=True,wohnungserkundung_scope_id='scope',
        wohnungserkundung_scope_polygon_xy=[-1.,-1.,3.,-1.,3.,3.,-1.,3.],
        metric_session_id='metric-delivery',metric_scope_map_fingerprint='a'*64,
        portal_crossing_enabled=False,coverage_enabled=False,region_graph_shadow_enabled=False,
        require_hwt601_fusion=True,hwt601_active_drive=True,hwt_development_contract=True,
        overall_timeout_s=60.,goal_timeout_s=30.,behavior_tree='/fake/no_recovery.xml')
    rclpy.init(args=['--ros-args',*[x for k,v in values.items() for x in ('-p',k+':='+json.dumps(v))]])
    node=ExploreNode(); producer=Node('source_delivery_producer')
    executor=MultiThreadedExecutor(num_threads=4); executor.add_node(node);executor.add_node(producer)
    worker=threading.Thread(target=executor.spin,daemon=True);worker.start()
    raw=producer.create_publisher(Imu,'/shadow/hwt601/imu/data_raw',qos_profile_sensor_data)
    maps=producer.create_publisher(OccupancyGrid,'/map',1)
    costs=producer.create_publisher(OccupancyGrid,node._global_costmap_topic,1)
    wheel=producer.create_publisher(String,'/base_hardware/state_json',10)
    localization=producer.create_publisher(String,'/localization/status_json',10)
    plans=producer.create_publisher(Path,'/plan',10)
    stop=threading.Event()
    def publish():
        while not stop.is_set():
            sample=Imu();sample.header.stamp=producer.get_clock().now().to_msg()
            sample.header.frame_id='hwt601_link';sample.angular_velocity_covariance[8]=.001
            raw.publish(sample);stop.wait(.02)
    source=threading.Thread(target=publish,daemon=True);source.start()
    try:
        until=time.monotonic()+3.
        while 'raw' not in node._hwt_guard.health.samples and time.monotonic()<until:time.sleep(.01)
        assert 'raw' in node._hwt_guard.health.samples
        grid=OccupancyGrid();grid.header.frame_id='map';grid.info.width=grid.info.height=10
        grid.info.resolution=.1;grid.info.origin.orientation.w=1.;grid.data=[0]*100
        with node._metric_lock:
            began=time.monotonic()
            for _ in range(8):
                grid.header.stamp=producer.get_clock().now().to_msg()
                maps.publish(grid);costs.publish(grid)
                wheel.publish(String(data='{}'))
                localization.publish(String(data='{"schema_version":1}'))
                plan=Path();plan.header.frame_id='map';plans.publish(plan)
                time.sleep(.04)
            time.sleep(.15)
            with node._hwt_guard.health.lock:
                sample=node._hwt_guard.health.samples['raw']
                details=node._hwt_guard.health.sample_details['raw']
            # An actual newly stamped sensor message reached the real guard
            # during contention, inside the unchanged 300-ms freshness bound.
            assert sample[1]>began+.2 and 0<=time.monotonic()-sample[2]<.3
            assert details['delivery_path']=='executor_callback'
            assert details['content_valid'] is True
        stop.set();source.join(timeout=1.)
        time.sleep(.35)
        # No queue draining or map status can rejuvenate a missing raw source.
        with node._hwt_guard.health.lock:
            assert time.monotonic()-node._hwt_guard.health.samples['raw'][2]>.3
    finally:
        stop.set();source.join(timeout=1.)
        executor.shutdown(timeout_sec=3.);worker.join(timeout=3.)
        producer.destroy_node();node.destroy_node();rclpy.shutdown()
