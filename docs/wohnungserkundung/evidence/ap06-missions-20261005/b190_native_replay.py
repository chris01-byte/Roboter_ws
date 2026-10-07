"""Replay one immutable scan/odom/static-TF stream through actual native SLAM.

No observed map, map->odom transform, navigation goal or new sensor sample is
fed back. ROS clock follows the recorded receipt timeline. Component only.
"""
import argparse,base64,gzip,hashlib,json,os,signal,subprocess,threading,time
from pathlib import Path
import rclpy,yaml
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile,DurabilityPolicy,qos_profile_sensor_data
from rclpy.serialization import deserialize_message,serialize_message
from ament_index_python.packages import get_package_prefix
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import OccupancyGrid
from tf2_msgs.msg import TFMessage
from rosgraph_msgs.msg import Clock


def run(args):
    if not Path('/.dockerenv').exists() or os.environ.get('AP06_SIMULATION')!='1':
        raise RuntimeError('isolated simulation required')
    args.output.mkdir(parents=True,exist_ok=False)
    trace=args.source/'acquisition.jsonl.gz'
    rows=[json.loads(line) for line in gzip.open(trace,'rt')]
    digest=hashlib.sha256(trace.read_bytes()).hexdigest()
    config=yaml.safe_load((args.source/'native_params.yaml').read_text())
    config=config['slam_toolbox']['ros__parameters']
    config.update(resolution=args.resolution,use_sim_time=True)
    params=args.output/'params.yaml'
    params.write_text(yaml.safe_dump({'slam_toolbox':{'ros__parameters':config}}))
    rclpy.init();node=Node('ap06_immutable_input_replay',parameter_overrides=[Parameter('use_sim_time',value=True)])
    clock=node.create_publisher(Clock,'/clock',100)
    tf=node.create_publisher(TFMessage,'/tf',1000)
    static_qos=QoSProfile(depth=100,durability=DurabilityPolicy.TRANSIENT_LOCAL)
    static=node.create_publisher(TFMessage,'/tf_static',static_qos)
    scan=node.create_publisher(LaserScan,'/scan_normiert',qos_profile_sensor_data)
    maps=[];references=[]
    node.create_subscription(OccupancyGrid,'/map',lambda m:maps.append(m),static_qos)
    def reference(msg):
        references.extend(t for t in msg.transforms if t.header.frame_id=='map' and t.child_frame_id=='odom')
    node.create_subscription(TFMessage,'/tf',reference,1000)
    executor=SingleThreadedExecutor();executor.add_node(node)
    thread=threading.Thread(target=executor.spin,daemon=True);thread.start()
    def advance(ns):
        msg=Clock();msg.clock.sec=ns//10**9;msg.clock.nanosec=ns%10**9;clock.publish(msg)
    advance(rows[0]['ros_ns'])
    log=(args.output/'slam.log').open('w')
    command=[str(Path(get_package_prefix('slam_toolbox'))/'lib/slam_toolbox/sync_slam_toolbox_node'),'--ros-args','--params-file',str(params)]
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
    counts={'scan':0,'odom_tf':0,'static_tf':0,'excluded_map_tf':0}
    try:
        deadline=time.monotonic()+15
        while scan.get_subscription_count()==0 or tf.get_subscription_count()<2:
            if time.monotonic()>deadline:raise RuntimeError('native SLAM reader discovery')
            advance(rows[0]['ros_ns']);time.sleep(.05)
        # Discovery is complete before the first original input.
        began=time.monotonic();origin=rows[0]['at']
        for row in rows:
            due=began+row['at']-origin
            while time.monotonic()<due:time.sleep(max(0.,min(.005,due-time.monotonic())))
            advance(row['ros_ns'])
            if row['topic'] not in ('/tf','/tf_static','/scan_normiert'):continue
            payload=base64.b64decode(row['cdr'])
            if row['topic']=='/scan_normiert':
                scan.publish(deserialize_message(payload,LaserScan));counts['scan']+=1
            else:
                message=deserialize_message(payload,TFMessage)
                if row['topic']=='/tf':
                    counts['excluded_map_tf']+=sum(t.header.frame_id=='map' for t in message.transforms)
                    message.transforms=[t for t in message.transforms if t.header.frame_id=='odom' and t.child_frame_id=='base_link']
                    counts['odom_tf']+=len(message.transforms)
                    if message.transforms:tf.publish(message)
                else:
                    static.publish(message);counts['static_tf']+=len(message.transforms)
        # Drain computation without changing the final sensor samples/stamps.
        time.sleep(.3)
        assert maps and references,'native output missing'
        for i,m in enumerate(maps):(args.output/f'map-{i:03d}.cdr').write_bytes(serialize_message(m))
        final=maps[-1]
        result=dict(kind=__doc__,input_sha256=digest,resolution=args.resolution,
            messages_published=counts,maps=len(maps),references=len(references),
            final_map_sha256=hashlib.sha256(serialize_message(final)).hexdigest(),
            final_shape=[final.info.height,final.info.width],
            final_map_stamp=[final.header.stamp.sec,final.header.stamp.nanosec],
            native_map_odom=[references[-1].transform.translation.x,references[-1].transform.translation.y,
                           references[-1].transform.rotation.z,references[-1].transform.rotation.w],
            product_mission_qualified=False)
        (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
    finally:
        if process.poll() is None:process.send_signal(signal.SIGINT)
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        executor.shutdown(timeout_sec=3);thread.join(3);node.destroy_node();rclpy.shutdown();log.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resolution',type=float,choices=(.01,.02),required=True)
    run(parser.parse_args())
