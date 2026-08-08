"""
Misplacement tolerance: how precisely must the strip be positioned?

Reads metrics_placement.json, takes the position that best serves LOW grades, and
offsets the strip by +/- 1 and 2 cm around it.

WHY THIS DECIDES SHIPPABILITY
-----------------------------
A placement that only works when perfectly aligned is not a product. The strip
has to be applied by a parent or a nurse to a child who will not hold still, and
the anatomical landmark (the ureterovesical junction) is not externally visible.
If accuracy at the optimum is high but collapses 1 cm away, the honest conclusion
is that the design needs a landmark, a longer strip, or an alignment aid, not
that low-grade reflux is detectable.

Outputs metrics_tolerance.json
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
GRADES = (1, 2, 3, 4, 5)
MOTION = (0.0, 0.30)
N_TRIAL = 32
OFFSETS_CM = (-2.0, -1.0, 0.0, 1.0, 2.0)


def _feasible(off, span, zc0, n_per_strip, height):
    """Can the strip actually sit on the body at this offset?

    A span-S strip on a height-H torso can only be centred within
    [S/2H, 1-S/2H], and the electrode acceptance window adds a further
    half-pitch at each end. Offsets outside that are not a poor placement, they
    are not a placement at all: place_strips raises rather than silently
    snapping electrodes onto the end cap. Recording them as untestable is the
    honest result, and the feasible range is itself a design constraint worth
    reporting.
    """
    dz = span / max(n_per_strip - 1, 1)
    half = 0.40 * dz
    z0 = (zc0 + off / height) * height - span / 2.0
    return (z0 - half >= -1e-9) and (z0 + span + half <= height + 1e-9)

P = json.load(open("metrics_placement.json"))
BEST = P["best_low_grade"]
SPAN = float(BEST["span"])
ZC0 = float(BEST["z_center"])

_W = {}
_WORLD_CACHE_MAX = 2


def _init():
    global _MESH
    _MESH = eit3d.make_cylinder(R=5.5, height=HEIGHT, n_rings=6, nz=17)


def _world(zc):
    key = round(zc, 5)
    if key not in _W:
        if len(_W) >= _WORLD_CACHE_MAX:
            _W.pop(next(iter(_W)))
        _W[key] = ds.StripWorld(N_STRIP, span=SPAN, mesh=_MESH, z_center=zc)
    return _W[key]


def _run_one(args):
    off, motion, grade, i = args
    zc = ZC0 + off / HEIGHT
    label = "reflux" if i % 2 == 0 else "antegrade"
    side = +1 if (i // 2) % 2 == 0 else -1
    w = _world(zc)
    dZ = ds.simulate_trial(w, label, np.random.default_rng(970_000 + i),
                           grade=grade, side=side, T=T, snr_db=SNR,
                           motion_amp=motion)
    d, s, ev = ds.decide_direction(ds.direction_features(dZ, w))
    return dict(off=off, motion=motion, grade=grade, i=i, label=label,
                dir=int(d), want=(+1 if label == "reflux" else -1),
                lat_ok=bool((s == 0) == (side > 0)))


def wilson(p, n, z=1.96):
    if n <= 0 or p != p:
        return (float("nan"), float("nan"))
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def summarize(rs):
    if not rs:
        return dict(dir_acc=float("nan"), n=0)
    acc = float(np.mean([r["dir"] == r["want"] for r in rs]))
    refl = [r for r in rs if r["label"] == "reflux"]
    return dict(dir_acc=acc, n=len(rs), ci=wilson(acc, len(rs)),
                reflux_acc=float(np.mean([r["dir"] == r["want"] for r in refl]))
                if refl else float("nan"),
                abstain=float(np.mean([r["dir"] == 0 for r in rs])))


def main():
    t0 = time.time()
    feasible = [o for o in OFFSETS_CM
                if _feasible(o, SPAN, ZC0, N_STRIP, HEIGHT)]
    skipped = [o for o in OFFSETS_CM if o not in feasible]
    if skipped:
        print(f"[tol] offsets {skipped} cm put the strip off the body at "
              f"span={SPAN} cm, z_center={ZC0:.2f} and are NOT testable; "
              f"running {feasible}", flush=True)
    jobs = [(o, m, g, i) for o in feasible for g in GRADES
            for m in MOTION for i in range(N_TRIAL)]
    print(f"[tol] {len(jobs)} trials around span={SPAN} z_center={ZC0:.3f} "
          f"(offsets {OFFSETS_CM} cm)", flush=True)

    nproc = max(1, min(4, (os.cpu_count() or 4) - 2))
    recs = []
    with Pool(nproc, initializer=_init) as pool:
        for k, r in enumerate(pool.imap_unordered(_run_one, jobs, chunksize=4)):
            recs.append(r)
            if (k + 1) % 200 == 0:
                el = time.time() - t0
                print(f"[tol] {k+1}/{len(jobs)}  {el/60:.1f} min  "
                      f"eta {(el/(k+1)*(len(jobs)-k-1))/60:.1f} min", flush=True)

    out = {"config": dict(model_version=ds.MODEL_VERSION, n_strip=N_STRIP, span=SPAN, z_center=ZC0, snr=SNR,
                          offsets_cm=list(OFFSETS_CM),
                          height=HEIGHT, grades=list(GRADES),
                          motion=list(MOTION), n_trial=N_TRIAL)}
    grid = {}
    for o in skipped:
        grid[f"{o:+.0f}"] = dict(untestable=True,
                                 reason="strip leaves the body at this offset")
    for o in feasible:
        k = f"{o:+.0f}"
        grid[k] = {}
        for g in GRADES:
            for m in MOTION:
                grid[k][f"g{g}_m{m}"] = summarize(
                    [r for r in recs if r["off"] == o and r["grade"] == g
                     and r["motion"] == m])
        grid[k]["low_grade_still"] = summarize(
            [r for r in recs if r["off"] == o and r["grade"] in (1, 2)
             and r["motion"] == 0.0])
        grid[k]["high_grade_still"] = summarize(
            [r for r in recs if r["off"] == o and r["grade"] >= 3
             and r["motion"] == 0.0])
    out["grid"] = grid

    # how much does 1 cm and 2 cm of misplacement cost?
    base = grid["+0"]["low_grade_still"]["dir_acc"]
    out["cost"] = {
        f"{o:+.0f}cm": (grid[f"{o:+.0f}"]["low_grade_still"]["dir_acc"] - base)
        for o in feasible}
    out["untestable_offsets_cm"] = skipped
    out["feasible_offsets_cm"] = feasible
    out["runtime_min"] = (time.time() - t0) / 60.0
    with open("metrics_tolerance.json", "w") as f:
        json.dump(out, f, indent=1)
    print(f"[tol] done in {out['runtime_min']:.1f} min -> metrics_tolerance.json",
          flush=True)
    for o in feasible:
        k = f"{o:+.0f}"
        lo = grid[k]["low_grade_still"]; hi = grid[k]["high_grade_still"]
        print(f"[tol]  {o:+.0f} cm : low grades {100*lo['dir_acc']:5.1f}%   "
              f"high grades {100*hi['dir_acc']:5.1f}%", flush=True)


if __name__ == "__main__":
    main()
