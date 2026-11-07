# Rebuilding and changing the model

You only need this if you want to rerun the scripts. To look at the model, open the viewer or the `.blend`.

## Requirements

- **Blender 5.2** (built on 5.2.3 LTS, Windows). The aerial was imported once with the [BlenderGIS](https://github.com/domlysz/BlenderGIS) add-on. It's only needed to re-import imagery; the `.blend` files already contain the aerial.
- **Python 3.10+** for the scripts that run outside Blender: `pip install -r requirements.txt`.
- **Node 18+** for the viewer build (three r187, esbuild 0.28).

## Two kinds of scripts

**Blender scripts** (`*_blender.py`, `p7_snapshot.py`, `p7_change_view.py`, `p8_export_glb.py`, `p5*_import_blender.py`) run inside Blender. Open a `.blend` from `blend/`, then in the Python console or Text Editor run:

```python
exec(open(r'<repo>/work/p8_render_blender.py').read())
```

They find the repo root as the folder above the open `.blend` (override with `SH249_ROOT = '<repo>/'` before the `exec`). Most take their options as globals set before the `exec`, for example:

```python
CAMS = [('CAM_Review_Oblique', 'test_overview')]; VIEW = 'change'; PCT = 50
exec(open(r'<repo>/work/p8_render_blender.py').read())
```

Run Blender scripts one at a time. The original build ran them over MCP, where big scripts time out.

**Everything else** (`p2_*` … `p8_*` without `_blender`) is plain Python run **from the repo root**, e.g. `python work/p7_geom.py work/ work/p7_data.json`. Some of the extraction scripts (Phases 2–5) were written as one-off steps: they read `plans/…` and `work/…` relative to the current folder and write their output into the current folder or `work/`. Read the top of a script before running it.

## Coordinate frames (quick reference)

- **Plan feet:** X east, Y north (State Plane grid north), origin `ORIGIN_SC` on the Spring Cypress midline between the outer mainlane edges.
- **PDF point → plan feet:** `X = (x + dx − 836.9) × 40/72`, `Y = −(y + dy − 305.5) × 40/72`, with per-sheet offsets (dx, dy) from the table in `BUILD_LOG.md` Phase 1.
- **Blender** is metres internally (feet × 0.3048), displayed in feet. Pavement z = 0; curb and island tops at 0.5 ft; the aerial at z = −0.10 m.
- **Georeference:** the origin is at lat 30.0130799, lon −95.5906606. Scene +Y has a true bearing of 1.670°, and the aerial is rotated +2.9668° about the origin (State Plane vs. UTM 15N). `work/p6_common.py` has the scene ↔ UTM helpers.
- **glTF / viewer:** Y-up metres; Blender (x, y, z) → glTF (x, z, −y).

## Changing the model

1. Open `blend/sh249_sc_v09.blend` (the clean model), make the change, and save it as a new version (v11, …).
2. Check that nothing else moved: `MODE = 'compare'` then exec `p7_snapshot.py`. It fingerprints every E_/P_/CTX_ object, material and node group against `work/p7_baseline_v08.json`. To compare against v09 instead, exec the script text with `.replace('p7_baseline_v08.json', 'p8_baseline_v09.json')`.
3. Save a separate export copy and do all export prep there. The glTF exporter calls `mesh.validate()`, which can modify meshes in the open file.

## Rebuilding the exports (Phase 8 pipeline)

1. **GLB (Blender, export copy only):** exec `p8_export_glb.py` (globals `OUT`, `DRACO=False`, `GPU_INST=True`, `JPEG_Q=85`). It asserts the file name ends in `v10_export.blend`; edit that for a new copy. Writes `export/sh249_springcypress.glb` and `work/p8_cameras.json`.
2. **Post-process:** `python work/p8_glb_post.py in.glb out.glb` removes empty Reference nodes and tags the instanced trees. `python work/p8_glbinfo.py out.glb` prints the node tree, a size breakdown and an extras check.
3. **Viewer:** copy `work/p8_viewer/` to a scratch folder and rename `p8_viewer_main.js` → `src/main.js`, `p8_viewer_template.html` → `src/template.html`, `p8_viewer_package.json` → `package.json`. Then run `npm i`, then `node p8_build_viewer.mjs <glb> <p8_cameras.json> <out.html>`. `p8_shoot_viewer.py` takes headless-Chrome screenshots (needs Playwright).
4. **KMZ:** `python work/p8_build_kmz.py <glb> <out.kmz>`.
5. **Renders (Blender):** `p8_render_blender.py` with `VIEW = 'existing' | 'proposed' | 'change' | 'radar'`. For change renders, stamp the legend with `python work/p7_legend.py <png>` (edits the file in place).

**Viewer-only changes** (colours, presets, lighting, layer toggles) are edits to `p8_viewer_main.js` / `p8_viewer_template.html`, followed by step 3. `window.__viewer` exposes `setMode`, `setLayer`, `goto`, `look`, `pickAt`, `selectByName` and `stats` for testing.

## Gotchas found during the build

- `AERIAL_NAIP2022_60cm` is unselectable, so a selection-only export silently drops it. The export script unlocks it and locks it again.
- `export_hierarchy_full_collections` writes nodes even for excluded, empty collections; `p8_glb_post.py` removes them.
- Hidden objects are exported when they're selected, which is why the radar zones export with `use_renderable = False`.
- `scene.ray_cast` hits the hidden `REF_` plan planes, so skip them in raycasts.
- Keep the view transform on **Standard**: the sun and sky strengths were tuned for it. If the lighting gets reset, rerun `p6_light_blender.py`.
- The change view (`p7_change_view.py`) swaps materials and must be restored before saving. The render scripts apply and restore it automatically.
