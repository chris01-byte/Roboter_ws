"""AP-04 decisions use actual Explorer geometry and candidate functions."""
import copy
import math
import time
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest
from explore.explore_node import ExploreNode, Frontier
from explore.metric_frontier import known_safe_mask, MetricTaskPolicy
from explore.metric_frontier_candidates import boundary_samples, lidar_view, visible_boundary_cells
from explore.exploration_scope import AuthorizedExplorationScope, rasterize_scope
from explore.portal_memory import Point2D
from explore.portal_source_adapter import PortalSourceCorrelation, raw_map_portal_source_from_values
from test_metric_frontier import adaptive_fixture


def fixture(case='ring', revision=1, rotation=0.):
    n, old = adaptive_fixture()
    g = old[0]
    # Synthetic sensor specification is explicitly 1.2 m here (all competitors
    # get the same scan). No hidden groundtruth or optional semantic feed.
    h, w = 60, 90
    res = .1
    g.info.width=w; g.info.height=h
    g.info.origin.position.x=g.info.origin.position.y=0.
    g.info.origin.orientation.z=math.sin(rotation/2)
    g.info.origin.orientation.w=math.cos(rotation/2)
    rr, cc = np.indices((h, w))
    if case == 'ring':
        a = np.where((rr-28)**2+(cc-28)**2 <= 17**2, 0, -1)
        pose = (2.85, 2.85, 0.)
    elif case == 'concave':
        free = ((cc>=8)&(cc<=65)&(rr>=8)&(rr<=45))
        free &= ~((cc>=35)&(rr>=26))
        a=np.where(free,0,-1);pose=(2.05,1.85,0.)
    else:
        a=np.full((h,w),100)
        a[6:54,6:84]=0
        boundary = 42 + (revision-1)*3
        a[boundary:54,6:84]=-1
        pose=(2.05,2.05,0.)
    g.data=a.ravel().tolist();cost=copy.deepcopy(g)
    cost.data=a.ravel().tolist()  # Unknown preserved on both maps.
    c=old[1];source=raw_map_portal_source_from_values(**n._metric_grid_values(g))
    correlation=PortalSourceCorrelation(c.context,revision,source.fingerprint,source.source_stamp_ns)
    corners=tuple(n._grid_to_world(col,row,g.info) for col,row in
                  ((0,0),(w-1,0),(w-1,h-1),(0,h-1)))
    n._metric_scope=AuthorizedExplorationScope('scope',c.context,tuple(Point2D(*p) for p in corners))
    px,py=n._grid_to_world(pose[0]/res-.5,pose[1]/res-.5,g.info)
    pose=(px,py,pose[2]+rotation)
    n._global_costmap=cost;n._global_costmap_received_at=time.monotonic()
    n._approach_dist_m=.6;n._metric_candidate_source='boundary_samples'
    known,safe=known_safe_mask(a,n._metric_scope,correlation,(0.,0.),rotation,res,.28)
    inputs=[g,correlation,pose,known,safe,cost,(a>=0)&(a<100)]
    scan=dict(ranges=np.ones(360),angle_min=-math.pi,angle_increment=math.pi/180,
              range_min=.05,range_max=1.2,frame_id='laser',received_at=time.monotonic(),key=(100,0,360))
    n._door_lidar_scan_snapshot=lambda: dict(scan, received_at=time.monotonic())
    n._door_lidar_mount=lambda frame:(0.,0.,0.)
    n._door_lidar_scan_timeout=.5;n._door_lidar_max_range=4.
    n.get_clock=lambda:SimpleNamespace(now=lambda:SimpleNamespace(nanoseconds=100*10**9))
    return n,inputs,scan


def scope_mask(n, inputs):
    g,c=inputs[:2];q=g.info.origin.orientation
    return rasterize_scope(n._metric_scope,context=c.context,width=g.info.width,height=g.info.height,
        resolution_m=g.info.resolution,origin_x_m=g.info.origin.position.x,origin_y_m=g.info.origin.position.y,
        origin_yaw_rad=2*math.atan2(q.z,q.w),maximum_cells=1000000)


