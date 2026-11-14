#!/usr/bin/env python3
"""Device-free DDS smoke for the WE portal single-child runtime.

This script starts only local synthetic ROS nodes.  It publishes no velocity,
opens no device and performs no physical motion.
"""

import json
import os
import threading
import time
from types import SimpleNamespace


os.environ.setdefault("ROS_DOMAIN_ID", "193")

import rclpy  # noqa: E402
from geometry_msgs.msg import Twist  # noqa: E402
from nav2_msgs.action import NavigateToPose  # noqa: E402
from rclpy.action import (  # noqa: E402
    ActionClient,
    ActionServer,
    CancelResponse,
    GoalResponse,
)
from rclpy.callback_groups import ReentrantCallbackGroup  # noqa: E402
from rclpy.executors import MultiThreadedExecutor  # noqa: E402
from rclpy.node import Node  # noqa: E402

from explore.exploration_child_goal import (  # noqa: E402
    ExplorationGoalIntent,
)
from explore.exploration_nav_runtime import (  # noqa: E402
    ExplorationNavigationSession,
)
from explore.explore_node import ExploreNode  # noqa: E402
from explore.portal_memory import (  # noqa: E402
    Point2D,
    PortalConfirmationState,
    PortalMapContext,
    PortalSnapshot,
    TraversalDirection,
    TraversalEvent,
)
from explore.portal_task_evidence import PortalGoalCandidate  # noqa: E402
from explore.portal_traversal_runtime import (  # noqa: E402
    PortalTraversalRuntimeOutcome,
)


class FakeNavServer(Node):
    def __init__(self):
        super().__init__("we_m3t_fake_nav")
        self.goal_count = 0
        self._server = ActionServer(
            self,
            NavigateToPose,
            "/we_m3t_fake_navigate_to_pose",
            execute_callback=self._execute,
            goal_callback=self._goal,
            cancel_callback=self._cancel,
            callback_group=ReentrantCallbackGroup(),
        )

    def _goal(self, _request):
        self.goal_count += 1
        return GoalResponse.ACCEPT

    @staticmethod
    def _cancel(_goal_handle):
        return CancelResponse.ACCEPT

    def _execute(self, goal_handle):
        deadline = time.monotonic() + 0.25
        while time.monotonic() < deadline:
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                return NavigateToPose.Result()
            time.sleep(0.01)
        goal_handle.succeed()
        return NavigateToPose.Result()


class CommandWatcher(Node):
    def __init__(self):
        super().__init__("we_m3t_command_watcher")
        self.messages = []
        self.create_subscription(
            Twist, "/cmd_vel", self.messages.append, 10)
        self.create_subscription(
            Twist, "/cmd_vel_explore_direct_raw", self.messages.append, 10)


def _candidate(context):
    return PortalGoalCandidate(
        intent_id="intent-dds-portal-8",
        task_id="task-portal_000001",
        region_id="region_000002",
        portal_id="portal_000001",
        direction=TraversalDirection.A_TO_B,
        context=context,
        map_revision=8,
        frame_id="map",
        source_fingerprint="a" * 64,
        source_stamp_ns=8_000_000_000,
        scope_id="scope-dds",
        scope_fingerprint="b" * 64,
        target_x_m=1.5,
        target_y_m=0.0,
        target_yaw_rad=0.0,
        target_row=0,
        target_col=2,
        route_length_m=2.0,
        path_cells=((0, 0), (0, 1), (0, 2)),
    )


def _portal():
    return PortalSnapshot(
        portal_id="portal_000001",
        side_a=Point2D(0.0, 0.0),
        side_b=Point2D(1.0, 0.0),
        first_revision=6,
        last_revision=7,
        observation_count=2,
        evidence_count=2,
        qualified_evidence_count=2,
        confirmation_state=PortalConfirmationState.CONFIRMED,
        confirmed=True,
        confirmed_traversal_count=0,
    )


