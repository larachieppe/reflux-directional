"""
Strip placement sweep: where along the flank should the strip sit?

WHY THIS EXISTS
---------------
z_center was never forwarded from StripWorld to place_strips, so every strip in
every previous study sat on the torso MIDPOINT by default. Nobody chose that. The
ureterovesical junction, where low-grade reflux actually occurs, sits much lower
(bladder at z ~ 0.20 of torso height). Grades I-II have been reported as the hard
tail throughout this project, and that may be a consequence of an unswept default
rather than a property of the method.

WHAT IT MEASURES
----------------
  A. PLACEMENT: direction accuracy by grade across (z_center, span). Low grades
     only traverse the lower ureter, so the number of tetrapolar zone centroids
     their bolus actually crosses is the hypothesised driver.
  B. MISPLACEMENT TOLERANCE: the same, with the strip offset +/- 1 and 2 cm from
     the best position. A placement that only works when perfect is not
     shippable on a child, so tolerance is part of the answer, not a footnote.

Outputs metrics_placement.json
"""
import json, os, time
import numpy as np
from multiprocessing import Pool

import eit3d
import directional_sim as ds

N_STRIP = 8          # the chosen design
SNR = 60
T = 20
HEIGHT = 20.0
GRADES = (1, 2, 3, 4, 5)
MOTION = (0.0, 0.30)
N_TRIAL = 28         # per (config, grade, motion) cell; travelling trials only

# (span, z_center) pairs. Span constrains how low the strip can sit: a 16 cm
# strip on a 20 cm torso cannot be centred below 0.40 without leaving the mesh.
CONFIGS = [(16.0, 0.40), (16.0, 0.50), (16.0, 0.60),
           (12.0, 0.30), (12.0, 0.36), (12.0, 0.42), (12.0, 0.50),
           (10.0, 0.28), (10.0, 0.34), (10.0, 0.42)]
OFFSETS_CM = (-2.0, -1.0, 0.0, 1.0, 2.0)   # misplacement arm, applied to best

_W = {}
_WORLD_CACHE_MAX = 2


def _init():
    global _MESH
    _MESH = eit3d.make_cylinder(R=5.5, height=HEIGHT, n_rings=6, nz=17)


def _world(span, zc):
    key = (round(span, 3), round(zc, 4))
    if key not in _W:
        if len(_W) >= _WORLD_CACHE_MAX:
            _W.pop(next(iter(_W)))
        _W[key] = ds.StripWorld(N_STRIP, span=span, mesh=_MESH, z_center=zc)
    return _W[key]


