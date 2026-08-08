"""
Attribute the post-audit changes to individual fixes.

Four corrections landed at once and all of them touch the numbers:
  MESH  defect 36/37  non-conforming mesh -> conforming; electrodes no longer
                      63% buried in tissue
  FAT   defect 38     the fat/muscle boundary no longer slides with body motion
  STAT  defect 39/40  gate statistic: unadjusted R^2 averaged with a weight
                      containing itself -> adjusted R^2 with an honest weight
  THR   defect 50     LIN_GATE 0.35 -> 0.16, recalibrated on the new statistic

Running the studies again would produce a new set of numbers with no way to say
WHICH fix moved WHAT. A full 2x2x2 would cost about four hours, so this runs six
arms instead: all-old, each fix applied ALONE, all-new, and all-new with the old
threshold. Differencing a single-fix arm against all-old gives that fix's main
effect; the last pair separates the gate STATISTIC from the gate THRESHOLD.
Interactions between fixes are therefore NOT measured, which is the price of the
shorter run and is worth remembering if the main effects do not sum to the total.

Trials are PAIRED across arms: the seed depends only on the trial index and the
label, never on the arm, so every arm sees the identical anatomy, bolus, motion
and noise and the arms can be differenced directly.

Endpoints are the ones the report leads with: direction accuracy raw and on calls
made, abstention rate, and the false-retrograde rate on empty windows.

Outputs metrics_ablation.json
"""
import json, os, time
import numpy as np
from multiprocessing import Pool

import eit3d
import strip3d
import directional_sim as ds

N_STRIP = 8
SPAN = 12.0
Z_CENTER = 0.50
SNR = 60
T = 20
MOTIONS = (0.0, 0.60)          # still, and the level where motion bites
N_TRIAL = 60                   # per (arm, motion, class)
SEED0 = 7_000_000              # disjoint from every study and from the gate calib

# (name, legacy_mesh, legacy_fat, legacy_lin, gate)
# Two arm sets. ABLATE_SET=main attributes mesh / fat / gate against all-old;
# ABLATE_SET=gate isolates the two halves of the gate correction on the corrected
# physics, which the first run could not do because decide_direction bound
# lin_gate at definition time and the threshold never actually varied.
_MAIN = [
    ("all-old",         True,  True,  True,  0.35),
    ("mesh-fixed",      False, True,  True,  0.35),
    ("fat-fixed",       True,  False, True,  0.35),
    ("gate-fixed",      True,  True,  False, 0.16),
    ("all-new",         False, False, False, 0.16),
    ("all-new/oldthr",  False, False, False, 0.35),
]
# corrected mesh and fat throughout; only the gate statistic and threshold move
_GATE = [
    ("oldstat+oldthr",  False, False, True,  0.35),
    ("oldstat+newthr",  False, False, True,  0.16),
    ("newstat+oldthr",  False, False, False, 0.35),
    ("newstat+newthr",  False, False, False, 0.16),
]
ARMS = _GATE if os.environ.get("ABLATE_SET") == "gate" else _MAIN
OUT = os.environ.get("ABLATE_OUT", "metrics_ablation.json")

_STATE = {}


def _init(legacy_mesh, legacy_fat, legacy_lin, gate):
    global _MESH
    _MESH = (eit3d.make_cylinder_legacy(R=5.5, height=20.0, n_rings=6, nz=17)
             if legacy_mesh else
             eit3d.make_cylinder(R=5.5, height=20.0, n_rings=6, nz=17))
    ds.LEGACY_FAT = legacy_fat
    ds.LEGACY_LIN = legacy_lin
    ds.LIN_GATE = gate
    _STATE.clear()


def _world():
    if "w" not in _STATE:
        _STATE["w"] = ds.StripWorld(N_STRIP, span=SPAN, mesh=_MESH,
                                    z_center=Z_CENTER)
    return _STATE["w"]


