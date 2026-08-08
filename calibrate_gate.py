"""
Calibrate the abstain gate on a dedicated sample, on seeds no study uses.

WHY THIS EXISTS. LIN_GATE was a single hand-set constant (0.35) that dominated
the error budget and had never been swept -- and, worse, it was calibrated
against the UNADJUSTED R-squared. Defect 46 replaced that statistic with the
ADJUSTED R-squared, whose expectation under the null is 0 regardless of zone
count, so the old threshold no longer means what it meant. A gate tuned to one
statistic and applied to another is not a gate, it is a coincidence.

HOW THIS AVOIDS THE OBVIOUS TRAP. Defect 25 was choosing an operating point on
the data it was then scored on. Here the calibration draws from a seed block
(4_000_000+) that no run_*.py touches, so the threshold is fixed before any study
sees it. The sweep and both curves are written out, so the choice is auditable
and can be moved without re-running anything.

Writes metrics_gate.json and prints the recommended LIN_GATE.
"""
import json, os, time
import numpy as np
from multiprocessing import Pool

import eit3d
import directional_sim as ds

N_STRIP = 8
SPAN = 12.0
Z_CENTER = 0.50
SNR = 60
T = 20
MOTIONS = (0.0, 0.30, 0.60)         # calibrate across the usable motion range
N_PER = 40                          # per (class, motion)
TRAV = ("reflux", "antegrade")
EMPTY = ("noflow", "bladder")
SEED0 = 4_000_000                   # disjoint from every study's seed block


def _init():
    global _MESH
    _MESH = eit3d.make_cylinder(R=5.5, height=20.0, n_rings=6, nz=17)


_W = {}


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
    dZ = ds.simulate_trial(w, label, np.random.default_rng(SEED0 + 500_000 + i),
                           grade=grade, side=side, T=T, snr_db=SNR,
                           motion_amp=motion)
    feat = ds.direction_features(dZ, w)
    # the raw sign the gate would let through, and the statistic it thresholds
    s = max((0, 1), key=lambda k: feat[k].get("dif_energy", 0.0))
    lin = float(feat[s].get("lin", 0.0))
    ev = float(feat[s].get("fused_ev", 0.0))
    want = {"reflux": +1, "antegrade": -1}.get(label, 0)
    return dict(label=label, motion=motion, lin=lin, ev=ev, want=want,
                travelling=(want != 0),
                sign_ok=bool(want != 0 and np.sign(ev) == want))


def main():
    t0 = time.time()
    jobs, i = [], 0
    for m in MOTIONS:
        for lab in TRAV + EMPTY:
            for _ in range(N_PER):
                jobs.append((lab, m, i)); i += 1
    print(f"[gate] {len(jobs)} calibration trials on seeds {SEED0}+", flush=True)

    nproc = max(1, min(3, (os.cpu_count() or 4) - 2))
    with Pool(nproc, initializer=_init) as pool:
        recs = list(pool.imap_unordered(_one, jobs, chunksize=8))

    trav = np.array([r["lin"] for r in recs if r["travelling"]])
    empt = np.array([r["lin"] for r in recs if not r["travelling"]])
    # Among travelling trials, only those whose SIGN is right are worth keeping:
    # letting through a confidently wrong call is not a win.
    good = np.array([r["lin"] for r in recs if r["travelling"] and r["sign_ok"]])

    sweep = []
    for thr in np.arange(-0.40, 0.96, 0.02):
        keep_good = float((good >= thr).mean()) if good.size else float("nan")
        rej_empty = float((empt < thr).mean()) if empt.size else float("nan")
        sweep.append(dict(thr=float(thr), keeps_correct_events=keep_good,
                          rejects_empty=rej_empty,
                          youden=keep_good + rej_empty - 1.0))
    best = max(sweep, key=lambda s: s["youden"])

    out = dict(
        config=dict(model_version=ds.MODEL_VERSION, n_strip=N_STRIP, span=SPAN, z_center=Z_CENTER, snr=SNR, T=T,
                    motions=list(MOTIONS), n_per=N_PER, seed_block=SEED0,
                    statistic="adjusted R^2 of arrival time vs zone height"),
        n_travelling=int(trav.size), n_empty=int(empt.size),
        n_correct_sign=int(good.size),
        travelling_median=float(np.median(trav)) if trav.size else float("nan"),
        empty_median=float(np.median(empt)) if empt.size else float("nan"),
        travelling_p10=float(np.percentile(trav, 10)) if trav.size else float("nan"),
        empty_p90=float(np.percentile(empt, 90)) if empt.size else float("nan"),
        sweep=sweep, recommended=best,
        previous_gate=float(ds.LIN_GATE),
        runtime_min=(time.time() - t0) / 60.0,
    )
    json.dump(out, open("metrics_gate.json", "w"), indent=1)
    print(f"[gate] travelling median {out['travelling_median']:+.3f}  "
          f"empty median {out['empty_median']:+.3f}")
    print(f"[gate] RECOMMENDED LIN_GATE = {best['thr']:+.2f}  "
          f"(keeps {100*best['keeps_correct_events']:.0f}% of correct events, "
          f"rejects {100*best['rejects_empty']:.0f}% of empty, "
          f"Youden {best['youden']:.2f})")
    print(f"[gate] previous value was {out['previous_gate']}, calibrated against "
          f"the UNADJUSTED statistic")
    print(f"[gate] done in {out['runtime_min']:.1f} min -> metrics_gate.json")


if __name__ == "__main__":
    main()
