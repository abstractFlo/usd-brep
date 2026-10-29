"""Check an installed usd-brep wheel: it imports, tessellates a box, and the face of every
polygon comes back (the face_ids cadler added) and matches the box's six faces; a chamfer sets the
two faces of an edge back by distances of their own (chamfer_edges_two_distances, cadler's too).

    python cadler/smoke.py
"""

import numpy as np
import usd_brep as ub

box = ub.create_box((0.0, 0.0, 0.0), 10.0, 20.0, 30.0)
poly = ub.tessellate(box, chord_height_tolerance=0.01, surface_angle_tolerance_deg=10.0, curve_angle_tolerance_deg=10.0)
arr = poly.to_numpy_arrays(face_varying_normals=True, source=box)
ids = np.asarray(arr["face_ids"])
assert len(box.faces()) == 6, len(box.faces())
assert len(ids) > 0 and set(ids.tolist()) == set(range(6)), sorted(set(ids.tolist()))
print(f"usd-brep {ub.__file__}: {len(ids)} polygons on {len(box.faces())} faces")

# the box's edge between its top (z = 30) and its front (y = 0): 2 on the reference face, 5 on the other
for reference, (on_top, on_front) in (("top", (2, 5)), ("front", (5, 2))):
    body = ub.create_box((0.0, 0.0, 0.0), 10.0, 20.0, 30.0)
    edge = next(e for e in body.edges() if all(abs(v.point()[1]) < 1e-9 and abs(v.point()[2] - 30) < 1e-9 for v in e.vertices()))
    faces = {name: next(f for f in edge.faces() if all(abs(v.point()[axis] - at) < 1e-9 for v in f.vertices())) for name, axis, at in (("top", 2, 30), ("front", 1, 0))}
    ub.chamfer_edges_two_distances(body, [edge], [faces[reference]], [2.0], [5.0])
    points = [v.point() for v in body.vertices()]
    assert abs(body.volume() - (6000 - 0.5 * 2 * 5 * 10)) < 1e-6, body.volume()
    assert any(abs(p[1] - on_top) < 1e-6 and abs(p[2] - 30) < 1e-6 for p in points), (reference, points)
    assert any(abs(p[1]) < 1e-6 and abs(p[2] - (30 - on_front)) < 1e-6 for p in points), (reference, points)
print("chamfer with two distances: the setbacks as asked, on either face")
