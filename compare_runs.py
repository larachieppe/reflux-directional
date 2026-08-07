"""
Side-by-side comparison of the pre-fix (baseline_prefix/) and post-fix metrics.

Exists so the cost of each defect is visible rather than quietly absorbed by
republishing corrected numbers.
"""
import json, os, sys

OLD = "baseline_prefix"


def load(name):
    new = json.load(open(name))
    old_p = os.path.join(OLD, name)
    old = json.load(open(old_p)) if os.path.exists(old_p) else None
    return old, new


def f(x, pct=True, d=0):
    if x is None or x != x:
        return "  n/a"
    return f"{100*x:.{d}f}%" if pct else f"{x:.3f}"


def delta(o, n, pct=True):
    if o is None or n is None or o != o or n != n:
        return ""
    d = 100 * (n - o) if pct else (n - o)
    if abs(d) < 0.5 and pct:
        return "  ="
    return f" {d:+.0f}" if pct else f" {d:+.3f}"


def row(label, o, n, pct=True, w=34):
    print(f"  {label:<{w}} {f(o,pct):>7} -> {f(n,pct):>7}{delta(o,n,pct)}")


def sec(t):
    print(f"\n{'='*74}\n{t}\n{'='*74}")


od, nd = load("metrics_directional.json")
og, ng = load("metrics_design.json")

sec("STUDY 1  ELECTRODE COUNT   direction accuracy, grade >= III")
MOT = ng["config"]["motion"] if ng else []
EM = nd["config"]["motion"]


def dacc(M, n, m):
    try:
        d = M["primary"][str(n)][str(m)]
        return float("nan") if d.get("undecidable", 0) > 0.99 else d["dir_acc"]
    except Exception:
        return None


for m in EM:
    print(f"\n  --- motion {m} cm ---")
    for n in nd["config"]["counts"]:
        row(f"N={n}", dacc(od, n, m) if od else None, dacc(nd, n, m))

sec("STUDY 1  LATERALITY")
for m in EM:
    print(f"\n  --- motion {m} cm ---")
    for n in nd["config"]["counts"]:
        o = od["primary"][str(n)][str(m)]["lat_acc"] if od else None
        row(f"N={n}", o, nd["primary"][str(n)][str(m)]["lat_acc"])

sec("STUDY 1  AUC   (old: ONE value copied across all motion levels)")
for n in nd["config"]["counts"]:
    vals = [nd["primary"][str(n)][str(m)]["auc"] for m in EM]
    ovals = [od["primary"][str(n)][str(m)]["auc"] for m in EM] if od else []
    spread = max(vals) - min(vals)
    ospread = (max(ovals) - min(ovals)) if ovals else float("nan")
    print(f"  N={n:<3} old {min(ovals) if ovals else float('nan'):.3f}-{max(ovals) if ovals else float('nan'):.3f} "
          f"(spread {ospread:.3f})   new {min(vals):.3f}-{max(vals):.3f} (spread {spread:.3f})")

sec("STUDY 1  SPAN and SNR sweeps")
for k in sorted(nd["span_sweep"], key=float):
    o = od["span_sweep"].get(k, {}).get("dir_acc") if od else None
    row(f"span {float(k):.0f} cm", o, nd["span_sweep"][k]["dir_acc"])
print()
for k in sorted(nd["snr_sweep"], key=int):
    o = od["snr_sweep"].get(k, {}).get("dir_acc") if od else None
    row(f"SNR {k} dB", o, nd["snr_sweep"][k]["dir_acc"])

if ng:
    sec("STUDY 2  LOCKED DESIGN   direction / laterality / AUC")
    for m in ng["config"]["motion"]:
        o = og["operating"].get(str(m)) if og else None
        n_ = ng["operating"][str(m)]
        print(f"\n  --- motion {m} cm ---")
        row("direction", o["dir_acc"] if o else None, n_["dir_acc"])
        row("laterality", o["lat_acc"] if o else None, n_["lat_acc"])
        row("AUC", o["auc"] if o else None, n_["auc"], pct=False)
        if "abstain_rate" in n_:
            row("abstain rate (travelling)", None, n_["abstain_rate"])
        if "empty_abstain" in n_:
            row("abstain on EMPTY windows", None, n_["empty_abstain"])
        if "empty_called_retro" in n_:
            row("empty windows called retrograde", None, n_["empty_called_retro"])

    sec("STUDY 2  BY GRADE   (still)")
    for g in (1, 2, 3, 4, 5):
        o = og["grade"][str(g)]["0.0"]["dir_acc"] if og else None
        row(f"grade {['','I','II','III','IV','V'][g]}", o, ng["grade"][str(g)]["0.0"]["dir_acc"])

    sec("STUDY 2  MULTI-EVENT SCREENING RULE")
    S, OS = ng["subject"], (og.get("subject") if og else None)
    K = S["k_events"]
    print(f"  per-event sensitivity {f(S['per_event_sens'])}   "
          f"per-event false positive {f(S['per_event_fp'])}")
    print(f"  {'rule':<12} {'sens':>8} {'spec':>8} {'chance':>8}")
    for k in range(1, K + 1):
        mark = " <-- chosen" if str(k) == str(S["best_k"]) else ""
        print(f"  >={k} of {K:<6} {f(S['sens_k'][str(k)]):>8} "
              f"{f(S['spec_k'][str(k)]):>8} {f(S['chance_k'][str(k)]):>8}{mark}")
    if OS and "sens_k" in OS:
        bk = str(OS.get("best_k", "3"))
        print(f"\n  old chosen rule >={bk}: sens {f(OS['sens_k'][bk])} spec {f(OS['spec_k'][bk])}")
    row("refluxers never detected", (OS or {}).get("never_detected_reflux"),
        S["never_detected_reflux"])

print("\n")
