"""
Study 8: does the second excitation frequency earn its cost?

WHY THIS EXISTS
---------------
Every study solves the forward problem at BOTH 50 and 100 kHz, which doubles the
cost of the most expensive step in the project. The estimator then does this:

    ser = dZ.real.mean(axis=1)

It AVERAGES them. No feature in FEATURE_NAMES is derived from frequency at all.
So the design pays twice for a measurement it uses only to halve noise, and the
report has never tested whether a second frequency buys anything.

There is a real physical reason it might. Urine has no cell membranes
(eps_r ~ 80, essentially water) while soft tissue is dominated by them
(eps_r ~ 26,000). Urine and tissue therefore disperse very differently with
frequency, so a DIFFERENCE between two frequencies should suppress tissue and
preferentially retain urine -- a contrast agent made of arithmetic.

WHAT IT MEASURES
----------------
Four estimator arms on identical trials, paired by seed:
    f0     50 kHz alone            -- halves the compute
    f1     100 kHz alone           -- halves the compute
    mean   the average (current)   -- the incumbent
    diff   f1 - f0, the dispersion contrast
If f0 alone matches mean, the second frequency is pure cost and should be
dropped. If diff beats both, the design should be reading dispersion rather than
magnitude, which is a different instrument.

HONESTY ABOUT THE DISPERSION MODEL
----------------------------------
This model uses a single log-frequency fit, sigma(f) = sigma0 (1 + 0.04 log10
(f/50k)), so muscle rises only 1.2% between the two frequencies. Real tissue
follows a Cole-Cole relaxation whose beta-dispersion is far stronger across this
band. A null result for `diff` here is therefore a statement about THIS
dispersion model, not about dual-frequency bioimpedance, and the study reports
the contrast actually available so the two can be told apart.

Outputs metrics_multifreq.json
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
N_TRIAL = 40                     # per (class, motion), per arm
SEED0 = 6_000_000
MODES = ("f0", "f1", "mean", "diff", "phase", "imag")
CLASSES = ("reflux", "antegrade", "noflow", "bladder")


def _placement():
    try:
        b = json.load(open("metrics_placement.json"))["best_low_grade"]
        return float(b["span"]), float(b["z_center"])
    except Exception:
        return 12.0, 0.36


SPAN, Z_CENTER = _placement()
_W = {}


def _init(mode):
    global _MESH
    _MESH = eit3d.make_cylinder(R=5.5, height=HEIGHT, n_rings=6, nz=17)
    ds.FREQ_MODE = mode
    _W.clear()


def _world():
    if "w" not in _W:
        _W["w"] = ds.StripWorld(N_STRIP, span=SPAN, mesh=_MESH, z_center=Z_CENTER)
    return _W["w"]


def _one(args):
    label, motion, i = args
    w = _world()
    rng = np.random.default_rng(SEED0 + i)
    grade = ds.sample_grade(rng)
    side = +1 if rng.random() < 0.5 else -1
    dZ = ds.simulate_trial(w, label, np.random.default_rng(SEED0 + 800_000 + i),
                           grade=grade, side=side, T=T, snr_db=SNR,
                           motion_amp=motion)
    feat = ds.direction_features(dZ, w)
    d, s, ev = ds.decide_direction(feat)
    want = {"reflux": +1, "antegrade": -1}.get(label, 0)
    return dict(label=label, motion=motion, grade=int(grade), dir=int(d),
                want=want, travelling=(want != 0),
                lin=float(feat[s].get("lin", 0.0)))


def summarise(rs):
    trav = [r for r in rs if r["travelling"]]
    empt = [r for r in rs if not r["travelling"]]
    dec = [r for r in trav if r["dir"] != 0]
    low = [r for r in trav if r["grade"] <= 2]
    return dict(
        n_trav=len(trav), n_empty=len(empt),
        dir_acc=float(np.mean([r["dir"] == r["want"] for r in trav])) if trav else float("nan"),
        dir_acc_decided=float(np.mean([r["dir"] == r["want"] for r in dec])) if dec else float("nan"),
        abstain=float(np.mean([r["dir"] == 0 for r in trav])) if trav else float("nan"),
        false_retro=float(np.mean([r["dir"] > 0 for r in empt])) if empt else float("nan"),
        low_grade_acc=float(np.mean([r["dir"] == r["want"] for r in low])) if low else float("nan"),
        mean_lin_travelling=float(np.mean([r["lin"] for r in trav])) if trav else float("nan"),
    )


def dispersion_available():
    """How much contrast is actually on offer between the two frequencies."""
    out = {}
    for t in ("muscle", "fat", "kidney", "urine", "bladder"):
        a, b = ds.admittivity(t, 50e3), ds.admittivity(t, 100e3)
        out[t] = dict(sigma_50k=float(a.real), sigma_100k=float(b.real),
                      rel_change=float(b.real / a.real - 1.0))
    out["urine_minus_muscle_contrast"] = float(
        out["urine"]["rel_change"] - out["muscle"]["rel_change"])
    return out


def main():
    t0 = time.time()
    jobs, i = [], 0
    for m in MOTIONS:
        for lab in CLASSES:
            for _ in range(N_TRIAL):
                jobs.append((lab, m, i)); i += 1
    print(f"[mf] {len(MODES)} arms x {len(jobs)} trials at "
          f"{SPAN:.0f} cm @ z={Z_CENTER:.2f}", flush=True)

    disp = dispersion_available()
    print(f"[mf] dispersion available 50->100 kHz: urine "
          f"{100*disp['urine']['rel_change']:+.2f}%, muscle "
          f"{100*disp['muscle']['rel_change']:+.2f}%, contrast "
          f"{100*disp['urine_minus_muscle_contrast']:+.2f} points", flush=True)

    nproc = max(1, min(3, (os.cpu_count() or 4) - 2))
    out = dict(config=dict(model_version=ds.MODEL_VERSION, n_strip=N_STRIP, span=SPAN, z_center=Z_CENTER,
                           snr=SNR, T=T, motions=list(MOTIONS),
                           n_trial=N_TRIAL, modes=list(MODES), seed0=SEED0),
               dispersion=disp, arms={})
    for mode in MODES:
        ta = time.time()
        with Pool(nproc, initializer=_init, initargs=(mode,)) as pool:
            recs = list(pool.imap_unordered(_one, jobs, chunksize=8))
        per = {str(m): summarise([r for r in recs if r["motion"] == m])
               for m in MOTIONS}
        out["arms"][mode] = dict(per_motion=per, overall=summarise(recs),
                                 minutes=round((time.time() - ta) / 60.0, 1))
        o = out["arms"][mode]["overall"]
        print(f"[mf] {mode:>5}: acc {100*o['dir_acc']:5.1f}%  "
              f"on-calls {100*o['dir_acc_decided']:5.1f}%  "
              f"abstain {100*o['abstain']:5.1f}%  FR {100*o['false_retro']:5.1f}%  "
              f"low-grade {100*o['low_grade_acc']:5.1f}%  "
              f"({out['arms'][mode]['minutes']} min)", flush=True)

    base = out["arms"]["mean"]["overall"]["dir_acc"]
    out["vs_mean"] = {m: out["arms"][m]["overall"]["dir_acc"] - base for m in MODES}
    out["runtime_min"] = (time.time() - t0) / 60.0
    json.dump(out, open("metrics_multifreq.json", "w"), indent=1)
    print(f"[mf] done in {out['runtime_min']:.1f} min -> metrics_multifreq.json",
          flush=True)


if __name__ == "__main__":
    main()
