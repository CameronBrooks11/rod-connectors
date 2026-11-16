// rod-connectors: printable hubs that join round rods at any angles.
//
//   use <rod_connectors.scad>
//
//   rod_connector([
//     rod([1, 0, -0.8]),
//     rod([0, 1, -0.8], diameter=12.7),
//     rod([0, 0, 1], screw=4),
//   ]);
//
// Each rod gets a socket: a bore that runs `depth` into the hub and stops at
// a solid core, so a rod seats against it instead of meeting the others in
// the middle. The core is as small as it can be without two bores breaking
// into each other.
//
// Units are millimetres. Directions are any non-zero vector; only their
// direction is used.

// ---- Rods --------------------------------------------------------------------

// A rod: the direction it leaves the hub, and the socket that takes it.
//
//   dir            direction from the hub's centre along the rod
//   diameter       the rod's diameter
//   depth          how far the rod goes into its socket
//   wall           socket wall thickness
//   clearance      added to the bore's diameter so the rod slides in
//   inner_fn       facets of the bore (undef: $fn)
//   outer_fn       facets of the outside; 8 prints with flat faces
//   screw          diameter of a set-screw hole through the wall, 0 for none
//   slot           width of a clamping slit along the socket, 0 for none
//   feature_angle  where around the rod the screw hole goes, in degrees;
//                  the slot goes opposite it
function rod(dir, diameter = 25.4, depth = 50, wall = 5, clearance = 0.2,
             inner_fn = undef, outer_fn = 8, screw = 0, slot = 0, feature_angle = 0) =
  assert(is_list(dir) && len(dir) == 3 && norm(dir) > 0,
         str("rod: dir must be a non-zero [x, y, z], got ", dir))
  assert(diameter > 0, str("rod: diameter must be > 0, got ", diameter))
  assert(depth > 0, str("rod: depth must be > 0, got ", depth))
  assert(wall > 0, str("rod: wall must be > 0, got ", wall))
  assert(clearance >= 0, str("rod: clearance must be >= 0, got ", clearance))
  assert(screw >= 0 && screw < 2 * wall + diameter,
         str("rod: screw must be >= 0 and narrower than the socket, got ", screw))
  assert(slot >= 0 && slot < diameter + clearance,
         str("rod: slot must be >= 0 and narrower than the bore, got ", slot))
  ["rod", dir / norm(dir), diameter, depth, wall, clearance, inner_fn, outer_fn,
   screw, slot, feature_angle];

function rod_dir(r) = r[1];
function rod_diameter(r) = r[2];
function rod_depth(r) = r[3];
function rod_wall(r) = r[4];
function rod_clearance(r) = r[5];
function rod_bore_radius(r) = (r[2] + r[5]) / 2;
function rod_outer_radius(r) = rod_bore_radius(r) + r[4];

// ---- Geometry helpers ------------------------------------------------------------

// The transform that turns the socket's own axis, +Z, onto the unit vector d:
// a rotation about Y by d's polar angle, then about Z by its azimuth.
function rod_matrix(d) =
  let(
    theta = acos(max(-1, min(1, d.z))),
    phi = atan2(d.y, d.x),
    ct = cos(theta), st = sin(theta), cp = cos(phi), sp = sin(phi)
  )
  [[cp * ct, -sp, cp * st, 0],
   [sp * ct, cp, sp * st, 0],
   [-st, 0, ct, 0],
   [0, 0, 0, 1]];

function _angle(a, b) = acos(max(-1, min(1, a * b)));

// How far from the centre rod i's bore starts. Two bores of radius R whose
// axes meet at angle a keep a wall of thickness w between them, half on each
// side of the plane between them, once each starts at
// R / tan(a / 2) + w / (2 sin(a / 2)) or further. w is the thinner of the two
// rods' walls. Each bore starts at the largest such distance over the other
// rods, and at least `core` out.
function rod_connector_stop(rods, i, core = 3) =
  max(concat([core], [
    for (j = [0:len(rods) - 1]) if (j != i)
      let(
        a = _angle(rod_dir(rods[i]), rod_dir(rods[j])),
        r = max(rod_bore_radius(rods[i]), rod_bore_radius(rods[j])),
        w = min(rod_wall(rods[i]), rod_wall(rods[j]))
      )
      r / tan(a / 2) + w / (2 * sin(a / 2))
  ]));

// ---- Parts -------------------------------------------------------------------

// A hub joining `rods`, a list of rod() values. `core` is the least distance
// from the centre to the bottom of any socket.
module rod_connector(rods, core = 3) {
  assert(is_list(rods) && len(rods) > 0, "rod_connector: rods must be a non-empty list of rod()");
  for (i = [0:len(rods) - 1])
    assert(rods[i][0] == "rod", str("rod_connector: rods[", i, "] is not a rod()"));
  assert(core >= 0, str("rod_connector: core must be >= 0, got ", core));
  for (i = [0:len(rods) - 1], j = [0:len(rods) - 1])
    if (i < j)
      assert(_angle(rod_dir(rods[i]), rod_dir(rods[j])) > 1,
             str("rod_connector: rods ", i, " and ", j, " point the same way"));

  stops = [for (i = [0:len(rods) - 1]) rod_connector_stop(rods, i, core)];

  difference() {
    union()
      for (i = [0:len(rods) - 1])
        multmatrix(rod_matrix(rod_dir(rods[i])))
          _socket_outer(rods[i], stops[i]);
    for (i = [0:len(rods) - 1])
      multmatrix(rod_matrix(rod_dir(rods[i])))
        _socket_cut(rods[i], stops[i]);
  }
}

// The space rod r fills when pushed fully home: its own diameter, from the
// bottom of its socket to the mouth, where `extra` mm more would push it.
// For checking a design, not for printing.
module rod_body(rods, i, core = 3, extra = 0) {
  r = rods[i];
  stop = rod_connector_stop(rods, i, core);
  multmatrix(rod_matrix(rod_dir(r)))
    translate([0, 0, stop - extra])
      cylinder(h = rod_depth(r) + extra, r = rod_diameter(r) / 2,
               $fn = r[6] == undef ? $fn : r[6]);
}

// One socket's outside, along +Z from the centre to the mouth. The flats of
// a faceted outside face along the axes.
module _socket_outer(r, stop) {
  n = r[7];
  rotate([0, 0, 180 / n])
    cylinder(h = stop + rod_depth(r), r = rod_outer_radius(r), $fn = n);
}

// What one socket removes: the bore, and any screw hole or slot. The bore
// runs a little past the mouth so the cut is clean.
module _socket_cut(r, stop) {
  eps = 0.01;
  depth = rod_depth(r);
  inner_fn = r[6] == undef ? $fn : r[6];
  translate([0, 0, stop])
    cylinder(h = depth + eps, r = rod_bore_radius(r), $fn = inner_fn);
  // Set screw: through one wall, halfway along the socket.
  if (r[8] > 0)
    translate([0, 0, stop + depth / 2])
      rotate([0, 0, r[10]])
        rotate([0, 90, 0])
          cylinder(h = rod_outer_radius(r) + eps, r = r[8] / 2, $fn = 24);
  // Clamping slot: through the opposite wall, from the mouth to halfway down.
  if (r[9] > 0)
    translate([0, 0, stop + depth / 2])
      rotate([0, 0, r[10] + 180])
        translate([0, -r[9] / 2, 0])
          cube([rod_outer_radius(r) + eps, r[9], depth / 2 + eps]);
}