def main():
    rclpy.init()
    fake_nav = FakeNavServer()
    client_node = Node("we_m3t_nav_owner")
    watcher = CommandWatcher()
    executor = MultiThreadedExecutor(num_threads=4)
    for node in (fake_nav, client_node, watcher):
        executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    context = PortalMapContext("session-dds", "map-dds", "map")
    candidate = _candidate(context)
    intent = ExplorationGoalIntent(
        candidate.intent_id,
        candidate.task_id,
        candidate.region_id,
        context,
        candidate.map_revision,
    )
    portal = _portal()
    event = TraversalEvent(
        event_id="validated-dds-portal-8",
        portal_id=portal.portal_id,
        context=context,
        map_revision=8,
        event_time_ns=8_100_000_000,
        direction=TraversalDirection.A_TO_B,
        crossing_confirmed=True,
    )
    monitor_calls = []
    outcome = PortalTraversalRuntimeOutcome(
        confirmed=True,
        reason="full_chassis_crossing_confirmed",
        sample_count=4,
        assessment=SimpleNamespace(traversal_event=event),
    )
    monitor = SimpleNamespace(
        observe=lambda: monitor_calls.append("observe") or True,
        finish=lambda **kwargs: outcome,
    )
    recorded_events = []
    attempts = []

    shadow = SimpleNamespace(
        portal_snapshots=lambda: (portal,),
        record_validated_traversal=lambda selected, **_kwargs: (
            recorded_events.append(selected)
            or SimpleNamespace(graph=SimpleNamespace(entered=True))),
    )
    adapter = ExploreNode.__new__(ExploreNode)
    adapter._nav_client = ActionClient(
        client_node,
        NavigateToPose,
        "/we_m3t_fake_navigate_to_pose",
        callback_group=ReentrantCallbackGroup(),
    )
    adapter._global_frame = "map"
    adapter._behavior_tree = "/synthetic/no_recovery.xml"
    adapter._cancel_timeout_s = 1.0
    adapter._goal_timeout_s = 3.0
    adapter._robot_xy = lambda: (0.0, 0.0)
    adapter._record_coverage_pose = lambda _pose: None
    adapter.get_clock = client_node.get_clock
    adapter.get_logger = client_node.get_logger
    adapter._wohnungserkundung_runtime_lock = threading.Lock()
    adapter._region_graph_shadow_lock = threading.Lock()
    adapter._wohnungserkundung_active_child = None
    adapter._wohnungserkundung_accessible_scope_verified = True
    adapter._wohnungserkundung_portal_monitor_factory = (
        lambda selected, current: monitor
        if selected is candidate and current is portal else None)
    adapter._wohnungserkundung_task_policy_session = SimpleNamespace(
        record_attempt=attempts.append)
    adapter._region_graph_shadow = shadow
    adapter._region_graph_shadow_latest_correlation = SimpleNamespace(
        context=context,
        map_revision=8,
        fingerprint=candidate.source_fingerprint,
        source_stamp_ns=candidate.source_stamp_ns,
    )

    try:
        run, traversal = adapter._run_wohnungserkundung_child(
            ExplorationNavigationSession(context),
            intent,
            candidate,
            SimpleNamespace(is_cancel_requested=False),
            lambda: False,
        )
        time.sleep(0.15)
        result = {
            "ros_domain_id": os.environ["ROS_DOMAIN_ID"],
            "fake_nav_goal_count": fake_nav.goal_count,
            "navigation_status": run.navigation_status,
            "traversal_confirmed": traversal.confirmed,
            "monitor_observation_count": len(monitor_calls),
            "recorded_event_count": len(recorded_events),
            "task_attempt_count": len(attempts),
            "command_message_count": len(watcher.messages),
        }
        assert result["fake_nav_goal_count"] == 1
        assert result["navigation_status"] == "success"
        assert result["traversal_confirmed"] is True
        assert result["monitor_observation_count"] >= 3
        assert result["recorded_event_count"] == 1
        assert result["task_attempt_count"] == 0
        assert result["command_message_count"] == 0
        print(json.dumps(result, sort_keys=True))
    finally:
        executor.shutdown(timeout_sec=2.0)
        for node in (watcher, client_node, fake_nav):
            node.destroy_node()
        rclpy.shutdown()
        spin_thread.join(timeout=2.0)


if __name__ == "__main__":
    main()
