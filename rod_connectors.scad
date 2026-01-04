$fn = $preview ? 32 : 128;
z_fight = $preview ? 0.05 : 0;

rod_diameter = 25.4 + 0.2; // 1 inch plus tolerance
connector_wall_thickness = 5; // thickness of connector walls
inner_fn = $fn; // smooth inner clearance
outer_fn = 8; // faceted outer shell

connector_vectors = [
  [50, 0, -40],
  [0, 50, -40],
  [-50, 0, -40],
  [0, -50, -40],
  [0, 0, 50],
];

/* 
connector_vectors = [
  [50, 10, 0],
  [-10, 50, 0],
  [0, 0, 50],
  [-50, -10, 0],
  [10, -50, 0],
  [0, 0, -50],
  [50, 0, 50],
  [50, 0, -50],
  [-50, 0, 50],
  [-50, 0, -50],
]; 
*/

module orient_to_vector(v) {
  d = v / norm(v);

  axis = cross(d, [0, 0, 1]);
  s = norm(axis);
  c = d.z;

  angle = atan2(s, c);

  eps = 1e-9;

  if (s < eps) {
    if (c > 0)
      children();
    // already facing +Z
    else
      rotate(a=180, v=[1, 0, 0]) // facing -Z
        children();
  } else {
    axis_unit = axis / s;
    rotate(a=angle, v=axis_unit)
      children();
  }
}

// Outer solid for one connector
module rod_connector_outer(v) {
  length = norm(v);

  orient_to_vector(v)
    translate([0, 0, 0])
      rotate([0, 0, 360 / outer_fn / 2]) // orient flats along axes
        cylinder(
          h=length + rod_diameter,
          r=rod_diameter / 2 + connector_wall_thickness,
          center=false,
          $fn=outer_fn
        );
}

// Inner clearance for one connector
module rod_connector_inner(v, shift = 0) {
  length = norm(v);

  orient_to_vector(v)
    translate([0, 0, -z_fight / 2 + shift])
      cylinder(
        h=length + z_fight + rod_diameter - shift,
        r=rod_diameter / 2,
        center=false,
        $fn=inner_fn
      );
}

// Union of all outer shells
module assemble_connectors_outer() {
  union() {
    for (v = connector_vectors)
      rod_connector_outer(v);
  }
}

// Union of all inner clearances
module assemble_connectors_inner(shift = 0) {
  union() {
    for (v = connector_vectors)
      rod_connector_inner(v, shift);
  }
}

// Final combined part: all outers minus all inners
difference() {
  assemble_connectors_outer();
  assemble_connectors_inner();
}
