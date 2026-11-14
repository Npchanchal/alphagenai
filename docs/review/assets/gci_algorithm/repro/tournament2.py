import random, statistics as st, math, json
from rules import *
random.seed(7)
inc=json.load(open("incentives.json"))
# recompute width class
sig=1.5; mu=5.0
noise=[random.gauss(0,sig) for _ in range(3000)]
def es(f,L,U):
    xs=[f(L,U,mu+e) for e in noise]; xs=[x for x in xs if x is not None]; return st.mean(xs)
hs=[i*0.25 for i in range(1,25)]
for n,f in RULES.items():
    ew=[es(f,mu-h,mu+h) for h in hs]
    if max(ew)-min(ew)<0.5: inc[n]["width"]="ignores width"
    else:
        k=max(range(len(hs)),key=lambda i:ew[i])
        inc[n]["width"]="rewards widest" if k>=len(hs)-2 else f"peaks at ±{hs[k]:.2f} (honest ±1.92)"
        inc[n]["width_gain_wide"]=ew[-1]-es(f,mu-1.92,mu+1.92)

def rank(xs):
    o=sorted(range(len(xs)),key=lambda i:xs[i]); r=[0]*len(xs)
    for k,i in enumerate(o): r[i]=k
    return r
def spearman(a,b):
    ra,rb=rank(a),rank(b); n=len(a); ma=mb=(n-1)/2
    num=sum((x-ma)*(y-mb) for x,y in zip(ra,rb)); den=math.sqrt(sum((x-ma)**2 for x in ra)*sum((y-mb)**2 for y in rb))
    return num/den
# validity: 400 companies, 5-year windows A and B
N=400; YEARS=5
comp=[]
for i in range(N):
    s=random.uniform(0.5,3.0)
    b=0.0 if random.random()<0.5 else random.uniform(0,2*s)
    u=random.uniform(0.4,2.5)
    comp.append((s,b,1.2816*s*u))
def window(seed):
    rnd=random.Random(seed); rows=[]
    for (s,b,h) in comp:
        r=[]
        for _ in range(YEARS):
            m=rnd.uniform(1,15); g=m-b; r.append((g-h,g+h,m+rnd.gauss(0,s)))
        rows.append(r)
    return rows
WA,WB=window(11),window(22)
truth=[-math.sqrt(b*b+s*s) for (s,b,h) in comp]
def level(f,rows):
    xs=[f(*x) for x in rows]; xs=[x for x in xs if x is not None]
    return st.mean(xs) if xs else 0
res={}
for n,f in RULES.items():
    la=[level(f,r) for r in WA]; lb=[level(f,r) for r in WB]
    res[n]={"validity":spearman(la,truth),"stability":spearman(la,lb)}
    print(f"{n:36s} validity rho={res[n]['validity']:+.2f}  stability rho={res[n]['stability']:+.2f}  width: {inc[n]['width']}")
# near-zero and unit tests (real Infosys rows + synthetic unit pair)
rows={"INFY FY22 12–14→19.7":(12,14,19.7),"INFY FY23 13–15→15.4":(13,15,15.4),"INFY FY24 4–7→1.4":(4,7,1.4),
      "INFY FY25 1–3→4.2":(1,3,4.2),"INFY FY26 0–3→3.1":(0,3,3.1)}
real={n:{k:f(*v) for k,v in rows.items()} for n,f in RULES.items()}
unit={n:(f(1,3,0),f(19,21,18)) for n,f in RULES.items()}   # same 1pp miss below range
alt={}
for n,f in RULES.items():
    a=st.mean([x for x in [f(4,6,9),f(4,6,1),f(4,6,9),f(4,6,1)] if x is not None])   # alternate 3pp beat / 3pp miss
    b=st.mean([x for x in [f(4,6,6.5)]*4 if x is not None])                        # steady 0.5pp beat
    alt[n]=(a,b)
json.dump({"inc":inc,"val":res,"real":real,"unit":unit,"alt":alt},open("results.json","w"),indent=1)
for n in RULES: print(f"{n:36s} unit(1pp miss @2% vs @20%)={unit[n][0]!s:>6.6} / {unit[n][1]!s:>6.6}  alt={alt[n][0]:.1f} steady={alt[n][1]:.1f}  real={[None if v is None else round(v,1) for v in real[n].values()]}")
