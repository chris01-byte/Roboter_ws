// ============================================================================
//  condition_nodes.hpp  -  BT-Condition-Knoten (Topic-Abos)
//  ---------------------------------------------------------------------------
//  Diese Knoten abonnieren ein ROS-2-Topic und liefern bei jedem Tick
//  SUCCESS oder FAILURE - sie fuehren KEINE Aktion aus, sie PRUEFEN nur.
//
//  WICHTIGE PARAMETER (Topic-Namen) -> zentral in config/bt_params.yaml:
//      is_estop_clear.topic        (Standard: /safety/estop)
//      is_object_grasped.topic     (Standard: /gripper/grasp_detected)
//  Die Namen werden in bt_orchestrator_main.cpp gesetzt; hier stehen KEINE
//  fest verdrahteten Topic-Namen.
// ============================================================================
#pragma once

#include "behaviortree_ros2/bt_topic_sub_node.hpp"
#include "std_msgs/msg/bool.hpp"

// ---------------------------------------------------------------------------
//  IsEstopClear
//  SUCCESS  = KEIN Not-Aus aktiv (Roboter darf arbeiten)
//  FAILURE  = Not-Aus aktiv ODER noch keine Nachricht empfangen (sicher)
//
//  Konvention des Topics /safety/estop (std_msgs/Bool):
//      data == true   -> Not-Aus AKTIV
//      data == false  -> frei
// ---------------------------------------------------------------------------
class IsEstopClear : public BT::RosTopicSubNode<std_msgs::msg::Bool>
{
public:
  IsEstopClear(const std::string & name,
               const BT::NodeConfig & conf,
               const BT::RosNodeParams & params)
  : BT::RosTopicSubNode<std_msgs::msg::Bool>(name, conf, params) {}

  // Keine zusaetzlichen Ports noetig.
  static BT::PortsList providedPorts() { return providedBasicPorts({}); }

  // Letzten Zustand behalten: Topic publiziert typischerweise langsamer als
  // der BT tickt. Ohne Latching wuerde jeder Tick ohne neue Nachricht zu
  // FAILURE werden.
  bool latchLastMessage() const override { return true; }

  // Wird bei jedem Tick mit der zuletzt empfangenen Nachricht aufgerufen.
  BT::NodeStatus onTick(const std::shared_ptr<std_msgs::msg::Bool> & last_msg) override
  {
    if (!last_msg) {
      // Noch keine Daten -> sicherheitshalber als "nicht frei" behandeln.
      return BT::NodeStatus::FAILURE;
    }
    return last_msg->data ? BT::NodeStatus::FAILURE   // true  = Not-Aus aktiv
                          : BT::NodeStatus::SUCCESS;   // false = frei
  }
};

// ---------------------------------------------------------------------------
//  IsObjectGrasped
//  SUCCESS  = Drucksensoren melden ein sicher gegriffenes Objekt
//  FAILURE  = kein Objekt / noch keine Nachricht
//
//  Topic /gripper/grasp_detected (std_msgs/Bool): data == true -> gegriffen
// ---------------------------------------------------------------------------
class IsObjectGrasped : public BT::RosTopicSubNode<std_msgs::msg::Bool>
{
public:
  IsObjectGrasped(const std::string & name,
                  const BT::NodeConfig & conf,
                  const BT::RosNodeParams & params)
  : BT::RosTopicSubNode<std_msgs::msg::Bool>(name, conf, params) {}

  static BT::PortsList providedPorts() { return providedBasicPorts({}); }

  bool latchLastMessage() const override { return true; }

  BT::NodeStatus onTick(const std::shared_ptr<std_msgs::msg::Bool> & last_msg) override
  {
    if (!last_msg) {
      return BT::NodeStatus::FAILURE;
    }
    return last_msg->data ? BT::NodeStatus::SUCCESS   // true = gegriffen
                          : BT::NodeStatus::FAILURE;
  }
};

// ---------------------------------------------------------------------------
//  IsOffboardAvailable  (Befund K5)
//  SUCCESS  = KI-Server (Offboard) erreichbar -> Wahrnehmung nutzbar
//  FAILURE  = nicht erreichbar ODER noch keine Nachricht (konservativ)
//
//  Zweck: verhindert, dass ein WLAN-/Serverausfall ungewollt den Explore-
//  Fallback der Objektsuche ausloest. Wird im Baum VOR die Erkundung
//  gesetzt (nur erkunden, wenn die Wahrnehmung ueberhaupt erreichbar ist).
//  Quelle: /offboard/available (std_msgs/Bool) vom link_monitor.
// ---------------------------------------------------------------------------
class IsOffboardAvailable : public BT::RosTopicSubNode<std_msgs::msg::Bool>
{
public:
  IsOffboardAvailable(const std::string & name,
                      const BT::NodeConfig & conf,
                      const BT::RosNodeParams & params)
  : BT::RosTopicSubNode<std_msgs::msg::Bool>(name, conf, params) {}

  static BT::PortsList providedPorts() { return providedBasicPorts({}); }

  bool latchLastMessage() const override { return true; }

  BT::NodeStatus onTick(const std::shared_ptr<std_msgs::msg::Bool> & last_msg) override
  {
    if (!last_msg) {
      // Kein link_monitor / kein Stand -> konservativ als "nicht erreichbar".
      return BT::NodeStatus::FAILURE;
    }
    return last_msg->data ? BT::NodeStatus::SUCCESS   // true  = erreichbar
                          : BT::NodeStatus::FAILURE;   // false = nicht erreichbar
  }
};
