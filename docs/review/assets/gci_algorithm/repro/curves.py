import json, random, statistics as st
from rules import *
random.seed(3); sig=1.5; mu=5.0; hon=1.2816*sig
noise=[random.gauss(0,sig) for _ in range(3000)]
def es(f,L,U):
    xs=[f(L,U,mu+e) for e in noise]; xs=[x for x in xs if x is not None]; return st.mean(xs)
bs=[i*0.2 for i in range(0,21)]; hs=[i*0.25 for i in range(1,25)]
out={"bs":bs,"hs":hs,"hon":hon,"low":{},"wid":{}}
for n,f in RULES.items():
    e=[es(f,mu-b-hon,mu-b+hon) for b in bs]; out["low"][n]=[x-e[0] for x in e]
    out["wid"][n]=[es(f,mu-h,mu+h) for h in hs]
json.dump(out,open("curves.json","w"))