def _one(args):
    motion, label, i = args
    w = _world()
    # PAIRED: the seed depends only on (i, label), never on the arm, so every
    # arm sees the identical trial and the arms can be differenced directly.
    rng = np.random.default_rng(SEED0 + i)
    grade = ds.sample_grade(rng)
    side = +1 if rng.random() < 0.5 else -1
    dZ = ds.simulate_trial(w, label, np.random.default_rng(SEED0 + 900_000 + i),
                           grade=grade, side=side, T=T, snr_db=SNR,
                           motion_amp=motion)
    d, s, ev = ds.decide_direction(ds.direction_features(dZ, w))
    want = {"reflux": +1, "antegrade": -1}.get(label, 0)
    return dict(motion=motion, label=label, grade=grade, dir=int(d), want=want,
                travelling=(want != 0))


def summarise(recs):
    trav = [r for r in recs if r["travelling"]]
    empt = [r for r in recs if not r["travelling"]]
    dec = [r for r in trav if r["dir"] != 0]
    return dict(
        n_trav=len(trav), n_empty=len(empt),
        dir_acc=float(np.mean([r["dir"] == r["want"] for r in trav])) if trav else float("nan"),
        dir_acc_decided=float(np.mean([r["dir"] == r["want"] for r in dec])) if dec else float("nan"),
        abstain=float(np.mean([r["dir"] == 0 for r in trav])) if trav else float("nan"),
        false_retro=float(np.mean([r["dir"] > 0 for r in empt])) if empt else float("nan"),
        low_grade_acc=(float(np.mean([r["dir"] == r["want"] for r in trav if r["grade"] <= 2]))
                       if any(r["grade"] <= 2 for r in trav) else float("nan")),
    )


def main():
    t0 = time.time()
    jobs = []
    i = 0
    for m in MOTIONS:
        for lab in ("reflux", "antegrade", "noflow", "bladder"):
            for _ in range(N_TRIAL):
                jobs.append((m, lab, i)); i += 1
    print(f"[abl] {len(ARMS)} arms x {len(jobs)} trials = "
          f"{len(ARMS)*len(jobs)} forward runs", flush=True)

    nproc = max(1, min(3, (os.cpu_count() or 4) - 2))
    out = {"config": dict(model_version=ds.MODEL_VERSION, n_strip=N_STRIP, span=SPAN, z_center=Z_CENTER, snr=SNR,
                          T=T, motions=list(MOTIONS), n_trial=N_TRIAL,
                          seed0=SEED0,
                          arms=[dict(name=a[0], legacy_mesh=a[1], legacy_fat=a[2],
                                     legacy_lin=a[3], gate=a[4]) for a in ARMS]),
           "arms": {}}

    for (name, lm, lf, ll, gate) in ARMS:
        ta = time.time()
        with Pool(nproc, initializer=_init,
                  initargs=(lm, lf, ll, gate)) as pool:
            recs = list(pool.imap_unordered(_one, jobs, chunksize=8))
        per_motion = {}
        for m in MOTIONS:
            per_motion[str(m)] = summarise([r for r in recs if r["motion"] == m])
        out["arms"][name] = dict(per_motion=per_motion,
                                 overall=summarise(recs),
                                 minutes=round((time.time() - ta) / 60.0, 1))
        s0 = per_motion[str(MOTIONS[0])]; s1 = per_motion[str(MOTIONS[-1])]
        print(f"[abl] {name:17s} still acc {100*s0['dir_acc']:5.1f}% "
              f"FR {100*s0['false_retro']:5.1f}% | "
              f"m{MOTIONS[-1]} acc {100*s1['dir_acc']:5.1f}% "
              f"abst {100*s1['abstain']:5.1f}% FR {100*s1['false_retro']:5.1f}% "
              f"({out['arms'][name]['minutes']} min)", flush=True)

    out["runtime_min"] = (time.time() - t0) / 60.0
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"[abl] done in {out['runtime_min']:.1f} min -> {OUT}",
          flush=True)


if __name__ == "__main__":
    main()
