import json
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.exploration_persistence import (  # noqa: E402
    ExplorationPersistenceError,
    ExplorationStateRepository,
    MapVersionBinding,
    binding_from_map_manager_status,
)
from explore.frontier_task_feed import frontier_inventory_from_clusters  # noqa: E402
from explore.map_status_adapter import MapStatusCorrelationResult  # noqa: E402
from explore.portal_memory import (  # noqa: E402
    Point2D,
    PortalMapContext,
    PortalObservation,
    PortalObservationInventory,
    PortalSide,
    PortalStructuralEvidence,
    ReachabilityState,
    ReachabilityUpdate,
    TraversalDirection,
    TraversalEvent,
)
from explore.portal_source_adapter import PortalSourceCorrelation  # noqa: E402
from explore.region_graph import RegionSeed, RegionTaskState  # noqa: E402
from explore.region_graph_shadow import RegionGraphShadowSession  # noqa: E402


FINGERPRINT = "a" * 64
BINDING = MapVersionBinding(
    "wohnung", "20260915T100000Z-aaaaaaaaaaaa", FINGERPRINT,
    100, 80, 0.05, "map")
CONTEXT = PortalMapContext("we-resume", f"map-{FINGERPRINT}", "map")


def manager_status(*, age=0.1, fingerprint=FINGERPRINT,
                   width=100, event="save_result", ok=True):
    saved = {
        "name": BINDING.name, "version": BINDING.version,
        "fingerprint": FINGERPRINT, "width": 100, "height": 80,
        "resolution": 0.05, "frame_id": "map",
    }
    return json.dumps({
        "schema_version": 1, "event": event, "ok": ok,
        "map": {
            "age_seconds": age,
            "summary": {
                "fingerprint": fingerprint, "width": width, "height": 80,
                "resolution": 0.05, "frame_id": "map",
            },
        },
        "storage": {"last_saved": saved},
        "saved": saved,
    })


def map_status(revision=10):
    return MapStatusCorrelationResult(
        context=CONTEXT, map_revision=revision,
        fingerprint=FINGERPRINT, source_stamp_ns=revision,
        source_map_age_seconds=0.1, map_changed=True, replayed=False)


def portal_inventory(revision):
    observation = PortalObservation(
        observation_id=f"portal-observation-{revision}", context=CONTEXT,
        map_revision=revision, near_side=Point2D(1.0, 0.0),
        far_side=Point2D(2.0, 0.0), uncertainty_m=0.01,
        structural_evidence=PortalStructuralEvidence.QUALIFIED)
    return PortalObservationInventory(
        inventory_id=f"portal-inventory-{revision:064x}", context=CONTEXT,
        map_revision=revision, observations=(observation,))


def populated_state():
    shadow = RegionGraphShadowSession(
        map_status(), RegionSeed("start", CONTEXT, 10))
    shadow.observe_portal_inventory(portal_inventory(10))
    shadow.observe_portal_inventory(portal_inventory(11))
    shadow.record_validated_traversal(TraversalEvent(
        event_id="crossing-1", portal_id="portal_000001", context=CONTEXT,
        map_revision=12, event_time_ns=12,
        direction=TraversalDirection.A_TO_B, crossing_confirmed=True))
    shadow.observe_frontier_inventory(frontier_inventory_from_clusters(
        PortalSourceCorrelation(
            CONTEXT, 13, "b" * 64, 13), ((3.0, 0.5, 9),)))
    shadow.update_portal_reachability(ReachabilityUpdate(
        update_id="blocked-side-a", portal_id="portal_000001",
        side=PortalSide.A, context=CONTEXT, map_revision=13,
        observed_at_ns=13, state=ReachabilityState.TEMPORARILY_BLOCKED,
        reason="synthetic_closed_door",
        recheck_condition="fresh_map_and_route_required"))
    return shadow


