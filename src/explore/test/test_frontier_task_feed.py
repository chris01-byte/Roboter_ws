from copy import deepcopy
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.frontier_task_feed import (  # noqa: E402
    FrontierTaskFeedCapacityError,
    FrontierTaskFeedError,
    FrontierTaskPolicy,
    FrontierTaskTracker,
    frontier_inventory_from_clusters,
)
from explore.portal_memory import PortalMapContext  # noqa: E402
from explore.portal_source_adapter import PortalSourceCorrelation  # noqa: E402


CONTEXT = PortalMapContext("session-1", "map-1", "map")


def correlation(revision=1, fingerprint=None, stamp=None):
    return PortalSourceCorrelation(
        context=CONTEXT,
        map_revision=revision,
        fingerprint=fingerprint or f"{revision:064x}",
        source_stamp_ns=stamp or revision,
    )


def inventory(revision, clusters):
    return frontier_inventory_from_clusters(
        correlation(revision), clusters)


def test_inventory_is_exact_order_independent_and_replayable():
    first = frontier_inventory_from_clusters(
        correlation(), [(2.0, 1.0, 7), (0.0, 0.0, 4)])
    reordered = frontier_inventory_from_clusters(
        correlation(), [(0.0, 0.0, 4), (2.0, 1.0, 7)])
    tracker = FrontierTaskTracker(CONTEXT)

    accepted = tracker.observe(first)
    before_replay = tracker.tracks()
    replay = tracker.observe(reordered)

    assert first == reordered
    assert accepted.duplicate is False
    assert replay.duplicate is True
    assert tuple(item.frontier_id for item in accepted.assignments) == (
        "frontier_000001", "frontier_000002")
    assert tracker.tracks() == before_replay


def test_unique_nearby_cluster_keeps_identity_across_map_growth():
    tracker = FrontierTaskTracker(
        CONTEXT, policy=FrontierTaskPolicy(association_radius_m=0.60))
    created = tracker.observe(inventory(1, [(1.0, 2.0, 20)]))
    matched = tracker.observe(inventory(2, [(1.2, 2.1, 24)]))

    assert created.assignments[0].created is True
    assert matched.assignments[0].created is False
    assert matched.assignments[0].frontier_id == (
        created.assignments[0].frontier_id)
    assert tracker.tracks()[0].observation_count == 2
    assert tracker.tracks()[0].last_revision == 2


def test_missing_cluster_never_deletes_or_completes_a_track():
    tracker = FrontierTaskTracker(CONTEXT)
    tracker.observe(inventory(1, [(1.0, 2.0, 20)]))

    empty = tracker.observe(inventory(2, []))

    assert empty.assignments == ()
    assert tuple(track.frontier_id for track in tracker.tracks()) == (
        "frontier_000001",)
    assert tracker.tracks()[0].last_revision == 1


def test_ambiguous_geometry_never_silently_merges_existing_tracks():
    tracker = FrontierTaskTracker(
        CONTEXT, policy=FrontierTaskPolicy(association_radius_m=0.60))
    tracker.observe(inventory(1, [(0.0, 0.0, 5), (0.8, 0.0, 5)]))

    ambiguous = tracker.observe(inventory(2, [(0.4, 0.0, 8)]))

    assert ambiguous.assignments[0].created is True
    assert ambiguous.assignments[0].frontier_id == "frontier_000003"
    assert tuple(track.frontier_id for track in tracker.tracks()) == (
        "frontier_000001", "frontier_000002", "frontier_000003")

    repeated = tracker.observe(inventory(3, [(0.4, 0.0, 8)]))

    assert repeated.assignments[0].created is False
    assert repeated.assignments[0].frontier_id == "frontier_000003"
    assert len(tracker.tracks()) == 3


def test_same_revision_with_different_inventory_fails_closed():
    tracker = FrontierTaskTracker(CONTEXT)
    tracker.observe(inventory(1, [(0.0, 0.0, 5)]))

    with pytest.raises(FrontierTaskFeedError, match="bereits einen anderen"):
        tracker.observe(frontier_inventory_from_clusters(
            correlation(1, fingerprint="f" * 64, stamp=2),
            [(2.0, 0.0, 5)],
        ))


def test_capacity_failure_does_not_mutate_tracks():
    tracker = FrontierTaskTracker(
        CONTEXT,
        policy=FrontierTaskPolicy(max_frontiers=1),
    )
    tracker.observe(inventory(1, [(0.0, 0.0, 5)]))
    before = deepcopy(tracker.tracks())

    with pytest.raises(FrontierTaskFeedCapacityError, match="voll"):
        tracker.observe(inventory(2, [(2.0, 0.0, 5)]))

    assert tracker.tracks() == before
    assert tracker.latest_revision == 1


@pytest.mark.parametrize("clusters", [None, [(0.0, 0.0, 0)], [(float("nan"), 0.0, 1)]])
def test_invalid_inventory_inputs_fail_closed(clusters):
    with pytest.raises((FrontierTaskFeedError, TypeError)):
        frontier_inventory_from_clusters(correlation(), clusters)
