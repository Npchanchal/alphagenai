import random, statistics as st, math, json
from rules import *
random.seed(2026)
out={}
# T1 low-ball and T2 width, sigma=1.5pp, midpoint 5
sig=1.5; mu=5.0; hon=1.2816*sig
noise=[random.gauss(0,sig) for _ in range(4000)]
def exp_score(f,L,U):
    xs=[f(L,U,mu+e) for e in noise]; xs=[x for x in xs if x is not None]
    return st.mean(xs)
bs=[i*0.25 for i in range(0,17)]
hs=[i*0.25 for i in range(1,25)]
for name,f in RULES.items():
    eb=[exp_score(f,mu-b-hon,mu-b+hon) for b in bs]
    ew=[exp_score(f,mu-h,mu+h) for h in hs]
    kb=max(range(len(bs)),key=lambda i:eb[i]); kh=max(range(len(hs)),key=lambda i:ew[i])
    out[name]={"lowball_best_b":bs[kb],"lowball_gain":eb[kb]-eb[0],"best_halfwidth":hs[kh],"widest":hs[kh]==hs[-1] or (ew[-1]>=ew[kh]-1e-9)}
    print(f"{name:36s} lowball best b={bs[kb]:4.2f} gain={eb[kb]-eb[0]:+6.1f} | best half-width={hs[kh]:4.2f} (honest {hon:.2f}){' WIDEST' if out[name]['widest'] else ''}")
json.dump(out,open("incentives.json","w"))
