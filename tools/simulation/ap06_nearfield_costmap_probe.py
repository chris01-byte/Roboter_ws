"""Native VL53/Nav2 regression; synthetic map/TF, no actions or motor node."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import numpy as np
import yaml
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from ament_index_python.packages import get_package_prefix
from geometry_msgs.msg import TransformStamped
from lifecycle_msgs.srv import ChangeState
from nav_msgs.msg import OccupancyGrid
from sensor_msgs.msg import PointCloud2
from robot_interfaces.msg import NearFieldStatus
from tf2_ros import StaticTransformBroadcaster

from ap06_closed_product import require_isolation
from ap06_sensors import vl53_producer
from ap06_world import World


def run(args):
    require_isolation()
    args.output.mkdir(parents=True, exist_ok=False)
    params = yaml.safe_load((args.repo/'src/robot_navigation/config/nav2_params_real.yaml').read_text())
    (args.output/'params.yaml').write_text(yaml.safe_dump(params))
    result = dict(passed=False, kind='native_costmap_component_only', hardware_qualified=False,
                  actions_sent=0, motor_nodes=0, synthetic_map_and_tf=True)
    rclpy.init()
    node = Node('ap06_nearfield_costmap_probe')
    log = (args.output/'planner.log').open('w')
    process = None
    try:
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        maps = node.create_publisher(OccupancyGrid, '/map', qos)
        clouds = {name: node.create_publisher(PointCloud2, topic, 10) for name, topic in (
            ('pub_left', '/near_field/left/points'), ('pub_right', '/near_field/right/points'),
            ('pub_left_cm', '/near_field/left/points_costmap'),
            ('pub_right_cm', '/near_field/right/points_costmap'))}
        clouds['pub_status'] = node.create_publisher(NearFieldStatus, '/near_field/status', 10)
        world = World(.8, [-1.6, 0., 0.])
        producer = vl53_producer(node, world, clouds)
        node.create_timer(.1, producer._tick)
        tf = StaticTransformBroadcaster(node)
        transforms = []
        for parent, child, xyz in (('map', 'odom', (0., 0., 0.)),
                ('odom', 'base_link', (0., 0., 0.)),
                ('base_link', 'vl53_left_link', (.290, .095, .215)),
                ('base_link', 'vl53_right_link', (.290, -.095, .215))):
            t = TransformStamped(); t.header.stamp = node.get_clock().now().to_msg()
            t.header.frame_id, t.child_frame_id = parent, child
            t.transform.translation.x, t.transform.translation.y, t.transform.translation.z = xyz
            t.transform.rotation.w = 1.; transforms.append(t)
        tf.sendTransform(transforms)
        grid = OccupancyGrid(); grid.header.frame_id = 'map'
        grid.info.resolution = .03; grid.info.width = grid.info.height = 140
        grid.info.origin.position.x = grid.info.origin.position.y = -2.1
        grid.info.origin.orientation.w = 1.; grid.data = [0]*(140*140)
        def publish_map():
            grid.header.stamp = node.get_clock().now().to_msg(); maps.publish(grid)
        node.create_timer(.5, publish_map); publish_map()
        received = []
        node.create_subscription(OccupancyGrid, '/global_costmap/costmap', received.append, qos)
        executable = Path(get_package_prefix('nav2_planner'))/'lib/nav2_planner/planner_server'
        command = [str(executable), '--ros-args', '--params-file', str(args.output/'params.yaml')]
        (args.output/'command.json').write_text(json.dumps(command))
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        def wait(predicate, seconds, label):
            deadline = time.monotonic()+seconds
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('native planner exited during '+label)
                rclpy.spin_once(node, timeout_sec=.05)
                if predicate(): return
            raise TimeoutError(label)
        client = node.create_client(ChangeState, '/planner_server/change_state')
        wait(lambda: client.service_is_ready(), 15., 'native lifecycle service')
        for state in (1, 3):
            request = ChangeState.Request(); request.transition.id = state
            future = client.call_async(request)
            wait(future.done, 20., 'lifecycle '+str(state))
            assert future.result().success
        def sample(label):
            start = len(received)
            wait(lambda: len(received) >= start+4, 10., label+' four native updates')
            m = received[-1]; a = np.asarray(m.data).reshape(m.info.height, m.info.width)
            np.save(args.output/(label+'.npy'), a)
            rows, cols = np.indices(a.shape)
            x = m.info.origin.position.x+(cols+.5)*m.info.resolution
            y = m.info.origin.position.y+(rows+.5)*m.info.resolution
            return int(np.count_nonzero((a>=99)&(x>.35)&(x<1.05)&(np.abs(y)<.5)))
        result['far_return_lethal_cells'] = sample('far')
        # Physical near wall in the cone, outside native body clearing. The
        # original measured-point producer and separate marking source must
        # still insert obstacles after clearing endpoints lose marking rights.
        world.obstacles.append(np.array([[-1.12,-.5],[-1.08,-.5],[-1.08,.5],[-1.12,.5]]))
        result['near_obstacle_lethal_cells'] = sample('near')
        result['passed'] = (result['far_return_lethal_cells'] == 0
                            and result['near_obstacle_lethal_cells'] > 0)
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGINT)
            try: process.wait(timeout=4.)
            except subprocess.TimeoutExpired:
                process.terminate(); process.wait(timeout=4.)
        node.destroy_node(); rclpy.shutdown(); log.close()
        (args.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(run(parser.parse_args()))