def test_binding_requires_fresh_successful_exact_map_manager_save():
    assert binding_from_map_manager_status(
        manager_status(), require_successful_save_event=True) == BINDING
    with pytest.raises(ExplorationPersistenceError, match="nicht frisch"):
        binding_from_map_manager_status(manager_status(age=2.1))
    with pytest.raises(ExplorationPersistenceError, match="passt nicht"):
        binding_from_map_manager_status(manager_status(fingerprint="b" * 64))
    with pytest.raises(ExplorationPersistenceError, match="passt nicht"):
        binding_from_map_manager_status(manager_status(width=101))
    with pytest.raises(ExplorationPersistenceError, match="save_result"):
        binding_from_map_manager_status(
            manager_status(event="status"), require_successful_save_event=True)


def test_save_load_restore_preserves_ids_graph_open_tasks_and_blocked_door(
        tmp_path):
    repository = ExplorationStateRepository(tmp_path / "we")
    original = populated_state()
    repository.save(BINDING, original.persistent_state())

    loaded = repository.load(BINDING)
    restored = RegionGraphShadowSession.restore_persistent_state(
        map_status(0), RegionSeed("restart", CONTEXT, 0), loaded.state)
    source = restored.status_source(
        map_status(0), portal_memory_age_seconds=0.0,
        region_graph_age_seconds=0.0)

    assert [item.portal_id for item in source.portals] == ["portal_000001"]
    assert [item.region_id for item in source.graph.regions] == [
        "region_000001", "region_000002"]
    assert source.graph.current_region_id == "region_000002"
    assert [item.task_id for item in source.graph.tasks] == [
        "task-frontier_000001", "task-observe-portal_000001",
        "task-portal-portal_000001"]
    assert source.graph.tasks[0].state is RegionTaskState.OPEN
    assert any(
        item.side is PortalSide.A
        and item.state is ReachabilityState.TEMPORARILY_BLOCKED
        for item in source.reachability)
    # Loading/restoring is pure and returns no intent or navigation target.
    assert not hasattr(loaded, "navigation_goal")


def test_corrupt_newest_falls_back_and_incomplete_temp_is_ignored(tmp_path):
    repository = ExplorationStateRepository(tmp_path / "we")
    first = repository.save(BINDING, {"state_schema": 1, "value": 1})
    newest = repository.save(BINDING, {"state_schema": 1, "value": 2})
    newest.write_text("{broken", encoding="utf-8")
    (newest.parent / ".tmp-incomplete").write_text("partial", encoding="utf-8")

    loaded = repository.load(BINDING)

    assert loaded.path == first
    assert loaded.state["value"] == 1


def test_duplicate_save_event_is_idempotent(tmp_path):
    repository = ExplorationStateRepository(tmp_path / "we")
    state = {"state_schema": 1, "task_ids": ["task-1"]}

    first = repository.save(BINDING, state)
    replay = repository.save(BINDING, state)

    assert replay == first
    assert len(list(first.parent.glob("state-*.json"))) == 1


def test_wrong_map_unknown_schema_and_only_corruption_fail_closed(tmp_path):
    repository = ExplorationStateRepository(tmp_path / "we")
    path = repository.save(BINDING, {"state_schema": 1})
    wrong = MapVersionBinding(
        BINDING.name, BINDING.version, "b" * 64,
        BINDING.width, BINDING.height, BINDING.resolution, BINDING.frame_id)
    with pytest.raises(ExplorationPersistenceError, match="Kein gueltiger"):
        repository.load(wrong)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["schema_version"] = 99
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ExplorationPersistenceError, match="bekanntes Schema"):
        repository.load(BINDING)


def test_manual_semantic_room_file_is_never_touched(tmp_path):
    manual = tmp_path / "semantic_maps" / FINGERPRINT / "manual.json"
    manual.parent.mkdir(parents=True)
    manual.write_text('{"room_name":"Kueche"}', encoding="utf-8")
    repository = ExplorationStateRepository(tmp_path / "we")

    repository.save(BINDING, populated_state().persistent_state())
    repository.load(BINDING)

    assert manual.read_text(encoding="utf-8") == '{"room_name":"Kueche"}'