def candidates(n, inputs, scan):
    # Shared proof for comparison; only frontier extraction differs.
    return n._metric_candidates(inputs,.3)


@pytest.mark.parametrize('case',['ring','concave','long','blocked','growth','revisit','no_semantics'])
def test_mandatory_candidate_cases(case):
    n,inputs,scan=fixture(case)
    found=candidates(n,inputs,scan)
    assert found, n._frontier_rank_stats
    for candidate in found:
        assert n._metric_route(inputs,(candidate.x,candidate.y),candidate.yaw) is not None
    if case == 'ring':
        legacy=n._detect_frontiers(inputs[0],.3)
        assert len(legacy)==1
        assert n._metric_candidates(inputs,.3,frontiers=legacy,view=n._metric_observation_view()) == []
    if case == 'long':
        assert max(math.dist(a.frontier_xy,b.frontier_xy) for a in found for b in found)>3.
        sights=[visible_boundary_cells(inputs[0],scope_mask(n,inputs),(c.x,c.y,c.yaw),n._metric_observation_view()) for c in found]
        assert len(set.union(*[set(s) for s in sights]))>2*max(map(len,sights))
    if case == 'blocked':
        best=found[0];blocked=copy.deepcopy(inputs[5])
        col,row=n._world_to_grid(best.x,best.y,blocked.info)
        arr=np.asarray(blocked.data).reshape(60,90).copy();arr[row-2:row+3,col-2:col+3]=100
        blocked.data=arr.ravel().tolist();inputs[5]=blocked;inputs[6]=(arr>=0)&(arr<100)
        n._global_costmap=blocked
        alternatives=candidates(n,inputs,scan)
        assert alternatives and all(math.dist((c.x,c.y),(best.x,best.y))>.3 for c in alternatives)
    if case in ('growth','revisit'):
        n2,updated,scan2=fixture(case,revision=2)
        if case=='growth':
            # Real size growth with shifted origin, preserving existing content
            # in world coordinates; AP-02 independently tests live invalidation.
            for index in (0,5):
                g=updated[index];arr=np.asarray(g.data).reshape(60,90)
                arr=np.pad(arr,((0,1),(1,0)),constant_values=-1)
                g.info.width=91;g.info.height=61;g.info.origin.position.x=-.1;g.data=arr.ravel().tolist()
            source=raw_map_portal_source_from_values(**n2._metric_grid_values(updated[0]))
            updated[1]=replace(updated[1],fingerprint=source.fingerprint)
            arr=np.asarray(updated[0].data).reshape(61,91)
            updated[3],updated[4]=known_safe_mask(arr,n2._metric_scope,updated[1],(-.1,0.),0.,.1,.28)
            costs=np.asarray(updated[5].data).reshape(61,91);updated[6]=(costs>=0)&(costs<100)
        updated[2]=(found[0].x,found[0].y,found[0].yaw)
        # No mission history passed into the adapter. Same instance sees new
        # raster evidence, including when its pose is a previously visited goal.
        n2._metric_scope=n._metric_scope;n._global_costmap=updated[5]
        again=candidates(n,updated,scan)
        assert again and updated[1].fingerprint!=inputs[1].fingerprint
        assert all(c.revision==2 and c.fingerprint==updated[1].fingerprint for c in again)
    assert not hasattr(n,'_portal_memory')  # no optional semantics supplied


def test_rotated_origin_produces_equivalent_world_candidates():
    a,ia,sa=fixture('long');b,ib,sb=fixture('long',rotation=math.pi/2)
    ca=candidates(a,ia,sa);cb=candidates(b,ib,sb)
    assert ca and len(ca)==len(cb)
    assert {tuple(round(v,4) for v in (-c.y,c.x)) for c in ca} == {
        tuple(round(v,4) for v in (c.x,c.y)) for c in cb}


