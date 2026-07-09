// ============================================================================
//  perception_nodes.hpp  -  BT-Service-Knoten fuer Wahrnehmung & Planung
//  ---------------------------------------------------------------------------
//  GetObjectPose        : Welt-Modell nach Objektpose fragen.
//  DetectObjectFine     : Objektpose im Nahbereich verfeinern (RefineObjectPose).
//  ComputeApproachPose  : Objektpose -> erreichbare Basis-Zielpose.
//  ComputeGrasp         : Objektpose -> Greif-/Vorgreifpose + Greiferweite.
//
//  WICHTIGE PARAMETER (ROS-Namen) -> zentral in config/bt_params.yaml:
//      get_object_pose.service_name        (/world_model/get_object_pose)
//      refine_object_pose.service_name     (/world_model/refine_object_pose)
//      compute_approach_pose.service_name  (/planner/compute_approach_pose)
//      compute_grasp.service_name          (/grasp/compute)
// ============================================================================
#pragma once

#include "behaviortree_ros2/bt_service_node.hpp"
#include "robot_interfaces/srv/get_object_pose.hpp"
#include "robot_interfaces/srv/refine_object_pose.hpp"
#include "robot_interfaces/srv/compute_approach_pose.hpp"
#include "robot_interfaces/srv/compute_grasp.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"

// ---------------------------------------------------------------------------
//  GetObjectPose
//  In : "target" (string)         = Objektklasse, z.B. "cup"
//  Out: "pose"   (PoseStamped)    = gefundene Pose (map)
// ---------------------------------------------------------------------------
class GetObjectPoseNode : public BT::RosServiceNode<robot_interfaces::srv::GetObjectPose>
{
public:
  GetObjectPoseNode(const std::string & name,
                    const BT::NodeConfig & conf,
                    const BT::RosNodeParams & params)
  : BT::RosServiceNode<robot_interfaces::srv::GetObjectPose>(name, conf, params) {}

  static BT::PortsList providedPorts()
  {
    return providedBasicPorts({
      BT::InputPort<std::string>("target"),
      BT::OutputPort<geometry_msgs::msg::PoseStamped>("pose")
    });
  }

  bool setRequest(Request::SharedPtr & request) override
  {
    return getInput("target", request->class_name).has_value();
  }

  BT::NodeStatus onResponseReceived(const Response::SharedPtr & response) override
  {
    if (!response->found) {
      return BT::NodeStatus::FAILURE;   // Objekt (noch) nicht bekannt
    }
    setOutput("pose", response->pose);  // Ergebnis aufs Blackboard schreiben
    return BT::NodeStatus::SUCCESS;
  }
};

// ---------------------------------------------------------------------------
//  DetectObjectFine  (nutzt Service RefineObjectPose)
//  In : "pose_in"  (PoseStamped)  = grobe Pose
//  Out: "pose_out" (PoseStamped)  = verfeinerte Pose
//  Im XML werden beide auf dieselbe Blackboard-Variable {object_pose} gemappt.
// ---------------------------------------------------------------------------
class DetectObjectFineNode : public BT::RosServiceNode<robot_interfaces::srv::RefineObjectPose>
{
public:
  DetectObjectFineNode(const std::string & name,
                       const BT::NodeConfig & conf,
                       const BT::RosNodeParams & params)
  : BT::RosServiceNode<robot_interfaces::srv::RefineObjectPose>(name, conf, params) {}

  static BT::PortsList providedPorts()
  {
    return providedBasicPorts({
      BT::InputPort<geometry_msgs::msg::PoseStamped>("pose_in"),
      BT::OutputPort<geometry_msgs::msg::PoseStamped>("pose_out")
    });
  }

  bool setRequest(Request::SharedPtr & request) override
  {
    return getInput("pose_in", request->coarse_pose).has_value();
  }

  BT::NodeStatus onResponseReceived(const Response::SharedPtr & response) override
  {
    if (!response->success) {
      return BT::NodeStatus::FAILURE;
    }
    setOutput("pose_out", response->refined_pose);
    return BT::NodeStatus::SUCCESS;
  }
};

// ---------------------------------------------------------------------------
//  ComputeApproachPose
//  In : "object_pose" (PoseStamped), "standoff" (double, [m])
//  Out: "base_goal"   (PoseStamped)
// ---------------------------------------------------------------------------
class ComputeApproachPoseNode : public BT::RosServiceNode<robot_interfaces::srv::ComputeApproachPose>
{
public:
  ComputeApproachPoseNode(const std::string & name,
                          const BT::NodeConfig & conf,
                          const BT::RosNodeParams & params)
  : BT::RosServiceNode<robot_interfaces::srv::ComputeApproachPose>(name, conf, params) {}

  static BT::PortsList providedPorts()
  {
    return providedBasicPorts({
      BT::InputPort<geometry_msgs::msg::PoseStamped>("object_pose"),
      BT::InputPort<double>("standoff"),
      BT::OutputPort<geometry_msgs::msg::PoseStamped>("base_goal")
    });
  }

  bool setRequest(Request::SharedPtr & request) override
  {
    if (!getInput("object_pose", request->object_pose)) {
      return false;
    }
    double standoff = 0.5;             // Default, falls Port leer
    getInput("standoff", standoff);
    request->standoff = static_cast<float>(standoff);
    return true;
  }

  BT::NodeStatus onResponseReceived(const Response::SharedPtr & response) override
  {
    if (!response->success) {
      return BT::NodeStatus::FAILURE;
    }
    setOutput("base_goal", response->base_goal);
    return BT::NodeStatus::SUCCESS;
  }
};

// ---------------------------------------------------------------------------
//  ComputeGrasp
//  In : "object_pose"   (PoseStamped)
//  Out: "grasp_pose"    (PoseStamped)
//       "pregrasp_pose" (PoseStamped)
//       "gripper_width" (double, [m])
// ---------------------------------------------------------------------------
class ComputeGraspNode : public BT::RosServiceNode<robot_interfaces::srv::ComputeGrasp>
{
public:
  ComputeGraspNode(const std::string & name,
                   const BT::NodeConfig & conf,
                   const BT::RosNodeParams & params)
  : BT::RosServiceNode<robot_interfaces::srv::ComputeGrasp>(name, conf, params) {}

  static BT::PortsList providedPorts()
  {
    return providedBasicPorts({
      BT::InputPort<geometry_msgs::msg::PoseStamped>("object_pose"),
      BT::OutputPort<geometry_msgs::msg::PoseStamped>("grasp_pose"),
      BT::OutputPort<geometry_msgs::msg::PoseStamped>("pregrasp_pose"),
      BT::OutputPort<double>("gripper_width")
    });
  }

  bool setRequest(Request::SharedPtr & request) override
  {
    // object_cloud bleibt leer; der Server kann die Punktwolke selbst beschaffen.
    return getInput("object_pose", request->object_pose).has_value();
  }

  BT::NodeStatus onResponseReceived(const Response::SharedPtr & response) override
  {
    if (!response->success) {
      return BT::NodeStatus::FAILURE;
    }
    setOutput("grasp_pose", response->grasp_pose);
    setOutput("pregrasp_pose", response->pregrasp_pose);
    setOutput("gripper_width", static_cast<double>(response->gripper_width));
    return BT::NodeStatus::SUCCESS;
  }
};
