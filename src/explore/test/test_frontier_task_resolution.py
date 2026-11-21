from dataclasses import replace
import ast
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from amadeus_map_identity import (  # noqa: E402
    compact_occupancy_cells,
    map_snapshot_fingerprint,
)
from explore.child_result_policy import (  # noqa: E402
    ChildResultDisposition,
    ChildResultDispositionState,
)
from explore.exploration_policy import (  # noqa: E402
    TaskAttempt,
    TaskAttemptOutcome,
)
from explore.frontier_goal_candidate import FrontierGoalCandidate  # noqa: E402
from explore.frontier_task_evidence import FrontierTaskEvidencePolicy  # noqa: E402
from explore.frontier_task_feed import FrontierTrackSnapshot  # noqa: E402
from explore.frontier_task_resolution import (  # noqa: E402
    FrontierTaskResolutionCapacityError,
    FrontierTaskResolutionError,
    FrontierTaskResolutionState,
    build_frontier_task_resolution_evidence,
)
from explore.portal_memory import Point2D, PortalMapContext  # noqa: E402
from explore.portal_source_adapter import PortalSourceCorrelation  # noqa: E402


CONTEXT = PortalMapContext('session-m3p', 'map-m3p', 'map')
ORIGIN = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)


def _candidate():
    return FrontierGoalCandidate(
        intent_id='intent-7',
        task_id='task-frontier_000001',
        region_id='region_000001',
        frontier_id='frontier_000001',
        map_revision=7,
        frame_id='map',
        source_fingerprint='a' * 64,
        source_stamp_ns=700,
        target_x_m=1.45,
        target_y_m=1.05,
        target_yaw_rad=0.0,
        target_row=10,
        target_col=14,
        frontier_x_m=1.45,
        frontier_y_m=1.05,
        route_length_m=0.9,
        information_gain_square_m=0.5,
    )


def _disposition():
    return ChildResultDisposition(
        result_id='result-7',
        intent_id='intent-7',
        task_id='task-frontier_000001',
        map_revision=7,
        state=ChildResultDispositionState.PROGRESSED,
        reason='child_goal_reached_reobserve_frontier',
        attempt=TaskAttempt(
            attempt_id='attempt-7',
            task_id='task-frontier_000001',
            context=CONTEXT,
            map_revision=7,
            outcome=TaskAttemptOutcome.PROGRESSED,
            reason='child_goal_reached_reobserve_frontier',
        ),
        terminates_exploration=False,
    )


def _map(*, revision=8, unknown=False, target=0, width=31, height=31):
    cells = [0] * (width * height)
    if unknown:
        cells[10 * width + 16] = -1
    cells[10 * width + 14] = target
    compact = compact_occupancy_cells(cells=cells, cell_count=len(cells))
    fingerprint = map_snapshot_fingerprint(
        width=width,
        height=height,
        resolution=0.1,
        frame_id='map',
        origin=ORIGIN,
        compact_cells=compact,
    )
    return {
        'correlation': PortalSourceCorrelation(
            context=CONTEXT,
            map_revision=revision,
            fingerprint=fingerprint,
            source_stamp_ns=revision * 100,
        ),
        'width': width,
        'height': height,
        'resolution': 0.1,
        'frame_id': 'map',
        'origin': ORIGIN,
        'cells': cells,
        'source_stamp_ns': revision * 100,
    }


def _track(*, revision=8, frontier_id='frontier_000001', x=1.45):
    return FrontierTrackSnapshot(
        frontier_id=frontier_id,
        centroid=Point2D(x, 1.05),
        size_cells=8,
        first_revision=3,
        last_revision=revision,
        observation_count=3,
    )


def _build(*, map_values=None, tracks=(), candidate=None,
           disposition=None, policy=None):
    return build_frontier_task_resolution_evidence(
        _candidate() if candidate is None else candidate,
        _disposition() if disposition is None else disposition,
        **(_map() if map_values is None else map_values),
        tracks=tracks,
        policy=policy or FrontierTaskEvidencePolicy(
            information_radius_m=0.4),
    )


