// ============================================================================
//  navigation_nodes.hpp  -  BT-Knoten fuer Navigation (Nav2)
//  ---------------------------------------------------------------------------
//  NavigateToPose : Action-Knoten -> faehrt die Basis zu einer Zielpose.
//  ClearCostmaps  : Service-Knoten -> leert die lokale Costmap (Recovery).
//
//  WICHTIGE PARAMETER (ROS-Namen) -> zentral in config/bt_params.yaml:
//      navigate.action_name           (Standard: navigate_to_pose)
//      clear_costmaps.service_name    (Standard: /local_costmap/clear_entirely_local_costmap)
// ============================================================================
#pragma once

#include "behaviortree_ros2/bt_action_node.hpp"
#include "behaviortree_ros2/bt_service_node.hpp"
#include "nav2_msgs/action/navigate_to_pose.hpp"
#include "nav2_msgs/srv/clear_entire_costmap.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"

// ---------------------------------------------------------------------------
//  NavigateToPose  (Action-Client auf Nav2)
//  Port:  "goal" (PoseStamped, map-Frame) = Wohin die Basis fahren soll.
// ---------------------------------------------------------------------------
class NavigateToPoseNode : public BT::RosActionNode<nav2_msgs::action::NavigateToPose>
{
public:
  NavigateToPoseNode(const std::string & name,
                     const BT::NodeConfig & conf,
                     const BT::RosNodeParams & params)
  : BT::RosActionNode<nav2_msgs::action::NavigateToPose>(name, conf, params) {}

  static BT::PortsList providedPorts()
  {
    return providedBasicPorts({
      BT::InputPort<geometry_msgs::msg::PoseStamped>("goal")   // Zielpose
    });
  }

  // Wird vor dem Senden aufgerufen: Blackboard-Port -> ROS-Goal fuellen.
  bool setGoal(Goal & goal) override
  {
    geometry_msgs::msg::PoseStamped target;
    if (!getInput("goal", target)) {
      RCLCPP_ERROR(logger(), "[NavigateToPose] Port 'goal' fehlt");
      return false;   // ohne Ziel keinen Auftrag senden
    }
    goal.pose = target;
    return true;
  }

  // Ergebnis vom Action-Server ausgewertet.
  BT::NodeStatus onResultReceived(const WrappedResult & wr) override
  {
    return (wr.code == rclcpp_action::ResultCode::SUCCEEDED)
             ? BT::NodeStatus::SUCCESS
             : BT::NodeStatus::FAILURE;   // -> loest im Baum den Recovery-Fallback aus
  }

  // Kommunikationsfehler (Server nicht da, Timeout, ...).
  BT::NodeStatus onFailure(BT::ActionNodeErrorCode error) override
  {
    RCLCPP_ERROR(logger(), "[NavigateToPose] Fehler-Code: %d", static_cast<int>(error));
    return BT::NodeStatus::FAILURE;
  }
};

// ---------------------------------------------------------------------------
//  ClearCostmaps  (Service-Client auf Nav2)
//  Leert die lokale Costmap; nuetzlich als erster Recovery-Schritt, wenn die
//  Navigation klemmt. Kein Port noetig (leerer Request/Response).
// ---------------------------------------------------------------------------
class ClearCostmapsNode : public BT::RosServiceNode<nav2_msgs::srv::ClearEntireCostmap>
{
public:
  ClearCostmapsNode(const std::string & name,
                    const BT::NodeConfig & conf,
                    const BT::RosNodeParams & params)
  : BT::RosServiceNode<nav2_msgs::srv::ClearEntireCostmap>(name, conf, params) {}

  static BT::PortsList providedPorts() { return providedBasicPorts({}); }

  bool setRequest(Request::SharedPtr & /*request*/) override
  {
    return true;   // Request ist leer
  }

  BT::NodeStatus onResponseReceived(const Response::SharedPtr & /*response*/) override
  {
    return BT::NodeStatus::SUCCESS;
  }
};
