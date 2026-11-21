// Native AP-06 regression against the actual pinned/patched Karto methods.
#include <karto_sdk/Karto.h>
#include <cmath>
#include <iostream>
#include <stdexcept>

class BoundedScan : public karto::LocalizedRangeScan {
public:
  BoundedScan(double x0, double y0, double x1, double y1) {
    m_BoundingBox.Add(karto::Vector2<double>(x0, y0));
    m_BoundingBox.Add(karto::Vector2<double>(x1, y1));
    m_IsDirty = false;
  }
};
class GridProbe : public karto::OccupancyGrid {
public:
  using karto::OccupancyGrid::ComputeDimensions;
};
void require(bool condition, const char* message) {
  if (!condition) throw std::runtime_error(message);
}
int main() {
  const double resolution = static_cast<double>(static_cast<float>(.03));
  BoundedScan first(-1.2000001493, -1.40000013287, 4.2, 1.4);
  karto::LocalizedRangeScanVector initial{&first};
  int width, height; karto::Vector2<double> origin;
  GridProbe::ComputeDimensions(initial, resolution, width, height, origin);
  for (const auto &delta : {karto::Vector2<double>(-.001985344847, -.00006557910),
                            karto::Vector2<double>(-.065, -.097),
                            karto::Vector2<double>(-.302, -.151)}) {
    BoundedScan grown(-1.2000001493+delta.GetX(), -1.40000013287+delta.GetY(), 4.3, 1.5);
    karto::LocalizedRangeScanVector scans{&first, &grown};
    int next_width, next_height; karto::Vector2<double> next_origin;
    GridProbe::ComputeDimensions(scans, resolution, next_width, next_height, next_origin);
    const double dx = (origin.GetX()-next_origin.GetX())/resolution;
    const double dy = (origin.GetY()-next_origin.GetY())/resolution;
    require(std::abs(dx-std::round(dx)) < 1e-10 &&
            std::abs(dy-std::round(dy)) < 1e-10, "growth moved the physical lattice");
    karto::OccupancyGrid before(width, height, origin, resolution);
    karto::OccupancyGrid after(next_width, next_height, next_origin, resolution);
    for (auto point : {karto::Vector2<double>(0.,0.), karto::Vector2<double>(.30,-.45),
                       karto::Vector2<double>(-.8,.12)}) {
      auto old_cell = before.WorldToGrid(point), new_cell = after.WorldToGrid(point);
      require(new_cell.GetX()-old_cell.GetX() == std::lround(dx) &&
              new_cell.GetY()-old_cell.GetY() == std::lround(dy),
              "same observed point changed its cell after bounding box growth");
    }
    require(next_origin.GetX() <= grown.GetBoundingBox().GetMinimum().GetX() &&
            next_origin.GetY() <= grown.GetBoundingBox().GetMinimum().GetY(),
            "negative-coordinate bound was cropped");
    auto edge=after.WorldToGrid(grown.GetBoundingBox().GetMaximum());
    require(after.IsValidGridIndex(edge), "farthest measured endpoint was cropped");
  }
  std::cout << "native Karto: stable subcell/growing lattice, negative bounds and endpoint coverage passed\n";
}
