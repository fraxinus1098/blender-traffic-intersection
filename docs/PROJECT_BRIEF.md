# Project brief (original build instructions)

This is the original brief given to Claude at the start of the build. It sets the goal, lists the source sheets and the key facts pulled from the plans, and lays out the build phases. Kept for context; the status lines were updated at the end of the build.

## Goal

Build a 3D model of the TxDOT traffic signal upgrade at **SH 249 at Spring Cypress Rd** (CSJ 0720-03-153). It is a diamond interchange, so there are two signalized frontage-road intersections: the SB feeder and the NB feeder. The model shows **existing vs. proposed** on top of an aerial basemap. Deliverables:
- an interactive 3D viewer in the browser;
- a KMZ for Google Earth;
- 4–6 renders.

The audience is a TxDOT project manager. This is an exploratory test, so a convincing, roughly-to-scale result matters more than survey precision.

**Status (2026-11-07): Spring Cypress is complete (Phases 0–9).** Deliverables are in `export/`: `sh249_springcypress.glb`, `sh249_springcypress_viewer.html`, `sh249_springcypress.kmz` and `final_*.png`. The clean model is `blend/sh249_sc_v11.blend`; the export copy is `blend/sh249_sc_v12_export.blend`. Phase 9 (lidar heights, photo overlays, viewer tools) is in `PLAN_v11.md` and `BUILD_LOG.md`.


## Source sheets (`plans/SH249_Select_Sheets.pdf`)

The plans are CAD-plotted vector PDFs. All plan sheets are 1" = 40', with north up. Sheets 1 of 2 and 2 of 2 join at the match lines.

| Sheet | Content | Use |
|---|---|---|
| 23 | Traffic signal notes | Mounting heights, backplates |
| 24–25 | Spring Cypress signal existing | Existing poles, arms, heads, ped poles (callouts A–M) |
| 26–27 | Spring Cypress signal proposed | Proposed pole locations, arm lengths, head and radar positions |
| 28 | Spring Cypress proposed details | Head types, signs, ped heads, radar schedule |
| 38–39 | Spring Cypress markings & ramps existing | Curb and lane geometry, existing markings |
| 40–41 | Spring Cypress markings & ramps proposed | Proposed markings, curb ramps, R1-5BL |
| 67 | LMA(5) Spring Cypress | Pole and arm schedule (pole heights, arm types) |

The plans contain no phasing sheet. TxDOT signal maintenance provides the timing, so there is no phasing animation.

## Key facts from the plans

**Heights (sheets 23 and 67):**
- Vehicle signal heads mount horizontally on the mast arm, **17'-6" above the roadway**.
- Heads have black housings and black backplates with a 2" yellow retroreflective border.
- Mast-arm poles are **30' poles with luminaire**. ILSN (illuminated street name sign) poles are 24'.
- APS push buttons sit **3'-6" to 4'-0" above the sidewalk**.
- Ped signals are countdown, symbol type.

**Speeds:** Spring Cypress 45 mph; SB feeder 50 mph; NB feeder 45 mph.

**Mainlanes:** shown only as outlines, so they are probably grade-separated. Confirm against the aerial and model them as simple context.

**Existing (to be removed), sheets 24–25:**
- Dual mast-arm poles and mast-arm poles with luminaires.
- Pedestal ped poles with ped heads, push buttons and signs.
- The existing controller.
- These stay: R3-8 UMS, R3-8L, ITS ground boxes, the CTMS hub and the fiber.

**Proposed mast arms, sheets 26–27:**

| Callout | Location | Arm length |
|---|---|---|
| A | SB feeder side | 55' |
| B | SB feeder side | 55' |
| C | SB feeder side | 55' |
| K | NB feeder side | 55' |
| L | NB feeder side | 60' |
| M | NB feeder side | 55' |

- Every mast arm has a luminaire and a street name sign. Some heads are pole-mounted (C, M).

**Proposed equipment:**
- Radar presence detection PR1–PR6; advance detection ADV1–ADV4.
- Pedestal ped poles with APS: D–J and N–T.
- Controller cabinet U (full-actuated, with battery backup).
- Electrical service pole V.

**Signal heads (sheet 28):**
- 3-section horizontal R-Y-G for most positions.
- 4-section horizontal left-arrow heads (H, R).
- 5-section vertical with right-turn arrows (D, N).

**Signs (sheet 28):**
- S1: "Spring Cypress Rd", 96"x18", white on green.
- S2: "SH 249", 48"x18".
- S3/S4: R6-1 One Way, 36x12.
- S5: R3-8L, 30x30.
- S6: R1-5BL, 36x36 (sheets 40–41).

**Radar schedule (sheet 28):**
- ADV1: SB feeder. ADV2: EB Spring Cypress. ADV3: WB Spring Cypress. ADV4: NB feeder.
- PR1: SB. PR2: EB. PR3: WB. PR4: EB. PR5: WB. PR6: NB.

**Markings and ramps (sheets 40–41):**
- New crosswalks and 24" stop bars, plus lane lines and arrows.
- Curb ramps: Types 1, 5, 21 and 22.

## Folder layout

```
blender-traffic-intersection/
  plans/     extracted PDF + one PNG (300 dpi) per Spring Cypress sheet, masked/ overlays
  imagery/   aerial GeoTIFF (NAIP 2022, 0.6 m, from TxGIO)
  blend/     v11 = clean model, v12_export = export copy, v09 = Phase 7 model (earlier saves not kept)
  work/      build scripts (p2_*.py … p9_*.py), intermediate data, textures,
             p9_viewer/ (viewer source), p9_photos/ (photo overlays)
  export/    GLB, viewer HTML, KMZ, final renders
```

