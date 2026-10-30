# Changelog of cadler's usd-brep

What this fork changed in NVIDIA's usd-brep, per version in `cadler/version`, newest first;
NVIDIA's own changes are in `CHANGELOG.md`. Written from the git history by
`cadler/changelog.py`; do not edit it by hand.

## 1.0.1+cadler.7 - 2026-10-30 (not released yet)

- SMLib straightens the end of a fillet/fillet intersection where the two surfaces touch: G2 rounds meeting at a box corner end their miter at the vertex along the bisector, without a cluster of control points or a zero-angle corner the tessellation could not close; version 1.0.1+cadler.7

## 1.0.1+cadler.6 - 2026-10-30

- cadler/CHANGELOG.md lists what this fork changed in NVIDIA's usd-brep per version in cadler/version, written from the git history by cadler/changelog.py, and every commit carries its own entry
- SMLib takes fillets off faces that sit on patches of their own (a STEP import) and gets them right or fails: DeleteFilletFace makes the uv trim curves of the faces beside it again after extending them, remove_fillet works on a copy it keeps only when AssertValid passes, joining faces split on one surface and widening the planes beside a single fillet first; remove_fillet_faces takes off the fillets asked for, with their group when they cannot go alone; Face.user_ids(); version 1.0.1+cadler.6

## 1.0.1+cadler.5 - 2026-10-29

- SMLib chamfers an edge with two distances: the reference face set back by one, the other face by another, through the fillet solver's second radius on a linear section; chamfer_edges_two_distances in Python; version 1.0.1+cadler.5

## 1.0.1+cadler.4 - 2026-10-29

- SMLib crashes cadler hit rounding the seams of a rounded top: a squeezed strut made a vertex loop twice, a polar box without a surface, a vertex glued after it was deleted or left mated, and an edge between two loops of one face deleted with that face; version 1.0.1+cadler.4

## 1.0.1+cadler.3 - 2026-10-28

- Windows wheel built with VS 2022's own MSVC v143 (try): no v142 toolset installed first in CI
- Unclamped NURBS clamped where SMLib reads them, the same curve or surface
- cadler/threads on Windows and macOS: the release harness after each platform's build
- Brep.memory_used(): the bytes a Brep holds, from SmBrep::GetMemoryUsed
- Two SMLib crashes cadler hit: a fillet at a corner SMLib has no case for, and a boolean that leaves an edge without its vertex; version 1.0.1+cadler.3
- cadler/threads: the harness covers the SM_API operations cadler calls, and bodies shared by threads

## 1.0.1+cadler.2 - 2026-10-27

- cadler/threads: __aarch64_have_lse_atomics is libgcc's, not a global of SMLib
- cadler/threads: std::__ioinit (gcc < 13) is the runtime's, not a global of SMLib
- SMLib in threads: a context per thread, every global an operation writes thread_local, checked under ThreadSanitizer
- squeeze_face: a tiny face squeezed away, the faces around it meeting at a vertex

## 1.0.1+cadler.1 - 2026-10-22

- cadler wheel builds: scripts, version, GitHub Actions for Linux, Windows and macOS, package index on Pages
- macOS: newer clang, room to rewrite library paths, Python from the importing interpreter
- PolyBrep.to_numpy_arrays(source=brep): the face of each polygon
