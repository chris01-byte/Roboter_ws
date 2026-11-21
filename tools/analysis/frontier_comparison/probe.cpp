// Comparison-only stdin/stdout bridge to the unmodified, pinned upstream core.
// No ROS node, Nav2 client, publisher, mission or persistent suppression state.
#include <iostream>
#include <iomanip>
#include "frontier_exploration_ros2/frontier_search.hpp"
int main() {
  using namespace frontier_exploration_ros2;
  nav_msgs::msg::OccupancyGrid map, cost;
  geometry_msgs::msg::Pose pose;
  int w, h, value, minimum;
  double resolution, ox, oy, yaw;
  if (!(std::cin >> w >> h >> resolution >> ox >> oy >> yaw
        >> pose.position.x >> pose.position.y >> minimum) ||
      w <= 0 || h <= 0 || resolution <= 0 || w * h > 1000000) return 2;
  // Upstream ignores rotation. Explicitly reject it, as the AP-04 contract permits.
  if (std::abs(yaw) > 1e-9) { std::cout << "unsupported_origin_rotation\n"; return 0; }
  map.info.width=w; map.info.height=h; map.info.resolution=resolution;
  map.info.origin.position.x=ox; map.info.origin.position.y=oy;
  map.info.origin.orientation.w=1.;
  for (int i=0; i<w*h; ++i) { if (!(std::cin >> value)) return 2; map.data.push_back(value); }
  cost=map; cost.data.clear();
  for (int i=0; i<w*h; ++i) { if (!(std::cin >> value)) return 2; cost.data.push_back(value); }
  FrontierSearchOptions options; options.min_frontier_size_cells=minimum;
  const auto result=get_frontier(pose,OccupancyGrid2d(map),OccupancyGrid2d(cost),std::nullopt,0.,false,options);
  std::cout << std::setprecision(17);
  for (const auto & f: result.frontiers)
    std::cout << f.center_point.first << ' ' << f.center_point.second << ' ' << f.size << '\n';
}
