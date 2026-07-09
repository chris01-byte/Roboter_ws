#!/usr/bin/env python3
# ============================================================================
#  mock_servers_node.py  -  Trockenlauf-Server fuer den Behavior-Tree (WP-2)
#  ---------------------------------------------------------------------------
#  Stellt ALLE Gegenstellen bereit, die der bt_orchestrator aufruft, und
#  antwortet mit erfundenen (festen) Ergebnissen. So laeuft der komplette
#  Pick-and-Place-Baum OHNE Hardware, Nav2 oder MoveIt durch.
#
#  Bereitgestellt:
#    Actions : /navigate_to_pose, /move_arm_to_pose, /move_arm_to_named,
#              /gripper_controller/gripper_cmd
#    Services: /world_model/get_object_pose, /world_model/refine_object_pose,
#              /planner/compute_approach_pose, /grasp/compute,
#              /local_costmap/clear_entirely_local_costmap
#    Topics  : /safety/estop (Bool), /gripper/grasp_detected (Bool)
#
#  TESTSCHALTER (Dauer, gezielte Fehler) -> config/mock_params.yaml
#  (dort steht oben ein Zeilen-Index).
# ============================================================================

import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy

from std_msgs.msg import Bool
from geometry_msgs.msg import PoseStamped

from nav2_msgs.action import NavigateToPose
from nav2_msgs.srv import ClearEntireCostmap
from control_msgs.action import GripperCommand

from robot_interfaces.action import MoveArmToPose, MoveArmToNamed, ExploreArea
from robot_interfaces.srv import (
    GetObjectPose, RefineObjectPose, ComputeApproachPose, ComputeGrasp)


