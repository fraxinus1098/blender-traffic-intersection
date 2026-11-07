"""Phase 8 GLB post-process (container). usage: python3 p8_glb_post.py in.glb out.glb
- drops the empty 'Reference' collection node and its (empty) child collection nodes
- gives the EXT_mesh_gpu_instancing tree nodes (CTX_Trees.N) context extras (instancing drops per-tree extras)
- prints a check of the result"""
import json, struct, sys
src, dst = sys.argv[1], sys.argv[2]
f = open(src, 'rb').read()
jl = struct.unpack('<I', f[12:16])[0]; J = json.loads(f[20:20 + jl]); BIN = f[20 + jl + 8:]
N = J['nodes']
def subtree(i):
    s = [i]
    for c in N[i].get('children', []): s += subtree(c)
    return s
drop = set()
for i, n in enumerate(N):
    if n.get('name') == 'Reference':
        st = subtree(i)
        assert all('mesh' not in N[k] for k in st), 'Reference subtree has meshes'
        drop |= set(st)
remap = {}; newN = []
for i, n in enumerate(N):
    if i not in drop: remap[i] = len(newN); newN.append(n)
for n in newN:
    if 'children' in n:
        n['children'] = [remap[c] for c in n['children'] if c not in drop]
for s in J['scenes']:
    s['nodes'] = [remap[c] for c in s['nodes'] if c not in drop]
J['nodes'] = newN
ninst = 0
for n in newN:
    ext = n.get('extensions', {}).get('EXT_mesh_gpu_instancing')
    if ext:
        cnt = J['accessors'][ext['attributes']['TRANSLATION']]['count']; ninst += cnt
        n.setdefault('extras', {}).update({'sh249_status': 'context', 'sh249_phase': 'context', 'sh249_type': 'tree',
            'sh249_source': 'NAIP-derived',
            'sh249_note': 'NAIP-derived tree (generic broadleaf); positions and crown sizes approximate (assumptions 50-52). %d trees share this mesh.' % cnt})
js = json.dumps(J, separators=(',', ':')).encode()
js += b' ' * ((4 - len(js) % 4) % 4)
out = b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + len(BIN)) + struct.pack('<I', len(js)) + b'JSON' + js + f[20 + jl:20 + jl + 8] + BIN
open(dst, 'wb').write(out)
print('dropped nodes', sorted(drop), 'instanced trees', ninst, 'bytes', len(out))
