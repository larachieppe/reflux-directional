"""
Correct subject-level (multi-event) analysis, and a disclosed-threshold confusion
matrix. Used both by run_design.py and to repair an existing metrics_design.json.

WHY THIS EXISTS
---------------
The first version pooled refluxing and healthy children and counted "direction call
correct" as a hit. Three things were wrong with that:

  1. On a HEALTHY child a correct call is a true NEGATIVE, not a detection, so the
     curve measured per-child accuracy while being published as sensitivity.
  2. Because half the cohort is healthy, the metric's CHANCE FLOOR is
     P(Binom(6,0.5) >= 2) = 89%, which sits ABOVE the ~80% VCUG line it was being
     compared against. A coin-flip detector would have "beaten VCUG".
  3. The "never detected" bar counted healthy children with zero correct calls,
     for whom zero correct means six consecutive FALSE POSITIVES, the opposite of
     what the label claimed.

The corrected analysis models the actual screening rule -- flag a child if at least
k of K observed events read retrograde -- and reports sensitivity and specificity
for that rule separately, with the chance floor drawn explicitly.
"""
from math import comb


def binom_at_least(k, n, p):
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def subject_analysis(per_subject, K):
    """per_subject: list of dicts with keys label ('reflux'|'antegrade') and n_hit
    (number of the K events whose DIRECTION call was correct).

    For a reflux child, n_hit = events correctly read as retrograde -> true positives.
    For a healthy child, the events wrongly read as retrograde are (K - n_hit)
    -> false positives under the same rule.
    """
    refl = [s for s in per_subject if s["label"] == "reflux"]
    ante = [s for s in per_subject if s["label"] == "antegrade"]
    nR, nA = max(len(refl), 1), max(len(ante), 1)

    pe_sens = sum(s["n_hit"] for s in refl) / (nR * K) if refl else float("nan")
    pe_fp = sum(K - s["n_hit"] for s in ante) / (nA * K) if ante else float("nan")

    sens, spec, chance, youden = {}, {}, {}, {}
    for k in range(1, K + 1):
        se = sum(1 for s in refl if s["n_hit"] >= k) / nR
        fp = sum(1 for s in ante if (K - s["n_hit"]) >= k) / nA
        sens[str(k)] = se
        spec[str(k)] = 1.0 - fp
        # chance floor: a coin-flip detector, same rule, same K
        chance[str(k)] = binom_at_least(k, K, 0.5)
        youden[str(k)] = se + (1.0 - fp) - 1.0

    # independence prediction uses the REFLUX per-event rate only, and is compared
    # against the reflux-only empirical curve, so the two are like for like
    indep = {str(k): binom_at_least(k, K, pe_sens) if pe_sens == pe_sens else float("nan")
             for k in range(1, K + 1)}

    hist_r = [0] * (K + 1)
    hist_a = [0] * (K + 1)
    for s in refl:
        hist_r[s["n_hit"]] += 1
    for s in ante:
        hist_a[K - s["n_hit"]] += 1        # healthy: count FALSE retrograde calls

    best_k = max(youden, key=lambda k: youden[k]) if youden else "1"
    return dict(
        k_events=K, n_reflux=len(refl), n_healthy=len(ante),
        per_event_sens=pe_sens, per_event_fp=pe_fp,
        sens_k=sens, spec_k=spec, chance_k=chance, youden_k=youden,
        indep_k=indep, best_k=best_k,
        best_sens=sens.get(best_k, float("nan")),
        best_spec=spec.get(best_k, float("nan")),
        hist_reflux_hits=hist_r, hist_healthy_falsepos=hist_a,
        never_detected_reflux=hist_r[0] / nR if refl else float("nan"),
    )


def confusion_at_threshold(sub, scores, thr, thr_label):
    """Four-condition confusion at a DISCLOSED threshold.

    The first version used the median of all scores, which forces a 50% predicted
    positive rate against 25% prevalence and caps specificity at 66.7% no matter how
    good the model is. Any published confusion must name its operating point.
    """
    conf = {}
    for r, p in zip(sub, scores):
        pred = "reflux" if p >= thr else ("antegrade" if r["dir"] < 0 else "not-reflux")
        conf.setdefault(r["label"], {}).setdefault(pred, 0)
        conf[r["label"]][pred] += 1
    return {"counts": conf, "threshold": float(thr), "threshold_label": thr_label}