class MockServers(Node):
    def __init__(self):
        super().__init__('mock_servers')
        cb = ReentrantCallbackGroup()   # erlaubt parallele Callbacks (Timer + Actions)

        # -------------------------------------------------------------------
        #  Parameter (Defaults; Override via config/mock_params.yaml)
        # -------------------------------------------------------------------
        self.declare_parameter('nav_duration', 1.5)
        self.declare_parameter('arm_duration', 1.0)
        self.declare_parameter('gripper_duration', 0.5)
        self.declare_parameter('explore_duration', 2.0)
        self.declare_parameter('service_delay', 0.2)
        self.declare_parameter('object_found', True)
        self.declare_parameter('grasp_succeeds', True)
        self.declare_parameter('fail_navigation', False)
        self.declare_parameter('fail_arm', False)
        self.declare_parameter('estop_active', False)
        self.declare_parameter('close_position_threshold', 0.05)
        # publish_estop=false -> Mock ueberlaesst /safety/estop dem safety_monitor
        # (fuer Kombi-Tests: echte Mission + echter Not-Aus-Waechter).
        self.declare_parameter('publish_estop', True)
        # provide_navigation=false -> Mock stellt /navigate_to_pose und den
        # Costmap-Clear-Service NICHT bereit (Kombi-Test mit ECHTEM Nav2,
        # sonst gaebe es zwei Server auf demselben Action-Namen).
        self.declare_parameter('provide_navigation', True)

        gp = self.get_parameter
        self.nav_duration = float(gp('nav_duration').value)
        self.arm_duration = float(gp('arm_duration').value)
        self.gripper_duration = float(gp('gripper_duration').value)
        self.explore_duration = float(gp('explore_duration').value)
        self.service_delay = float(gp('service_delay').value)
        self.object_found = bool(gp('object_found').value)
        self.grasp_succeeds = bool(gp('grasp_succeeds').value)
        self.fail_navigation = bool(gp('fail_navigation').value)
        self.fail_arm = bool(gp('fail_arm').value)
        self.estop_active = bool(gp('estop_active').value)
        self.close_threshold = float(gp('close_position_threshold').value)
        self.publish_estop = bool(gp('publish_estop').value)
        self.provide_navigation = bool(gp('provide_navigation').value)

        # -------------------------------------------------------------------
        #  Topics
        #  /safety/estop          : latched (transient_local) -> spaete Sub bekommen Stand
        #  /gripper/grasp_detected: wird je nach Greifer-Kommando gesetzt
        # -------------------------------------------------------------------
        latched = QoSProfile(depth=1)
        latched.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL
        latched.reliability = QoSReliabilityPolicy.RELIABLE
        self.grasp_pub = self.create_publisher(Bool, '/gripper/grasp_detected', 10)

        self.is_grasped = False
        self._publish_grasp()
        self.create_timer(0.2, self._publish_grasp, callback_group=cb)

        # /safety/estop nur publizieren, wenn nicht der safety_monitor die
        # Quelle ist (publish_estop=false -> Kombi-Test mit echtem Waechter).
        if self.publish_estop:
            self.estop_pub = self.create_publisher(Bool, '/safety/estop', latched)
            self._publish_estop()
            self.create_timer(0.2, self._publish_estop, callback_group=cb)

        # -------------------------------------------------------------------
        #  Action-Server
        # -------------------------------------------------------------------
        # cancel_callback=ACCEPT (K7): ohne diesen lehnt rclpy Cancel per Default
        # ab - dann laeuft die Aktion trotz Not-Aus/Abbruch stur zu Ende.
        if self.provide_navigation:
            ActionServer(self, NavigateToPose, '/navigate_to_pose',
                         execute_callback=self.exec_nav,
                         cancel_callback=self._on_cancel, callback_group=cb)
        ActionServer(self, MoveArmToPose, '/move_arm_to_pose',
                     execute_callback=self.exec_arm_pose,
                     cancel_callback=self._on_cancel, callback_group=cb)
        ActionServer(self, MoveArmToNamed, '/move_arm_to_named',
                     execute_callback=self.exec_arm_named,
                     cancel_callback=self._on_cancel, callback_group=cb)
        ActionServer(self, GripperCommand, '/gripper_controller/gripper_cmd',
                     execute_callback=self.exec_gripper,
                     cancel_callback=self._on_cancel, callback_group=cb)
        # /explore_area (K5/I5): ohne diesen Mock war der Explore-Zweig der
        # Objektsuche im Trockentest gar nicht durchspielbar.
        ActionServer(self, ExploreArea, '/explore_area',
                     execute_callback=self.exec_explore,
                     cancel_callback=self._on_cancel, callback_group=cb)

        # -------------------------------------------------------------------
        #  Service-Server
        # -------------------------------------------------------------------
        self.create_service(GetObjectPose, '/world_model/get_object_pose',
                            self.srv_get_object, callback_group=cb)
        self.create_service(RefineObjectPose, '/world_model/refine_object_pose',
                            self.srv_refine, callback_group=cb)
        self.create_service(ComputeApproachPose, '/planner/compute_approach_pose',
                            self.srv_approach, callback_group=cb)
        self.create_service(ComputeGrasp, '/grasp/compute',
                            self.srv_grasp, callback_group=cb)
        if self.provide_navigation:
            # Beim echten Nav2 stellt die Costmap diesen Service selbst bereit.
            self.create_service(ClearEntireCostmap, '/local_costmap/clear_entirely_local_costmap',
                                self.srv_clear, callback_group=cb)

        self.get_logger().info('Mock-Server bereit: alle Actions/Services/Topics laufen.')

    # ======================= Abbruch (K7) ===============================
    def _on_cancel(self, goal_handle):
        # Alle laufenden Mock-Aktionen duerfen abgebrochen werden.
        return CancelResponse.ACCEPT

    def _sleep_cancelable(self, goal_handle, duration: float) -> bool:
        """Wartet 'duration' Sekunden, prueft dabei ~alle 50 ms auf Abbruch.
        Rueckgabe: True, wenn abgebrochen wurde (Aufrufer soll sauber beenden)."""
        steps = max(1, int(duration / 0.05))
        for _ in range(steps):
            if goal_handle.is_cancel_requested:
                return True
            time.sleep(0.05)
        return False

    # ======================= Topic-Helfer ===============================
    def _publish_estop(self):
        self.estop_pub.publish(Bool(data=self.estop_active))

    def _publish_grasp(self):
        self.grasp_pub.publish(Bool(data=self.is_grasped))

    def _fake_pose(self, frame='map', x=1.0, y=0.0, z=0.0):
        p = PoseStamped()
        p.header.frame_id = frame
        p.header.stamp = self.get_clock().now().to_msg()
        p.pose.position.x = x
        p.pose.position.y = y
        p.pose.position.z = z
        p.pose.orientation.w = 1.0
        return p

    # ======================= Action-Callbacks ===========================
    def exec_nav(self, goal_handle):
        self.get_logger().info('[mock] NavigateToPose ...')
        steps = max(1, int(self.nav_duration * 5))
        for i in range(steps):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                return NavigateToPose.Result()
            fb = NavigateToPose.Feedback()
            fb.distance_remaining = float(steps - i) * 0.1
            goal_handle.publish_feedback(fb)
            time.sleep(0.2)
        if self.fail_navigation:
            self.get_logger().warn('[mock] NavigateToPose ABBRUCH (fail_navigation=true)')
            goal_handle.abort()
            return NavigateToPose.Result()
        goal_handle.succeed()
        return NavigateToPose.Result()

    def exec_arm_pose(self, goal_handle):
        self.get_logger().info('[mock] MoveArmToPose ...')
        res = MoveArmToPose.Result()
        if self._sleep_cancelable(goal_handle, self.arm_duration):
            res.success = False
            res.message = 'mock canceled'
            goal_handle.canceled()
            return res
        if self.fail_arm:
            res.success = False
            res.message = 'mock fail_arm'
            goal_handle.abort()
            return res
        res.success = True
        res.message = 'mock ok'
        goal_handle.succeed()
        return res

    def exec_arm_named(self, goal_handle):
        name = goal_handle.request.target_name
        self.get_logger().info(f'[mock] MoveArmToNamed -> "{name}" ...')
        res = MoveArmToNamed.Result()
        if self._sleep_cancelable(goal_handle, self.arm_duration):
            res.success = False
            res.message = 'mock canceled'
            goal_handle.canceled()
            return res
        res.success = True
        res.message = f'mock at {name}'
        goal_handle.succeed()
        return res

    def exec_gripper(self, goal_handle):
        pos = float(goal_handle.request.command.position)
        closing = pos < self.close_threshold
        self.get_logger().info(
            f'[mock] Gripper position={pos:.3f} ({"schliessen" if closing else "oeffnen"})')
        if self._sleep_cancelable(goal_handle, self.gripper_duration):
            res = GripperCommand.Result()
            res.position = pos
            goal_handle.canceled()
            return res
        # Greif-Detektion setzen (Timer publiziert sie kontinuierlich weiter).
        self.is_grasped = bool(closing and self.grasp_succeeds)
        self._publish_grasp()
        time.sleep(0.15)  # kurz warten, damit das Topic VOR dem Action-Result ankommt
        res = GripperCommand.Result()
        res.position = pos
        res.effort = float(goal_handle.request.command.max_effort)
        res.reached_goal = True
        res.stalled = self.is_grasped   # stalled=true -> hat auf Objekt zugegriffen
        goal_handle.succeed()
        return res

    def exec_explore(self, goal_handle):
        self.get_logger().info('[mock] ExploreArea ...')
        res = ExploreArea.Result()
        if self._sleep_cancelable(goal_handle, self.explore_duration):
            res.success = False
            res.message = 'mock explore canceled'
            res.frontiers_visited = 0
            goal_handle.canceled()
            return res
        res.success = True
        res.message = 'mock explore fertig'
        res.frontiers_visited = 3
        res.explored_area_m2 = 12.0
        goal_handle.succeed()
        return res

    # ======================= Service-Callbacks ==========================
    def srv_get_object(self, req, res):
        time.sleep(self.service_delay)
        res.found = self.object_found
        res.pose = self._fake_pose('map', 1.0, 0.0, 0.2)
        res.confidence = 0.9 if self.object_found else 0.0
        self.get_logger().info(f'[mock] GetObjectPose("{req.class_name}") -> found={res.found}')
        return res

    def srv_refine(self, req, res):
        time.sleep(self.service_delay)
        res.success = True
        res.refined_pose = req.coarse_pose   # einfach durchreichen
        return res

    def srv_approach(self, req, res):
        time.sleep(self.service_delay)
        res.success = True
        goal = req.object_pose
        goal.pose.position.x -= req.standoff  # simpler Standoff entlang x
        res.base_goal = goal
        return res

    def srv_grasp(self, req, res):
        time.sleep(self.service_delay)
        res.success = True
        res.grasp_pose = req.object_pose
        res.pregrasp_pose = self._fake_pose(
            req.object_pose.header.frame_id,
            req.object_pose.pose.position.x,
            req.object_pose.pose.position.y,
            req.object_pose.pose.position.z + 0.10)  # 10 cm darueber
        res.gripper_width = 0.03   # < close_position_threshold -> gilt als "schliessen"
        return res

    def srv_clear(self, req, res):
        # ClearEntireCostmap hat leere Response
        return res


def main(args=None):
    rclpy.init(args=args)
    node = MockServers()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
