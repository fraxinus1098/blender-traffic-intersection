# Plan: v11 improvements

Written 2026-11-07 for a fresh Claude Code session that will implement this. Branch: `v11-improvements`.

The project (Phases 0–8) is finished and published. This plan adds a better model (v11), street-level photo overlays, a richer viewer and a better KMZ. Outputs stay the same kind: **one self-contained offline HTML viewer** and **one KMZ**, plus screenshots for the repo.

## Read first

- `CLAUDE.md`: the rules (clean model is never edited in place, export prep only in an export copy, keep folder layout, `sh249_*` tags and E_/P_/CTX_/ENG_ collection names).
- `docs/BUILD.md`: how scripts run, coordinate frames, the Phase 8 export pipeline, gotchas.
- `docs/BUILD_LOG.md`: per-phase record, callout tables, sheet offsets.
- `docs/ASSUMPTIONS.md`: the 73 assumptions; several get replaced below.
- `docs/CLAUDE_WORKFLOW.md`: the original session notes. The container/`device_*` file-transfer parts **no longer apply** (see Environment).

## Environment (different from the original build)

- Claude Code runs in **WSL (Linux)**; Blender 5.2 runs on **Windows**, driven by the Blender MCP (`mcp__blender__execute_blender_code`). There is no cloud container and no `device_*` tool: heavy Python runs locally in WSL, and Blender reads the same files.
- Code running in Blender sees **Windows paths**. The repo is at `\\wsl.localhost\Ubuntu\home\shortie1\Projects\blender-traffic-intersection\`. Set `SH249_ROOT` to that (with trailing backslash) before exec-ing repo scripts if root detection fails.
- MCP rules still apply: small calls, set `result` to a dict, one element type at a time.
- WSL Python lacks Pillow etc. at the moment. Make a venv (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`; `.venv/` must be gitignored) and add `laspy[lazrs]` for lidar.
- Mapillary token: read from env var `MAPILLARY_TOKEN`. **Never write the token into the repo.** Ask the user for it if it isn't set.

## Decisions already made (don't re-litigate)

- Audience: civil/traffic engineers. It's a fun project for experimenting with the Blender MCP.
- Single offline HTML file. No Google 3D Tiles, no API keys in the page, no network requests at runtime.
- File size is not a concern (no compression work).
- No phone layout work.
- No sharper aerial: free options are older or need tokens, and the good ones (H-GAC 2024) are paid. Stay on NAIP 2022.
- Lidar: **heights only**. Pavement stays flat (z = 0); no terrain mesh.
- No flythrough video, no signal-phasing animation, no repo/LFS work, no "generalize the pipeline".
- Street-level imagery: Mapillary only (CC BY-SA 4.0). No Google Street View (ToS), no Nearmap (paid).

## Versioning

- `blend/sh249_sc_v09.blend` stays untouched. New clean model: **`blend/sh249_sc_v11.blend`**. New export copy: **`blend/sh249_sc_v12_export.blend`** (update the filename assert in `p8_export_glb.py`).
- Before changing v11, take a fingerprint baseline of v09 if needed (`p8_baseline_v09.json` already exists). After each model step, run `p7_snapshot.py` in compare mode and check that **only the intended objects changed**. At the end, save a new baseline `work/p9_baseline_v11.json`.
- New scripts use the prefix **`p9_`** (this is Phase 9). Blender-side scripts end in `_blender.py`.
- Update `CLAUDE.md` at the end: v11 is the clean model, v12 the export copy, Phase 9 done.

## Phase 9A: model v11

### 9A.1 Lidar heights (2024 survey)

Data: USGS 3DEP **TX_Houston_B24** (published 2026-01-29), 4 LAZ tiles covering the site, about 330 MB total:
`15RTP249322`, `15RTP249323`, `15RTP250322`, `15RTP250323`.
Find the download URLs with the TNM API:
`https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Lidar%20Point%20Cloud%20(LPC)&bbox=-95.594,30.010,-95.587,30.016&outputFormat=JSON` (filter titles containing `TX_Houston_B24`).
Put the LAZ files in **`lidar/` (gitignored)**; only derived JSON is committed.

