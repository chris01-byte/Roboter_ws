// Humble rclpy does not expose publisher_gid in subscription callbacks.
// Observe actual DDS provenance with its native rclcpp MessageInfo API.
#include <rclcpp/rclcpp.hpp>
#include <tf2_msgs/msg/tf_message.hpp>
#include <iostream>
#include <iomanip>
#include <set>
#include <sstream>

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("ap06_tf_ownership_probe");
  std::set<std::string> seen;
  auto subscription = node->create_subscription<tf2_msgs::msg::TFMessage>(
    "/tf", rclcpp::QoS(100),
    [&seen](tf2_msgs::msg::TFMessage::ConstSharedPtr message,
            const rclcpp::MessageInfo & info) {
      const auto & gid = info.get_rmw_message_info().publisher_gid;
      for (const auto & transform : message->transforms) {
        std::ostringstream record;
        record << "{\"parent\":" << std::quoted(transform.header.frame_id)
               << ",\"child\":" << std::quoted(transform.child_frame_id)
               << ",\"gid\":[";
        for (size_t i = 0; i < RMW_GID_STORAGE_SIZE; ++i) {
          record << (i ? "," : "") << static_cast<unsigned int>(gid.data[i]);
        }
        record << "]}";
        if (seen.insert(record.str()).second) {
          std::cout << record.str() << std::endl;
        }
      }
    });
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
