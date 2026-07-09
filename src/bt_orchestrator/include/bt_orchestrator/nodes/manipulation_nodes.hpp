// ============================================================================
//  manipulation_nodes.hpp  -  BT-Action-Knoten fuer Arm & Greifer
//  ---------------------------------------------------------------------------
//  MoveArmToPose   : TCP zu kartesischer Zielpose (Server kapselt MoveIt 2).
//  MoveArmToNamed  : Arm in benannte Pose ("stowed" / "ready").
//  GripperCommand  : Greifer oeffnen/schliessen (control_msgs/GripperCommand).
//
//  WICHTIGE PARAMETER (ROS-Namen) -> zentral in config/bt_params.yaml:
//      move_arm_to_pose.action_name    (/move_arm_to_pose)
//      move_arm_to_named.action_name   (/move_arm_to_named)
//      gripper.action_name             (/gripper_controller/gripper_cmd)
// ============================================================================
#pragma once

#include "behaviortree_ros2/bt_action_node.hpp"
#include "robot_interfaces/action/move_arm_to_pose.hpp"
#include "robot_interfaces/action/move_arm_to_named.hpp"
#include "control_msgs/action/gripper_command.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"

// ---------------------------------------------------------------------------
//  MoveArmToPose
//  In: "pose" (PoseStamped) = Ziel-Pose des TCP.
// ---------------------------------------------------------------------------
class MoveArmToPoseNode : public BT::RosActionNode<robot_interfaces::action::MoveArmToPose>
{
public:
  MoveArmToPoseNode(const std::string & name,
                    const BT::NodeConfig & conf,
                    const BT::RosNodeParams & params)
  : BT::RosActionNode<robot_interfaces::action::MoveArmToPose>(name, conf, params) {}

  static BT::PortsList providedPorts()
  {
    return providedBasicPorts({
      BT::InputPort<geometry_msgs::msg::PoseStamped>("pose")
    });
  }

  bool setGoal(Goal & goal) override
  {
    return getInput("pose", goal.target_pose).has_value();
  }

  BT::NodeStatus onResultReceived(const WrappedResult & wr) override
  {
    const bool ok = (wr.code == rclcpp_action::ResultCode::SUCCEEDED) && wr.result->success;
    return ok ? BT::NodeStatus::SUCCESS : BT::NodeStatus::FAILURE;
  }

  BT::NodeStatus onFailure(BT::ActionNodeErrorCode error) override
  {
    RCLCPP_ERROR(logger(), "[MoveArmToPose] Fehler-Code: %d", static_cast<int>(error));
    return BT::NodeStatus::FAILURE;
  }
};

// ---------------------------------------------------------------------------
//  MoveArmToNamed
//  In: "target_name" (string) = "stowed" oder "ready".
// ---------------------------------------------------------------------------
class MoveArmToNamedNode : public BT::RosActionNode<robot_interfaces::action::MoveArmToNamed>
{
public:
  MoveArmToNamedNode(const std::string & name,
                     const BT::NodeConfig & conf,
                     const BT::RosNodeParams & params)
  : BT::RosActionNode<robot_interfaces::action::MoveArmToNamed>(name, conf, params) {}

  static BT::PortsList providedPorts()
  {
    return providedBasicPorts({
      BT::InputPort<std::string>("target_name")
    });
  }

  bool setGoal(Goal & goal) override
  {
    return getInput("target_name", goal.target_name).has_value();
  }

  BT::NodeStatus onResultReceived(const WrappedResult & wr) override
  {
    const bool ok = (wr.code == rclcpp_action::ResultCode::SUCCEEDED) && wr.result->success;
    return ok ? BT::NodeStatus::SUCCESS : BT::NodeStatus::FAILURE;
  }

  BT::NodeStatus onFailure(BT::ActionNodeErrorCode error) override
  {
    RCLCPP_ERROR(logger(), "[MoveArmToNamed] Fehler-Code: %d", static_cast<int>(error));
    return BT::NodeStatus::FAILURE;
  }
};

// ---------------------------------------------------------------------------
//  GripperCommand  (control_msgs/action/GripperCommand)
//  In: "position"   (double, [m]) = Ziel-Oeffnung/-Schliessweite
//      "max_effort" (double)      = max. Greifkraft
//  Erfolg: reached_goal ODER stalled (stalled = der Greifer hat auf ein
//  Objekt zugegriffen -> beim Schliessen erwuenscht).
// ---------------------------------------------------------------------------
class GripperCommandNode : public BT::RosActionNode<control_msgs::action::GripperCommand>
{
public:
  GripperCommandNode(const std::string & name,
                     const BT::NodeConfig & conf,
                     const BT::RosNodeParams & params)
  : BT::RosActionNode<control_msgs::action::GripperCommand>(name, conf, params) {}

  static BT::PortsList providedPorts()
  {
    return providedBasicPorts({
      BT::InputPort<double>("position"),
      BT::InputPort<double>("max_effort")
    });
  }

  bool setGoal(Goal & goal) override
  {
    double position = 0.0;
    double max_effort = 20.0;          // Default-Greifkraft
    if (!getInput("position", position)) {
      RCLCPP_ERROR(logger(), "[GripperCommand] Port 'position' fehlt");
      return false;
    }
    getInput("max_effort", max_effort);
    goal.command.position = position;
    goal.command.max_effort = max_effort;
    return true;
  }

  BT::NodeStatus onResultReceived(const WrappedResult & wr) override
  {
    if (wr.code != rclcpp_action::ResultCode::SUCCEEDED) {
      return BT::NodeStatus::FAILURE;
    }
    const bool ok = wr.result->reached_goal || wr.result->stalled;
    return ok ? BT::NodeStatus::SUCCESS : BT::NodeStatus::FAILURE;
  }

  BT::NodeStatus onFailure(BT::ActionNodeErrorCode error) override
  {
    RCLCPP_ERROR(logger(), "[GripperCommand] Fehler-Code: %d", static_cast<int>(error));
    return BT::NodeStatus::FAILURE;
  }
};
