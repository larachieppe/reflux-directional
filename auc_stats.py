"""
Honest AUC reporting.

THREE DEFECTS THIS FIXES.

20. The published AUC is not the direction rule. `_fit_auc` trains an elastic-net
    logistic regression over the WHOLE feature vector with 5-fold CV, so the
    number describes a learned classifier, not the sign-of-slope decision the
    project is built on. The proof is N=4, which abstains on 100% of trials and
    has dir_acc = NaN, yet reports AUC 0.852 -- a figure identical, to three
    decimals, to its energy-only ablation at every motion level (0.852 / 0.720 /
    0.449 / 0.260). At that configuration the classifier is running entirely on
    amplitude. Reporting it as the design's performance reproduces exactly the
    failure mode the project claims to avoid: scoring presence of conductive
    fluid rather than its direction.

21. No AUC was reported with a confidence interval. Each cell rests on N_AUC = 64
    four-class trials, about 16 reflux against 48 rest, which by Hanley-McNeil
    gives a 95% interval of roughly +/-0.10 to +/-0.16. The entire spread across
    electrode counts (0.852 to 0.979) fits inside a single cell's interval, so no
    between-count AUC comparison in Study 1 was ever meaningful.

22. N=4 at motion 0.9 reports AUC 0.260, which is significantly BELOW chance even
    at this precision. An out-of-fold AUC that low is not noise, it is a model
    that inverts out of sample -- a small-n overfitting artifact.

The replacement metric is `rule_auc`: the ranking performance of the DIRECTION
DECISION itself, scored as signed evidence (dir * ev) against the reflux label,
computed from the saved per-trial records with no model fitting at all.
"""
import json, math
import numpy as np


# ------------------------------------------------------------------ intervals
def auc_se(a, n1, n2):
    """Hanley-McNeil standard error of an AUC."""
    if n1 <= 0 or n2 <= 0 or a != a:
        return float("nan")
    a = min(max(a, 1e-6), 1 - 1e-6)
    q1 = a / (2 - a)
    q2 = 2 * a * a / (1 + a)
    v = (a * (1 - a) + (n1 - 1) * (q1 - a * a) + (n2 - 1) * (q2 - a * a)) / (n1 * n2)
    return math.sqrt(max(v, 0.0))


def auc_ci(a, n1, n2, z=1.96):
    se = auc_se(a, n1, n2)
    if se != se:
        return (float("nan"), float("nan"))
    return (max(0.0, a - z * se), min(1.0, a + z * se))


def auc(y, score):
    """Mann-Whitney AUC with midranks for ties."""
    y = np.asarray(y, int)
    s = np.asarray(score, float)
    ok = np.isfinite(s)
    y, s = y[ok], s[ok]
    n1, n2 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n2 == 0:
        return float("nan"), n1, n2
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s), float)
    sv = s[order]
    i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    r1 = ranks[y == 1].sum()
    return float((r1 - n1 * (n1 + 1) / 2.0) / (n1 * n2)), n1, n2


# ------------------------------------------------- direction-rule AUC
def rule_auc(records, **filt):
    """AUC of the DIRECTION DECISION itself: signed evidence vs the reflux label.

    No model is fitted. The score is `dir * ev`, which is exactly what the device
    would output: which way it thinks the bolus went, and how strongly. An
    abstention (dir = 0) scores 0, i.e. it ranks between the two classes rather
    than being silently dropped -- dropping abstentions is what let a
    configuration that never answers look competitive.
    """
    rs = [r for r in records
          if all(r.get(k) == v for k, v in filt.items())]
    if not rs:
        return dict(auc=float("nan"), n1=0, n2=0, ci=(float("nan"),) * 2, n=0)
    y = [1 if r["label"] == "reflux" else 0 for r in rs]
    s = [r.get("dir", 0) * abs(r.get("ev", 0.0)) for r in rs]
    a, n1, n2 = auc(y, s)
    return dict(auc=a, n1=n1, n2=n2, ci=auc_ci(a, n1, n2), n=len(rs))


def main():
    R = json.load(open("records_directional.json"))
    E = json.load(open("metrics_directional.json"))
    counts = E["config"]["counts"]
    motions = E["config"]["motion"]

    print("Study 1: the published classifier AUC against the honest direction-rule AUC")
    print(f"{'N':>3} {'motion':>6} | {'classifier':>10} {'95% CI':>16} | "
          f"{'dir-only':>9} {'energy-only':>11} | {'RULE AUC':>9} {'95% CI':>16}")
    out = {}
    for n in counts:
        for m in motions:
            d = E["primary"][str(n)][str(m)]
            a = d.get("auc", float("nan"))
            lo, hi = auc_ci(a, 16, 48)
            r = rule_auc(R, n=n, motion=m, mode="auc")
            out[f"{n}_{m}"] = dict(classifier=a, classifier_ci=[lo, hi],
                                   direction_only=d.get("auc_direction_only"),
                                   energy_only=d.get("auc_energy_only"),
                                   rule=r["auc"], rule_ci=list(r["ci"]),
                                   n1=r["n1"], n2=r["n2"])
            print(f"{n:>3} {m:>6} | {a:10.3f} [{lo:5.3f},{hi:5.3f}] | "
                  f"{d.get('auc_direction_only',float('nan')):9.3f} "
                  f"{d.get('auc_energy_only',float('nan')):11.3f} | "
                  f"{r['auc']:9.3f} [{r['ci'][0]:5.3f},{r['ci'][1]:5.3f}]")
        print()
    json.dump(out, open("metrics_auc_corrected.json", "w"), indent=1)
    print("-> metrics_auc_corrected.json")


if __name__ == "__main__":
    main()
