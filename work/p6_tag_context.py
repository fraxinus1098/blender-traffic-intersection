"""Phase 6 (Blender): tag the Phase 3 mainlane context objects like the new CTX_ objects (properties only)."""
import bpy
NOTE = 'Phase 3 context: deck edges from sheets 38-39; soffit 18 ft, deck 24 ft, rails, bents and fill are illustrative (assumption 12)'
TYPES = {'CTX_SH249_Deck': 'bridge_deck', 'CTX_SH249_Rails': 'bridge_rail',
         'CTX_SH249_Embankment': 'bridge_embankment', 'CTX_SH249_Bents': 'bridge_bents'}
for n, t in TYPES.items():
    o = bpy.data.objects[n]
    o['sh249_status'] = 'context'; o['sh249_phase'] = 'context'; o['sh249_type'] = t
    o['sh249_note'] = NOTE; o['sh249_source'] = 'plan-derived (sheets 38-39)'
result = {'tagged': list(TYPES)}
