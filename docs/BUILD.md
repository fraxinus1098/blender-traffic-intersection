# Rebuilding and changing the model

You only need this if you want to rerun the scripts. To look at the model, open the viewer or the `.blend`.

## Requirements

- **Blender 5.2** (built on 5.2.3 LTS, Windows). The aerial was imported once with the [BlenderGIS](https://github.com/domlysz/BlenderGIS) add-on. It's only needed to re-import imagery; the `.blend` files already contain the aerial.
- **Python 3.10+** for the scripts that run outside Blender, in a venv: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (`.venv/` is gitignored). Phase 9 adds `laspy[lazrs]` and `scikit-image` (lidar). For viewer screenshots: `.venv/bin/python -m playwright install chromium`.
- **Node 18+** for the viewer build (three r187, esbuild 0.28).
- **Phase 9 data that is not in the repo** (only needed to rerun 9A/9B): the lidar tiles in `lidar/` and the Mapillary downloads in `work/p9_photos/raw/` (both gitignored and not kept after the build; download them as described below). Everything derived from them is committed (`work/p9_lidar.json`, `p9_bridge.json`, the photo overlays), so the exports rebuild without them.

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

1. Open `blend/sh249_sc_v11.blend` (the clean model since Phase 9), make the change, and save it as a new version (v13, …).
2. Check that nothing else moved: `MODE = 'compare'` then exec `p7_snapshot.py`. It fingerprints every E_/P_/CTX_ object, material and node group against `work/p7_baseline_v08.json`; to compare against v11, exec the script text with `.replace('p7_baseline_v08.json', 'p9_baseline_v11.json')` (v09: `p9_baseline_v09.json`). `MODE = 'save'` with the same replace writes a new baseline.
3. Save a separate export copy and do all export prep there. The glTF exporter calls `mesh.validate()`, which can modify meshes in the open file.

## Rebuilding the exports (Phase 8 pipeline, kept for the record)

1. **GLB (Blender, export copy only):** exec `p8_export_glb.py` (globals `OUT`, `DRACO=False`, `GPU_INST=True`, `JPEG_Q=85`). It asserts the file name ends in `v10_export.blend` (that copy was removed after Phase 9; use the Phase 9 pipeline). Writes `export/sh249_springcypress.glb` and `work/p8_cameras.json`.
2. **Post-process:** `python work/p8_glb_post.py in.glb out.glb` removes empty Reference nodes and tags the instanced trees. `python work/p8_glbinfo.py out.glb` prints the node tree, a size breakdown and an extras check.
3. **Viewer:** copy `work/p8_viewer/` to a scratch folder and rename `p8_viewer_main.js` → `src/main.js`, `p8_viewer_template.html` → `src/template.html`, `p8_viewer_package.json` → `package.json`. Then run `npm i`, then `node p8_build_viewer.mjs <glb> <p8_cameras.json> <out.html>`. `p8_shoot_viewer.py` takes headless-Chrome screenshots (needs Playwright).
4. **KMZ:** `python work/p8_build_kmz.py <glb> <out.kmz>`.
5. **Renders (Blender):** `p8_render_blender.py` with `VIEW = 'existing' | 'proposed' | 'change' | 'radar'`. For change renders, stamp the legend with `python work/p7_legend.py <png>` (edits the file in place).

In Phase 8, viewer-only changes were edits to `p8_viewer_main.js` / `p8_viewer_template.html`, followed by step 3. `window.__viewer` exposes `setMode`, `setLayer`, `goto`, `look`, `pickAt`, `selectByName` and `stats` for testing.

## Phase 9 (v11 model, v12 exports)

Blender runs on Windows here and Claude Code in WSL, so pass the repo root to every Blender exec **with backslashes**: `SH249_ROOT = '\\\\wsl.localhost\\Ubuntu\\home\\<user>\\...\\blender-traffic-intersection\\'`. The scripts' own root detection gives `//wsl.localhost/...`, which Blender reads as relative to the .blend (render output then lands in `blend/wsl.localhost/...`).

**Lidar download (9A.1).** USGS 3DEP TX_Houston_B24 tiles `15RTP249322`, `15RTP249323`, `15RTP250322`, `15RTP250323` (334 MB) into `lidar/`. Find the URLs with the TNM API: `https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Lidar%20Point%20Cloud%20(LPC)&bbox=-95.594,30.010,-95.587,30.016&outputFormat=JSON` (titles containing `TX_Houston_B24`). The files are on rockyweb.usgs.gov, which allows one connection at a time and answers HTTP 429 for a while after each file: download one tile at a time with `curl -f -C - -o <file> <url>` in a retry loop (without `-f` the 429 page is saved as the .laz).

**Mapillary (9B).** Put a client token in `~/.config/sh249/mapillary_token` (never in the repo) and `export MAPILLARY_TOKEN=$(cat ~/.config/sh249/mapillary_token)`. Image metadata: `https://graph.mapillary.com/<id>?fields=thumb_original_url,camera_parameters,computed_rotation,computed_geometry,computed_compass_angle,width,height,captured_at,creator` with header `Authorization: OAuth $MAPILLARY_TOKEN`; save it as `work/p9_photos/raw/<id>_full.json` and the original as `<id>_orig.jpg`.

**Model v11 (9A), in order** (`.venv/bin/python` from the repo root for plain scripts; `_blender` scripts exec'd in v11):

| Step | Script | Notes |
|---|---|---|
| 9A.1 | `p9_lidar.py` | → `work/p9_lidar.json`, `docs/images/p9_lidar_check.jpg`, caches `lidar/p9_*.npz` |
| | `p9_apply_lidar_blender.py` with `STEP = 'buildings'`, `'trees'`, `'bridge'` | `trees` also runs `p9_trees_blender.py` and resets tree z |
| 9A.2 | `p9_build_bridge.py` → `p9_bridge_blender.py` | needs `p9_keepout.json`; rerun after the `trees` step |
| 9A.3 | `p9_textures.py` → `p9_concrete_blender.py` | `work/tex/p9_concrete_pave.jpg`, `paveUV` on `E_RD_Pavement` |
| 9A.4 | `p9_signs_blender.py`, `p9_trees_blender.py`, `p9_vehicles_blender.py`, `p9_aerial_fade.py` → `p9_horizon_blender.py` | |

**Photo overlays (9B):** `p9_photo_prep.py <id>` → pick points into `work/p9_photos/p9_picks.json` (`p9_photo_solve.py project <id> solved` draws the model points on the photo) → `p9_photo_solve.py solve <id> <points>` → in Blender, `IDS = [...]; LAYER = 'existing' | 'proposed' | 'removed'; POSE = 'solved'; PCT = 50; OUT = SH249_ROOT + 'work\\p9_photos\\render\\'` then exec `p9_photo_render_blender.py` (once per layer) → `p9_photo_composite.py`.

**Exports (9C–9E):**
1. In v11: compare against `p9_baseline_v11.json`, then save as `blend/sh249_sc_v12_export.blend` (export prep only in that copy).
2. **GLB:** in v12_export, `OUT = SH249_ROOT + 'work\\p9_tests\\v12_raw.glb'` then exec `p9_export_glb.py` (asserts the `v12_export` filename; writes `work/p9_cameras.json`). Then `.venv/bin/python work/p9_glb_post.py work/p9_tests/v12_raw.glb export/sh249_springcypress.glb`; `p8_glbinfo.py` prints the tree.
3. **Sheet planes** (once): the `REF_*` plane corners and UVs are in `work/p9_sheet_planes.json` (exported from v12_export over MCP; rerun only if the planes move).
4. **Viewer:** `.venv/bin/python work/p9_viewer_data.py work/p9_tests/p9_viewer_data.json` (plan sheets, photos, cones). In a scratch folder: `src/main.js` ← `work/p9_viewer/p9_viewer_main.js`, `src/template.html` ← `p9_viewer_template.html`, `package.json` ← `p9_viewer_package.json`, plus `p9_build_viewer.mjs`; `npm i`; `node p9_build_viewer.mjs <glb> work/p9_cameras.json <viewer_data.json> export/sh249_springcypress_viewer.html`.
5. **Viewer test:** `.venv/bin/python work/p9_shoot_viewer.py <html> <outdir> '<shots json>' [WxH] [#hash]`. It prints any non-file request (must be none) and the console messages. `window.__viewer` exposes `setMode`, `setLayer`, `goto`, `look`, `pickAt`, `selectByName`, `setSplit`, `setSheets`, `measure`, `clearance`, `where`, `setTool`, `openPhoto`, `setPhotoLayer`, `photoIn3D`, `flyTo`, `equipment`, `cone`, `link`, `copyLink` and `stats`.
6. **KMZ:** `.venv/bin/python work/p9_build_kmz.py export/sh249_springcypress.glb export/sh249_springcypress.kmz`; check with `p9_kmz_check.py <kmz> <out.jpg>` (plot over the NAIP and placement agreement).
7. **Renders:** in v12_export, `p8_render_blender.py` as in Phase 8 (`OUT = SH249_ROOT + 'export\\'`), then `p7_legend.py` on the change render. Afterwards compare v12_export against `p9_baseline_v11.json` (expect no differences).

## Gotchas found during the build

- `AERIAL_NAIP2022_60cm` is unselectable, so a selection-only export silently drops it. The export script unlocks it and locks it again.
- `export_hierarchy_full_collections` writes nodes even for excluded, empty collections; `p8_glb_post.py` removes them.
- Hidden objects are exported when they're selected, which is why the radar zones export with `use_renderable = False`.
- `scene.ray_cast` hits the hidden `REF_` plan planes, so skip them in raycasts.
- Keep the view transform on **Standard**: the sun and sky strengths were tuned for it. If the lighting gets reset, rerun `p6_light_blender.py`.
- The change view (`p7_change_view.py`) swaps materials and must be restored before saving. The render scripts apply and restore it automatically.
- Excluding a view-layer collection and including it again resets the viewport hide (eye icon) of its objects. Scripts that toggle `exclude` must record and restore `hide_get()` (the hidden `P_CUT_*` ramp cutters are the case that matters); `p9_photo_render_blender.py` does.
- The glTF exporter writes a second UV set as `TEXCOORD_1` with `texCoord: 1` on the material (`MAT_P9_ConcretePave` on `E_RD_Pavement`); three.js r187 reads it without changes.