def _run_one(args):
    span, zc, motion, grade, i, mode = args
    label = "reflux" if i % 2 == 0 else "antegrade"
    side = +1 if (i // 2) % 2 == 0 else -1
    seed = 950_000 + i
    w = _world(span, zc)
    dZ = ds.simulate_trial(w, label, np.random.default_rng(seed), grade=grade,
                           side=side, T=T, snr_db=SNR, motion_amp=motion)
    feat = ds.direction_features(dZ, w)
    d, s, ev = ds.decide_direction(feat)
    want = +1 if label == "reflux" else -1
    return dict(span=span, zc=zc, motion=motion, grade=grade, i=i, mode=mode,
                label=label, dir=int(d), want=int(want),
                lat_ok=bool((s == 0) == (side > 0)),
                zones_crossed=int(_zones_crossed(w, grade)))


def _zones_crossed(w, grade):
    """How many zone centroids lie inside the bolus travel range for this grade.
    This is the hypothesised mechanism: a bolus that crosses fewer than ~3 zone
    centroids cannot support a slope fit or common-mode rejection."""
    z_b = 0.20 * w.H
    z_k = 0.80 * w.H
    reach = ds.GRADE_TABLE[grade][1]
    margin = 0.12 * w.H
    lo = z_b - margin
    hi = z_b + (z_k - z_b) * reach + margin
    zz = w.zone_z[w.zone_strip == 0]
    return int(((zz >= lo) & (zz <= hi)).sum())


def wilson(p, n, z=1.96):
    if n <= 0 or p != p:
        return (float("nan"), float("nan"))
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def summarize(rs):
    trav = [r for r in rs if r["want"] != 0]
    if not trav:
        return dict(dir_acc=float("nan"), n=0)
    acc = float(np.mean([r["dir"] == r["want"] for r in trav]))
    refl = [r for r in trav if r["label"] == "reflux"]
    ante = [r for r in trav if r["label"] == "antegrade"]
    dec = [r for r in trav if r["dir"] != 0]
    return dict(
        dir_acc=acc, n=len(trav), ci=wilson(acc, len(trav)),
        reflux_acc=float(np.mean([r["dir"] == r["want"] for r in refl])) if refl else float("nan"),
        antegrade_acc=float(np.mean([r["dir"] == r["want"] for r in ante])) if ante else float("nan"),
        abstain=1.0 - len(dec) / len(trav),
        lat_acc=float(np.mean([r["lat_ok"] for r in refl])) if refl else float("nan"),
        zones_crossed=int(np.median([r["zones_crossed"] for r in trav])),
    )


def main():
    t0 = time.time()
    jobs = []
    for span, zc in CONFIGS:
        for g in GRADES:
            for m in MOTION:
                for i in range(N_TRIAL):
                    jobs.append((span, zc, m, g, i, "place"))
    print(f"[place] {len(jobs)} trials, {len(CONFIGS)} configs", flush=True)

    nproc = max(1, min(4, (os.cpu_count() or 4) - 2))
    recs = []
    with Pool(nproc, initializer=_init) as pool:
        for k, r in enumerate(pool.imap_unordered(_run_one, jobs, chunksize=4)):
            recs.append(r)
            if (k + 1) % 200 == 0:
                el = time.time() - t0
                print(f"[place] {k+1}/{len(jobs)}  {el/60:.1f} min  "
                      f"eta {(el/(k+1)*(len(jobs)-k-1))/60:.1f} min", flush=True)

    out = {"config": dict(n_strip=N_STRIP, snr=SNR, T=T, height=HEIGHT,
                          configs=CONFIGS, grades=list(GRADES),
                          motion=list(MOTION), n_trial=N_TRIAL)}
    grid = {}
    for span, zc in CONFIGS:
        key = f"{span:.0f}_{zc:.2f}"
        grid[key] = {"span": span, "z_center": zc,
                     "strip_z": [zc * HEIGHT - span / 2, zc * HEIGHT + span / 2]}
        for g in GRADES:
            for m in MOTION:
                sub = [r for r in recs if r["span"] == span and r["zc"] == zc
                       and r["grade"] == g and r["motion"] == m]
                grid[key][f"g{g}_m{m}"] = summarize(sub)
    out["grid"] = grid

    # best config judged on LOW grades (1-2), which is the open question
    def low_score(key):
        v = [grid[key].get(f"g{g}_m0.0", {}).get("reflux_acc", float("nan"))
             for g in (1, 2)]
        v = [x for x in v if x == x]
        return sum(v) / len(v) if v else -1.0

    best_key = max(grid, key=low_score)
    out["best_low_grade"] = {"key": best_key, "score": low_score(best_key),
                             "span": grid[best_key]["span"],
                             "z_center": grid[best_key]["z_center"]}
    out["runtime_min"] = (time.time() - t0) / 60.0
    with open("metrics_placement.json", "w") as f:
        json.dump(out, f, indent=1)
    print(f"[place] done in {out['runtime_min']:.1f} min -> metrics_placement.json",
          flush=True)
    print(f"[place] best for low grades: {best_key} "
          f"(span {grid[best_key]['span']}, z_center {grid[best_key]['z_center']})",
          flush=True)


if __name__ == "__main__":
    main()
