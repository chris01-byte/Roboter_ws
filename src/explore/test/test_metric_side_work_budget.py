"""Actual later A52 geometry: do not raycast impossible observation routes."""
import time
import threading
import copy

from explore.metric_frontier import MetricTaskPolicy
from explore.explore_node import Frontier
from test_metric_robot_side_observation import fixture


def test_impossible_view_geometry_consumes_no_visibility_work(monkeypatch):
    node, inputs, _ = fixture('ap06_a52_selection')
    import explore.metric_frontier_runtime as runtime
    original = runtime.visible_boundary_cells
    checked_routes = []; checked_stops = set(); visible = []
    route = node._metric_route
    stop_pose = node._metric_rollout_stop_pose
    def geometry(values, xy, yaw):
        result = route(values, xy, yaw)
        if result is not None:
            checked_routes.append(result)
        return result
    def actual_stop(values, proved_route, yaw, **kwargs):
        assert proved_route in checked_routes, ('unproved route', proved_route)
        result = stop_pose(values, proved_route, yaw, **kwargs)
        checked_stops.add(tuple(result))
        return result
    def sight(grid, scope, pose, view):
        # A failed route is already conclusive; this expensive work cannot
        # make its pose admissible. All geometry and rays remain real code.
        assert tuple(pose) in checked_stops, ('unproved view', pose)
        visible.append(pose)
        return original(grid, scope, pose, view)
    node._metric_route = geometry
    node._metric_rollout_stop_pose = actual_stop
    monkeypatch.setattr(runtime, 'visible_boundary_cells', sight)
    # Use the same exact evidence-bound memo as the owning selection pass.
    node._metric_selection_cache = threading.local()
    node._metric_selection_cache.memo = {'inputs': inputs}
    frontier = Frontier((1.304999970830977, .13499999698251486), 1)
    candidate = node._metric_robot_side_observation(inputs, frontier,
        MetricTaskPolicy(.6, 30., 2), node._metric_scope_mask(inputs), time.monotonic())
    assert candidate is not None and candidate.observation_points
    assert visible and node._metric_waypoints_clear(inputs, candidate.route, candidate.yaw) is not None


def test_actual_selection_finds_view_with_served_first_observer_and_same_budget():
    from explore.metric_checkpoint import restore_policy
    node, inputs, metadata = fixture('ap06_a52_selection')
    recorded, _ = restore_policy(metadata['checkpoint'], time.monotonic(),
                                 metadata['checkpoint']['saved_wall_time'])
    # Earlier-history component variant, on these explicitly later rasters.
    policy = MetricTaskPolicy(.6, 30., 2)
    policy.attempts['metric-task-4'] = copy.deepcopy(recorded.attempts['metric-task-4'])
    policy.next_id = 4
    node._global_costmap_received_at = time.monotonic()
    candidates = node._metric_select(inputs, policy, .3)
    assert candidates and not candidates[0].requires_nav2_plan
    candidate = candidates[0]
    assert candidate.observation_points
    assert node._metric_waypoints_clear(inputs, candidate.route, candidate.yaw) is not None
    assert policy.attempts['metric-task-4'].completed
    assert policy.attempts['metric-task-4'].tries == 1
    assert policy.attempts[candidate.task_id].tries == 0
