"""
Repair metrics_design.json in place using the corrected analysis.

The trial data itself is fine; only two derived blocks were wrong, and both can be
recomputed exactly from what was already saved:

  subject   -> recomputed from records_design.json (label, subj, dir, want)
  confusion -> recomputed from the saved operating scores at a DISCLOSED threshold

Run after run_design.py. Idempotent.
"""
import json
import numpy as np
from analyze_subjects import subject_analysis, confusion_at_threshold

M = json.load(open("metrics_design.json"))
R = json.load(open("records_design.json"))
C = M["config"]
K = C["k_events"]

# ---- subject block ---------------------------------------------------------
by_subj = {}
for r in R:
    if r["mode"] == "subject":
        by_subj.setdefault(r["subj"], []).append(r)
per_subject = []
for c, evs in sorted(by_subj.items()):
    hits = sum(1 for r in evs if r["dir"] == r["want"])
    per_subject.append(dict(subj=c, label=evs[0]["label"], grade=evs[0]["grade"],
                            n_hit=int(hits)))
old = M.get("subject", {})
M["subject"] = subject_analysis(per_subject, K)
M["subject"]["motion"] = C["subj_motion"]
M["subject"]["n_subjects"] = len(per_subject)
M["subject"]["_superseded_pooled_k_of_K"] = old.get("empirical_k_of_K")

# ---- confusion block -------------------------------------------------------
mid = M["confusion"]["motion"] if "confusion" in M else C["motion"][len(C["motion"]) // 2]
op = M["operating"][str(mid)]
sub = [r for r in R if r["mode"] == "op" and r["motion"] == mid]
sc = np.array(op["scores"], float)
y = np.array(op["labels"], int)
if len(sub) != len(sc):
    raise SystemExit(f"record/score length mismatch: {len(sub)} vs {len(sc)}")
neg = np.sort(sc[y == 0])
thr90 = float(neg[min(int(0.90 * len(neg)), len(neg) - 1)])
M["confusion"] = confusion_at_threshold(sub, sc, thr90, "90% specificity")
M["confusion"]["motion"] = mid
M["confusion"]["prevalence"] = float(y.mean())

S = M["subject"]
print(f"repaired.  reflux children n={S['n_reflux']}, healthy n={S['n_healthy']}")
print(f"  per-event sensitivity {100*S['per_event_sens']:.1f}%   "
      f"per-event false-positive {100*S['per_event_fp']:.1f}%")
print(f"  best rule: >={S['best_k']} of {K}   "
      f"sens {100*S['best_sens']:.1f}%  spec {100*S['best_spec']:.1f}%")
print("  k :  sens   spec   chance-floor")
for k in range(1, K + 1):
    print(f"  {k} : {100*S['sens_k'][str(k)]:5.1f}  {100*S['spec_k'][str(k)]:5.1f}  "
          f"{100*S['chance_k'][str(k)]:5.1f}")
print(f"  never-detected refluxers: {100*S['never_detected_reflux']:.1f}%")
print(f"  confusion threshold: {M['confusion']['threshold']:.3f} "
      f"({M['confusion']['threshold_label']}), prevalence {100*M['confusion']['prevalence']:.0f}%")

with open("metrics_design.json", "w") as f:
    json.dump(M, f)
print("wrote metrics_design.json")
