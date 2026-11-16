"""Check rod_connectors.scad by rendering it.

usage: python3 tests/test_rod_connectors.py [OPENSCAD]

- Every example renders with --hardwarnings, as one solid.
- rod_matrix turns the socket's axis, +Z, onto each rod's direction.
- Every rod in the test connectors goes fully home without touching the hub,
  and 1 mm further hits the core: the socket has a floor.
- No two rods at full depth touch each other, and every two bores keep the
  thinner rod's wall between them.
- dir_spherical, dir_euler and dir_quat give the directions they describe:
  dir_euler matches where OpenSCAD's own rotate() takes +Z, and the other two
  match the maths, and each other where they describe the same rotation.
- rod() and rod_connector() refuse bad input with their messages.
"""

import json
import math
import os
import struct
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "rod_connectors.scad")

# Connectors to probe, as OpenSCAD lists of rod() values.
CONNECTORS = {
    "five-way hub": "[for (v = [[1,0,-0.8],[0,1,-0.8],[-1,0,-0.8],[0,-1,-0.8]]) rod(v), rod([0,0,1])]",
    "cube corner": "[rod([1,0,0], diameter=19.05, depth=35), rod([0,1,0], diameter=19.05, depth=35),"
                   " rod([0,0,1], diameter=19.05, depth=35)]",
    "mixed rods": "[rod([0,0,1], screw=4), rod([1,0,0], diameter=12.7, depth=30, wall=4, slot=2),"
                  " rod([-1,1,-1], diameter=10, depth=25, wall=3)]",
    "close pair": "[rod([1,0,0], diameter=10, depth=20, wall=2), rod([1,0.6,0], diameter=16, depth=20, wall=3)]",
}

results = []


def check(label, ok, got):
    results.append(ok)
    print(f"{'ok  ' if ok else 'FAIL'} {label}: {got}")


def run(openscad, source, out, tmp, hard=False):
    path = os.path.join(tmp, "probe.scad")
    with open(path, "w") as f:
        f.write(f"use <{LIB}>\n$fn = 48;\n"
                "function transpose(m) = [for (j = [0:len(m[0]) - 1]) [for (i = [0:len(m) - 1]) m[i][j]]];\n"
                + source)
    cmd = [openscad, "-o", out] + (["--hardwarnings"] if hard else [])
    if out.endswith(".stl"):
        cmd += ["--export-format", "binstl"]
    return subprocess.run(cmd + [path], capture_output=True, text=True)


def empty(result):
    return "top level object is empty" in result.stderr


def echoes(result):
    """ECHO values. OpenSCAD prints about 6 significant digits, so compare them to 1e-5."""
    return [json.loads(l.split("ECHO: ", 1)[1]) for l in result.stderr.splitlines()
            if l.startswith("ECHO: ")]


def solids(path):
    """How many separate solids a binary STL holds, by joining shared corners."""
    data = open(path, "rb").read()
    (n,) = struct.unpack_from("<I", data, 80)
    parent = {}

    def find(v):
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    for i in range(n):
        v = struct.unpack_from("<9f", data, 84 + i * 50 + 12)
        corners = [v[0:3], v[3:6], v[6:9]]
        for c in corners:
            parent.setdefault(c, c)
        root = find(corners[0])
        for c in corners[1:]:
            parent[find(c)] = root
    return len({find(v) for v in parent})


