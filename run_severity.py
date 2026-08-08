"""
Study 9: can the device report SEVERITY, not just presence?

WHY THIS EXISTS
---------------
Arena's requirement list asks for a three-bucket severity grade, and this project
has never measured whether that is possible. Every study to date answers a binary
question -- is this reflux, yes or no -- and then reports accuracy BY grade, which
is a different thing entirely: it conditions on a grade the device does not know.

Severity matters clinically because management diverges on it. Low-grade reflux
is usually watched and often resolves; high-grade reflux drives surgical
decisions and carries the scarring risk. A device that detects reflux but cannot
say how bad it is leaves the decision where it started.

WHAT IT MEASURES
----------------
Whether any quantity the estimator already computes carries grade information,
and how well a three-bucket call can be made from it:
    low       grades I-II    (60% of reflux, usually observed)
    moderate  grade III      (22%)
    high      grades IV-V    (18%, the surgical tail)

Candidate signals, all already produced per trial:
    |ev|          magnitude of the arrival-time evidence
    energy        total differential energy on the firing strip
    dif_energy    per-zone differential energy
    lin           wave coherence
    n_cross       how many zone centroids the bolus passes
A bigger, further-travelling bolus should raise energy and cross more zones, so
the physics says the information ought to be there. Whether it survives noise,
anatomy variation and motion is the question.

Reports Spearman correlation of each signal against true grade, and the
three-bucket confusion from a simple threshold rule fitted on a DISJOINT seed
block, so the reported accuracy is out-of-sample.

Outputs metrics_severity.json
"""
import json, os, time
import numpy as np
from multiprocessing import Pool

import eit3d
import directional_sim as ds

N_STRIP = 8
SNR = 60
T = 20
HEIGHT = 20.0
MOTIONS = (0.0, 0.30)
N_TRIAL = 70                 # per (grade, motion); grades are swept explicitly
GRADES = (1, 2, 3, 4, 5)
SEED_FIT = 8_000_000         # threshold fitting
SEED_EVAL = 8_500_000        # scoring, disjoint
BUCKET = {1: "low", 2: "low", 3: "moderate", 4: "high", 5: "high"}


def _placement():
    try:
        b = json.load(open("metrics_placement.json"))["best_low_grade"]
        return float(b["span"]), float(b["z_center"])
    except Exception:
        return 12.0, 0.36


SPAN, Z_CENTER = _placement()
_W = {}


def _init():
    global _MESH
    _MESH = eit3d.make_cylinder(R=5.5, height=HEIGHT, n_rings=6, nz=17)


def _world():
    if "w" not in _W:
        _W["w"] = ds.StripWorld(N_STRIP, span=SPAN, mesh=_MESH, z_center=Z_CENTER)
    return _W["w"]


def _n_cross(w, grade):
    z_b, z_k = 0.20 * w.H, 0.80 * w.H
    reach = ds.GRADE_TABLE[grade][1]
    margin = 0.12 * w.H
    zz = w.zone_z[w.zone_strip == 0]
    return int(((zz >= z_b - margin) & (zz <= z_b + (z_k - z_b) * reach + margin)).sum())


def _one(args):
    grade, motion, i, seed0 = args
    w = _world()
    rng = np.random.default_rng(seed0 + i)
    side = +1 if rng.random() < 0.5 else -1
    dZ = ds.simulate_trial(w, "reflux", np.random.default_rng(seed0 + 400_000 + i),
                           grade=grade, side=side, T=T, snr_db=SNR,
                           motion_amp=motion)
    feat = ds.direction_features(dZ, w)
    d, s, ev = ds.decide_direction(feat)
    f = feat[s]
    return dict(grade=int(grade), bucket=BUCKET[grade], motion=motion,
                block=("fit" if seed0 == SEED_FIT else "eval"),
                detected=bool(d > 0),
                abs_ev=float(abs(ev)),
                energy=float(f.get("energy", 0.0)),
                dif_energy=float(f.get("dif_energy", 0.0)),
                lin=float(f.get("lin", 0.0)),
                n_cross=_n_cross(w, grade))


def spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 5:
        return float("nan")
    rx = np.argsort(np.argsort(x[ok])).astype(float)
    ry = np.argsort(np.argsort(y[ok])).astype(float)
    rx -= rx.mean(); ry -= ry.mean()
    den = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    return float((rx * ry).sum() / den) if den > 0 else float("nan")


