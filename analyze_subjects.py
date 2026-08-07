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

    For a healthy child the false positives are the events actually called
    RETROGRADE. Pass that count as `n_retro`.

    DEFECT 26, FIXED. This used to infer false positives as (K - n_hit), which is
    every event NOT correctly called antegrade -- and that set includes every
    ABSTENTION. The estimator declines to answer routinely (up to half of windows
    under motion), so abstentions were being scored as false alarms, understating
    specificity, while the docstring claimed the quantity was "events wrongly read
    as retrograde". A device that says "I don't know" has not raised a false
    alarm. Callers that do not yet supply n_retro fall back to the old behaviour
    and are flagged in the returned dict, so the difference is never silent.
    """
    refl = [s for s in per_subject if s["label"] == "reflux"]
    ante = [s for s in per_subject if s["label"] == "antegrade"]
    nR, nA = max(len(refl), 1), max(len(ante), 1)

    have_retro = all("n_retro" in s for s in ante) if ante else True

    def fp_of(s):
        return s["n_retro"] if have_retro else (K - s["n_hit"])

    pe_sens = sum(s["n_hit"] for s in refl) / (nR * K) if refl else float("nan")
    pe_fp = sum(fp_of(s) for s in ante) / (nA * K) if ante else float("nan")

    sens, spec, chance, youden = {}, {}, {}, {}
    for k in range(1, K + 1):
        se = sum(1 for s in refl if s["n_hit"] >= k) / nR
        fp = sum(1 for s in ante if fp_of(s) >= k) / nA
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
        hist_a[fp_of(s)] += 1              # healthy: count FALSE retrograde calls

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
        # False. The caller did not supply n_retro, so false positives were
        # inferred as (K - n_hit) and ABSTENTIONS are being counted as false
        # alarms. Any specificity from such a run is a lower bound.
        fp_counts_abstentions=(not have_retro),
        # chance_k is the chance floor for SENSITIVITY under a coin-flip
        # detector. It is NOT a floor for specificity, and must not be printed
        # in a column that spans both.
        chance_k_applies_to="sensitivity",
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
