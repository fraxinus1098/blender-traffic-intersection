# Notes for Claude (or anyone picking this up later)

3D visualization of the TxDOT signal upgrade at SH 249 at Spring Cypress Rd (CSJ 0720-03-153), built in Blender 5.2 over the Blender MCP. The project is finished (Phases 0–9). The Louetta Rd interchange in the same plan PDF was never built and isn't planned.

Phase 9 (v11 improvements: lidar heights, rebuilt bridge, concrete pavement, Mapillary photo overlays, a richer viewer and KMZ) is done; the plan and its status are in `docs/PLAN_v11.md`. **The clean model is `blend/sh249_sc_v11.blend`; the export copy is `blend/sh249_sc_v12_export.blend`.**

Read first:
- `docs/BUILD_LOG.md`: what was built and how, phase by phase, plus coordinate frames and sheet offsets
- `docs/ASSUMPTIONS.md`: the 86 assumptions
- `docs/BUILD.md`: how to run the scripts, the Phase 9 run order and export pipeline (WSL + Windows Blender, venv, lidar download, Mapillary)
- `docs/CLAUDE_WORKFLOW.md`: the original Claude-session working notes (MCP call rules, container/device file transfer, md5 checks)

Rules that still apply:
- `blend/sh249_sc_v11.blend` is the clean model (v09 is the Phase 7 one, kept). Don't edit either in place; save changes as a new version, and check with `work/p7_snapshot.py` (`MODE='compare'`) against `work/p9_baseline_v11.json`.
- Do export prep only in an export copy, never in the clean model.
- Keep the folder layout: the .blend files load `work/tex/`, `imagery/` and `plans/masked/` by relative path.
- Keep the `sh249_*` custom-property tags and the collection names (E_/P_/CTX_/ENG_); the viewer's modes and layers depend on them.
- Blender MCP calls: keep them small, and set `result` to a dict.
- Pass `SH249_ROOT` to Blender scripts with backslashes (`\\wsl.localhost\Ubuntu\...\`); see `docs/BUILD.md` Phase 9.
- Never write the Mapillary token into the repo (it lives in `~/.config/sh249/mapillary_token`).
