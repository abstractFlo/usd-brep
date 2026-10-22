"""Check an installed usd-brep wheel: it imports, tessellates a box, and the face of every
polygon comes back (the face_ids cadler added) and matches the box's six faces.

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