@pytest.mark.parametrize('change,reason',[
    ('missing','missing_stale'),('old','missing_stale'),('future','missing_stale'),
    ('stamp','stamp_stale'),('mask','no_valid_rays'),('range','geometry_invalid'),
    ('mount','tf_missing')])
def test_sensor_boundaries_fail_closed(change,reason):
    n,i,s=fixture('long')
    n._door_lidar_scan_snapshot=lambda:s
    if change=='missing':n._door_lidar_scan_snapshot=lambda:None
    elif change=='old':s['received_at']-=1.
    elif change=='future':s['received_at']+=1.
    elif change=='stamp':s['key']=(99,0,360)
    elif change=='mask':s['ranges'][:]=np.nan
    elif change=='range':s['range_max']=float('inf')
    elif change=='mount':n._door_lidar_mount=lambda frame:None
    with pytest.raises(ValueError,match=reason):n._metric_candidates(i,.3)


def test_visibility_stops_at_walls_unknown_and_range_and_respects_mask():
    n,i,s=fixture('long');g=i[0];allowed=scope_mask(n,i)
    s['ranges'][:]=np.nan;s['ranges'][180]=1.
    v=lidar_view(s,(0.,0.,0.),time.monotonic(),.5,4.)
    assert not visible_boundary_cells(g,allowed,(2.,2.,0.),v) # boundary beyond range
    assert visible_boundary_cells(g,allowed,(2.,3.8,math.pi/2),v)
    v=replace(v,range_m=.1)
    assert not visible_boundary_cells(g,allowed,(2.,3.8,math.pi/2),v)
    v=replace(v,range_m=1.2);arr=np.asarray(g.data).reshape(60,90).copy();arr[40,:]=100;g.data=arr.ravel().tolist()
    assert not visible_boundary_cells(g,allowed,(2.,3.8,math.pi/2),v)
    arr[40,:]=-1;g.data=arr.ravel().tolist()
    hits=visible_boundary_cells(g,allowed,(2.,3.8,math.pi/2),v)
    assert hits and all(row==40 for row,col in hits)


def test_candidate_capacity_is_explicit_not_silent_completion():
    n,i,s=fixture('long')
    with pytest.raises(ValueError,match='capacity_exhausted'):
        boundary_samples(i[0],scope_mask(n,i),n._grid_to_world,.3,limit=1)


def test_candidate_generation_does_not_own_visited_policy():
    n,i,s=fixture('long');first=candidates(n,i,s)
    p=MetricTaskPolicy(.6,30.,2);selected=n._metric_select(i,p,.3)
    p.record(selected[0],'observed',time.monotonic(),i[1].fingerprint)
    assert candidates(n,i,s)==first  # stateless adapter must still supply it
    assert n._metric_select(i,p,.3)!=selected  # AP-05 policy explicitly unchanged


def test_changed_local_evidence_returns_opportunity_near_previous_observation_pose():
    n,i,s=fixture('long');first=n._metric_select(i,MetricTaskPolicy(.6,30.,2),.3)[0]
    n2,updated,scan=fixture('revisit',revision=2)
    again=n2._metric_candidates(updated,.3)
    near=[c for c in again if math.dist((c.x,c.y),(first.x,first.y))<.6]
    assert near and updated[1].fingerprint!=i[1].fingerprint
    old_hits=visible_boundary_cells(i[0],scope_mask(n,i),(first.x,first.y,first.yaw),n._metric_observation_view())
    new_hits=visible_boundary_cells(updated[0],scope_mask(n2,updated),(near[0].x,near[0].y,near[0].yaw),n2._metric_observation_view())
    assert new_hits-old_hits  # actual new local boundary, not only a new ID


