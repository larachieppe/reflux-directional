"""
Study 10: the two hardware specifications nothing has ever set.

WHY THIS EXISTS
---------------
An engineer asked to build this device needs two numbers that appear nowhere in
the project:

  A. HOW MANY SAMPLES over a void. T = 20 frames is hard-coded in every runner
     and has never been swept. It silently sets the sampling requirement, the
     minimum recording length, and how much of a void must be captured before a
     call can be made. If 10 frames suffice, the front end and the storage
     budget halve; if 40 are needed, a short or partially-missed void is
     undiagnosable.

  B. HOW MANY ELECTRODES MAY FAIL. Electrodes lift, gel dries, a child pulls at
     a lead. Nothing has tested what happens when one is dead. With 8 per strip
     and overlapping tetrapolar apertures there should be graceful degradation,
     because a dead electrode removes only the zones that use it -- but "should"
     is not a measurement, and a dead electrode near the middle of the strip
     kills more apertures than one at the end.

WHAT IT MEASURES
----------------
  A. direction accuracy, abstention and false-retrograde against T
  B. the same against the number of dead electrodes per strip, with the dead set
     drawn at random per trial, and separately for an END electrode versus a
     MIDDLE one, since they are not equivalent

Outputs metrics_hardware.json
"""
import json, os, time
import numpy as np
from multiprocessing import Pool

import eit3d
import directional_sim as ds

N_STRIP = 8
SNR = 60
HEIGHT = 20.0
MOTION = 0.30
FRAMES = (8, 12, 16, 20, 28, 40)
N_DEAD = (0, 1, 2, 3)
DEAD_WHERE = ("random", "end", "middle")
N_TRIAL = 45
CLASSES = ("reflux", "antegrade", "noflow", "bladder")
SEED0 = 9_000_000


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


class _Reduced:
    """A view of a world with some electrodes declared dead.

    A dead electrode does not shrink the array geometrically -- it removes every
    tetrapolar zone that would have used it as a drive or a sense contact. The
    forward solve is unchanged; only which zones the estimator may read changes,
    which is exactly what a lifted electrode does in hardware.
    """

    def __init__(self, w, dead):
        keep = [i for i, z in enumerate(w.zones)
                if not (set(z["drive"]) | set(z["sense"])) & dead]
        self.zones = [w.zones[i] for i in keep]
        self.zone_z = w.zone_z[keep]
        self.zone_strip = w.zone_strip[keep]
        self.zone_m = w.zone_m[keep]
        self.apertures = sorted(set(self.zone_m.tolist()))
        self._keep = np.asarray(keep, int)
        for a in ("R", "H", "L", "n_per_strip", "span", "spacing", "solver",
                  "mesh", "cent", "ur_x", "z_bladder", "z_kidney", "z_center"):
            setattr(self, a, getattr(w, a))


