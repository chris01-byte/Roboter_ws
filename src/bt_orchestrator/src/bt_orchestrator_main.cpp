// ============================================================================
//  bt_orchestrator_main.cpp  -  Behavior-Tree-Orchestrator als MISSIONS-SERVER
//  ===========================================================================
//  ROLLE (WP-4 / Befund K1):
//    Frueher lief hier EINE Mission beim Start durch und das Programm beendete
//    sich. JETZT ist dieser Node ein DAUERLAEUFER mit einem Action-Server
//    'run_mission' (robot_interfaces/RunMission). Der mission_manager (WP-4)
//    ist der Client: ein Auftrag aus GUI/LLM wird zu einem Goal -> hier laeuft
//    dann der passende Behavior-Tree WIRKLICH (statt Simulation). Damit ist
//    die Luecke zwischen Bedien-Layer und Ausfuehrung geschlossen.
//
//  ABLAUF JE MISSION:
//    Goal rein -> Baum je mission_type waehlen -> Blackboard aus dem Goal
//    fuellen -> mit tick_rate_hz ticken -> echte Phase + Fortschritt als
//    Feedback -> SUCCESS/FAILURE als Result. Genau EINE Mission gleichzeitig
//    (weitere Goals werden abgelehnt).
//
//  THREADING (WICHTIG, bei Portierung beachten):
//    Bewusst SINGLE-THREADED (rclcpp::spin). Der Tick laeuft in einem
//    Wall-Timer; tickOnce() ist nicht-blockierend (RUNNING, solange auf
//    Server gewartet wird). Zwischen den Timer-Ticks bedient derselbe
//    Executor die Action-/Service-Antworten der BT-Knoten. Deshalb KEIN
//    MultiThreadedExecutor noetig - und Goal-Callbacks koennen sich nicht
//    mit dem Tick ueberlappen.
//
//  WICHTIGE PARAMETER -> config/bt_params.yaml (nur dort aendern!).
//  Trockentest: autostart_mission:=pick_and_place startet eine Mission beim
//  Hochfahren selbst (siehe mock_servers/dry_run.launch.py).
// ============================================================================
#include <algorithm>
#include <cmath>
#include <chrono>
#include <functional>
#include <memory>
#include <stdexcept>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"

#include "behaviortree_cpp/bt_factory.h"
#include "behaviortree_cpp/loggers/abstract_logger.h"        // StatusChangeLogger
#include "behaviortree_cpp/loggers/groot2_publisher.h"        // Live-Visualisierung
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "robot_interfaces/action/run_mission.hpp"

// Unsere Knoten (Header-only):
#include "bt_orchestrator/nodes/condition_nodes.hpp"
#include "bt_orchestrator/nodes/navigation_nodes.hpp"
#include "bt_orchestrator/nodes/perception_nodes.hpp"
#include "bt_orchestrator/nodes/manipulation_nodes.hpp"
#include "bt_orchestrator/nodes/exploration_nodes.hpp"

using namespace std::chrono_literals;
using namespace std::placeholders;

using RunMission = robot_interfaces::action::RunMission;
using GoalHandle = rclcpp_action::ServerGoalHandle<RunMission>;

// Kleiner Helfer: baut die RosNodeParams (ROS-Name + Timeout) fuer einen Knoten.
static BT::RosNodeParams makeParams(const rclcpp::Node::SharedPtr & node,
                                    const std::string & ros_name,
                                    std::chrono::milliseconds server_timeout = 5000ms)
{
  BT::RosNodeParams p;
  p.nh = node;
  p.default_port_value = ros_name;
  p.server_timeout = server_timeout;
  return p;
}

// ---------------------------------------------------------------------------
//  PhaseLogger  -  liefert die ECHTE aktuelle Phase (Name des laufenden
//  Blatt-Knotens, z.B. "NavigateToPose") und zaehlt fertige Blaetter fuer
//  eine grobe Fortschrittsschaetzung. Reine Beobachtung, greift nicht ein.
// ---------------------------------------------------------------------------
class PhaseLogger : public BT::StatusChangeLogger
{
public:
  explicit PhaseLogger(BT::TreeNode * root)
  : BT::StatusChangeLogger(root) {}

