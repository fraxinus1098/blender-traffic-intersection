# Build log (Phases 0–8)

The detailed record of how the model was built, phase by phase, written during the build on 2026-11-06. Script names refer to files in `work/`; file versions refer to `blend/sh249_sc_vNN.blend` (only v09 and v10_export are kept in this repo). For the short version see the README; for how to re-run things see `BUILD.md`.

Sessions: 2026-11-06 (Phases 0–8). Blender 5.2.3 LTS on Windows, MCP connected. **Phases 0–8 are done; Spring Cypress is complete.** Clean model: **`blend/sh249_sc_v09.blend`** (Phase 7). Export copy: **`blend/sh249_sc_v10_export.blend`** (Phase 8; identical to v09 by the integrity fingerprint). Deliverables in `export/`: `sh249_springcypress.glb`, `sh249_springcypress_viewer.html`, `sh249_springcypress.kmz`, `final_*.png`. Underground items (conduit, bores, fiber re-route, proposed ground boxes; callouts 1–41 on sheets 26–27) are deliberately not modeled.

## Phase 0: Setup (done)
- Units: Imperial, length unit = feet, unit scale 1.0 (true scale). Blender's internal values are metres (a sheet plane is 207.264 × 134.112 m). Color view transform: Standard.
- Collections:
  - Reference, with children REF_SIG_Existing, REF_SIG_Proposed, REF_MRK_Existing and REF_MRK_Proposed;
  - Aerial, Context, Existing (children E_Roadway, E_Markings, E_Signals, E_Signals_Remain), Proposed (children P_Signals, P_Markings, P_Ramps, P_Signs, P_RampCutters), Engineering (child ENG_RadarZones since Phase 7).
- **BlenderGIS is installed and enabled** from `addons/BlenderGIS_addon.zip`. It works on Blender 5.2 for GeoTIFF import. EPSG:32615 was added to its predefined CRS list in the add-on preferences.

## Aerial imagery
- File: `imagery/SH249_SpringCypress_NAIP2022_60cm.tif`.
- Source: NAIP 2022 natural color, from the TxGIO image server `NAIP/NAIP22_NCCIR_60cm` (exportImage, bands 0,1,2).
- Size: 2000 × 1340 px, RGB, 0.6169 m/px.
- CRS: **EPSG:32615 (UTM 15N, metres)**. Upper-left corner at E 249515.695, N 3323477.014.
- The mainlanes run on a bridge over Spring Cypress, so they are grade-separated.
- Sharper imagery (checked 2026-11-06; **decided not to pursue unless free**): H-GAC sells 2024 6-inch imagery at $500 per tile (MrSID only; a 2026 collection is planned). TxGIO's Texas Imagery Service is available to Texas government entities, so TxDOT may already have access. The free StratMap Harris County imagery is 12-inch from 2013, older than NAIP 2022. NAIP 2022 is kept.

## Phase 1: Sheet registration (done)

**Scale (verified from the vector PDF):** the 0–40 ft bar is exactly 72.0 pt.
- 1 pt = 0.5556 ft; 1 px at 300 dpi = 0.13333 ft.
- A sheet plane is 680 × 440 ft.

