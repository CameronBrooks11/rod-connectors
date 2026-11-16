// A cube-frame corner: three 3/4-inch rods along +X, +Y and +Z.
use <../rod_connectors.scad>

$fn = $preview ? 32 : 96;

d = 19.05;
rod_connector([
  rod([1, 0, 0], diameter=d, depth=35),
  rod([0, 1, 0], diameter=d, depth=35),
  rod([0, 0, 1], diameter=d, depth=35),
]);
