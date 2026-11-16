// One hub, three rod sizes: a 1-inch post held by a set screw, a 1/2-inch
// arm that clamps with a slot, and a 10 mm stay at an angle.
use <../rod_connectors.scad>

$fn = $preview ? 32 : 96;

rod_connector([
  rod([0, 0, 1], diameter=25.4, screw=4),
  rod([1, 0, 0], diameter=12.7, depth=30, wall=4, slot=2, feature_angle=90),
  rod([-1, 1, -1], diameter=10, depth=25, wall=3),
]);