**Offsets into the sheet-24 frame** (PDF pt, y down; add to the sheet's coordinates):

| Sheet | dx | dy | Check |
|---|---|---|---|
| 24 | 0 | 0 | reference |
| 25 | +594.7 | 0.0 | match line A-A identical; curb continuous across the join |
| 26 | −9.8 | −25.8 | 44-segment vote; Phase 5a overlay confirms |
| 27 | +453.9 | −33.2 | match line B-B agrees exactly; Phase 5a overlay confirms |
| 38 | −51.6 | −142.1 | segment vote |
| 39 | +724.8 | −53.9 | collinear with match line C-C |
| 40 | −51.6 | −142.1 | via 26; equals 38 |
| 41 | +724.2 | −53.9 | within 0.3 ft of 39 |

No rotation between sheets; all are drawn north-up (that "north" is State Plane grid north; see Phase 2).

**Origin (Blender 0,0,0, empty `ORIGIN_SC`):** (836.9, 305.5) pt in the sheet-24 frame. It is the Spring Cypress midline, midway between the outer SB and NB mainlane edges.
- World mapping: X_ft = (x24 − 836.9) × 0.5556 and Y_ft = −(y24 − 305.5) × 0.5556.

**In Blender:** each sheet is a plane `REF_<sheet>_...`, unselectable, at a stacked z of 0 to 0.03 m, using a masked RGBA PNG from `plans/masked/`. **All REF_ planes are hidden (viewport and render)** because they z-fight with the pavement. Note: `scene.ray_cast` still hits them; skip `REF_` objects in raycasts. To compare against the plans, unhide one and raise it to z ≈ 0.2 m (or use the composite check above).

## Phase 2: Aerial and georeference (done)

**Import:** BlenderGIS `importgis.georaster`, mode PLANE, rastCRS EPSG:32615 → `AERIAL_NAIP2022_60cm` in Aerial, z = −0.10 m, unselectable. Material `MAT_Aerial_NAIP` is an unlit Emission shader; its UV map is named `rastUVmap`. Any mesh using this material needs its UV layer named `rastUVmap`.

**Finding: the plans are on Texas State Plane South Central (EPSG 2278/4204) grid north**, −2.967° from UTM 15N grid north here. A free-rotation fit independently landed on −3.0°.

**Alignment method** (scripts in `work/p2_*.py`): plan linework rasterized to a 0.25 m grid, long thin components only, scored against aerial **vegetation edges** (ExG = 2G − R − B). Plain gray-level edges were ambiguous.

**Result (plan → UTM):** UTM = O_guess + R(−2.9668°)·P + (−5.9, −2.1) m, where O_guess = (250132.603, 3323063.683). In Blender the plans and origin stay fixed; the aerial is rotated **+2.9668°** about Z and placed at (5.783, 2.403, −0.10) m. Residual about 1 m.

**Scene origin (ORIGIN_SC) georeference — used for the KMZ:**
- **Lat 30.0130799, Lon −95.5906606** (WGS84)
- UTM 15N: E 250126.703, N 3323061.583
- TX SPC South Central (ftUS): E 3047378.23, N 13931640.08
- **The scene's +Y axis has a true bearing of 1.670°** (scene north is 1.67° east of true north); the KMZ heading is 1.670.
- Also stored as scene custom properties (`SH249_*`), which the GLB carries as scene extras. BlenderGIS can't store a rotation, so any later BlenderGIS import (OSM, DEM) must be rotated +2.9668° about the scene origin.

## Phase 3: Existing roadway (done)

**Source:** vector linework of sheets 38/39 via pdfplumber (`work/p3_ext.py`). Each sheet is clipped at match line C-C, the same line on both sheets: (−44.8, 93.3) → (64.6, −94.0) ft.

**Line styles on the marking sheets:**

| Style | Meaning |
|---|---|
| 0.24 pt gray (0.608) solid | existing curbs, island outlines, deck edges, small symbols |
| 0.72 pt black solid | existing pavement markings (lane lines, gore hatching, stop bars) |
| black fills (lw 0) | arrows, word markings, stop bars, plus annotation glyphs |
| 0.72 pt black dashed [4.8,4.8] | dotted turn-guide lines through the intersections |
| 0.24 pt gray dashed | utilities (ignored) |
| 1.2 pt gray dash-dot | approximate ROW (ignored) |
| 1.2 pt black | title block and seals (ignored) |

**Surface method** (`work/p3_build_rd.py`):
- Curb lines are rasterized at 0.25 ft, with the two SH 249 deck-edge lines excluded, and 66 hand closures added (driveway mouths, island noses, curb ends extended to the model edge) plus auto-joins of curb ends under 7 ft apart.
- Connected regions are classified as pavement (the region that reaches every approach), islands (non-pavement regions not touching the model edge) or roadside.
- Then: a 1-ft curb band, vectorize, simplify to 0.15 ft, triangulate (earcut), and compute aerial UVs.
- Model extent: X −400…560 ft, Y −240…210 ft.

**Objects (Existing / E_Roadway):**
- `E_RD_Pavement` at z = 0 (MAT_Asphalt).
- `E_RD_Curb`: 1-ft band at 6" plus the vertical curb face (MAT_Curb since Phase 6; was MAT_Concrete).
- `E_RD_Roadside` at 6", aerial-textured.
- `E_RD_Sidewalk_assumed`.
- Islands at 6": `E_ISL_SB_RT_Triangle`, `E_ISL_NB_RT_Triangle`, `E_ISL_N_UturnMedian`, `E_ISL_S_UturnMedian`, `E_ISL_Center_Median`, `E_ISL_W_Median`, `E_ISL_E_Median`, `E_ISL_NE_Landscaped` (grass).

**Markings (E_Markings, `work/p3_build_mk.py`):**
- `E_MK_White` and `E_MK_Yellow` sit 1 cm above the pavement.
- Lines are 6" quads; fills and crosswalk blocks keep their plotted shape; dotted guide lines are 2.67 ft on and off.
- Annotation glyphs, leader wedges and road-name labels are filtered out.

**Mainlanes (Context, `work/p3_build_br.py`):**
- `CTX_SH249_Deck`: 143 ft wide, soffit 18 ft, top 24 ft.
- `CTX_SH249_Rails`.
- `CTX_SH249_Embankment`: fill north and south of the span.
- `CTX_SH249_Bents`: N, center and S medians, 8 × 3-ft columns each, plus caps.

**Scene:** `SUN_Main`, `CAM_Review_Top` (ortho) and `CAM_Review_Oblique` (from the SW) are in Engineering. Review renders: `export/phase3_oblique.png` and `export/phase3_plan_markings.png`.

## Phase 4: Existing signals (done, saved as v05)

**Source:** vector symbols on sheets 24/25 (pages 1/2), extracted with `work/p4_words.py` (text), `work/p4_fills.py` (shapes) and `work/p4_ped.py` (ped-head arrows). Geometry is generated by `work/p4_build_sig.py` → `work/p4_existing_signals.json`. Checked by overlay composite: poles, arms, ped poles and boxes land on the plan symbols within about 1 ft.

**Callouts.** The circled letters are equipment callouts A–M; there is **no callout I**. The uncircled letters A–P are signal-head IDs, which are separate (head types are from the "Existing signal heads and signs" table).

| Callout | Sheet | Item | Plan location (ft) | Modeled as |
|---|---|---|---|---|
| A | 24 | pedestal ped pole, 1 ped head | (−161.6, 43.6) | `E_PED_A` |
| B | 24 | pedestal ped pole, 2 ped heads | (−242.6, 42.7) | `E_PED_B` |
| C | 24 | dual mast arm, SW corner of SB int. | pole (−210.9, −10.3); arms 55.0' E and 32.0' N | `E_MA_C_Dual55x32ft` |
| D | 24 | pedestal ped pole, 2 ped heads | (−174.8, −84.5) | `E_PED_D` |
| E | 24 | mast arm, SE of SB int. | pole (−99.5, −67.0); arm 43.9' N | `E_MA_E_44ft` |
| F | 25 | pedestal ped pole, 1 ped head | (194.5, −51.6) | `E_PED_F` |
| G | 25 | pedestal ped pole, 2 ped heads | (277.5, −49.5) | `E_PED_G` |
| H | 25 | dual mast arm, NE corner of NB int. | pole (252.4, 7.2); arms 54.9' W and 32.0' S | `E_MA_H_Dual55x32ft` |
| J | 25 | pedestal ped pole, 2 ped heads | (208.8, 91.6) | `E_PED_J` |
| K | 25 | mast arm, NW of NB int. | pole (145.1, 65.6); arm 43.9' S | `E_MA_K_44ft` |
| L | 25 | signal controller | 6×6 pad at (8.1, 59.0), cabinet 4×2 ft | `E_CTRL_L` |
| M | 25 | electrical service pole (two drawn) | (203.1, 98.6) and (243.5, 75.8) | `E_ELECSVC_M1`, `E_ELECSVC_M2` |

**Vehicle heads** (`E_HEAD_<id>_<type>`, all facing taken from the plan arrows):
- C north arm: P (3-sec + ONE WAY left), N, both facing E (WB). C east arm: L, K facing NNW (SB). M: 4-section vertical on a pole bracket, facing ENE (WB left).
- E arm: J (3-sec + ONE WAY right), H, facing W (EB).
- K arm: A, B (3-sec + ONE WAY right), facing E (WB).
- H west arm: C, D facing SSE (NB). H south arm: F, G (3-sec + ONE WAY left) facing W (EB). E: 4-section vertical on a pole bracket, facing WSW (EB left).
- Street-name signs: 6 (two on each dual arm, one on E and one on K), at the plan sign positions, facing the same way as the heads on that arm.

**Retained items** (collection `E_Signals_Remain`):
- `E_SIGN_R3-8_UMS_SB`, `E_SIGN_R3-8_UMS_NB`;
- `E_SIGN_R3-8L_W`, `E_SIGN_R3-8L_CtrMedW`, `E_SIGN_R3-8L_CtrMedE`, `E_SIGN_R3-8R`;
- `E_ITSGB_1` … `E_ITSGB_7`;
- `E_CTMS_Hub` (6×6 pad at (89.3, −53.2)).

Fiber and plain ground boxes are not modeled.

**Tagging for the Phase 7 change view:** every Phase 4 object has these custom properties:
- `sh249_status` = `remove` (27 objects, collection `E_Signals`) or `remain` (14 objects, `E_Signals_Remain`);
- `sh249_phase` = `existing`;
- `sh249_sheet`;
- `sh249_type`;
- `sh249_note` = callout text from the plan, for the viewer's click info.

Poles, heads and ped poles also carry `sh249_callout`; heads carry `sh249_head`; mast arms carry `sh249_arm_ft`. Each object's origin is at its base (heads: at the housing centre).

**New materials:** MAT_SigPole_Galv, MAT_SigHead_Black, MAT_Lens_Red/Yellow/Green (red slightly emissive), MAT_PedLens (orange, slightly emissive), MAT_Sign_Green/White/Black, MAT_Cabinet, MAT_Lum_Lens, MAT_GroundBox_Lid.

**Cameras added (Engineering):** `CAM_P4_SB`, `CAM_P4_NB` (oblique close-ups), `CAM_P4_PlanCheck` (ortho, for overlay checks). Review renders: `export/phase4_SB.png` and `export/phase4_NB.png`. v05 was saved with the scene camera on `CAM_Review_Oblique` at 2400 × 1350. Plan-check composites: `export/phase4_plancheck_SB.png` and `_NB.png` (scripts `work/p4_composite.py`, `work/p4_gridcrop.py`).

## Phase 5a: Proposed signals (done, saved as v06)

**Page indices confirmed by title-block sheet number:** 26 → page 3, 27 → page 4, **28 → page 5** (pages 3–5 are "Sheet 1–3 of 4" of the proposed-signal set; sheet 29 is not in the extract).

**Source and scripts** (`work/`): `p5_words.py`, `p5_fills.py` (vector objects in plan feet), `p5_heads.py` / `p5_heads2.py` (arm, head, sign and arrow extraction), `p5_gridcrop.py` (gridded sheet crops, now handles dy), `p5_build_sig.py` → `p5_proposed_signals.json` (64 objects + sign-text metadata), `p5_import_blender.py` (Blender import + text legends; set `ONLY` to rebuild named objects), `p5_composite.py`.

**Symbol vocabulary on 26/27 (differs from 24/25):**
- mast arm = 5-point 0.24-pt black closed outline (tapered); pole = concentric 0.24-pt circles (use the ~2.1-ft ring as the centre);
- vehicle head = 0.72-pt outlined rectangle about 1.3 × 3.75 ft on the arm, plus a stem and an open 4-point triangle; facing = housing centre → farthest triangle vertex;
- APS ped pole = stack of ~20 concentric 0.72-pt circles (~1.9 ft, reads as a solid dot); find by the tiny centre ring;
- arm sign = 0.72-pt 13-point outline; radar = filled ~2.5-ft body + 0.72-pt 3-point arcs (ADV = concentric arcs); luminaire = cluster of short ticks ~8 ft from the pole;
- head IDs and callouts reuse letters: on sheet 26 heads are K–T, ped poles D–J; on sheet 27 heads are A–J, ped poles N–T.

**Collection `Proposed / P_Signals` (64 objects)**, all tagged `sh249_status = new`, `sh249_phase = proposed`, `sh249_callout`, `sh249_sheet`, `sh249_type`, `sh249_note` (plan callout text). Heads also carry `sh249_head`; mast arms `sh249_arm_ft`; radar and arm signs `sh249_pole`; radar `sh249_aim_deg`; ped poles `sh249_ped_heads`, `sh249_push_button`.

| Callout | Pole (ft) | Arm (measured) | Heads (facing) | Arm signs | Radar | Luminaire dir |
|---|---|---|---|---|---|---|
| A | (−248.3, 41.5) | 54.9' | T, S, R(4-sec) → E (WB, SB int.) | S2 "SH 249", S3 R6-1L | PR1 (pole) | 15° |
| B | (−166.0, −91.0) | 54.9' | Q, P, O → NNW (SB feeder) | S1 "Spring Cypress Rd" | PR2 (pole), ADV1 (arm) | 120° |
| C | (−86.4, −62.6) | 54.9' | K, L, M → W (EB); N 5-sec pole-mounted | S2, S4 R6-1R | PR3, ADV2 (arm) | 181° |
| K | (286.1, −43.7) | 54.9' | J, I, H(4-sec) → W (EB, NB int.) | S2, S3 R6-1L | PR6 (pole) | 201° |
| L | (206.8, 87.2) | 59.9' | E, F, G → SSE (NB feeder) | S1 | PR5 (pole), ADV4 (arm) | 285° |
| M | (131.0, 62.5) | 54.9' | C, B, A → E (WB); D 5-sec pole-mounted | S2, S4 R6-1R | PR4, ADV3 (arm) | 289° |

(Directions are math angles, 0° = scene east, CCW.)

- **APS pedestal poles:** D (−169.7, 53.3), E (−233.8, 49.2), F (−240.8, 39.6), G (−219.0, −8.1, 2 heads), H (−185.2, −77.6), I (−173.9, −84.2), J (−95.8, −75.4); N (194.0, −56.0), O (272.2, −51.2), P (279.3, −41.4), Q (259.8, 7.8, 2 heads), R (231.3, 76.5), S (217.8, 82.7), T (141.9, 63.5). Crosswalk pairs: D–E, F–G–H, I–J; S–T, R–Q–P, N–O.
- **Controller U:** 6×6 pad at (24.7, 59.8), 4×2 cabinet on an 18-in. base (sheet 23 note 8), plus `P_CTRL_U_BBU`.
- **Electrical service V:** Type D pole at (195.7, 106.7).
- **S5 R3-8L:** ground-mounted at (245.5, 1.5) on the median east of the NB intersection, facing west (EB). Detail 7 on sheet 27 labels the same sign "S6", likely a drafting slip (the build doc's S6 = R1-5BL from sheets 40–41).
- **Sheet 67 (LMA(5)):** 5 × 55L + 1 × 60L single mast arms on 30' poles with luminaire, Type IV fixed-mount arms (55IV ×5, 60IV ×1), 8' luminaire arms ×6, 48-A drilled shafts 22 ft deep (poles A, B, C, K, L, M).
- **Plan-overlay check:** poles, arms, heads, ped poles, signs and S5 land on the sheet 26/27 symbols (`export/phase5a_plancheck_SB.png`, `_NB.png`).
- **New materials:** `MAT_Retro_Yellow` (backplate border), `MAT_Radar`.
- **New cameras (Engineering):** `CAM_P5_SB`, `CAM_P5_NB` (copies of the P4 views), `CAM_P5_ArmA_WBdriver`, `CAM_P5_ArmL_NBdriver`. Review renders in `export/phase5a_*.png` were made with `E_Signals` excluded; scene camera restored to `CAM_Review_Oblique` at 2400 × 1350.
- **Not modeled (decision):** numbered items 1–41 on sheets 26–27 (conduit, bores, ground boxes, fiber re-route). They are underground or flush and add little to a visualization.

**Plan questions settled (best educated guesses, decided 2026-11-06; flag to the designer if it matters):**

| Question | Decision | Why |
|---|---|---|
| 4-section heads H and R: sheet 28 labels the lenses <R <R <Y <G | Modeled as the standard TxDOT flashing-yellow-arrow head: red arrow, yellow arrow, flashing yellow arrow, green arrow | Two red arrows isn't a standard head; the second "<R" is most likely a slip for the flashing yellow arrow |
| ADV3 drawn on arm M, but callout M lists only a presence radar | Keep ADV3 on arm M as drawn | The drawing and the radar schedule (ADV3 = WB advance) agree; the callout text is the odd one out |
| R3-8L called S5 on the main plan, S6 in Detail 7 | S5 = R3-8L; S6 = R1-5BL | Sheet 28 and the main plan say S5; S6 is the R1-5BL on sheets 40–41 |
| Pole-mounted 5-section heads D and N: height | Housing centred at 15.8 ft (bottom about 13.1 ft) | The 17'-6" rule is for mast-arm heads; at 17'-6" the backplate would hit the arm |
| PR3 and PR4 aim (plan symbols show none) | Aimed at their scheduled stop-bar zones | Final aim is set by the radar vendor (sheet 23 notes 39, 43, 44) |

These are recorded in the affected objects' `sh249_note` and baked into `p5_build_sig.py`.

## Phase 5b: Proposed markings, curb ramps and S6 (done, saved as v07)

**Source:** sheets 40/41 (pages 14/15), offsets as for 38/39, clipped at match line D-D (the same line as C-C). Scripts in `work/`: `p5b_styles.py` (vector dump), `p5b_mk.py` (classification), `p5b_pads.py` (detectable-warning pads), `p5b_build.py` (meshes), `p5b_import_blender.py`, `p5b_cut_blender.py`, `p5b_gc.py` / `p5b_zoom.py` (review crops).

**Symbol vocabulary on 40/41 (differs from 38/39):**
- black fills: stop bars, crosswalk bars, arrows, word markings, plus annotation text and leader arrowheads (dropped by size: fills under 5 ft);
- black 0.24-pt lines: proposed lane lines, gore borders and hatching, ramp outlines, text leaders; black 0.72-pt: callout circles and leaders, broken-line dashes, RPM squares;
- dashed black 0.24-pt curves: U-turn / turn guide lines (K); gray 0.24 pt: existing curbs and background;
- detectable warnings: 5.5 × 2 ft groups of about 24 tiny filled dots (19 pads).
- Leader filter: polylines touching an arrowhead fill (up to 4.5 ft) or a callout circle, and any straight segment over 20 ft that is more than 15° off both road directions (5° and 121°).

**Objects:**
- `P_Markings`: `P_MK_White` (stop bars, crosswalks, lane lines, 12-in. hatching, dotted guides, arrows, words), `P_MK_Yellow` (median edges), `P_MK_RPM` (129 raised markers, J). Markings sit 1.5 cm above the pavement (existing ones are at 1 cm).
- `P_Ramps` (13 objects, 19 pads):
  - SB: Type 1 at pads 0 (SE), 2 (NW across the channel), 3 (NE); Type 5 at pads 8, 9 (SW); Type 21 median cut-through 6–7 (west median); Type 22 island walkway 1–4–5 (NW channel island).
  - NB: Type 1 at pads 11 (SE across the channel), 12 (SW), 13 (NW); Type 5 at pad 17 (NE); Type 21 cut-through 16–18 (east median); Type 22 walkway 10–14–15 (SE channel island).
- `P_Signs`: `P_SIGN_S6_R1-5BL_SB` at (−282.2, 95.3) facing 68°, `P_SIGN_S6_R1-5BL_NB` at (316.8, −98.1) facing −118.5°, each by its right-turn channel stop bar.
- Existing `E_MK_White` / `E_MK_Yellow` are now tagged `sh249_status = remove` (replaced by the proposed plan; sheet 23 note 36).
- **Plan-overlay check:** markings, ramps and S6 land on the sheet 40/41 symbols (`export/phase5b_plancheck_SB.png`, `_NB.png`). Review renders: `export/phase5b_SB.png`, `_NB.png`, `_SB_ramps.png`, `_NB_ramps.png` (cameras `CAM_P5b_SB_Ramps`, `CAM_P5b_NB_Ramps`).
- New materials: `MAT_DetectWarn`, `MAT_Sign_Red`, `MAT_RPM_White`, `MAT_RPM_Amber`.

## Phase 6: Context and look (done, saved as v08)

**Rebuild order** (all scripts in `work/`; container steps need `p6_common.py` beside them and the staged NAIP tif, `p3_rd_masks.npz`, `p5b_pads.json`):
1. Container: `p6_fetch_osm.sh` → `p6_osm_raw.json`; `p6_osm.py` → `p6_osm_buildings.json`; `p6_build_ctx.py` → `p6_context.json`; `p6_aerial_grid.py` → `p6_aerial_scene.npz`; `p6_trees.py` → `p6_trees.json` + `p6_trees_overlay.png`; `p6_textures.py` → `tex/p6_*.jpg`; `p6_sun.py` (prints the sun vector).
2. Blender: `p6_import_blender.py` (`STEP = 'buildings' | 'trees' | 'all'`; re-running replaces CTX_BLDG_* / CTX_TREE_* only), `p6_tag_context.py`, `p6_materials_blender.py`, `p6_light_blender.py`, then `p6_render_blender.py` for the review renders.

**OSM buildings** (collection `Context / CTX_Buildings`, 18 objects):
- Overpass query over the model extent + 200 ft margin (bbox 30.0115, −95.5929, 30.0146, −95.5879), fetched 2026-11-06 from the cloud container. Footprints converted WGS84 → UTM 15N → scene (rotate +2.9668° about ORIGIN_SC); they line up with the NAIP roofs (`work/p6_bldg_overlay.png`). Buildings that intersect the margin rectangle are kept whole.
- No footprint has `height` or `building:levels`, so all heights are assumed by type (assumption 47). Flat-roofed prisms from z = −0.10 m (aerial level), walls `MAT_CTX_Bldg_Wall`, roofs `MAT_CTX_Bldg_Roof`.
- The Mobil fuel canopy (`building=roof`) is `CTX_BLDG_Canopy_Mobil`: a 2-ft slab at 15–17 ft on three 1.5-ft columns along its long axis (`MAT_CTX_Canopy`).
- Names: `CTX_BLDG_<OSM name>` or `CTX_BLDG_<type>_<OSM way id>`. Tags: `sh249_status = context`, `sh249_phase = context`, `sh249_type = building_massing | building_canopy`, `sh249_note` (OSM way ID, name, building tag, height and its basis), `sh249_source`, `sh249_osm_id`, `sh249_height_ft`.
- OSM has no trees (no `natural=tree/wood/tree_row`) in the area. Some buildings visible in the aerial are not in OSM (e.g. one NE of the 7-Eleven) and are not modeled.

**Trees** (collection `Context / CTX_Trees`, 131 objects, NAIP-derived):
- Canopy mask from NAIP resampled to the scene frame at 1 ft (`p6_aerial_scene.npz`): ExG = 2G − R − B > 14 **and** mean RGB < 127 (tree canopy is darker than mown grass), opened with a 4-ft disc, closed with 2 ft, blobs ≥ 40 ft²; long thin blobs (minor-axis sd < 4 ft, aspect > 3) dropped as cast shadows of walls and light poles.
- Trunks must be ≥ 3 ft from pavement, curb band or sidewalk (`p3_rd_masks.npz` classes 1, 4, 5) and outside the blocked area: bridge deck footprint (Phase 3 edge lines extended through the margin) + 8 ft, building footprints + 4 ft, ramp pads + 12 ft.
- Greedy packing on the canopy distance transform: crown radius = clip(1.15 × inscribed radius + 1, 5, 16) ft, needing at least an 8-ft inscribed disc; height = clip(2.1 r + 8 ± 2, 16, 45) ft. 117 trees fall in the context margin, 14 on roadside inside the model extent.
- Geometry: 8 shared meshes `CTX_TreeMesh_<S|M|L|XL>_<A|B>` (6-sided trunk + lumpy icosphere crown, 88 faces, 54 vertices; A/B differ only in canopy green). Each `CTX_TREE_nnn_<var>` object links one mesh and is scaled to (r, r, h) with a random Z rotation. Materials `MAT_CTX_TreeTrunk`, `MAT_CTX_TreeCanopy_A/B`.
- Tags: `sh249_status/phase = context`, `sh249_type = tree`, `sh249_note` ("NAIP-derived …, crown dia, height"), `sh249_source = NAIP-derived`, `sh249_variant`.
- The four Phase 3 bridge objects now carry the same context tags (`sh249_type = bridge_deck | bridge_rail | bridge_embankment | bridge_bents`).

**Materials** (`p6_materials_blender.py`; GLB-safe: UV Map `rastUVmap` → Mapping (Point, scale = 1233.77/T, 826.63/T) → Image Texture → Principled Base Color; the exporter writes KHR_texture_transform, checked in a trial export):

| Material | Texture (work/tex/) | Tile T | Roughness | Used by |
|---|---|---|---|---|
| MAT_Asphalt | p6_asphalt.jpg 2048² (grain, light aggregate, soft mottling, sealed cracks, faint stains) | 8 m | 0.92 | E_RD_Pavement |
| MAT_Curb (new) | p6_concrete_curb.jpg 1024² | 3 m | 0.85 | E_RD_Curb |
| MAT_Sidewalk | p6_sidewalk.jpg 1024² (lighter, broom streaks) | 3 m | 0.85 | E_RD_Sidewalk_assumed |
| MAT_Island_Concrete | p6_island_conc.jpg 1024² (darker, dirtier) | 3 m | 0.88 | E_ISL_* (concrete) |
| MAT_Grass | p6_grass.jpg 1024² (green with dry patches) | 4 m | 0.95 | E_ISL_NE_Landscaped |
| MAT_Paint_White / Yellow | p6_paint_white/yellow.jpg 512² (~8% worn speckle) | 1.5 m | 0.55 | E_MK_*, P_MK_White/Yellow |

- The marking meshes (`E_MK_White`, `E_MK_Yellow`, `P_MK_White`, `P_MK_Yellow`) had no UVs; a `rastUVmap` layer (same affine as the aerial) was added. Geometry unchanged.
- `MAT_Concrete` (56 UV-less users: foundations, pads, ramps), `MAT_Bridge_Concrete`, `MAT_Embankment`, `MAT_DetectWarn` and all signal materials are unchanged.
- Textures are tileable FFT noise generated by `p6_textures.py`; no procedural shader nodes.

**Lighting** (`p6_light_blender.py`):
- `SUN_Main` kept and re-aimed for **15 April 2026, 10:00 CDT (15:00 UTC)** at ORIGIN_SC: elevation 38.9°, true azimuth 102.1° (scene azimuth 100.5° from +Y), from `p6_sun.py` (NOAA algorithm). Energy 3.4, colour (1.0, 0.965, 0.91), angle 1.2° for soft shadows.
- World: clear-sky gradient on the view direction (ground haze below the horizon, pale blue horizon, blue zenith), strength 0.9. Hosek-Wilkie was tried but renders very dim in Eevee 5.2. View transform stays Standard.
- Eevee: shadows on (2 rays, 8 steps), raytracing + fast GI on, 64 render samples. Date/time stored as scene properties `SH249_sun_*`.

**Review renders** (proposed view, 2400 × 1350): `export/phase6_oblique.png`, `phase6_SB.png`, `phase6_NB.png`, `phase6_driver_WB_ArmA.png` (CAM_P5_ArmA_WBdriver). About 3 s each. Placement check: `work/p6_trees_overlay.png`.

**Size:** v08 .blend 1.84 MB (textures linked from `work/tex/`, relative paths). Trial GLB (Draco, all but Reference) 11.1 MB, mostly the aerial embedded as PNG (fixed in Phase 8 by JPEG).

**Unchanged:** all E_/P_ geometry, tags, the `P5b_RampCut` modifier and its hidden cutters (checked after the build). Only E_RD_Curb's material slot changed (MAT_Concrete → MAT_Curb) and the four marking meshes gained a UV layer.

## Phase 7: Engineering extras (done, saved as v09)

**Rebuild order** (scripts in `work/`):
1. Blender, on v08: `p7_snapshot.py` with `MODE='save'` → `p7_baseline_v08.json` (already saved; don't overwrite it from a later file).
2. Container (needs `p5b_mk.json`, `p5b_pads.json`, `p3_rd_masks.npz`): `python3 p7_geom.py <work_dir/> p7_data.json` (approaches, stop bars, lane centres, driver eye points, crosswalk camera points, radar-zone polygons in plan ft); `python3 p7_build_zones.py p7_data.json p7_radar_zones.json` (earcut fill + 0.6-ft outline meshes, Blender m); `p7_plot.py` → `p7_geom_overview.png` (check on the NAIP; needs `p6_common.py` and the tif). `p7_geom.py` hard-codes the stop-bar fill indices in `p5b_mk.json` (10, 24, 31–33, 89, 98, 106) and asserts their centroids.
3. Blender: `p7_radar_blender.py` (ENG_RZ_* + `CAM_P7_RadarTop`), `p7_cameras_blender.py` (CAM_P7_Drv_* / Ped_* / APS_*; global `APS_POLE`, default 'D'), `p7_visibility_blender.py` → `p7_visibility.json`, then `p7_render_blender.py`. On the device: `python3 work/p7_legend.py export/phase7_change_*.png` stamps the legend (run once per fresh render; it edits in place).

**Change view** (`p7_change_view.py`, globals `MODE = 'apply' | 'restore'`, `PURGE`):
- Tints the 111 E_/P_ objects tagged `sh249_status = remove` (red) or `new` (green), 484 material slots, by switching each slot to object-link and assigning a tinted copy `<material>__CV_<status>` (original shader mixed 60/40 with a tint Principled plus slight emission). Shared materials are never edited. remain, context, the E_RD_/E_ISL_ surfaces and P_RampCutters are untouched.
- The original slot state is stored in the scene property `SH249_p7_cv_state`; restore puts it back and (with PURGE) deletes the 34 copies. Apply refuses to run twice. `p7_render_blender.py` / `p8_render_blender.py` with `VIEW='change'` apply and restore around the renders, so the saved file never contains the tint.
- The change view shows everything (E_Signals and E_Markings included). Old and new markings overlap; the new ones (green, 1.5 cm) draw over the old (red, 1 cm).

**Radar zones** (collection `Engineering / ENG_RadarZones`, 10 objects `ENG_RZ_PR1`–`PR6`, `ENG_RZ_ADV1`–`ADV4`, 7,017 faces):
- One mesh per radar: translucent fill (slot 0), outline ribbon (slot 1) and a flat label converted from text (slot 2: id plus approach line, reading for the approaching driver; ADV labels double size). z = 3 cm (fill), 3.3 cm (edge), 3.6 cm (label). Materials `MAT_P7_RZ_PR_Fill/Edge` (cyan), `MAT_P7_RZ_ADV_Fill/Edge` (magenta), `MAT_P7_RZ_Label`; fills alpha 0.20, render method Blended (glTF alphaMode BLEND).
- **The collection has `hide_render = True`**, so normal renders are unaffected; `VIEW='radar'` turns it on temporarily. It is visible in the viewport.
- Tags: `sh249_type = radar_zone`, `sh249_status = sh249_phase = engineering`, `sh249_callout`, `sh249_radar` (the P_RADAR_* object), `sh249_zone_kind` (presence / advance), `sh249_approach`, `sh249_aim_deg`, `sh249_range_ft` (ADV), `sh249_fov_cover` (PR), `sh249_sheet = 28`, `sh249_note` (schedule designation + footprint basis).
- PR zone = approach width (stop-bar length) from the stop bar to 50 ft upstream, clipped to pavement. ADV zone = 2.5–5.5 s of travel upstream of the stop bar at the posted speed (SB feeder 50 mph: 183–403 ft; others 45 mph: 165–363 ft) inside a 12° beam on the radar's `sh249_aim_deg`, limited to the approach corridor. Outside the model extent (most of ADV1, ADV2, ADV4) the zone is not clipped to pavement, but it lines up with the road on the NAIP (`work/p7_geom_overview.png`).
- Approach ↔ radar (sheet 28 schedule): SB intersection: SB = PR1 + ADV1, EB = PR2 + ADV2, WB = PR3. NB intersection: NB = PR6 + ADV4, EB = PR4, WB = PR5 + ADV3.
- Coverage check (generic presence radar ±45°, 140 ft, from the modelled aim): PR2, PR5, PR6 ≥ 98 %; PR1 66 %, PR4 63 %, PR3 58 %. The final aim is the vendor's (sheet 23 notes 39, 43, 44); the PR3 and PR4 aims were assumed in Phase 5a.

**Cameras** (Engineering; tagged `sh249_type = camera_driver | camera_ped | camera_aps | camera_review`, with `sh249_note`):
- Driver (6): `CAM_P7_Drv_<SB|NB>int_<SB|NB|EB|WB>`. Eye 3.5 ft, 8 ft behind the upstream edge of the proposed stop bar, centred in lane 2 (from the left), looking down the lane-line axis, +7° pitch, 24 mm. Lanes: SB int: SB 3, EB 4, WB 3; NB int: NB 3 (plus a hatched gore), EB 3, WB 4.
- Pedestrian (8): `CAM_P7_Ped_<SB|NB>_<N|W|S|E|CH>`. Eye 5 ft above the walking surface (raycast), 5 ft behind the first crosswalk bar at the new ramp, facing the far ramp, −2° pitch, 24 mm. SB: N (E→D), W (F→G→H via the median), S (I→J), CH (right-turn channel, pad 2→1). NB: N (T→S), E (R→Q→P via the median), S (N→O), CH (pad 11→10).
- APS: `CAM_P7_APS_D` (pole D, PB1 R10-3eL), 35 mm. Radar overview: `CAM_P7_RadarTop` (ortho, 1500 ft wide, centre (75, −20) ft).

**Head-visibility check** (`p7_visibility_blender.py` → `p7_visibility.json`; proposed view; 3 × 3 rays to each head face; visible = at least 5 of 9 clear):
- **No problems found.** All 20 heads are 100 % visible from every lane (20 lanes) at the stop bar; nothing is blocked by arms, signs, luminaires, ped poles, trees or the bridge. Rays were checked to hit the right objects (heads, bent caps, deck).
- Sustained visibility: all 3–4 faces stay visible on every lane from the stop bar back to the MUTCD Table 4D-2 distance (460 ft at 45 mph, 540 ft at 50 mph), in 20-ft steps. The two inner approaches (WB to the SB intersection, EB to the NB intersection) are seen from under the bridge; the sight line passes below the modelled 18-ft soffit, which is an assumed height (assumption 12).
- Cone (MUTCD 4D.13, from 10 ft behind the stop line at the approach centre): all heads within ±12.5° (limit 20°).
- Longitudinal (4D.14, 40–180 ft past the stop line): 95–119 ft on the Spring Cypress approaches; 149–163 ft on the SB and NB feeder approaches (inside the limit, toward the far end).
- Vertical angle from the eye at the stop bar: 4.7–9.0°.
- Not covered: vehicles (e.g. trucks in the adjacent lane), grades and vertical curves (site modelled flat), and anything beyond the model extent other than OSM buildings and NAIP trees.

**Renders** (`export/phase7_*.png`, 2400 × 1350, 2.5–4.3 s each in Eevee; 21 frames ≈ 70 s; the visibility check takes 1.5 s):
- Change view: `phase7_change_oblique`, `_SB`, `_NB` (CAM_Review_Oblique, CAM_P5_SB, CAM_P5_NB), with a legend.
- Radar: `phase7_radar_top`, `_SB`, `_NB`.
- Driver: `phase7_drv_<sbint|nbint>_<dir>` (6). Pedestrian: `phase7_ped_<sb|nb>_<leg>` (8). APS: `phase7_aps_d`.
- Test renders and the trial radar GLBs are in `work/p7_tests/`.

**Unchanged:** `p7_snapshot.py MODE='compare'` after all Phase 7 work: the 302 E_/P_/CTX_ objects (geometry, transforms, material slots, tags, modifiers, visibility, collections), 46 materials and the `P5b_RampCut` node group are identical to v08. Additions: 5 `MAT_P7_RZ_*` materials, collection ENG_RadarZones (10 objects) and 16 cameras. v09 .blend: 2.0 MB, 351 objects, saved with the scene camera on CAM_Review_Oblique at 2400 × 1350.

## Phase 8: Export (done, export copy v10_export)

**Integrity:** v09 compared clean against `p7_baseline_v08.json` (only the 5 `MAT_P7_RZ_*` NEW), then fingerprinted as `work/p8_baseline_v09.json`, then saved as `blend/sh249_sc_v10_export.blend`. All export prep happened in that copy. After the export and the renders, v10_export still compares clean against v09 (302 objects, 51 materials, 1 node group, no differences); the only temporary changes (aerial `hide_select`, Reference layer exclude, render excludes, change view) are restored by the scripts. v09 was not opened for writing after the copy.

**GLB** (`export/sh249_springcypress.glb`, **6.06 MB, no Draco**; scripts `p8_export_glb.py` (Blender) + `p8_glb_post.py` (container); check with `p8_glbinfo.py`):
- Exporter settings: selection = all meshes in Aerial, Context, Existing, Proposed (minus P_RampCutters) and Engineering/ENG_RadarZones (301 objects); `use_visible = False`, `use_renderable = False`, `export_apply = True`, `export_extras = True`, `export_hierarchy_full_collections = True`, `export_gpu_instances = True`, `export_image_format = 'JPEG'` (quality 85), no cameras, no lights, Y-up. Draco off.
- Node tree (checked in the GLB JSON): `Scene Collection` → `Aerial` (AERIAL_NAIP2022_60cm), `Context` (4 bridge objects, CTX_Buildings 18, CTX_Trees 8 instanced nodes), `Engineering` → `ENG_RadarZones` (10), `Existing` → E_Markings 2, E_Roadway 12, E_Signals 27, E_Signals_Remain 14; `Proposed` → P_Markings 3, P_Ramps 13, P_Signals 64, P_Signs 2. Not exported: Reference, P_RampCutters, SUN_Main, ORIGIN_SC, cameras. The scene's `SH249_*` georeference properties come through as scene extras.
- Size breakdown: geometry 3.3 MB (Existing 1.66 MB / 34.7k tris, Proposed 1.22 MB / 23.9k, Context 0.25 MB / 5.8k with instancing, radar zones 0.21 MB / 7.0k, aerial 2 tris); images 2.5 MB (asphalt 2048² 1.2 MB, aerial 2000 × 1340 0.41 MB, grass 0.27, sidewalk 0.17, island 0.15, curb 0.15, paint white/yellow 0.08 each); JSON 0.41 MB.
- Ramp cuts baked: E_RD_Curb 11,556 tris (uncut 12,383), E_RD_Roadside 1,488 (1,578), E_RD_Sidewalk_assumed 603 (866), E_ISL_W_Median 296 (317) — the GLB counts equal the evaluated (cut) meshes. The openings are visible in the viewer (`work/p8_tests/viewer_13_ramp_cut_existing_only.png`). `P5b_RampCut` and the cutters are untouched in the .blend.
- Trees: EXT_mesh_gpu_instancing, 8 nodes `CTX_Trees.0`–`.7` carrying all 131 instances; they render in three.js. Per-tree tags are lost by instancing; `p8_glb_post.py` puts a shared context/tree note on the 8 nodes.
- Mesh validity: no mesh changed under `mesh.validate()` and the export logged no "not valid" warnings (see "Exporter gotchas").
- Materials: radar zones export as alphaMode BLEND; the aerial is base black + emissive texture (the viewer swaps it to unlit).

**Viewer** (`export/sh249_springcypress_viewer.html`, 8.7 MB, one self-contained file, works offline from a double-click; source in `work/p8_viewer/`; tested in headless Chrome from `file://` with no network requests, and by the user on their machine):
- three.js r187 + GLTFLoader + OrbitControls bundled with esbuild (minified, 638 KB) and inlined; GLB inlined as base64; camera presets inlined from `p8_cameras.json`.
- View modes: Existing (hides `sh249_status = new`), Proposed (hides `remove`), Both, Change (remove → 60 % toward red (0.85, 0.06, 0.05), new → green (0.10, 0.72, 0.14), small emissive, tinted material clones cached; legend shown).
- Layers: Existing signals & markings, Proposed signals/markings/ramps, Roadway surfaces (E_Roadway, separate so the road stays in Proposed mode), Context, Aerial, Radar detection zones (off by default).
- Click any object: info card with name, `sh249_note`, callout, status, type, sheet and the other `sh249_*` tags; yellow box highlight. Picking skips hidden objects and the aerial.
- 22 camera presets from the scene cameras: overview oblique, top, SB / NB close-ups, radar top, SB / NB curb ramps; 6 driver's-eye views; 8 crosswalk views + APS pole D. Perspective presets use the Blender lens (horizontal FOV); ortho cameras become a high 30°-wide perspective view of the same width. Smooth 0.9-s transitions.
- Rendering: log depth buffer, polygon offset on paint/RPM/detectable warnings, radar materials `depthWrite = false` + render order 10 (no flicker), sun shadows (4096 map over ±230 m around the interchange), hemisphere 2.4 + sun 3.4 from the Phase 6 sun direction, no tone mapping (matches Standard), CSS sky gradient behind a transparent canvas.
- "For illustration only – not for construction" label always on screen.
- Screenshots: `work/p8_tests/viewer_*.png`.

**KMZ** (`export/sh249_springcypress.kmz`, 463 KB; `p8_build_kmz.py`, container, pycollada):
- `doc.kml` + 7 COLLADA models (metres, Z-up, plain Lambert colours, double-sided, world transforms baked): Existing folder — signals to be removed (E_Signals, 5.9k tris), equipment to remain (E_Signals_Remain), existing markings (E_Markings); Proposed folder — proposed signals (P_Signals, 14.1k tris), S6 signs, proposed markings, curb ramps. No aerial, roadway, context or radar zones. Plus an origin pin and a LookAt over the interchange.
- Every model: `<Location>` Lat 30.0130799, Lon −95.5906606, `<heading>` 1.670, tilt/roll 0, `altitudeMode relativeToGround`; markings and ramps at altitude 0.10 m, equipment at 0.
- Checks: DAEs reload in pycollada; a top-down plot of the DAE vertices matches the plan layout (`work/p8_tests/p8_kmz_check.png`); placing plan points the way Google Earth does (origin + heading) agrees with the Phase 2 plan→UTM transform within 0.07 m across the model extent.
- **For the user to check in Google Earth Pro** (can't be done from here): poles at the curb corners and stop bars on the frontage roads in the imagery; turn off "3D Buildings" if the photogrammetry hides the markings; markings may float or sink a little where the terrain isn't flat.

**Final renders** (`export/final_*.png`, 2400 × 1350, Eevee about 3 s each; `p8_render_blender.py`):

| File | Camera | View |
|---|---|---|
| `final_overview_existing.png` | CAM_Review_Oblique | existing |
| `final_overview_proposed.png` | CAM_Review_Oblique | proposed |
| `final_change_oblique.png` | CAM_Review_Oblique | change, legend stamped by `p7_legend.py` |
| `final_SB_proposed.png` | CAM_P5_SB | proposed |
| `final_NB_proposed.png` | CAM_P5_NB | proposed |
| `final_driver_SBint_SB.png` | CAM_P7_Drv_SBint_SB | proposed |

v10_export saved with the scene camera on CAM_Review_Oblique at 2400 × 1350.

**Decided not to do (2026-11-06):** a higher-resolution aerial (no free source newer or sharper than NAIP 2022, see "Aerial imagery"); street-level photoreal 3D. Google's Photorealistic 3D Tiles can't be used offline or cached under Google's terms and already contain today's poles; own photogrammetry would need a drone/ground capture. The KMZ in Google Earth provides the real-world 3D context instead.

## Phase history
- v01–v04: Phases 0–3. v05: Phase 4. v06: Phase 5a. v07: Phase 5b. v08: Phase 6. **v09: Phase 7 (clean model).** **v10_export: Phase 8 export copy** (identical model; GLB, viewer, KMZ and final renders made from it).
- Only v09 and v10_export are kept in this repo. Their aerial image path was made relative when the repo was set up; nothing else changed.
