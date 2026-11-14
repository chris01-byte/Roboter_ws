"""Own diagnostic snapshot only; no health, motion or acceptance receipt."""
import copy, pickle, time, sys, cProfile, pstats, io, json
from pathlib import Path
sys.path.insert(0, '/evidence/ap06-repo/src/explore/test')
from test_metric_frontier import adaptive_fixture
from explore.metric_frontier import MetricTaskPolicy, MetricAttempt
from explore.metric_frontier_runtime import MetricInputs
from explore.metric_frontier_candidates import lidar_view

from rclpy.serialization import serialize_message
from explore.metric_frontier import StartEgressEvidence
import numpy as np
captured=[]; arrays={}; original_check=StartEgressEvidence.check_trajectory
def captured_check(self,poses,occupancy,allowed,to_grid,commit=False):
    if not commit and self.unknown.any() and len(poses)>1:
        index=len(captured);prefix=str(index)
        for name,value in dict(grid=np.frombuffer(serialize_message(self.grid),np.uint8),
                unknown=self.unknown,scope=self.scope_mask,poses=poses,
                occupancy=occupancy,allowed=allowed).items():arrays[prefix+'_'+name]=np.asarray(value).copy()
        captured.append(dict(pose=self.pose,bounds=self.bounds,initial_polygon=self.initial_polygon,
            valid=self.valid,reason=self.reason,
            remaining_area=[[int(k[0]),int(k[1]),v] for k,v in self.remaining_area.items()],
            departed_distance=[[int(k[0]),int(k[1]),v] for k,v in self.departed_distance.items()]))
    return original_check(self,poses,occupancy,allowed,to_grid,commit=commit)
StartEgressEvidence.check_trajectory=captured_check
record = pickle.loads(Path('/evidence/ap06-missions-20261005/mission-b-v201-selection/selection-object-1.pickle').read_bytes())
for label in ('original',):
    n, _ = adaptive_fixture()
    for key, value in record['attributes'].items(): setattr(n, key, copy.deepcopy(value))
    n._metric_egress = copy.deepcopy(record['evidence'])
    n._metric_scope = record['scope']
    n._metric_body_reference = lambda: record['reference']
    n._global_costmap_received_at = time.monotonic()
    n._metric_nav_path = None; n._metric_status = {}; n._visualize = False
    view = lidar_view(record['scan'], record['mount'], record['captured_monotonic'],
                      n._door_lidar_scan_timeout, n._door_lidar_max_range)
    n._metric_observation_view = lambda: view
    values = copy.deepcopy(record['inputs'])
    inputs = MetricInputs(values, record['reference'], record['physical_motion'])
    n._global_costmap = inputs[5]
    p = record['policy']; policy = MetricTaskPolicy(p['radius'], p['cooldown_s'], p['retry_limit'])
    policy.next_id = p['next_id']
    for key, stored in p['tasks'].items():
        fields = dict(stored)
        fields['retry_after'] = time.monotonic()+(0. if label.endswith('elapsed') else fields['retry_remaining_s'])
        fields.pop('retry_remaining_s')
        policy.attempts[key] = MetricAttempt(**fields)
    if label != 'original':
        identify = policy.identify
        def frontier_identity(frontier_xy, target_xy=None):
            key = identify(frontier_xy,target_xy)
            if policy.attempts[key].completed:
                key = identify(frontier_xy)
            return key
        policy.identify = frontier_identity
    print(label, 'pose', inputs[2], 'policy', p, flush=True)
    started = time.monotonic(); profile = cProfile.Profile(); profile.enable()
    try:
        candidates = n._metric_select(inputs, policy, .3)
        print(label, 'candidates', [(c.task_id,c.x,c.y,c.yaw) for c in candidates],
              'ranking', n._frontier_rank_stats, 'seconds', time.monotonic()-started, flush=True)
    except Exception as e: print(label, 'error', repr(e), 'seconds', time.monotonic()-started, flush=True)

    finally:
        profile.disable()
        profile.dump_stats('/evidence/ap06-missions-20261005/b204-selection.prof')
        stream=io.StringIO();pstats.Stats(profile,stream=stream).sort_stats('cumulative').print_stats(32)
        print(stream.getvalue(),flush=True)

out=Path('/evidence/ap06-repo/src/explore/test/data/ap06_b201_selection_trajectory')
np.savez_compressed(out.with_suffix('.npz'),**arrays)
out.with_suffix('.json').write_text(json.dumps(dict(kind='Actual B201 selection entry, original private inventory and history; offline geometry only, no live health or mission receipt',rows=captured),indent=2)+'\n')