  void callback(BT::Duration /*t*/, const BT::TreeNode & node,
                BT::NodeStatus prev, BT::NodeStatus status) override
  {
    // Nur Aktionen/Conditions (Blaetter) sind sinnvolle "Phasen" -
    // Kontrollknoten (Sequence/Fallback/...) nicht.
    const bool is_leaf = (node.type() == BT::NodeType::ACTION ||
                          node.type() == BT::NodeType::CONDITION);
    if (!is_leaf) {
      return;
    }
    if (status == BT::NodeStatus::RUNNING) {
      current_phase_ = node.name().empty() ? node.registrationName() : node.name();
    }
    if (prev == BT::NodeStatus::RUNNING && status == BT::NodeStatus::SUCCESS) {
      ++completed_leaves_;
    }
  }
  void flush() override {}

  const std::string & phase() const { return current_phase_; }
  int completed() const { return completed_leaves_; }

private:
  std::string current_phase_{"start"};
  int completed_leaves_{0};
};

// ---------------------------------------------------------------------------
//  MissionServer
// ---------------------------------------------------------------------------
class MissionServer
{
public:
  explicit MissionServer(rclcpp::Node::SharedPtr node)
  : node_(std::move(node))
  {
    // --- Parameter ---
    tick_hz_        = node_->declare_parameter<double>("tick_rate_hz", 10.0);
    subscription_warmup_s_ = node_->declare_parameter<double>(
      "mission_subscription_warmup_s", 1.0);
    default_object_ = node_->declare_parameter<std::string>("target_object", "Tasse");
    enable_groot2_  = node_->declare_parameter<bool>("enable_groot2", true);
    groot2_port_    = node_->declare_parameter<int>("groot2_port", 1667);
    pnp_xml_        = node_->declare_parameter<std::string>("pick_and_place_xml", "bt_xml/pick_and_place.xml");
    explore_xml_    = node_->declare_parameter<std::string>("explore_xml", "bt_xml/explore.xml");
    action_name_    = node_->declare_parameter<std::string>("run_mission.action_name", "/run_mission");
    autostart_      = node_->declare_parameter<std::string>("autostart_mission", "");
    if (!std::isfinite(subscription_warmup_s_) || subscription_warmup_s_ <= 0.0) {
      throw std::invalid_argument(
        "mission_subscription_warmup_s muss endlich und > 0 sein");
    }
    // Rueckwaertskompatibel: bt_xml_file bleibt als Alias fuer pick_and_place_xml.
    const std::string legacy_xml = node_->declare_parameter<std::string>("bt_xml_file", "");
    if (!legacy_xml.empty()) {
      pnp_xml_ = legacy_xml;
    }

    registerNodes();

    action_server_ = rclcpp_action::create_server<RunMission>(
      node_, action_name_,
      std::bind(&MissionServer::handleGoal, this, _1, _2),
      std::bind(&MissionServer::handleCancel, this, _1),
      std::bind(&MissionServer::handleAccepted, this, _1));

    const auto period = std::chrono::duration<double>(1.0 / std::max(1.0, tick_hz_));
    tick_timer_ = node_->create_wall_timer(
      std::chrono::duration_cast<std::chrono::nanoseconds>(period),
      std::bind(&MissionServer::onTick, this));

    RCLCPP_INFO(node_->get_logger(),
                "mission_server bereit -> Action '%s' (%.1f Hz).",
                action_name_.c_str(), tick_hz_);

    if (!autostart_.empty()) {
      // Selbst-Goal fuer den Trockentest (dry_run.launch.py): kurz warten,
      // bis der eigene Server und die Mock-Server erreichbar sind.
      autostart_timer_ = node_->create_wall_timer(
        2s, std::bind(&MissionServer::onAutostart, this));
    }
  }

private:
  // ---- Knoten einmalig registrieren (XML-Name <-> C++-Klasse + ROS-Name) --
  void registerNodes()
  {
    const std::string nav_action    = node_->declare_parameter<std::string>("navigate.action_name", "navigate_to_pose");
    const std::string clear_srv     = node_->declare_parameter<std::string>("clear_costmaps.service_name", "/local_costmap/clear_entirely_local_costmap");
    const std::string getobj_srv    = node_->declare_parameter<std::string>("get_object_pose.service_name", "/world_model/get_object_pose");
    const std::string refine_srv    = node_->declare_parameter<std::string>("refine_object_pose.service_name", "/world_model/refine_object_pose");
    const std::string approach_srv  = node_->declare_parameter<std::string>("compute_approach_pose.service_name", "/planner/compute_approach_pose");
    const std::string grasp_srv     = node_->declare_parameter<std::string>("compute_grasp.service_name", "/grasp/compute");
    const std::string movepose_act  = node_->declare_parameter<std::string>("move_arm_to_pose.action_name", "/move_arm_to_pose");
    const std::string movenamed_act = node_->declare_parameter<std::string>("move_arm_to_named.action_name", "/move_arm_to_named");
    const std::string gripper_act   = node_->declare_parameter<std::string>("gripper.action_name", "/gripper_controller/gripper_cmd");
    const std::string estop_topic   = node_->declare_parameter<std::string>("is_estop_clear.topic", "/safety/estop");
    const std::string grasped_topic = node_->declare_parameter<std::string>("is_object_grasped.topic", "/gripper/grasp_detected");
    const std::string offboard_topic = node_->declare_parameter<std::string>("is_offboard_available.topic", "/offboard/available");
    const std::string explore_action = node_->declare_parameter<std::string>("explore.action_name", "/explore_area");

    factory_.registerNodeType<NavigateToPoseNode>("NavigateToPose", makeParams(node_, nav_action, 120s));
    factory_.registerNodeType<ClearCostmapsNode>("ClearCostmaps", makeParams(node_, clear_srv));
    factory_.registerNodeType<GetObjectPoseNode>("GetObjectPose", makeParams(node_, getobj_srv));
    factory_.registerNodeType<DetectObjectFineNode>("DetectObjectFine", makeParams(node_, refine_srv));
    factory_.registerNodeType<ComputeApproachPoseNode>("ComputeApproachPose", makeParams(node_, approach_srv));
    factory_.registerNodeType<ComputeGraspNode>("ComputeGrasp", makeParams(node_, grasp_srv));
    factory_.registerNodeType<MoveArmToPoseNode>("MoveArmToPose", makeParams(node_, movepose_act, 60s));
    factory_.registerNodeType<MoveArmToNamedNode>("MoveArmToNamed", makeParams(node_, movenamed_act, 60s));
    factory_.registerNodeType<GripperCommandNode>("GripperCommand", makeParams(node_, gripper_act, 30s));
    factory_.registerNodeType<IsEstopClear>("IsEstopClear", makeParams(node_, estop_topic));
    factory_.registerNodeType<IsObjectGrasped>("IsObjectGrasped", makeParams(node_, grasped_topic));
    factory_.registerNodeType<IsOffboardAvailable>("IsOffboardAvailable", makeParams(node_, offboard_topic));
    factory_.registerNodeType<ExploreNode>("Explore", makeParams(node_, explore_action, 3600s));
  }

