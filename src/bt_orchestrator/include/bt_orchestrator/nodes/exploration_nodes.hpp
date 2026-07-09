// ============================================================================
//  exploration_nodes.hpp  -  BT-Knoten fuer autonome Erkundung (WP-5, Ebene 1)
//  ---------------------------------------------------------------------------
//  Explore : Action-Knoten -> startet die Frontier-Exploration (explore_node).
//            Der Knoten bleibt RUNNING, bis die Wohnung vollstaendig erkundet
//            ist ODER ein Timeout/Abbruch greift. Danach SUCCESS bzw. FAILURE.
//
//  WICHTIGE PARAMETER (ROS-Namen) -> zentral in config/bt_params.yaml:
//      explore.action_name    (Standard: /explore_area)
//
//  Ports (optional, mit sinnvollen Defaults):
//      timeout_s            max. Erkundungsdauer [s] (0 = unbegrenzt)
//      min_frontier_size_m  kleinste beachtete Frontier [m] (0 = Node-Default)
//      return_to_start      nach Fertigstellung zur Startpose zurueck
// ============================================================================
#pragma once

#include "behaviortree_ros2/bt_action_node.hpp"
#include "robot_interfaces/action/explore_area.hpp"

// ---------------------------------------------------------------------------
//  Explore  (Action-Client auf explore_node)
// ---------------------------------------------------------------------------
class ExploreNode : public BT::RosActionNode<robot_interfaces::action::ExploreArea>
{
public:
  ExploreNode(const std::string & name,
              const BT::NodeConfig & conf,
              const BT::RosNodeParams & params)
  : BT::RosActionNode<robot_interfaces::action::ExploreArea>(name, conf, params) {}

  static BT::PortsList providedPorts()
  {
    return providedBasicPorts({
      BT::InputPort<double>("timeout_s", 0.0, "Max. Erkundungsdauer [s], 0=unbegrenzt"),
      BT::InputPort<double>("min_frontier_size_m", 0.0, "Kleinste Frontier [m], 0=Node-Default"),
      BT::InputPort<bool>("return_to_start", false, "Nach Fertigstellung zurueck zur Startpose")
    });
  }

  // Blackboard-Ports -> ROS-Goal fuellen.
  bool setGoal(Goal & goal) override
  {
    double timeout = 0.0;
    double min_frontier = 0.0;
    bool return_to_start = false;
    getInput("timeout_s", timeout);
    getInput("min_frontier_size_m", min_frontier);
    getInput("return_to_start", return_to_start);
    goal.timeout_s = static_cast<float>(timeout);
    goal.min_frontier_size_m = static_cast<float>(min_frontier);
    goal.return_to_start = return_to_start;
    return true;
  }

  // Ergebnis vom Explore-Server: nur SUCCESS, wenn wirklich sauber erkundet.
  BT::NodeStatus onResultReceived(const WrappedResult & wr) override
  {
    if (wr.code == rclcpp_action::ResultCode::SUCCEEDED && wr.result->success) {
      RCLCPP_INFO(logger(), "[Explore] fertig: %s (Frontiers=%d)",
                  wr.result->message.c_str(), wr.result->frontiers_visited);
      return BT::NodeStatus::SUCCESS;
    }
    RCLCPP_WARN(logger(), "[Explore] nicht erfolgreich: %s",
                wr.result ? wr.result->message.c_str() : "kein Ergebnis");
    return BT::NodeStatus::FAILURE;
  }

  // Kommunikationsfehler (Server nicht da, Timeout, ...).
  BT::NodeStatus onFailure(BT::ActionNodeErrorCode error) override
  {
    RCLCPP_ERROR(logger(), "[Explore] Fehler-Code: %d", static_cast<int>(error));
    return BT::NodeStatus::FAILURE;
  }
};
