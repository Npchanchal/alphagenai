import math, warnings
warnings.filterwarnings("ignore")
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[5] / "backend"))
from app.services import gci_scoring as g
M = "revenue_growth_cc_pct"
S_FAM = 2.0      # fixed family scale (pp) for growth — calibrate in practice
W_TYP = 2.0      # typical range width (pp) for the family
K = 25.0         # points per scale unit
ALPHA = 0.2

def hit(L,U,A): return 100.0 if L <= A <= U else 0.0
def v4(L,U,A):
    o = g.GuidanceOutcome(period="FY", metric=M, guided_value=(L+U)/2, actual_value=A, guided_text="", guided_low=L, guided_high=U)
    return g.outcome_score_v4(o)
def core24(L,U,A):
    z,_ = g.core_vintage_z(M,L,U,A)
    return None if z is None else max(0.0, 100*(1-float(z)))
def r2(L,U,A):
    z = g.r2_vintage_terms(M,L,U,A).get("z")
    return None if z is None else max(0.0, 100*(1-float(z)))
def diffusion(L,U,A):
    m=(L+U)/2
    if m == 0: return None
    return 50+50*max(-1,min(1,(A-m)/abs(m)))
def conv(L,U,A, tau=0.01, alpha=45):
    m=(L+U)/2
    if m == 0: return None
    E=(A-m)/abs(m)
    if abs(E)<=tau: return 100.0
    if tau<E<=2.5*tau: return 90-10*((E-tau)/tau)
    if E>2.5*tau: return max(40.0,75-15*((E-2.5*tau)/tau))
    return max(-100.0,20-1.5*alpha*((abs(E)-tau)/tau))
def mape(L,U,A):
    m=(L+U)/2
    if m == 0: return None
    return max(0.0,100*(1-abs(A-m)/abs(m)))
def midpoint_pp(L,U,A): return max(0.0, 100 - K*abs(A-(L+U)/2)/S_FAM)
def D(L,U,A): return max(0.0,L-A)+max(0.0,A-U)
def interval(L,U,A): return 100 - K*((ALPHA/2)*(U-L) + D(L,U,A))/S_FAM
def range_p(L,U,A):
    a=(ALPHA/2)*W_TYP/S_FAM
    return max(0.0, min(100.0, 100 - K*(((ALPHA/2)*(U-L) + D(L,U,A))/S_FAM - a)))

RULES = {
 "Hit rate (in range = 1)": hit,
 "Conversation rubric": conv,
 "Relative error vs midpoint (MAPE)": mape,
 "Diffusion (owner v2.5 note)": diffusion,
 "CiteAlpha v4 (published)": v4,
 "GCI Core v2.4": core24,
 "GCI Range v2.4-R2 (A1–A5)": r2,
 "Midpoint error in points": midpoint_pp,
 "Interval score (linear)": interval,
 "Proposed: Range-P": range_p,
}
