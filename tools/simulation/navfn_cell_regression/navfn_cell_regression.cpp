// Exercise the actual linked NavFn plugin's protected coordinate methods.
// No lifecycle activation, publisher, motion action, or actuator is created.
#include <cmath>
#include <iostream>
#include <limits>
#include <memory>
#include "nav2_navfn_planner/navfn_planner.hpp"

class CoordinateProbe : public nav2_navfn_planner::NavfnPlanner
{
public:
  CoordinateProbe(double resolution, double x, double y)
  : grid_(new nav2_costmap_2d::Costmap2D(17, 13, resolution, x, y, 0))
  {
    costmap_ = grid_.get();
  }
  using NavfnPlanner::mapToWorld;
  using NavfnPlanner::worldToMap;
private:
  std::unique_ptr<nav2_costmap_2d::Costmap2D> grid_;
};

int main()
{
  unsigned failures = 0, checks = 0;
  auto require = [&](bool condition) {++checks; failures += !condition;};
  for (double resolution : {double(float(.03)), .02, .1}) {
    for (double origin : {-1.89, -.17, 0., 2.13}) {
      CoordinateProbe plugin(resolution, origin, origin+.27);
      for (unsigned col : {0u, 4u, 16u}) {
        for (unsigned row : {0u, 6u, 12u}) {
          double x = 0, y = 0;
          plugin.mapToWorld(col, row, x, y);
          require(std::abs(x-(origin+(col+.5)*resolution)) < 1e-12);
          require(std::abs(y-(origin+.27+(row+.5)*resolution)) < 1e-12);
          unsigned actual_col = 999, actual_row = 999;
          const double measured_x = origin+(col+.5)*resolution;
          const double measured_y = origin+.27+(row+.5)*resolution;
          require(plugin.worldToMap(measured_x, measured_y, actual_col, actual_row));
          require(actual_col == col && actual_row == row);
        }
      }
      unsigned col = 0, row = 0;
      // Last half-cell is in the map; neither upper boundary nor lost data is.
      require(plugin.worldToMap(origin+16.9*resolution,
        origin+.27+12.9*resolution, col, row) && col == 16 && row == 12);
      require(!plugin.worldToMap(origin+17.01*resolution, origin+.27, col, row));
      require(!plugin.worldToMap(origin-.01*resolution, origin+.27, col, row));
      require(!plugin.worldToMap(std::numeric_limits<double>::quiet_NaN(), origin, col, row));
      require(!plugin.worldToMap(origin, std::numeric_limits<double>::infinity(), col, row));
    }
  }
  std::cout << checks << " real NavFn coordinate checks, " << failures << " failures\n";
  return failures ? 1 : 0;
}
