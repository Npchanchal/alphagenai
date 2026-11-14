import json, datetime as dt
from rules import range_p, v4, r2
D=dt.date.fromisoformat
infy={ # period: (end, actual, [(as_of,L,U)...]) from backend seed (hand-labelled rows)
 "FY22":("2022-03-31",19.7,[("2021-04-14",12,14),("2021-07-14",14,16),("2021-10-13",16.5,17.5),("2022-01-12",19.5,20)]),
 "FY23":("2023-03-31",15.4,[("2022-04-13",13,15),("2022-07-24",14,16),("2022-10-13",15,16),("2023-01-12",16,16.5)]),
 "FY24":("2024-03-31",1.4,[("2023-04-13",4,7),("2023-07-20",1,3.5),("2023-10-12",1,2.5),("2024-01-11",1.5,2)]),
 "FY25":("2025-03-31",4.2,[("2024-04-18",1,3),("2024-07-18",3,4),("2024-10-17",3.75,4.5),("2025-01-16",4.5,5)]),
 "FY26":("2026-03-31",3.1,[("2025-04-17",0,3),("2025-07-23",1,3),("2025-10-16",2,3),("2026-01-14",3,3.5)]),
}
out={}
for p,(end,A,vs) in infy.items():
    sc=[range_p(L,U,A) for _,L,U in vs]
    days=[]
    for i,(d,_,_) in enumerate(vs):
        nxt=D(vs[i+1][0]) if i+1<len(vs) else D(end)
        days.append(max(0,(min(nxt,D(end))-D(d)).days))
    exp=sum(s*w for s,w in zip(sc,days))/sum(days)
    # Marvin-style: final vintage, minus a charge for each revision that left the prior range
    outside=sum(1 for i in range(1,len(vs)) if vs[i][1]>vs[i-1][2] or vs[i][2]<vs[i-1][1])
    out[p]={"opening":sc[0],"exposure":exp,"final":sc[-1],"revisions_outside_prior":outside,"vintage_scores":sc,"days":days}
    print(p, "opening %.1f  exposure %.1f  final %.1f  outside-prior revisions %d"%(sc[0],exp,sc[-1],outside), [round(x,1) for x in sc], days)
# naive baseline: last year's reported growth
act={p:v[1] for p,v in infy.items()}; mid={p:(v[2][0][1]+v[2][0][2])/2 for p,v in infy.items()}
ps=list(infy); ge=[];ne=[]
for i in range(1,len(ps)):
    ge.append(abs(act[ps[i]]-mid[ps[i]])); ne.append(abs(act[ps[i]]-act[ps[i-1]]))
print("guidance MAE %.2f naive MAE %.2f ratio %.2f"%(sum(ge)/len(ge),sum(ne)/len(ne),(sum(ge)/len(ge))/(sum(ne)/len(ne))), ge, ne)
out["_naive"]={"guidance_mae":sum(ge)/len(ge),"naive_mae":sum(ne)/len(ne),"pairs":list(zip(ps[1:],ge,ne))}
json.dump(out,open("vintages.json","w"),indent=1)