## Build phases

Pause for the user's review where marked. Phases 0–8 are done; see the Progress doc for what was built, the scripts, the rebuild order and the running assumptions list.

**0. Setup**
- Confirm the MCP connection and install the BlenderGIS add-on.
- Units: Imperial display, true scale (1 ft = 0.3048 m), so the exports come out at real size.

**1. Register the sheets**
- Import the SVGs as geometry and the PNGs as locked reference planes, in a "Reference" collection.
- Scale using the 0–40 ft scale bar.
- Join sheets 1 and 2 at the match lines.
- Register the marking sheets to the signal sheets using shared curb lines.
- Put the origin at the center of Spring Cypress, between the feeders.

**2. Aerial** (pause here for review)
- Import the GeoTIFF with BlenderGIS.
- Align the plans to the aerial by matching curbs.
- Record the origin's latitude and longitude.
- Show the user a screenshot before going on.

**3. Existing roadway** (sheets 38–39)
- Pavement, 6" curbs, sidewalks, islands, existing markings.
- The mainlanes as context.

**4. Existing signals** (sheets 24–25)
- Callouts A–M, in collection `Existing`.

**5. Proposed** (sheets 26–28, 40–41, 67)
- Mast arms at the plan lengths, with heads by type at 17'-6", luminaires, street name signs and radar units.
- APS ped poles, cabinet U, service pole V.
- New markings, ramps and signs.
- Collection: `Proposed`.

**6. Context and look**
- OSM building massing and trees.
- Materials: asphalt, concrete and paint.
- Lighting.

**7. Engineering extras** (done, v09)
- **Change view:** removed items tinted red, new items green (reversible material swap; renders only).
- **Radar zones:** PR footprints at the stop bars and ADV footprints upstream, labeled from the schedule (Engineering / ENG_RadarZones, tagged `sh249_type = radar_zone`).
- **Driver's-eye cameras:** 3.5 ft eye height at each stop bar, with a head-visibility check.
- **Pedestrian views:** crossing paths at the new ramps and an APS push-button close-up.

**8. Export** (done, v10_export; the user reviewed the GLB and viewer before the KMZ)
- **Work on a copy.** Open the clean model, confirm it with `work/p7_snapshot.py` (`MODE='compare'`), then save an export copy before any export prep. The clean model stays untouched. (Done: v09 → `blend/sh249_sc_v10_export.blend`; both fingerprint identical.)
- **GLB** (`export/sh249_springcypress.glb`, 6.06 MB, no Draco): `work/p8_export_glb.py` in Blender, then `work/p8_glb_post.py` in the container.
  - Separate named nodes for Existing, Proposed, Context, Aerial and Engineering (radar zones), using `export_hierarchy_full_collections`; node tree checked in the GLB JSON.
  - Reference, `P_RampCutters`, the sun, the origin empty and the cameras are left out (the post-process removes the empty Reference collection nodes the exporter writes anyway).
  - `export_apply = True` (ramp cuts baked), `export_extras = True`, `use_renderable = False`, textures as JPEG quality 85, `export_gpu_instances` for the trees.
  - The aerial is unselectable; the export script unlocks it for the export.
- **Viewer** (`export/sh249_springcypress_viewer.html`, 8.7 MB, works offline): three.js bundled inline with esbuild, GLB embedded as base64; Existing / Proposed / Both / Change modes; layer toggles including radar zones; click info; 22 presets from the scene cameras; "For illustration only – not for construction" label. Source in `work/p8_viewer/`; build and test steps in the Progress doc. Publishing it as a private artifact link is optional and not done.
- **KMZ** (`export/sh249_springcypress.kmz`, 463 KB): built in the container from the GLB with pycollada (`work/p8_build_kmz.py`), because Blender 5.2 has no COLLADA exporter. Signals, signs, markings and ramps only; Existing and Proposed folders; anchored at Lat 30.0130799, Lon −95.5906606, heading 1.670°, relative to ground. The user checks the alignment in Google Earth.
- **Renders** (`export/final_*.png`, 2400 × 1350, `work/p8_render_blender.py`, which adds `VIEW='existing'`): overview existing, overview proposed, change oblique (with legend), SB close-up, NB close-up, SB-feeder driver's eye.
- Not pursued: a sharper aerial (no free source better than NAIP 2022) and street-level photoreal 3D (Google 3D tiles can't be used offline; no own capture).

## Rules for the build

- Run Blender Python in small chunks, one element type at a time, because large scripts time out over MCP.
- After each phase, check a viewport screenshot and save a versioned file (`blend/sh249_sc_v01.blend`, …).
- Naming: `E_` for existing, `P_` for proposed, plus the callout letter and type. Examples: `P_MA_K_55ft`, `E_PED_B`, `P_HEAD_H_4sec`. Engineering items: `ENG_`, `CAM_`.
- Model only what's on the plans. Where the plans are silent, use a reasonable default and add it to a running **assumptions list** reported at the end.
- Don't change geometry, tags or shared materials from earlier phases; check with `work/p7_snapshot.py` before saving.
- Do export prep only in a copy of the clean model.
- After every `device_commit_files`, compare md5 on the device with the container copy (commits sometimes leave the old file in place).
- This is a visualization, not a design. Keep shared outputs private to the PM.
