import json, random, statistics as st
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
OUT="../"
plt.rcParams.update({"font.family":"Helvetica","font.size":9,"axes.spines.top":False,"axes.spines.right":False})
C=json.load(open("curves.json")); hon=C["hon"]
pick=["Conversation rubric","Diffusion (owner v2.5 note)","CiteAlpha v4 (published)","GCI Range v2.4-R2 (A1–A5)","Proposed: Range-P"]
cols=["#b45309","#7c3aed","#2563eb","#0891b2","#111827"]
# fig1 low-ball
bs=C["bs"]
fig,ax=plt.subplots(figsize=(6.4,3.3))
for n,c in zip(pick,cols):
    ax.plot(bs,C["low"][n],label=n,color=c,lw=2 if "Proposed" in n else 1.4)
ax.axhline(0,color="#9ca3af",lw=.8)
ax.set_xlabel("How far the company sets its range below its own expectation (pp)")
ax.set_ylabel("Change in expected row score")
ax.set_title("Guiding low: who gains? Growth guide at 5%, result noise σ = 1.5 pp",fontsize=9.5)
fig.legend(loc="lower center",ncol=3,frameon=False,fontsize=7.8); fig.tight_layout(rect=(0,0.13,1,1))
fig.savefig(OUT+"fig1_lowball.png",dpi=200); plt.close(fig)
# fig2 width
pick2=["Hit rate (in range = 1)","CiteAlpha v4 (published)","GCI Core v2.4","GCI Range v2.4-R2 (A1–A5)","Proposed: Range-P"]
cols2=["#9ca3af","#2563eb","#16a34a","#0891b2","#111827"]
hs=C["hs"]
fig,ax=plt.subplots(figsize=(6.4,3.3))
for n,c in zip(pick2,cols2):
    ax.plot(hs,C["wid"][n],label=n,color=c,lw=2 if "Proposed" in n else 1.4)
ax.axvline(hon,color="#9ca3af",ls="--",lw=.8); ax.text(hon+0.05,5,"honest 80% range ±1.92",fontsize=7.5,color="#6b7280")
ax.set_xlabel("Half-width of the guided range (pp), centred on the company's true expectation")
ax.set_ylabel("Expected row score"); ax.set_ylim(0,105)
ax.set_title("Wider ranges: which rules reward them?",fontsize=9.5)
fig.legend(loc="lower center",ncol=3,frameon=False,fontsize=7.8); fig.tight_layout(rect=(0,0.13,1,1))
fig.savefig(OUT+"fig2_width.png",dpi=200); plt.close(fig)
# fig3 validity vs stability
r=json.load(open("results.json"))["val"]
fig,ax=plt.subplots(figsize=(6.4,3.6))
OFF={"Hit rate (in range = 1)":(0.02,0.012),"CiteAlpha v4 (published)":(-0.02,-0.03),"GCI Range v2.4-R2 (A1–A5)":(0.02,-0.03),
 "GCI Core v2.4":(0.02,0.006),"Relative error vs midpoint (MAPE)":(0.02,-0.022),"Interval score (linear)":(0.02,-0.03),
 "Proposed: Range-P":(0.02,0.012),"Midpoint error in points":(0.02,-0.02)}
LAB={"Interval score (linear)":"Interval score (same point)","GCI Range v2.4-R2 (A1–A5)":"Range R2","CiteAlpha v4 (published)":"v4 (published)",
 "Diffusion (owner v2.5 note)":"Diffusion"}
for n,v in r.items():
    c="#111827" if "Proposed" in n else ("#b91c1c" if v["validity"]<0 else "#2563eb")
    ax.scatter(v["validity"],v["stability"],color=c,s=28)
    dx,dy=OFF.get(n,(0.02,0.005)); ha="right" if dx<0 else "left"
    ax.annotate(LAB.get(n,n),(v["validity"]+dx,v["stability"]+dy),fontsize=7,ha=ha)
ax.axvline(0,color="#9ca3af",lw=.8)
ax.set_xlim(-0.5,1.25); ax.set_xlabel("Validity: rank correlation with true midpoint reliability")
ax.set_ylabel("Stability: rank correlation across two 5-year windows")
ax.set_title("400 simulated companies, 5 closed years each",fontsize=9.5)
fig.tight_layout(); fig.savefig(OUT+"fig3_validity.png",dpi=200); plt.close(fig)
# fig4 Infosys vintages
import datetime as dt
v=json.load(open("vintages.json"))
infy=json.load(open('infy.json'))
fig,ax=plt.subplots(figsize=(6.6,3.4))
for p,(end,A,vs) in infy.items():
    for i,(d,L,U) in enumerate(vs):
        d0=dt.date.fromisoformat(d); d1=dt.date.fromisoformat(vs[i+1][0]) if i+1<len(vs) else dt.date.fromisoformat(end)
        ax.fill_between([d0,d1],[L,L],[U,U],color="#93c5fd" if i else "#2563eb",alpha=.55 if i else .8,lw=0)
    e=dt.date.fromisoformat(end); ax.plot([e],[A],marker="D",color="#b91c1c",ms=5)
    if p=="FY24": ax.text(e,A-1.3,f"{p} {A}%",fontsize=7,ha="center",color="#b91c1c")
    elif p=="FY25": ax.text(e,A+1.3,f"{p} {A}%",fontsize=7,ha="center",color="#b91c1c")
    else: ax.text(e+dt.timedelta(days=12),A+0.5,f"{p} {A}%",fontsize=7,ha="left",color="#b91c1c")
ax.set_ylabel("Revenue growth, constant currency (%)")
ax.set_title("Infosys: opening range (dark), later revisions (light), reported result (red)",fontsize=9.5)
fig.tight_layout(); fig.savefig(OUT+"fig4_infosys_vintages.png",dpi=200); plt.close(fig)
print("ok")
