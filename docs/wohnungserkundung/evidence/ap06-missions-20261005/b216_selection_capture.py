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


WRAPPER = "import copy,json,pickle,time\nfrom explore.metric_frontier_runtime import MetricFrontierRuntime as R\nfrom explore.metric_checkpoint import policy_state\noriginal=R._metric_select\nseen=set()\ndef recorded(self,inputs,policy,*args,**kwargs):\n stage=self._metric_status.get('arrivals',0)\n if stage != 2 or stage in seen:return original(self,inputs,policy,*args,**kwargs)\n seen.add(stage);began=time.monotonic();scan=self._door_lidar_scan_snapshot()\n record=dict(kind='Actual B216 live selection ENTRY and complete ORIGINAL history before distant proposal attempts; diagnostic only, not qualification',inputs=copy.deepcopy(list(inputs)),reference=getattr(inputs,'map_odom_reference',None),physical_motion=getattr(inputs,'physical_motion',None),evidence=copy.deepcopy(getattr(self,'_metric_egress',None)),scope=self._metric_scope,policy=policy_state(policy,began),scan=scan,mount=self._door_lidar_mount(scan['frame_id']),captured_monotonic=began,arrivals=stage,observations=self._metric_status.get('observations'),attributes={k:getattr(self,k,None) for k in ['_metric_start_egress_enabled','_metric_egress_expired','_metric_body_anchor_expired','_metric_egress_identity','_prealign_handoff_tolerance','_goal_clearance_m','_frontier_goal_max_cost','_goal_search_m','_min_goal_dist_m','_approach_dist_m','_metric_bounds','_map_timeout_s','_frontier_forward_cone_half_angle','_potential_scale','_gain_scale','_heading_scale','_metric_start_strategy','_metric_candidate_source','_metric_path_validation','_global_frame','_wohnungserkundung_evidence_max_cells','_door_lidar_scan_timeout','_door_lidar_max_range']})\n try:\n  candidates=original(self,inputs,policy,*args,**kwargs)\n  record['candidates']=[dict(task=c.task_id,goal=[c.x,c.y,c.yaw],frontier=c.frontier_xy,points=c.observation_points,cost=c.cost,native=c.requires_nav2_plan) for c in candidates]\n except Exception as error:\n  record['error']=str(error);candidates=None\n record.update(elapsed_s=time.monotonic()-began,ranking=dict(getattr(self,'_frontier_rank_stats',{})))\n with open('__OUTPUT__/selection-object-'+str(stage)+'.pickle','wb') as f:pickle.dump(record,f)\n with open('__OUTPUT__/selection-entry-'+str(stage)+'.json','w') as f:json.dump({k:record[k] for k in ('kind','arrivals','observations','elapsed_s','ranking','policy')},f,indent=2)\n if candidates is None:raise ValueError(record['error'])\n return candidates\nR._metric_select=recorded\nfrom explore.explore_node import main\nmain()\n"


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
        if command[:3] == [sys.executable, '-c', 'from explore.explore_node import main; main()']:
            command = [sys.executable, '-c', WRAPPER.replace('__OUTPUT__', str(args.output))]+command[3:]
        return original_popen(command, *positional, **keywords)
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