def main():
    t0 = time.time()
    jobs = []
    i = 0
    for seed0 in (SEED_FIT, SEED_EVAL):
        for m in MOTIONS:
            for g in GRADES:
                for _ in range(N_TRIAL):
                    jobs.append((g, m, i, seed0)); i += 1
    print(f"[sev] {len(jobs)} trials at {SPAN:.0f} cm @ z={Z_CENTER:.2f}", flush=True)

    nproc = max(1, min(3, (os.cpu_count() or 4) - 2))
    with Pool(nproc, initializer=_init) as pool:
        recs = list(pool.imap_unordered(_one, jobs, chunksize=8))

    # Split by seed block. imap_unordered returns results in COMPLETION order,
    # so neither zip(recs, jobs) nor slicing recs would recover the split -- each
    # record carries its own block tag instead.
    fit = [r for r in recs if r["block"] == "fit"]
    ev_ = [r for r in recs if r["block"] == "eval"]
    assert len(fit) and len(ev_), "seed blocks did not split"

    SIGNALS = ("abs_ev", "energy", "dif_energy", "lin", "n_cross")
    out = dict(config=dict(model_version=ds.MODEL_VERSION, n_strip=N_STRIP, span=SPAN, z_center=Z_CENTER, snr=SNR,
                           T=T, motions=list(MOTIONS), n_trial=N_TRIAL,
                           grades=list(GRADES), buckets=BUCKET,
                           seed_fit=SEED_FIT, seed_eval=SEED_EVAL))

    det = [r for r in recs if r["detected"]]
    out["detected_fraction"] = len(det) / max(len(recs), 1)
    out["spearman_vs_grade"] = {
        s: spearman([r[s] for r in det], [r["grade"] for r in det]) for s in SIGNALS}
    out["spearman_all_trials"] = {
        s: spearman([r[s] for r in recs], [r["grade"] for r in recs]) for s in SIGNALS}

    # three-bucket rule: two thresholds on the best-correlating signal, chosen on
    # the FIT block only, scored on the EVAL block
    best = max(SIGNALS, key=lambda s: abs(out["spearman_vs_grade"].get(s, 0.0) or 0.0))
    fdet = [r for r in fit if r["detected"]]
    edet = [r for r in ev_ if r["detected"]]
    order = 1 if (out["spearman_vs_grade"][best] or 0) >= 0 else -1
    vals = np.array([order * r[best] for r in fdet], float)
    if vals.size >= 10:
        t1, t2 = np.percentile(vals, [60.0, 82.0])   # match the 60/22/18 prior
    else:
        t1 = t2 = 0.0

    def call(r):
        v = order * r[best]
        return "low" if v < t1 else ("moderate" if v < t2 else "high")

    BUCKETS = ("low", "moderate", "high")
    conf = {b: {p: 0 for p in BUCKETS} for b in BUCKETS}
    for r in edet:
        conf[r["bucket"]][call(r)] += 1
    n_ev = max(len(edet), 1)
    acc = sum(conf[b][b] for b in BUCKETS) / n_ev
    # chance floor: always guess the most common bucket in the eval set
    counts = {b: sum(1 for r in edet if r["bucket"] == b) for b in BUCKETS}
    chance = max(counts.values()) / n_ev if n_ev else float("nan")
    out["three_bucket"] = dict(signal=best, thresholds=[float(t1), float(t2)],
                               order=order, confusion=conf, accuracy=acc,
                               chance_floor=chance, n_eval=len(edet),
                               n_fit=len(fdet), eval_counts=counts)
    out["runtime_min"] = (time.time() - t0) / 60.0
    json.dump(out, open("metrics_severity.json", "w"), indent=1)

    print(f"[sev] detected {100*out['detected_fraction']:.1f}% of reflux trials")
    print("[sev] Spearman vs true grade (detected trials only):")
    for s in SIGNALS:
        print(f"[sev]    {s:12s} {out['spearman_vs_grade'][s]:+.3f}")
    print(f"[sev] three-bucket on '{best}': {100*acc:.1f}% "
          f"against a {100*chance:.1f}% chance floor  (n={len(edet)}, out-of-sample)")
    print(f"[sev] done in {out['runtime_min']:.1f} min -> metrics_severity.json")


if __name__ == "__main__":
    main()
