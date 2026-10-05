// Exercise the actual installed native plugin, with unchanged 15 cm / .4 rad.
#include <cmath>
#include <iostream>
#include <string>
#include "nav2_controller/plugins/simple_goal_checker.hpp"
#include "rclcpp_lifecycle/lifecycle_node.hpp"

int main(int argc, char ** argv)
{
  const bool stateful = argc > 1 && std::string(argv[1]) == "true";
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp_lifecycle::LifecycleNode>("ap06_goal_checker_probe");
  node->declare_parameter("checker.xy_goal_tolerance", .15);
  node->declare_parameter("checker.yaw_goal_tolerance", .4);
  node->declare_parameter("checker.stateful", stateful);
  nav2_controller::SimpleGoalChecker checker;
  checker.initialize(node, "checker", nullptr);
  geometry_msgs::msg::Pose goal, pose;
  geometry_msgs::msg::Twist stopped;
  goal.orientation.z = std::sin(.5);
  goal.orientation.w = std::cos(.5);
  pose.orientation.w = 1.;
  pose.position.x = .14;
  const bool premature = checker.isGoalReached(pose, goal, stopped);
  pose.position.x = .16;
  pose.orientation = goal.orientation;
  const bool escaped_window = checker.isGoalReached(pose, goal, stopped);
  pose.position.x = .14;
  const bool valid = checker.isGoalReached(pose, goal, stopped);
  std::cout << "stateful=" << stateful << " premature=" << premature
            << " outside_15cm=" << escaped_window << " valid=" << valid << '\n';
  rclcpp::shutdown();
  return !premature && !escaped_window && valid ? 0 : 1;
}
