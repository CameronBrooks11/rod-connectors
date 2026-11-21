// A tripod head: three legs spread 120 degrees apart, each 25 degrees out
// from straight down, and a post straight up. Directions by angle with
// dir_spherical(theta, phi): theta from +Z, phi around from +X.
use <../rod_connectors.scad>

$fn = $preview ? 32 : 96;

splay = 25;
rod_connector(
    [
        for (phi = [0, 120, 240]) rod(dir_spherical(180 - splay, phi), diameter=16, depth=40, wall=4),
        rod(dir_spherical(0, 0), diameter=16, depth=30, wall=4, screw=4),
    ]
);
