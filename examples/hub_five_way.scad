// Five 1-inch rods: four legs splayed down and out, one post straight up.
// The connector this library started from.
use <../rod_connectors.scad>

$fn = $preview ? 32 : 96;

leg = function(x, y) rod([x, y, -0.8]);

rod_connector(
    [
        leg(1, 0),
        leg(0, 1),
        leg(-1, 0),
        leg(0, -1),
        rod([0, 0, 1]),
    ]
);
