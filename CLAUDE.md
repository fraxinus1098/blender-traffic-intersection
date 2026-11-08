# Notes for Claude (or anyone picking this up later)

3D visualization of the TxDOT signal upgrade at SH 249 at Spring Cypress Rd (CSJ 0720-03-153), built in Blender 5.2 over the Blender MCP. The project is finished (Phases 0–8). The Louetta Rd interchange in the same plan PDF was never built and isn't planned.

**Phase 9 (v11 improvements) is in progress on branch `v11-improvements`: read the "Status and handoff" section at the end of `docs/PLAN_v11.md` first.** The clean model for Phase 9 is `blend/sh249_sc_v11.blend`.

Read first:
- `docs/BUILD_LOG.md`: what was built and how, phase by phase, plus coordinate frames and sheet offsets
- `docs/ASSUMPTIONS.md`: the 73 assumptions
- `docs/BUILD.md`: how to run the scripts and the Phase 8 export pipeline
- `docs/CLAUDE_WORKFLOW.md`: the original Claude-session working notes (MCP call rules, container/device file transfer, md5 checks)

Rules that still apply:
- `blend/sh249_sc_v09.blend` is the clean model. Don't edit it in place; save changes as a new version, and check with `work/p7_snapshot.py` (`MODE='compare'`).
- Do export prep only in an export copy, never in the clean model.
- Keep the folder layout: the .blend files load `work/tex/`, `imagery/` and `plans/masked/` by relative path.
- Keep the `sh249_*` custom-property tags and the collection names (E_/P_/CTX_/ENG_); the viewer's modes and layers depend on them.
- Blender MCP calls: keep them small, and set `result` to a dict.