def _dead_set(w, k, where, rng):
    if k == 0:
        return set()
    n = w.n_per_strip
    out = set()
    for strip in (0, 1):
        base = strip * n
        if where == "end":
            idx = list(range(k))                       # from the inferior end
        elif where == "middle":
            c = n // 2
            idx = [c + j - k // 2 for j in range(k)]
        else:
            idx = rng.choice(n, size=k, replace=False).tolist()
        out |= {base + int(j) for j in idx}
    return out


def _one(args):
    kind, level, where, label, i = args
    w = _world()
    rng = np.random.default_rng(SEED0 + i)
    grade = ds.sample_grade(rng)
    side = +1 if rng.random() < 0.5 else -1
    T = level if kind == "frames" else 20
    dZ = ds.simulate_trial(w, label, np.random.default_rng(SEED0 + 300_000 + i),
                           grade=grade, side=side, T=T, snr_db=SNR,
                           motion_amp=MOTION)
    if kind == "dead" and level > 0:
        dead = _dead_set(w, level, where, np.random.default_rng(SEED0 + 600_000 + i))
        ww = _Reduced(w, dead)
        if len(ww.zones) == 0:
            return dict(kind=kind, level=level, where=where, label=label,
                        dir=0, want=0, travelling=False, n_zones=0)
        keep = ww._keep
        feat = ds.direction_features(dZ[:, :, keep], ww)
        nz = len(ww.zones)
    else:
        feat = ds.direction_features(dZ, w)
        nz = len(w.zones)
    d, s, ev = ds.decide_direction(feat)
    want = {"reflux": +1, "antegrade": -1}.get(label, 0)
    return dict(kind=kind, level=level, where=where, label=label, dir=int(d),
                want=want, travelling=(want != 0), n_zones=nz)


def summarise(rs):
    trav = [r for r in rs if r["travelling"]]
    empt = [r for r in rs if not r["travelling"]]
    dec = [r for r in trav if r["dir"] != 0]
    return dict(
        n_trav=len(trav),
        dir_acc=float(np.mean([r["dir"] == r["want"] for r in trav])) if trav else float("nan"),
        dir_acc_decided=float(np.mean([r["dir"] == r["want"] for r in dec])) if dec else float("nan"),
        abstain=float(np.mean([r["dir"] == 0 for r in trav])) if trav else float("nan"),
        false_retro=float(np.mean([r["dir"] > 0 for r in empt])) if empt else float("nan"),
        zones=int(np.median([r["n_zones"] for r in rs])) if rs else 0)


def main():
    t0 = time.time()
    jobs, i = [], 0
    for T in FRAMES:
        for lab in CLASSES:
            for _ in range(N_TRIAL):
                jobs.append(("frames", T, "-", lab, i)); i += 1
    for k in N_DEAD:
        for where in (DEAD_WHERE if k > 0 else ("random",)):
            for lab in CLASSES:
                for _ in range(N_TRIAL):
                    jobs.append(("dead", k, where, lab, i)); i += 1
    print(f"[hw] {len(jobs)} trials at {SPAN:.0f} cm @ z={Z_CENTER:.2f}", flush=True)

    nproc = max(1, min(3, (os.cpu_count() or 4) - 2))
    with Pool(nproc, initializer=_init) as pool:
        recs = list(pool.imap_unordered(_one, jobs, chunksize=8))

    out = dict(config=dict(model_version=ds.MODEL_VERSION, n_strip=N_STRIP, span=SPAN, z_center=Z_CENTER, snr=SNR,
                           motion=MOTION, frames=list(FRAMES), n_dead=list(N_DEAD),
                           dead_where=list(DEAD_WHERE), n_trial=N_TRIAL,
                           seed0=SEED0),
               frames={}, dropout={})
    for T in FRAMES:
        out["frames"][str(T)] = summarise([r for r in recs
                                           if r["kind"] == "frames" and r["level"] == T])
    for k in N_DEAD:
        for where in (DEAD_WHERE if k > 0 else ("random",)):
            sub = [r for r in recs if r["kind"] == "dead"
                   and r["level"] == k and r["where"] == where]
            out["dropout"][f"{k}_{where}"] = summarise(sub)
    out["runtime_min"] = (time.time() - t0) / 60.0
    json.dump(out, open("metrics_hardware.json", "w"), indent=1)

    print("[hw] A. samples per void")
    for T in FRAMES:
        d = out["frames"][str(T)]
        print(f"[hw]    T={T:>2}: acc {100*d['dir_acc']:5.1f}%  "
              f"on-calls {100*d['dir_acc_decided']:5.1f}%  "
              f"abstain {100*d['abstain']:5.1f}%  FR {100*d['false_retro']:5.1f}%")
    print("[hw] B. dead electrodes per strip")
    for k in N_DEAD:
        for where in (DEAD_WHERE if k > 0 else ("random",)):
            d = out["dropout"][f"{k}_{where}"]
            print(f"[hw]    {k} dead ({where:>6}): {d['zones']:>2} zones left  "
                  f"acc {100*d['dir_acc']:5.1f}%  abstain {100*d['abstain']:5.1f}%  "
                  f"FR {100*d['false_retro']:5.1f}%")
    print(f"[hw] done in {out['runtime_min']:.1f} min -> metrics_hardware.json")


if __name__ == "__main__":
    main()
