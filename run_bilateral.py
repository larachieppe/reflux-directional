"""
Study 7: bilateral reflux, and laterality as a reportable output.

WHY THIS EXISTS
---------------
Reporting which side refluxes -- left, right, or both -- is a stated clinical
requirement, and until now the model could not even represent the third case.
`side` was strictly +1 or -1, so every simulated child refluxed on exactly one
side, and `decide_direction` picks the SINGLE strip carrying more differential
energy, so "bilateral" was not in the output alphabet at all. Every laterality
number this project has published is therefore a two-class question asked of a
population that, clinically, is about one third three-class.

Bilateral VUR is roughly a third of cases and it is not a curiosity: bilateral
disease carries the higher risk of renal scarring, so a device that silently
collapses it to whichever kidney happens to shout louder is failing on the
patients who matter most.

WHAT IT MEASURES
----------------
  1. Four-class confusion over {none, left, right, bilateral}, using
     decide_laterality, which judges each strip independently against the same
     abstain gate and sign test that decide_direction applies to the winner.
  2. The specific failure the winner-takes-all rule predicts: bilateral cases
     read as unilateral. If that dominates, laterality needs the per-strip rule
     rather than a tweak.
  3. Whether a grade IMBALANCE between sides drives that collapse -- a grade IV
     on one side and a grade I on the other is the case most likely to be
     misread as unilateral.

Outputs metrics_bilateral.json
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
MOTIONS = (0.0, 0.30, 0.60)
N_TRIAL = 45                    # per (truth class, motion)
SEED0 = 5_000_000               # disjoint from every other study
TRUTHS = ("none", "right", "left", "bilateral")


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


def _one(args):
    truth, motion, i = args
    w = _world()
    rng = np.random.default_rng(SEED0 + i)
    g1 = ds.sample_grade(rng)
    g2 = ds.sample_grade(rng)
    if truth == "none":
        label, side, gg2 = ("noflow" if i % 2 == 0 else "bladder"), +1, None
    elif truth == "right":
        label, side, gg2 = "reflux", +1, None
    elif truth == "left":
        label, side, gg2 = "reflux", -1, None
    else:
        label, side, gg2 = "reflux", 0, g2
    dZ = ds.simulate_trial(w, label, np.random.default_rng(SEED0 + 700_000 + i),
                           grade=g1, side=side, T=T, snr_db=SNR,
                           motion_amp=motion, grade2=gg2)
    feat = ds.direction_features(dZ, w)
    pred, per = ds.decide_laterality(feat)
    d, s, ev = ds.decide_direction(feat)          # the old winner-takes-all rule
    old_pred = "none" if d <= 0 else ("right" if s == 0 else "left")
    return dict(truth=truth, motion=motion, pred=pred, old_pred=old_pred,
                g1=int(g1), g2=int(g2) if truth == "bilateral" else None,
                grade_gap=(abs(g1 - g2) if truth == "bilateral" else None),
                fired_r=bool(per[0][0]), fired_l=bool(per[1][0]))


def main():
    t0 = time.time()
    jobs, i = [], 0
    for m in MOTIONS:
        for t in TRUTHS:
            for _ in range(N_TRIAL):
                jobs.append((t, m, i)); i += 1
    print(f"[bil] {len(jobs)} trials at {SPAN:.0f} cm @ z={Z_CENTER:.2f}", flush=True)

    nproc = max(1, min(3, (os.cpu_count() or 4) - 2))
    with Pool(nproc, initializer=_init) as pool:
        recs = list(pool.imap_unordered(_one, jobs, chunksize=8))

    def confusion(rs, key="pred"):
        c = {t: {p: 0 for p in TRUTHS} for t in TRUTHS}
        for r in rs:
            c[r["truth"]][r[key]] += 1
        return c

    out = dict(config=dict(model_version=ds.MODEL_VERSION, n_strip=N_STRIP, span=SPAN, z_center=Z_CENTER,
                           snr=SNR, T=T, motions=list(MOTIONS),
                           n_trial=N_TRIAL, seed0=SEED0),
               per_motion={}, overall={})
    for m in MOTIONS:
        sub = [r for r in recs if r["motion"] == m]
        cm = confusion(sub)
        acc = sum(cm[t][t] for t in TRUTHS) / max(len(sub), 1)
        bil = [r for r in sub if r["truth"] == "bilateral"]
        out["per_motion"][str(m)] = dict(
            confusion=cm, accuracy=acc, n=len(sub),
            bilateral_recall=(sum(r["pred"] == "bilateral" for r in bil) / len(bil)
                              if bil else float("nan")),
            bilateral_collapsed=(sum(r["pred"] in ("left", "right") for r in bil) / len(bil)
                                 if bil else float("nan")),
            bilateral_missed=(sum(r["pred"] == "none" for r in bil) / len(bil)
                              if bil else float("nan")))
    cm_new, cm_old = confusion(recs), confusion(recs, "old_pred")
    out["overall"] = dict(
        confusion_per_strip=cm_new, confusion_winner_takes_all=cm_old,
        accuracy_per_strip=sum(cm_new[t][t] for t in TRUTHS) / len(recs),
        accuracy_winner_takes_all=sum(cm_old[t][t] for t in TRUTHS) / len(recs),
        n=len(recs))
    # does a grade imbalance between sides drive the collapse?
    bil = [r for r in recs if r["truth"] == "bilateral"]
    by_gap = {}
    for gap in sorted({r["grade_gap"] for r in bil if r["grade_gap"] is not None}):
        g = [r for r in bil if r["grade_gap"] == gap]
        by_gap[str(gap)] = dict(n=len(g),
                                recall=sum(r["pred"] == "bilateral" for r in g) / len(g))
    out["bilateral_by_grade_gap"] = by_gap
    out["runtime_min"] = (time.time() - t0) / 60.0
    json.dump(out, open("metrics_bilateral.json", "w"), indent=1)

    print(f"[bil] four-class accuracy: per-strip rule "
          f"{100*out['overall']['accuracy_per_strip']:.1f}%  vs "
          f"winner-takes-all {100*out['overall']['accuracy_winner_takes_all']:.1f}%",
          flush=True)
    for m in MOTIONS:
        d = out["per_motion"][str(m)]
        print(f"[bil]  motion {m}: acc {100*d['accuracy']:.1f}%  "
              f"bilateral recall {100*d['bilateral_recall']:.1f}%  "
              f"collapsed to one side {100*d['bilateral_collapsed']:.1f}%  "
              f"missed {100*d['bilateral_missed']:.1f}%", flush=True)
    print(f"[bil] done in {out['runtime_min']:.1f} min -> metrics_bilateral.json",
          flush=True)


if __name__ == "__main__":
    main()
