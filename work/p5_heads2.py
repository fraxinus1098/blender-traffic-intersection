import json,math
R=json.load(open('objs.json')); W=json.load(open('words.json'))
H={'26':{'T':(-236.88,15.86),'S':(-232.94,4.56),'R':(-228.81,-6.90),'Q':(-142.71,-83.80),'P':(-129.58,-81.41),'O':(-117.04,-78.86),
        'M':(-99.50,-38.54),'L':(-104.82,-26.88),'K':(-109.88,-15.57),'N':(-88.84,-61.13)},
   '27':{'J':(275.31,-17.38),'I':(271.38,-6.73),'H':(268.19,5.04),'E':(152.68,68.46),'F':(163.51,71.68),'G':(175.34,74.96),
        'C':(138.36,37.36),'B':(140.58,26.13),'A':(142.80,14.60),'D':(133.49,61.64)}}
res={}
for s,hs in H.items():
    tris=[o for o in R[s] if o['sc'].startswith('(0.0') and o['n']==4 and o['lw']==0.72 and not o['fill'] and 2.5<max(o['w'],o['h'])<6]
    for k,(x,y) in hs.items():
        best=None
        for o in tris:
            d=math.hypot(o['cx']-x,o['cy']-y)
            if d<11 and (best is None or d<best[0]): best=(d,o)
        if best:
            P=best[1]['pts'][:3]; tip=max(P,key=lambda p:math.hypot(p[0]-x,p[1]-y))
            ang=math.degrees(math.atan2(tip[1]-y,tip[0]-x)); res[k]=(s,x,y,round(ang,1),tip)
            print(s,k,(x,y),'tri d%.1f'%best[0],'tip',tip,'face %.1f'%ang)
        else: print(s,k,'NO TRI')
json.dump(res,open('heads.json','w'))
