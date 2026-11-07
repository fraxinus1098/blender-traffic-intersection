import json, struct, sys, collections
f=open(sys.argv[1],'rb').read()
L=struct.unpack('<I',f[12:16])[0]; J=json.loads(f[20:20+L]); binlen=len(f)-20-L-8
print('json',L,'bin',binlen,'ext',J.get('extensionsUsed'))
nodes=J['nodes']; scene=J['scenes'][0]
def name(i): return nodes[i].get('name')
def tree(i,d=0,maxd=2):
    n=nodes[i]; ch=n.get('children',[])
    if d<=maxd: print('  '*d+str(n.get('name')),'children=%d'%len(ch),'mesh' if 'mesh' in n else '', 'ext' if n.get('extensions') else '')
    for c in ch: tree(c,d+1,maxd)
for r in scene['nodes']: tree(r)
# size by bufferView usage
bv=J['bufferViews']; acc=J['accessors']
use=collections.Counter()
img=0
for im in J.get('images',[]):
    use['image:'+im.get('name','?')+':'+im.get('mimeType','')]+=bv[im['bufferView']]['byteLength']
# map mesh -> top collection
parent={}
for i,n in enumerate(nodes):
    for c in n.get('children',[]): parent[c]=i
def top(i):
    path=[]
    while i in parent: i=parent[i]; path.append(nodes[i].get('name'))
    return path[-1] if path else nodes[i].get('name')
meshbytes=collections.Counter(); seen=set()
for i,n in enumerate(nodes):
    if 'mesh' in n and n['mesh'] not in seen:
        seen.add(n['mesh']); t=top(i)
        for p in J['meshes'][n['mesh']]['primitives']:
            for a in list(p['attributes'].values())+[p.get('indices')]:
                if a is None: continue
                meshbytes[t]+=bv[acc[a]['bufferView']]['byteLength'] if 'bufferView' in acc[a] else 0
for k,v in sorted(use.items(),key=lambda x:-x[1]): print('%8.0f KB'%(v/1024),k)
for k,v in meshbytes.items(): print('%8.0f KB geometry'%(v/1024),k)
print('nodes',len(nodes),'meshes',len(J['meshes']),'materials',len(J['materials']))
inst=[n.get('name') for n in nodes if 'EXT_mesh_gpu_instancing' in n.get('extensions',{})]
print('gpu-instanced nodes',inst)
ex=[n for n in nodes if n.get('extras')]
print('nodes with extras',len(ex), ex[0]['name'], ex[0]['extras'])
