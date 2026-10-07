"""Diagnostic only: original finite inputs, full CDR history, no acceptance."""
import argparse
import base64
import gzip
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, '/evidence/ap06-repo/tools/simulation')
import ap06_closed_product as product
from rclpy.serialization import serialize_message
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import OccupancyGrid, Odometry
from tf2_msgs.msg import TFMessage
import yaml


class AcquisitionObserver(product.Observer):
    def __init__(self, out):
        super().__init__(out)
        self.acquisition = gzip.open(out/'acquisition.jsonl.gz', 'wt', compresslevel=1)
        self.acquisition_count = 0
        transient = QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        for topic, message, qos in (
            ('/scan_normiert', LaserScan, qos_profile_sensor_data),
            ('/tf', TFMessage, 1000), ('/tf_static', TFMessage, transient),
            ('/odom', Odometry, 100), ('/map', OccupancyGrid, transient)):
            def record(msg, topic=topic):
                self.acquisition.write(json.dumps(dict(topic=topic, at=time.monotonic(),
                    ros_ns=self.get_clock().now().nanoseconds,
                    cdr=base64.b64encode(serialize_message(msg)).decode()))+'\n')
                self.acquisition_count += 1
            self.create_subscription(message, topic, record, qos)

    def destroy_node(self):
        self.acquisition.close()
        (self.out/'acquisition-metadata.json').write_text(json.dumps(dict(
            kind='Actual closed-product diagnostic acquisition; no qualification',
            messages=self.acquisition_count), indent=2)+'\n')
        return super().destroy_node()


WRAPPER = r'''
import atexit,base64,json,queue,threading,time
from pathlib import Path
from rclpy.serialization import serialize_message
from explore.metric_frontier_runtime import MetricFrontierRuntime as R
out=Path('__OUTPUT__'); q=queue.SimpleQueue(); latest=[None]; seen=set(); count=[0]
def writer():
 with (out/'input-decisions.jsonl').open('w') as stream:
  while True:
   row=q.get()
   if row is None:break
   stream.write(json.dumps(row)+'\n');stream.flush()
thread=threading.Thread(target=writer);thread.start()
def finish():q.put(None);thread.join(3.)
atexit.register(finish)
prepare=R._metric_prepare_egress; original=R._metric_inputs_locked
def preparing(self,inputs):
 latest[0]=inputs
 return prepare(self,inputs)
def measured(self,*args,**kwargs):
 began=time.monotonic();latest[0]=None; error=None
 try:return original(self,*args,**kwargs)
 except Exception as exc:
  error=str(exc);raise
 finally:
  ended=time.monotonic();inputs=latest[0]
  if inputs is not None:
   motion=getattr(inputs,'physical_motion',None);ref=getattr(inputs,'map_odom_reference',None)
   key=(tuple(round(v,5) for v in ref) if ref else None,
        tuple(round(v/.03) for v in inputs[2]),error)
   row=dict(begin=began,end=ended,duration_s=ended-began,error=error,
       physical_motion=motion,pose=inputs[2],reference=ref,
       wheel_age_at_exit=[ended-at for at in motion[1:3]] if motion else None)
   if key not in seen and count[0]<64:
    seen.add(key);count[0]+=1
    row.update(raw_cdr=base64.b64encode(serialize_message(inputs[0])).decode(),
       cost_cdr=base64.b64encode(serialize_message(inputs[5])).decode(),
       scope=[[p.x,p.y] for p in self._metric_scope.vertices],
       bounds=self._metric_bounds)
   q.put(row)
R._metric_prepare_egress=preparing;R._metric_inputs_locked=measured
from explore.explore_node import main
main()
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resolution', type=float, choices=(.01,.02), required=True)
    args = parser.parse_args()
    original_params = product.params
    def parameters(repo, out):
        path = original_params(repo, out)
        config = yaml.safe_load(path.read_text())
        config['slam_toolbox']['ros__parameters']['resolution'] = args.resolution
        path.write_text(yaml.safe_dump(config))
        return path
    original_popen = product.subprocess.Popen
    def popen(command, *positional, **keywords):
        if command[:3] == [sys.executable, '-m', 'explore.explore_node']:
            command = [sys.executable, '-c', WRAPPER.replace('__OUTPUT__', str(args.output))]+command[3:]
        return original_popen(command, *positional, **keywords)
    product.Observer = AcquisitionObserver
    product.params = parameters
    product.subprocess.Popen = popen
    args.repo = Path('/evidence/ap06-repo')
    args.case = 'door68_start_b'
    args.tf_probe = Path('/evidence/ap06-tf-probe-build/tf_ownership_probe')
    args.manifest = args.repo/'tools/simulation/ap06_product_scenarios.json'
    args.ideal_lidar = args.profile_selection = args.capture_decisions = args.capture_geometry = False
    args.diagnostic_beams = 2160  # Original density; explicitly non-qualifying run.
    args.save_partial = True
    sys.exit(product.run(args))