Script `work/p9_lidar.py` (WSL, venv):
1. Read the tiles, check the CRS from the LAS header (expect UTM 15N or State Plane; convert with pyproj), crop to model extent + 60 m, transform to scene metres with the `p6_common.py` helpers.
2. Ground = class 2. Build a 0.5 m ground grid and a first-return/highest-point grid; normalized height = highest − ground.
3. Outputs into `work/p9_lidar.json`:
   - **Buildings**: for each OSM footprint in `p6_osm_buildings.json`, median roof height (points inside the footprint shrunk by 1 m, height > 2 m). Flag footprints with no roof returns.
   - **Trees**: canopy height model (class 5 / high veg, or height > 3 m outside buildings and the bridge), smooth, find local maxima (min spacing ~4 m, height > 4 m); per tree: position, height, crown radius (watershed or radius to 50 % height). Drop trees on pavement/curb using `p3_rd_masks.npz`, like Phase 6.
   - **Bridge**: deck-top elevation profile along the SH 249 deck (relative to the Spring Cypress pavement under it), and the header-bank/abutment slope shape at both ends.
   - **Optional as-built check**: look for points at the proposed mast-arm pole locations (callouts A–C, K–M). Expectation: not built (Mapillary 2026 photos still show the existing dual mast arm H). Just report.
4. A check plot `docs/images/p9_lidar_check.jpg` (tree tops and building heights over the NAIP).

Apply in Blender (`work/p9_apply_lidar_blender.py`): rescale building extrusions to measured heights (keep tags; update `sh249_*` height props), replace the 131 trees with the lidar trees (same instancing approach and materials as Phase 6; keep the collection name), set the bridge deck height from the profile.

Replaces assumptions **12** (deck height), **47** (building heights), **50–51** (tree positions/heights). Rewrite those entries in `ASSUMPTIONS.md` and say they're now measured (source, date, method).

### 9A.2 Bridge rebuild