  static bool quatIsZero(const geometry_msgs::msg::PoseStamped & p)
  {
    return p.pose.orientation.w == 0.0 && p.pose.orientation.x == 0.0 &&
           p.pose.orientation.y == 0.0 && p.pose.orientation.z == 0.0;
  }

  // ---- Action-Callbacks --------------------------------------------------
  rclcpp_action::GoalResponse handleGoal(
    const rclcpp_action::GoalUUID & /*uuid*/,
    std::shared_ptr<const RunMission::Goal> goal)
  {
    if (active_goal_) {
      RCLCPP_WARN(node_->get_logger(),
                  "Neues Goal abgelehnt: es laeuft bereits eine Mission.");
      return rclcpp_action::GoalResponse::REJECT;
    }
    if (goal->mission_type != "pick_and_place" && goal->mission_type != "explore") {
      RCLCPP_WARN(node_->get_logger(),
                  "Goal abgelehnt: kein Behavior-Tree fuer mission_type '%s' hinterlegt.",
                  goal->mission_type.c_str());
      return rclcpp_action::GoalResponse::REJECT;
    }
    return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
  }

  rclcpp_action::CancelResponse handleCancel(std::shared_ptr<GoalHandle> /*gh*/)
  {
    RCLCPP_INFO(node_->get_logger(), "Abbruch angefordert.");
    return rclcpp_action::CancelResponse::ACCEPT;   // im Tick sauber halten
  }