@pytest.mark.parametrize('source',['boundary_samples','legacy_centroid'])
def test_real_node_candidate_source_is_read_only(source):
    import json
    import rclpy
    from rclpy.parameter import Parameter
    from test_metric_frontier import require_isolated_ros
    require_isolated_ros()
    values=dict(exploration_strategy='metric_frontier',metric_candidate_source=source,
        wohnungserkundung_accessible_scope_verified=True,wohnungserkundung_scope_id='scope-test',
        wohnungserkundung_scope_polygon_xy=[-1.,-1.,3.,-1.,3.,3.,-1.,3.],
        metric_session_id='metric-test',metric_scope_map_fingerprint='a'*64,
        portal_crossing_enabled=False,coverage_enabled=False,overall_timeout_s=60.,
        region_graph_shadow_enabled=False,behavior_tree='/fake/no_recovery.xml')
    rclpy.init(args=['--ros-args',*[x for k,v in values.items() for x in ('-p',k+':='+json.dumps(v))]])
    n=None
    try:
        n=ExploreNode()
        assert n._metric_candidate_source==source
        other='legacy_centroid' if source=='boundary_samples' else 'boundary_samples'
        results=n.set_parameters([Parameter('metric_candidate_source',value=other)])
        assert not results[0].successful and n._metric_candidate_source==source
    finally:
        if n is not None:n.destroy_node()
        rclpy.shutdown()


def test_visibility_does_not_credit_unobserved_sensor_origin_or_min_range():
    n,i,s=fixture('long');g=i[0];allowed=scope_mask(n,i)
    v=n._metric_observation_view()
    # Sensor already in unknown: cannot look through it or call it new utility.
    assert not visible_boundary_cells(g,allowed,(2.,4.3,0.),v)
    v=replace(v,minimum_range_m=1.,angles=np.array([0.]))
    assert not visible_boundary_cells(g,allowed,(2.,4.15,math.pi/2),v)


def test_visibility_work_capacity_is_explicit():
    n,i,s=fixture('long');g=i[0];allowed=scope_mask(n,i)
    view=replace(n._metric_observation_view(),range_m=100000.)
    with pytest.raises(ValueError,match='visibility_capacity_exhausted'):
        visible_boundary_cells(g,allowed,i[2],view)


def test_scope_excludes_anchors_and_never_grants_external_unknown_sight():
    n,i,s=fixture('long');allowed=scope_mask(n,i);allowed[40:]=False
    assert not boundary_samples(i[0],allowed,n._grid_to_world,.3)
    assert not visible_boundary_cells(i[0],allowed,(2.,3.8,math.pi/2),n._metric_observation_view())


def test_unknown_raw_contour_and_costmap_obstacles_remain_exclusions():
    n,i,s=fixture('long');original=n._metric_candidates(i,.3)
    g=i[0];a=np.asarray(g.data).reshape(60,90).copy()
    a[6:42,6:84]=-1;g.data=a.ravel().tolist();i[3][:]=False;i[4][:]=False
    assert not n._metric_candidates(i,.3)
    n,i,s=fixture('long');i[6][:]=False
    assert not n._metric_candidates(i,.3)
    assert original


def test_actual_scan_geometry_range_cap_mount_and_mask_are_retained():
    n,i,s=fixture('long');s['range_max']=12.
    s['ranges'][100:170]=np.nan
    n._door_lidar_mount=lambda frame:(-.1,.02,math.pi/2)
    v=n._metric_observation_view()
    assert v.range_m==4. and v.mount==(-.1,.02,math.pi/2)
    assert len(v.angles)==290 and v.minimum_range_m==.05


def test_candidate_processing_consumes_budget_even_for_empty_result(monkeypatch):
    import explore.metric_frontier_runtime as runtime
    n,i,s=fixture('long');ticks=iter((0.,6.))
    monkeypatch.setattr(runtime,'time',SimpleNamespace(monotonic=lambda:next(ticks)))
    with pytest.raises(ValueError,match='processing_budget_exhausted'):
        n._metric_candidates(i,.3,frontiers=[])
