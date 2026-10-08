#!/usr/bin/env python3
"""Bounded component reconstruction of the c5 terminal selection, never a mission.

Original installed selector and 5 s wall deadline; at most two ordinary calls and
one cProfile call. Saved final CDR/TF plus saved final policy are NOT the exact
failed selector entry snapshot. No ROS Nodes, publishers or action clients.
"""
import argparse, copy, cProfile, gzip, hashlib, importlib, io, json, math, os
from collections import defaultdict, deque
from pathlib import Path
import pstats, sys, threading, time, traceback
from types import SimpleNamespace

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def stamp(msg): return msg.header.stamp.sec*10**9+msg.header.stamp.nanosec

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('/evidence/ap06-concept-20261008/revalidation-a/door68_start_a'))
    p.add_argument('--repo',type=Path,default=Path('/evidence/ap06-repo'))
    p.add_argument('--install-root',type=Path,default=Path('/evidence/ap06-old-product-install'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    assert Path('/.dockerenv').exists() and os.environ.get('AP06_SIMULATION')=='1'
    assert not any(Path(s).exists() for s in ('/dev/ttyUSB_BASE','/dev/ttyUSB_HWT601','/etc/nv_tegra_release'))
    a.output.mkdir(parents=True,exist_ok=False)
    import numpy as np, pytest, yaml, rclpy
    from rclpy.serialization import deserialize_message
    from rclpy.time import Time
    from tf2_ros import Buffer
    from geometry_msgs.msg import TransformStamped
    from nav_msgs.msg import OccupancyGrid
    from sensor_msgs.msg import LaserScan
    from explore.explore_node import ExploreNode
    from explore.exploration_scope import AuthorizedExplorationScope
    from explore.portal_memory import PortalMapContext,Point2D
    from explore.portal_source_adapter import PortalSourceCorrelation,raw_map_portal_source_from_values
    from explore.metric_egress_reference import ReferencedStartEgress
    from explore.metric_checkpoint import restore_policy,policy_state
    from explore.metric_frontier_candidates import lidar_view
    sys.path.insert(0,str(a.repo/'src/explore/test'))
    from test_metric_frontier import body_input_fixture
    modules={}
    for name in ('explore.explore_node','explore.metric_frontier_runtime','explore.metric_frontier',
            'explore.metric_frontier_candidates','explore.metric_egress_reference','explore.metric_checkpoint',
            'explore.frontier_task_evidence','explore.exploration_scope','amadeus_map_identity.fingerprint'):
        path=Path(importlib.import_module(name).__file__).resolve()
        assert a.install_root.resolve() in path.parents,(name,path)
        modules[name]=dict(path=str(path),sha256=sha(path))
    configs={};params={}
    for name in ('explore_params.yaml','metric_frontier_params.yaml','metric_frontier_simulation_params.yaml'):
        src=a.repo/'src/explore/config'/name
        dst=a.install_root/'explore/share/explore/config'/name
        assert src.read_bytes()==dst.read_bytes(),name
        configs[name]=dict(source=str(src),installed=str(dst),sha256=sha(dst))
        params.update(yaml.safe_load(dst.read_bytes())['explore_node']['ros__parameters'])
    checkpoints=list((a.source/'checkpoints').glob('**/state-*.json'))
    assert len(checkpoints)==1,checkpoints
    checkpoint=checkpoints[0];envelope=json.loads(checkpoint.read_bytes());state=envelope['state']
    result=json.loads((a.source/'result.json').read_bytes())
    assert result['metric']['reason']=='frontier_candidate_processing_budget_exhausted'
    assert result['metric']['start_reference']['retained']==[0,0]
    assert result['metric']['start_reference']['projected']==[0,0]
    assert result['metric']['start_reference']['retained_area_m2']==[0.,0.]
    raw=deserialize_message((a.source/'final_raw_map.cdr').read_bytes(),OccupancyGrid)
    cost=deserialize_message((a.source/'final_costmap.cdr').read_bytes(),OccupancyGrid)
    scan=deserialize_message((a.source/'final_scan.cdr').read_bytes(),LaserScan)
    transforms=defaultdict(lambda:deque(maxlen=256));wheel=None;last_metric=None
    with gzip.open(a.source/'events.jsonl.gz','rt') as stream:
        for line in stream:
            event=json.loads(line)
            if event['topic']=='/tf':
                v=event['transform'];transforms[v['parent'],v['child']].append(v)
            elif event['topic']=='/base_hardware/state_json':wheel=event['data']
    rclpy.init(args=[])
    try:
        buffer=Buffer()
        for values in transforms.values():
            for v in values:
                t=TransformStamped();t.header.frame_id,t.child_frame_id=v['parent'],v['child']
                t.header.stamp.sec,t.header.stamp.nanosec=v['stamp']
                t.transform.translation.x,t.transform.translation.y,t.transform.translation.z=v['translation']
                t.transform.rotation.x,t.transform.rotation.y,t.transform.rotation.z,t.transform.rotation.w=v['rotation']
                buffer.set_transform(t,'recorded_synthetic_c5')
        t=TransformStamped();t.header.frame_id,t.child_frame_id='base_link','laser_frame'
        t.transform.translation.x,t.transform.translation.z=.245,.660
        t.transform.rotation.z,t.transform.rotation.w=math.sin(math.pi/4),math.cos(math.pi/4)
        buffer.set_transform_static(t,'original_harness_static_mount')
        actual=buffer.lookup_transform('map','base_link',Time())
        ros_now=max(stamp(raw),stamp(cost),stamp(actual),stamp(scan))+1000000
        source=raw_map_portal_source_from_values(**ExploreNode._metric_grid_values(raw))
        assert source.fingerprint==state['fingerprint']==envelope['map_binding']['fingerprint']
        context=PortalMapContext(**state['context'])
        # Policy revision is not captured; it labels output only, not geometry.
        correlation=PortalSourceCorrelation(context,1,source.fingerprint,source.source_stamp_ns)
        scope=AuthorizedExplorationScope(state['scope']['scope_id'],context,
            tuple(Point2D(*xy) for xy in state['scope']['vertices']))
        report=dict(schema=1,diagnostic_only=True,mission_qualified=False,hardware_qualified=False,
            original_deadline_s=5.,source_commit='c5d2a9c00d146851799a907ba725ef0d0f30c815',
            installed_modules=modules,configs=configs,checkpoint=dict(path=str(checkpoint),sha256=sha(checkpoint)),
            script=dict(path=str(Path(__file__).resolve()),sha256=sha(__file__)),
            original_inputs={name:dict(path=str(a.source/name),sha256=sha(a.source/name)) for name in (
                'result.json','final_raw_map.cdr','final_costmap.cdr','final_scan.cdr','events.jsonl.gz')},
            limitations=['Component reconstruction, not exact failed selector entry or a mission.',
                'Saved final policy is after failed pass; newly identified task IDs may already exist.',
                'Saved cooldown remaining retained independently in each call; entry-pass cooldowns unavailable.',
                'Saved final common-time TF pose and final CDR may differ from discarded failing input object.',
                'Empty private inventory is reconstructed and asserted from final status; original ledger was not saved.',
                'Frozen recorded finite lidar view is geometric component data, never a new sensor freshness receipt.',
                'The final LaserScan predates final TF and fails the original observation stamp guard; only the finite geometry adapter is used offline.',
                'Monotonic selection clock is real, original 5 s budget unchanged. Source receipt refreshed for offline component only.',
                'No competing mission/DDS load; cProfile adds overhead and can change which budget check throws.',
                'Map revision label reconstructed as 1; fingerprint/context/source stamp exactly bound to checkpoint.'],
            affinity=sorted(os.sched_getaffinity(0)),ros_time_ns=ros_now,
            stamps_ns=dict(raw=stamp(raw),cost=stamp(cost),scan=stamp(scan),tf=stamp(actual)),
            shape=dict(raw=[raw.info.height,raw.info.width],cost=[cost.info.height,cost.info.width]),runs=[])
        with pytest.MonkeyPatch.context() as patch:
            node=body_input_fixture(patch,10.)
            for name in ('_metric_matches_status','_robot_pose_sample','_door_lidar_mount','_door_lidar_scan_snapshot'):
                delattr(node,name)
            node._metric_raw=(raw,source,10.);node._metric_correlation=correlation;node._metric_scope=scope
            node._metric_status_at=10.;node._metric_status={}
            node._global_costmap=cost;node._global_costmap_received_at=10.
            node._metric_egress=node._metric_egress_identity=None
            node._metric_egress_expired=node._metric_body_anchor_expired=False
            node._metric_bounds=(-.13,.33,-.25,.25)
            node._robot_base_frame='base_link';node._tf_buffer=buffer
            node.get_clock=lambda:SimpleNamespace(now=lambda:Time(nanoseconds=ros_now))
            node._door_scan_lock=threading.Lock();node._on_door_lidar_scan(scan)
            node._hwt_guard=SimpleNamespace(health=SimpleNamespace(lock=threading.RLock(),
                samples={'wheel':((1,0),10.,10.,True)},sample_details={'wheel':dict(
                    frame_id='odom',child_frame_id='base_link',position=[wheel['x'],wheel['y'],0.],
                    orientation=[0.,0.,math.sin(wheel['yaw']/2),math.cos(wheel['yaw']/2)])}))
            mapping=dict(_metric_start_strategy='metric_start_strategy',_metric_candidate_source='metric_candidate_source',
                _metric_path_validation='metric_path_validation',_metric_start_egress_enabled='metric_start_egress_enabled',
                _goal_clearance_m='goal_clearance_m',_frontier_goal_max_cost='frontier_goal_max_cost',
                _goal_search_m='goal_search_radius_m',_approach_dist_m='frontier_approach_distance_m',
                _min_goal_dist_m='min_goal_distance_m',_frontier_forward_cone_half_angle='frontier_forward_cone_half_angle_rad',
                _potential_scale='potential_scale',_gain_scale='gain_scale',_heading_scale='heading_scale',
                _map_timeout_s='map_timeout_s',_wohnungserkundung_evidence_max_cells='wohnungserkundung_evidence_max_cells',
                _door_lidar_max_range='door_lidar_max_range_m',_prealign_handoff_tolerance='prealign_handoff_tolerance_rad')
            for field,key in mapping.items():setattr(node,field,params[key])
            node._visualize=False;node._metric_nav_path=None;node._metric_active=None
            assert node._map_timeout_s==5.
            for _ in range(2): values=node._metric_inputs_locked(active=True)
            assert all(isinstance(e,ReferencedStartEgress) and e.valid and not e.unknown.any()
                and not e.fixed.unknown.any() and e.retained_region.is_empty for e in node._metric_egress)
            # Offline finite geometry adapter only: final scan predates final TF.
            # It is not a current sensor receipt or an original-entry replay.
            view=lidar_view(node._door_lidar_scan_snapshot(),node._door_lidar_mount(scan.header.frame_id),
                10.,node._door_lidar_scan_timeout,node._door_lidar_max_range)
            report.update(pose=list(values[2]),reference=list(values.map_odom_reference),
                scope_vertices=state['scope']['vertices'],fingerprint=source.fingerprint,
                mask_cells=dict(known=int(values[3].sum()),safe=int(values[4].sum()),cost_known=int(values[6].sum())),
                attributes={k:getattr(node,k) for k in mapping},finite_lidar_angles=len(view.angles))
        # Fixture monkeypatch has ended. No frozen monotonic clock in timed calls.
        assert time.monotonic()>1000
        node._metric_observation_view=lambda:view
        baseline_egress=copy.deepcopy(node._metric_egress)
        (a.output/'setup.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        for index in range(3):
            node._metric_egress=copy.deepcopy(baseline_egress)
            node._metric_status={};node._frontier_rank_stats={}
            node._metric_selection_cache=threading.local()
            node._global_costmap_received_at=time.monotonic()
            policy,_=restore_policy(state,time.monotonic(),state['saved_wall_time'])
            before=policy_state(policy,time.monotonic())
            profile=cProfile.Profile() if index==2 else None
            started=time.perf_counter();call=dict(index=index+1,profiled=profile is not None)
            try:
                if profile:profile.enable()
                selected=node._metric_select(values,policy,params['min_frontier_size_m'])
                call['selected']=[dict(task_id=c.task_id,goal=[c.x,c.y,c.yaw],route_length=len(c.route),
                    requires_nav2_plan=c.requires_nav2_plan,observation_points=len(c.observation_points)) for c in selected]
                call['outcome']='returned'
            except Exception as exc:
                call.update(outcome='exception',exception_type=type(exc).__name__,reason=str(exc))
                call['traceback']=traceback.format_exc()
                tb=exc.__traceback__;frames=[]
                while tb:
                    frame=tb.tb_frame
                    entry=dict(file=frame.f_code.co_filename,line=tb.tb_lineno,function=frame.f_code.co_name)
                    if frame.f_code.co_name=='_metric_candidates_in_pass':
                        loc=frame.f_locals
                        entry['locals']={k:loc.get(k) for k in ('step','goal','alternative','proposal','offset','normal_deferred','private_start_available')}
                        entry['candidates_so_far']=len(loc.get('candidates',()))
                        f=loc.get('f');entry['frontier']=None if f is None else [f.cx,f.cy,f.size]
                        entry['selection_elapsed_s']=time.monotonic()-loc['selection_started']
                    frames.append(entry);tb=tb.tb_next
                call['frames']=frames
            finally:
                if profile:profile.disable()
                call['elapsed_s']=time.perf_counter()-started
            call['rank_stats']=node._frontier_rank_stats
            call['policy_before']=before;call['policy_after']=policy_state(policy,time.monotonic())
            if profile:
                profile.dump_stats(str(a.output/'selection.prof'))
                out=io.StringIO();stats=pstats.Stats(profile,stream=out).sort_stats('cumulative');stats.print_stats(100)
                (a.output/'selection-profile.txt').write_text(out.getvalue())
                call['profile_total_s']=stats.total_tt
                call['profile_functions']=sorted([dict(file=file,line=line,function=name,calls=n,
                    primitive_calls=nc,own_s=tt,cumulative_s=ct) for (file,line,name),(nc,n,tt,ct,_) in stats.stats.items()],
                    key=lambda d:-d['cumulative_s'])[:100]
            report['runs'].append(call)
            (a.output/'result.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
            print(json.dumps({k:v for k,v in call.items() if k not in ('policy_before','policy_after','profile_functions')},allow_nan=False),flush=True)
        report['call_count']=dict(unprofiled=2,profiled=1,total=3)
        (a.output/'result.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    finally:rclpy.shutdown()

if __name__=='__main__':main()