  void handleAccepted(std::shared_ptr<GoalHandle> gh)
  {
    // Nicht blockieren: Baum aufbauen, dann uebernimmt der Tick-Timer.
    if (!startMission(gh)) {
      auto res = std::make_shared<RunMission::Result>();
      res->success = false;
      res->message = "Behavior-Tree konnte nicht geladen werden";
      res->final_phase = "";
      gh->abort(res);
    }
  }

  bool startMission(const std::shared_ptr<GoalHandle> & gh)
  {
    const auto goal = gh->get_goal();
    const bool is_explore = (goal->mission_type == "explore");
    const std::string xml = is_explore ? explore_xml_ : pnp_xml_;

    try {
      tree_ = std::make_unique<BT::Tree>(factory_.createTreeFromFile(xml));
    } catch (const std::exception & e) {
      RCLCPP_FATAL(node_->get_logger(), "Baum '%s' nicht ladbar: %s",
                   xml.c_str(), e.what());
      return false;
    }

    // Blackboard fuellen (Objekt + Ablageposen).
    const std::string obj = goal->object.empty() ? default_object_ : goal->object;
    tree_->rootBlackboard()->set("target_object", obj);

    geometry_msgs::msg::PoseStamped place = goal->place_base_goal;
    if (quatIsZero(place)) {          // Goal ohne Pose -> Default (Trockentest)
      place.header.frame_id = "map";
      place.pose.position.x = 0.0;
      place.pose.position.y = 1.0;
      place.pose.orientation.w = 1.0;
    }
    geometry_msgs::msg::PoseStamped place_pose = goal->place_pose;
    if (quatIsZero(place_pose)) {
      place_pose = place;
    }
    tree_->rootBlackboard()->set("place_base_goal", place);
    tree_->rootBlackboard()->set("place_pose", place_pose);

    phase_logger_ = std::make_unique<PhaseLogger>(tree_->rootNode());
    if (enable_groot2_) {
      try {
        groot_pub_ = std::make_unique<BT::Groot2Publisher>(*tree_, groot2_port_);
      } catch (const std::exception & e) {
        RCLCPP_WARN(node_->get_logger(),
                    "Groot2-Publisher nicht aktiv (Port %d belegt?): %s",
                    groot2_port_, e.what());
        groot_pub_.reset();
      }
    }

    est_total_leaves_ = is_explore ? 1 : 12;   // grobe Basis fuer Fortschritt
    mission_tick_ready_at_ = std::chrono::steady_clock::now() +
      std::chrono::duration_cast<std::chrono::steady_clock::duration>(
        std::chrono::duration<double>(subscription_warmup_s_));
    active_goal_ = gh;
    RCLCPP_INFO(node_->get_logger(),
                "Mission '%s' gestartet (Objekt '%s', Baum '%s'); "
                "Sicherheits-Subscriptions erhalten %.1f s Vorlauf.",
                goal->mission_type.c_str(), obj.c_str(), xml.c_str(),
                subscription_warmup_s_);
    return true;
  }

