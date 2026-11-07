import json,math
R=json.load(open('objs.json'))
ARMS={'26':{'A':((-248.30,41.46),(-228.28,-9.61)),'B':((-166.0,-90.98),(-112.56,-78.56)),'C':((-86.39,-62.55),(-110.72,-13.39))},
      '27':{'K':((286.1,-43.65),(267.28,7.89)),'L':((206.84,87.16),(150.0,68.33)),'M':((130.99,62.47),(143.61,9.06))}}
def segd(p,a,b):
    ax,ay=a;bx,by=b;px,py=p; dx,dy=bx-ax,by-ay; L2=dx*dx+dy*dy
    t=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/L2)); return math.hypot(px-ax-t*dx,py-ay-t*dy),t*math.sqrt(L2)
out={}
for s,arms in ARMS.items():
    for k,(a,b) in arms.items():
        print('== arm',k)
        for o in R[s]:
            if not o['sc'].startswith('(0.0'): continue
            if o['t'] not in ('curve','rect') or o['n']<4 or o['n']>9: continue
            d,t=segd((o['cx'],o['cy']),a,b)
            if d<7 and max(o['w'],o['h'])<7 and max(o['w'],o['h'])>0.8:
                print('   n%d lw%.2f fill%d c(%.2f,%.2f) wh(%.2f,%.2f) d%.1f s%.1f'%(o['n'],o['lw'],o['fill'],o['cx'],o['cy'],o['w'],o['h'],d,t), o['pts'] if o['n']<=5 else '')

print('#### signs')
for s,arms in ARMS.items():
    for k,(a,b) in arms.items():
        for o in R[s]:
            if not o['sc'].startswith('(0.0') or o['fill']: continue
            if o['n']<6 or o['n']>20: continue
            d,t=segd((o['cx'],o['cy']),a,b)
            if d<4 and 2.5<max(o['w'],o['h'])<10 and t>3:
                print(s,k,'n%d lw%.2f c(%.2f,%.2f) wh(%.2f,%.2f) d%.1f s%.1f'%(o['n'],o['lw'],o['cx'],o['cy'],o['w'],o['h'],d,t))