def test_new_exact_known_map_resolves_reached_frontier():
    result = _build(tracks=(_track(revision=7),))

    assert result.state is FrontierTaskResolutionState.RESOLVED
    assert result.resolved is True
    assert result.goal_map_revision == 7
    assert result.evidence_map_revision == 8
    assert result.checked_information_cells > 0
    assert result.unknown_information_cells == 0


def test_current_same_or_nearby_frontier_blocks_resolution():
    same = _build(tracks=(_track(),))
    nearby = _build(tracks=(
        _track(frontier_id='frontier_000002', x=1.75),))

    assert same.state is FrontierTaskResolutionState.CURRENT_FRONTIER_PRESENT
    assert nearby.state is FrontierTaskResolutionState.CURRENT_FRONTIER_PRESENT


def test_unknown_window_and_nonfree_target_block_resolution():
    unknown = _build(map_values=_map(unknown=True))
    occupied = _build(map_values=_map(target=100))

    assert unknown.state is (
        FrontierTaskResolutionState.INFORMATION_WINDOW_INCOMPLETE)
    assert unknown.unknown_information_cells == 1
    assert occupied.state is FrontierTaskResolutionState.TARGET_NOT_FREE


def test_window_clipped_by_map_boundary_is_not_complete():
    candidate = replace(
        _candidate(),
        target_x_m=0.15,
        frontier_x_m=0.15,
    )
    result = _build(candidate=candidate)

    assert result.state is (
        FrontierTaskResolutionState.INFORMATION_WINDOW_INCOMPLETE)
    assert result.checked_information_cells == 0


def test_old_map_wrong_context_or_nonprogress_result_fails_closed():
    with pytest.raises(FrontierTaskResolutionError, match='neueren'):
        _build(map_values=_map(revision=7))
    foreign = _map()
    foreign['correlation'] = replace(
        foreign['correlation'],
        context=PortalMapContext('foreign', 'map-m3p', 'map'))
    with pytest.raises(FrontierTaskResolutionError, match='neueren'):
        _build(map_values=foreign)
    with pytest.raises(FrontierTaskResolutionError, match='erfolgreichen'):
        _build(disposition=replace(
            _disposition(), state=ChildResultDispositionState.REEVALUATE,
            attempt=None))


def test_duplicate_future_tracks_and_capacity_fail_closed():
    with pytest.raises(FrontierTaskResolutionError, match='Duplikate'):
        _build(tracks=(_track(), _track()))
    with pytest.raises(FrontierTaskResolutionError, match='vor'):
        _build(tracks=(_track(revision=9),))
    with pytest.raises(FrontierTaskResolutionCapacityError):
        _build(
            tracks=(_track(),),
            policy=FrontierTaskEvidencePolicy(
                information_radius_m=0.4, max_tracks=1, max_cells=100),
        )


def test_resolution_evidence_value_object_rejects_false_positive_mutation():
    result = _build()
    with pytest.raises(FrontierTaskResolutionError, match='neuer'):
        replace(result, evidence_map_revision=result.goal_map_revision)
    with pytest.raises(FrontierTaskResolutionError, match='vollstaendig'):
        replace(result, unknown_information_cells=1)
    with pytest.raises(FrontierTaskResolutionError, match='fingerprint'):
        replace(result, source_fingerprint='not-a-fingerprint')


def test_resolution_module_has_no_ros_navigation_clock_or_device_imports():
    source = (
        PACKAGE_ROOT / 'explore' / 'frontier_task_resolution.py').read_text()
    tree = ast.parse(source)
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(
                alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split('.')[0])
    assert imported_roots.isdisjoint({
        'action_msgs', 'geometry_msgs', 'nav2_msgs', 'rclpy', 'serial',
        'subprocess', 'time',
    })