  // ---- Tick-Schleife (Wall-Timer) ----------------------------------------
  void onTick()
  {
    if (!active_goal_ || !tree_) {
      return;
    }

    if (active_goal_->is_canceling()) {
      tree_->haltTree();
      auto res = std::make_shared<RunMission::Result>();
      res->success = false;
      res->message = "Mission abgebrochen";
      res->final_phase = phase_logger_ ? phase_logger_->phase() : "";
      active_goal_->canceled(res);
      RCLCPP_INFO(node_->get_logger(), "Mission beendet mit Status: CANCELED");
      finishMission();
      return;
    }

    // Topic-basierte BT-Bedingungen werden erst zusammen mit dem Baum
    // erzeugt. Ohne diesen Vorlauf trifft der erste Tick IsEstopClear noch
    // vor der ersten (transient-local und periodischen) Statusnachricht und
    // beendet eine freie Mission faelschlich. Waere das Topic wirklich weg
    // oder der Not-Aus aktiv, liefert der erste Tick danach weiterhin
    // fail-closed FAILURE. Vor dem ersten Tick kann noch keine Action starten.
    if (std::chrono::steady_clock::now() < mission_tick_ready_at_) {
      return;
    }

    BT::NodeStatus status;
    try {
      status = tree_->tickOnce();
    } catch (const std::exception & e) {
      RCLCPP_ERROR(node_->get_logger(), "BT-Ausnahme waehrend Tick: %s", e.what());
      auto res = std::make_shared<RunMission::Result>();
      res->success = false;
      res->message = std::string("BT-Ausnahme: ") + e.what();
      res->final_phase = phase_logger_ ? phase_logger_->phase() : "";
      active_goal_->abort(res);
      finishMission();
      return;
    }

    // Feedback: echte Phase + grobe Fortschrittsschaetzung.
    auto fb = std::make_shared<RunMission::Feedback>();
    fb->phase = phase_logger_ ? phase_logger_->phase() : "";
    const int done = phase_logger_ ? phase_logger_->completed() : 0;
    fb->progress = (status == BT::NodeStatus::SUCCESS)
                     ? 1.0f
                     : std::min(0.95f,
                                static_cast<float>(done) /
                                static_cast<float>(std::max(1, est_total_leaves_)));
    active_goal_->publish_feedback(fb);

    if (status == BT::NodeStatus::RUNNING) {
      return;   // laeuft weiter
    }

    // Mission fertig -> Result. Log-Zeile bewusst identisch zur alten Fassung
    // (Trockentest/Pruefplan A1 grept nach genau diesem Text).
    const bool ok = (status == BT::NodeStatus::SUCCESS);
    RCLCPP_INFO(node_->get_logger(), "Mission beendet mit Status: %s",
                ok ? "SUCCESS" : "FAILURE");

    auto res = std::make_shared<RunMission::Result>();
    res->success = ok;
    res->message = ok ? "Mission erfolgreich" : "Mission fehlgeschlagen (BT FAILURE)";
    res->final_phase = phase_logger_ ? phase_logger_->phase() : "";
    if (ok) {
      active_goal_->succeed(res);
    } else {
      active_goal_->abort(res);
    }
    finishMission();
  }

  void finishMission()
  {
    groot_pub_.reset();
    phase_logger_.reset();
    tree_.reset();
    active_goal_.reset();
  }

  // ---- Autostart (nur Trockentest): Selbst-Goal ueber eigenen Client ------
  void onAutostart()
  {
    autostart_timer_->cancel();
    self_client_ = rclcpp_action::create_client<RunMission>(node_, action_name_);
    if (!self_client_->wait_for_action_server(5s)) {
      RCLCPP_ERROR(node_->get_logger(),
                   "Autostart: eigener Action-Server nicht erreichbar.");
      return;
    }
    RunMission::Goal goal;
    goal.mission_type = autostart_;
    RCLCPP_INFO(node_->get_logger(),
                "Autostart-Mission '%s' (Trockentest).", autostart_.c_str());
    self_client_->async_send_goal(goal);   // Ergebnis erscheint im Log
  }

  // ---- Member ------------------------------------------------------------
  rclcpp::Node::SharedPtr node_;
  BT::BehaviorTreeFactory factory_;

  double tick_hz_{10.0};
  double subscription_warmup_s_{1.0};
  std::string default_object_{"Tasse"};
  bool enable_groot2_{true};
  int groot2_port_{1667};
  std::string pnp_xml_, explore_xml_, action_name_, autostart_;

  rclcpp_action::Server<RunMission>::SharedPtr action_server_;
  rclcpp_action::Client<RunMission>::SharedPtr self_client_;
  rclcpp::TimerBase::SharedPtr tick_timer_;
  rclcpp::TimerBase::SharedPtr autostart_timer_;
  std::chrono::steady_clock::time_point mission_tick_ready_at_{};

  std::shared_ptr<GoalHandle> active_goal_;
  std::unique_ptr<BT::Tree> tree_;
  std::unique_ptr<BT::Groot2Publisher> groot_pub_;
  std::unique_ptr<PhaseLogger> phase_logger_;
  int est_total_leaves_{12};
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("bt_orchestrator");
  auto server = std::make_shared<MissionServer>(node);   // haelt den Server am Leben
  rclcpp::spin(node);                                    // SINGLE-THREADED (s. Kopf)
  rclcpp::shutdown();
  return 0;
}