The current `CTX_SH249_*` bridge is a flat white slab with green walls. Rebuild it as plausible, illustrative geometry (it's context, not design), using the Mapillary photos as visual reference:
- concrete deck with SH 249 mainlane pavement and lane lines (lane count from the plans/aerial),
- concrete traffic barrier on both edges with the **red stripe** seen in the photos,
- girders/box-beam fascia, bent caps, **round columns** at the three bents (positions as in `CTX_SH249_Bents`),
- header banks with **concrete slope paving** at both ends, sloping down to the frontage roads,
- deck height from 9A.1.
Keep it in the CTX_ collections with the same tags so viewer layers still work. Check it from the existing overview and driver cameras.

### 9A.3 Concrete frontage roads

The Mapillary photos show the frontage roads are **concrete with joints** (README "Known limits" guessed this). Switch those pavement surfaces to a concrete texture with a joint pattern (generated like the Phase 6 textures, into `work/tex/p9_*.jpg`). Check from the photos which areas are concrete vs asphalt (Spring Cypress itself may differ). Update the README known-limits line.

### 9A.4 Small items

- Text on street-name signs: proposed S1/S2 ("Spring Cypress Rd", "SH 249"), and the existing ones (the photo shows the existing far arm at NB int carries "SH 249"). Keep R10-3e and R3-8 faces as they are unless the photos show them clearly.
- Better low-poly trees: 3–4 variants (crown shapes), still instanced.
- A few static low-poly cars at stop bars for scale (new collection `CTX_Vehicles`, tagged context, toggled with the context layer).
- Horizon: soften where the aerial ends (fog or a fade) if it's simple.

**Acceptance for 9A:** snapshot compare shows only intended changes; the 6 final camera renders (`p8_render_blender.py`) look right; the plan-overlay check still lands signals within about 1 ft (signals weren't touched, so this should be trivially true).

## Phase 9B: Mapillary photo overlays

Goal: real street-level photos with the model drawn on top, in the viewer. All photos show the **existing** condition (the project isn't built as of Oct 2026), so each photo gets two overlays:
1. **Existing model** (accuracy check: do the modeled poles land on the real poles?),
2. **Proposed in change colours** (green new, red outline on what's removed). Don't try to paint old poles out of the photo.

Coverage found (bbox −95.5945, 30.0100, −95.5870, 30.0160): 1,496 images, 37 sequences.
- **Dashcam 4K**, user `graharg`, May–Nov 2026, many repeat drives. Wide/fisheye lens, hood and windshield in frame, timestamp/GPS overlay at the bottom. Candidates (WB approaches):
  - NB int: `28581715364843976` (verified: shows existing dual mast arm H at the NE corner and the far arm with "SH 249" sign), `1903727707705253`.
  - SB int: `2182717216005657`.
  - Other approaches: query the API for more (`fields=id,captured_at,compass_angle,computed_compass_angle,computed_geometry,width,camera_type,sequence`); also look at the Nov/Aug/Jun 2026 sequences for EB and frontage-road approaches.
- **Microsoft StreetSide 360° panoramas**, 2012/2015, 4064 × 2032 equirectangular, clean (no hood). Candidates: NB int `305513184508470` (about 4 m from centre), SB int `2861171350868048` (about 11 m).
- API: `https://graph.mapillary.com/images?bbox=...` and `https://graph.mapillary.com/<id>?fields=thumb_original_url,...` with header `Authorization: OAuth $MAPILLARY_TOKEN`.

Method (start small: **one dashcam frame per intersection**; add one 360° pano only if those match well):
1. Download originals into `work/p9_photos/` (commit only the final, cropped JPEGs used by the viewer; keep the license info with them).
2. Camera solve: start from Mapillary's `computed_geometry` / `computed_compass_angle`, eye height ~1.3 m (dashcam) or ~2.5–3 m (StreetSide car). For dashcam frames, estimate lens distortion (straight poles/lane lines) and undistort first, then crop off the hood and overlay text. Refine position, yaw, pitch, roll and focal length in Blender by matching modelled features (existing pole bases and tops, stop bars, lane lines, bridge edge) to the photo. Report the residual in pixels and feet. `fSpy`-style manual matching is fine; doing it through MCP calls is part of the experiment.
3. Render with `film_transparent`: existing-only and change-view proposed, at the photo's resolution, from the solved camera. For panos use an equirectangular panoramic camera.
4. Composite (WSL Python) → `work/p9_photos/<id>_{photo,existing,proposed}.jpg|png` for the viewer.

Attribution: CC BY-SA 4.0. Credit the photographer and Mapillary in `ATTRIBUTION.md` and in the viewer next to each photo. The composites are CC BY-SA 4.0 too.

**Acceptance for 9B:** modeled existing poles sit on the photographed poles within a few pixels near the intersection; the residual is written down in the build log.

## Phase 9C: viewer pass

Edit `work/p8_viewer/p8_viewer_main.js` and `p8_viewer_template.html` (copy them to `p9_viewer/` first if the changes are big; keep `p8_*` as the record). Rebuild with the Phase 8 step 3 process. Everything stays inline in one HTML; no network requests (check with `p8_shoot_viewer.py`, which lists any).

Features:
1. **Plan sheet overlay**: drape the masked sheets in `plans/masked/` (existing sheets in Existing mode, proposed in Proposed) on the ground, with an opacity slider. Placement uses the PNG pixel ↔ plan feet formula and sheet offsets in `CLAUDE_WORKFLOW.md`/`BUILD_LOG.md`, then plan feet → glTF. Check against the Phase 5 overlay images.
2. **Existing / Proposed split slider**: same camera, a draggable vertical divider (scissor test or two render passes).
3. **Deep links**: `#cam=<preset>&mode=<mode>&layers=...` (and a free camera pose), read on load and updated on change; a "copy link" button.
4. **Equipment list**: callouts A–M plus heads/ped poles, grouped by intersection and status; click flies to the object and opens its info panel (reuse `selectByName`).
5. **Measure tool**: click two points for distance (ft), and a vertical clearance readout (e.g. head bottom to pavement).
6. **Visibility cones**: for the selected driver camera, draw the MUTCD 4D cone and the head pass/fail from `work/p7_visibility.json`.
7. **Photo views (from 9B)**: a "Photos" section; each photo opens full-panel with an Existing ↔ Proposed toggle (or slider) and its credit; a marker in 3D shows where the photo was taken. A 360° pano, if made, is shown as a drag-to-look sphere.

Keep `window.__viewer` and extend it (`setSplit`, `measure`, `openPhoto`…) so headless screenshots can test each feature.

**Acceptance for 9C:** screenshots of each feature in `docs/images/viewer_2x_*.jpg`; no console errors; no network requests; opens offline by double-click.

## Phase 9D: KMZ pass

Update `work/p8_build_kmz.py` → `work/p9_build_kmz.py`:
1. Markings, ramps and radar zones as **KML Polygons with `clampToGround`** (draped) in place of lifted COLLADA. Keep signals and signs as COLLADA models.
2. **One Placemark per pole/cabinet/ped pole** with a balloon carrying the same info as the viewer panel (callout, status, type, sheet, arm length), in Existing/Proposed folders.
3. **GroundOverlays** of the masked plan sheets (LatLonBox with rotation from the State Plane ↔ UTM rotation and origin), off by default.
4. A **`gx:Tour`** flying through the main viewer presets.
5. Optional: test in Google Earth Pro whether Street View mode shows the models, and note the result.

**Acceptance for 9D:** opens in Google Earth Pro; markings sit on the ground without z-fighting; balloons show; overlays line up with Google's imagery to about the same ~1 m as the model. Ask the user to do the Google Earth check if it can't be done from here, and to send screenshots.

## Phase 9E: exports and docs

1. Export pipeline from `blend/sh249_sc_v12_export.blend`: GLB → post → viewer → KMZ → the 6 final renders (same names in `export/`).
2. Docs: add a Phase 9 section to `BUILD_LOG.md`; update `ASSUMPTIONS.md` (replaced and new assumptions, numbered after 73); update `BUILD.md` (venv, lidar download, p9 scripts, v11/v12); update `README.md` (new features, screenshots, known limits, credits); `ATTRIBUTION.md` (USGS 3DEP lidar, Mapillary CC BY-SA); `CLAUDE.md`.
3. `.gitignore`: `lidar/`, `.venv/`, raw photo downloads.

## Order and checkpoints

9A.1 → 9A.2 → 9A.3 → 9A.4 → 9B → 9C → 9D → 9E. Stop and show the user screenshots at the end of each sub-phase before moving on. Commit on the branch after each accepted sub-phase (only when the user says so).

## Status (updated 2026-11-07, end of session 2)

**Phase 9 is done (9A–9E)**; the record is `docs/BUILD_LOG.md` → "Phase 9". Clean model `blend/sh249_sc_v11.blend` (baseline `work/p9_baseline_v11.json`), export copy `blend/sh249_sc_v12_export.blend`; `export/` holds the v12 GLB, viewer, KMZ and final renders.

Decisions made with the user along the way (kept for the record):
- 9B: a pole-and-curb-anchored camera solve, with the residuals reported as findings instead of chasing pixel accuracy. Two dashcam frames; the StreetSide 360° panoramas were not done (optional).
- Bridge: square columns as photographed and two extra bents at the header-bank toes. Cars appear in every view (context). 80 lidar trees replace the 131 NAIP ones.

Open items:
- None required. The user checked the KMZ in Google Earth Pro on 2026-11-07 (looks good). Street View mode was not tested.
- Optional, not started: a StreetSide 360° panorama in the viewer.