def main():
    openscad = sys.argv[1] if len(sys.argv) > 1 else "openscad"
    with tempfile.TemporaryDirectory() as tmp:
        stl = os.path.join(tmp, "out.stl")
        csg = os.path.join(tmp, "out.csg")

        # Examples.
        for name in sorted(os.listdir(os.path.join(ROOT, "examples"))):
            if not name.endswith(".scad"):
                continue
            r = subprocess.run([openscad, "--hardwarnings", "--export-format", "binstl", "-o", stl,
                                os.path.join(ROOT, "examples", name)], capture_output=True, text=True)
            bad = [l for l in r.stderr.splitlines() if "WARNING" in l or "ERROR" in l]
            ok = r.returncode == 0 and not bad
            check(f"examples/{name} renders as one solid", ok and solids(stl) == 1,
                  bad[:1] or (f"{solids(stl)} solid(s)" if ok else f"exit {r.returncode}"))

        # Orientation.
        dirs = [[0, 0, 1], [0, 0, -1], [1, 0, 0], [0, -1, 0], [1, 1, -0.8], [-1, 1, -1], [0.3, -2, 0.5]]
        src = "".join(f"d = {d} / norm({d}); echo([rod_matrix(d) * [0,0,1,0], d]);\n" for d in dirs)
        worst = max(max(abs(a - b) for a, b in zip(got[:3], want))
                    for got, want in echoes(run(openscad, src, csg, tmp)))
        check("rod_matrix turns +Z onto each direction", worst < 1e-5, f"largest error {worst:.1e}")
        # And it is a pure rotation, so sockets keep their shape: orthonormal, determinant 1.
        src = "".join(f"d = {d} / norm({d}); m = rod_matrix(d); r = [for (i = [0:2]) [for (j = [0:2]) m[i][j]]];"
                      " echo([r * transpose(r), r[0] * cross(r[1], r[2])]);\n" for d in dirs)
        worst = 0
        for rrt, det in echoes(run(openscad, src, csg, tmp)):
            worst = max([worst, abs(det - 1)] + [abs(rrt[i][j] - (1 if i == j else 0))
                                                 for i in range(3) for j in range(3)])
        check("rod_matrix is a rotation", worst < 1e-5, f"largest error {worst:.1e}")

        # Directions from other descriptions.
        angles = [(0, 0, 0), (90, 0, 0), (0, 90, 0), (30, -45, 120), (-60, 20, -75), (180, 10, 45)]
        worst = 0
        for roll, pitch, yaw in angles:
            # Where OpenSCAD's rotate() puts a point 10 mm up +Z: a small sphere's centre.
            r = run(openscad, f"echo(dir_euler({roll}, {pitch}, {yaw}));\n"
                    f"rotate([{roll}, {pitch}, {yaw}]) translate([0, 0, 10]) sphere(0.5, $fn = 8);\n",
                    stl, tmp)
            (got,) = echoes(r)
            data = open(stl, "rb").read()
            (n,) = struct.unpack_from("<I", data, 80)
            pts = [struct.unpack_from("<3f", data, 84 + i * 50 + 12 + k * 12) for i in range(n) for k in range(3)]
            centre = [(max(p[a] for p in pts) + min(p[a] for p in pts)) / 2 / 10 for a in range(3)]
            worst = max([worst] + [abs(g - c) for g, c in zip(got, centre)])
        check("dir_euler matches OpenSCAD's rotate()", worst < 1e-3, f"largest difference {worst:.1e}")

        cases = [(theta, phi) for theta in (0, 30, 90, 135, 180) for phi in (0, 45, -120)]
        src = "".join(f"echo(dir_spherical({th}, {ph}));\n" for th, ph in cases)
        worst = max(max(abs(g - w) for g, w in zip(got, [math.sin(math.radians(th)) * math.cos(math.radians(ph)),
                                                          math.sin(math.radians(th)) * math.sin(math.radians(ph)),
                                                          math.cos(math.radians(th))]))
                    for got, (th, ph) in zip(echoes(run(openscad, src, csg, tmp)), cases))
        check("dir_spherical gives the direction at (theta, phi)", worst < 1e-5, f"largest error {worst:.1e}")

        # A quaternion for a turn of t degrees about an axis, against the same turn as a rotation matrix
        # (Rodrigues' formula), and unnormalised quaternions against normalised ones.
        def rodrigues(axis, t):
            k = [a / math.sqrt(sum(b * b for b in axis)) for a in axis]
            c, s = math.cos(math.radians(t)), math.sin(math.radians(t))
            z = [0, 0, 1]
            kxz = [k[1] * z[2] - k[2] * z[1], k[2] * z[0] - k[0] * z[2], k[0] * z[1] - k[1] * z[0]]
            kdz = sum(a * b for a, b in zip(k, z))
            return [z[i] * c + kxz[i] * s + k[i] * kdz * (1 - c) for i in range(3)]
        turns = [([1, 0, 0], 90), ([0, 1, 0], 90), ([1, 1, 0], 60), ([1, -2, 3], 140), ([0, 0, 1], 75)]
        src = ""
        for axis, t in turns:
            n = math.sqrt(sum(a * a for a in axis))
            h = math.radians(t) / 2
            q = [math.cos(h)] + [math.sin(h) * a / n for a in axis]
            src += f"echo(dir_quat({q}));\necho(dir_quat({[3 * v for v in q]}));\n"
        got = echoes(run(openscad, src, csg, tmp))
        worst = max(max(abs(g - w) for g, w in zip(got[2 * k + m], rodrigues(axis, t)))
                    for k, (axis, t) in enumerate(turns) for m in (0, 1))
        check("dir_quat turns +Z as the quaternion's rotation does, at any scale", worst < 1e-5,
              f"largest error {worst:.1e}")

        # Sockets: each rod fits fully home, and has a floor.
        for label, rods in CONNECTORS.items():
            count = echoes(run(openscad, f"echo(len({rods}));\n", csg, tmp))[0]
            for i in range(count):
                # Seated: 0.01 mm short of the floor, so the probe doesn't share its face.
                home = run(openscad, f"rods = {rods};\nintersection() {{ rod_connector(rods); "
                           f"rod_body(rods, {i}, extra=-0.01); }}\n", stl, tmp)
                deeper = run(openscad, f"rods = {rods};\nintersection() {{ rod_connector(rods); "
                             f"rod_body(rods, {i}, extra=1); }}\n", stl, tmp)
                check(f"{label}: rod {i} fits fully home, and stops at the floor",
                      empty(home) and not empty(deeper) and deeper.returncode == 0,
                      f"home {'clear' if empty(home) else 'touches the hub'}, "
                      f"1 mm deeper {'is stopped' if not empty(deeper) else 'passes through'}")

            # Bores: rods don't touch, and a wall stands between every two bores.
            for i in range(count):
                for j in range(i + 1, count):
                    rods_touch = run(openscad, f"rods = {rods};\nintersection() {{ rod_body(rods, {i}); "
                                     f"rod_body(rods, {j}); }}\n", stl, tmp)
                    # Each bore grown evenly by just under half the thinner wall: they must not meet.
                    grown = (f"rods = {rods};\n"
                             f"w = min(rod_wall(rods[{i}]), rod_wall(rods[{j}])) / 2 - 0.05;\n"
                             "module bore(k) { r = rods[k]; s = rod_connector_stop(rods, k);\n"
                             "  minkowski() { multmatrix(rod_matrix(rod_dir(r))) translate([0, 0, s])\n"
                             "    cylinder(h = rod_depth(r), r = rod_bore_radius(r)); sphere(w, $fn = 16); } }\n"
                             f"intersection() {{ bore({i}); bore({j}); }}\n")
                    walls = run(openscad, grown, stl, tmp)
                    check(f"{label}: rods {i} and {j} clear each other, with a wall between their bores",
                          empty(rods_touch) and empty(walls),
                          f"rods {'clear' if empty(rods_touch) else 'touch'}, "
                          f"wall {'kept' if empty(walls) else 'too thin'}")

        # Features: a probe through the screw hole and one through the slot are clear,
        # and hit solid wall on a socket without them.
        for label, feature, probe in [
            ("set-screw hole", "screw=4",
             "translate([0, 0, s + 25]) rotate([0, 90, 0]) cylinder(h = 30, r = 1.5, $fn = 12);"),
            ("clamping slot", "slot=2",
             "rotate([0, 0, 180]) translate([0, -0.75, s + 40]) cube([30, 1.5, 5]);"),
        ]:
            got = []
            for with_feature in (True, False):
                rods = f"[rod([0, 0, 1]{', ' + feature if with_feature else ''})]"
                r = run(openscad, f"rods = {rods};\ns = rod_connector_stop(rods, 0);\n"
                        f"intersection() {{ rod_connector(rods); {probe} }}\n", stl, tmp)
                got.append(empty(r))
            check(f"the {label} goes through the wall", got == [True, False],
                  f"probe {'clear' if got[0] else 'blocked'} with it, {'clear' if got[1] else 'blocked'} without")

        # Refusals.
        for label, source_text, message in [
            ("refuses a zero direction", "echo(rod([0, 0, 0]));", "dir must be a non-zero"),
            ("refuses a non-positive diameter", "echo(rod([0, 0, 1], diameter=0));", "diameter must be > 0"),
            ("refuses a screw wider than the socket", "echo(rod([0, 0, 1], screw=50));", "screw must be"),
            ("refuses two rods pointing the same way",
             "rod_connector([rod([0, 0, 1]), rod([0, 0, 2])]);", "point the same way"),
            ("refuses something that isn't a rod", "rod_connector([[0, 0, 1]]);", "is not a rod()"),
            ("refuses a zero quaternion", "echo(dir_quat([0, 0, 0, 0]));", "q must be a non-zero"),
        ]:
            r = run(openscad, source_text + "\n", stl, tmp)
            errors = [l for l in r.stderr.splitlines() if "ERROR" in l]
            check(label, bool(r.returncode != 0 and errors and message in errors[0]),
                  errors[0] if errors else f"exit {r.returncode}, no error")

    print(f"{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


main()
