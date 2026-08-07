"""
Study 6: non-rigid respiratory motion. The one genuinely existential risk.

WHY THIS IS THE MOST IMPORTANT REMAINING STUDY
----------------------------------------------
Every motion result so far was produced with a RIGID translation: one (T,3)
displacement applied identically to the body and the bolus. That is precisely the
perturbation that subtracting the across-zone mean provably nulls. A rigid-only
model can therefore only ever CONFIRM the common-mode rejection claim; it cannot
test it. The docstring in directional_sim.py asserting the claim is "TESTED
rather than assumed" was wrong.

Real respiratory motion is not rigid. It is a craniocaudal GRADIENT: the kidney
translates 1-3 cm with the diaphragm while the bladder is nearly fixed. A
displacement that varies linearly with height SURVIVES mean subtraction and feeds
straight into the arrival-time slope as a phase-locked, breathing-rate FALSE
TRAVELLING WAVE. That is the exact shape of the failure that took the prior
tomographic program from 73% to 44%.

ENDPOINTS
  1. FALSE-RETROGRADE RATE on non-travelling windows (no flow, bladder filling)
     against respiratory amplitude and gradient. This is the endpoint that
     matters: a device that invents reflux while the child breathes is unusable
     regardless of its accuracy on real events.
  2. Direction accuracy on real events, to see what the gradient costs.
  3. Whether the abstain gate catches it, or whether breathing produces waves
     coherent enough to pass the gate.

Outputs metrics_motion2.json
"""
import json, os, time
import numpy as np
from multiprocessing import Pool

import eit3d
import directional_sim as ds

N_STRIP = 8
SPAN = 16.0
SNR = 60
T = 20
GRADES = (3, 4, 5)
# Amplitudes must span REAL respiratory kidney excursion, which is 1-3 cm. With a
# full gradient the differential displacement across the strip is roughly 0.8*amp,
# so an earlier version topping out at 0.9 cm was testing a gradient far gentler
# than physiology and would have understated the risk.
AMPS = (0.0, 0.5, 1.0, 2.0, 3.0)   # cm of displacement (kidney end)
GRADS = (0.0, 0.5, 1.0)            # 0 = rigid (old model), 1 = full gradient
N_TRIAL = 36                       # per (amp, grad, class)
CLASSES = ("reflux", "antegrade", "noflow", "bladder")

_W = {}


def _init():
    global _MESH
    _MESH = eit3d.make_cylinder(R=5.5, height=20.0, n_rings=6, nz=17)


def _world():
    if "w" not in _W:
        _W["w"] = ds.StripWorld(N_STRIP, span=SPAN, mesh=_MESH)
    return _W["w"]


def _run_one(args):
    amp, grad, label, i = args
    w = _world()
    g = int(np.random.default_rng(660_000 + i).choice(GRADES))
    side = +1 if (i // 2) % 2 == 0 else -1
    dZ = ds.simulate_trial(w, label, np.random.default_rng(670_000 + i), grade=g,
                           side=side, T=T, snr_db=SNR, motion_amp=amp,
                           motion_grad=grad)
    feat = ds.direction_features(dZ, w)
    d, s, ev = ds.decide_direction(feat)
    want = {"reflux": +1, "antegrade": -1}.get(label, 0)
    return dict(amp=amp, grad=grad, label=label, i=i, dir=int(d), want=want,
                lin=float(feat[s].get("lin", 0.0)),
                ev=float(ev), travelling=(want != 0))


def wilson(p, n, z=1.96):
    if n <= 0 or p != p:
        return (float("nan"), float("nan"))
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main():
    t0 = time.time()
    jobs = [(a, g, c, i) for a in AMPS for g in GRADS
            for c in CLASSES for i in range(N_TRIAL)]
    print(f"[m2] {len(jobs)} trials  amps={AMPS} grads={GRADS}", flush=True)

    nproc = max(1, min(4, (os.cpu_count() or 4) - 2))
    recs = []
    with Pool(nproc, initializer=_init) as pool:
        for k, r in enumerate(pool.imap_unordered(_run_one, jobs, chunksize=6)):
            recs.append(r)
            if (k + 1) % 200 == 0:
                el = time.time() - t0
                print(f"[m2] {k+1}/{len(jobs)}  {el/60:.1f} min  "
                      f"eta {(el/(k+1)*(len(jobs)-k-1))/60:.1f} min", flush=True)

    out = {"config": dict(n_strip=N_STRIP, span=SPAN, snr=SNR, T=T,
                          amps=list(AMPS), grads=list(GRADS),
                          n_trial=N_TRIAL, classes=list(CLASSES))}
    grid = {}
    for a in AMPS:
        for g in GRADS:
            key = f"a{a}_g{g}"
            sub = [r for r in recs if r["amp"] == a and r["grad"] == g]
            empty = [r for r in sub if not r["travelling"]]
            trav = [r for r in sub if r["travelling"]]
            fr = float(np.mean([r["dir"] > 0 for r in empty])) if empty else float("nan")
            grid[key] = dict(
                amp=a, grad=g,
                false_retrograde=fr, false_retro_ci=wilson(fr, len(empty)),
                n_empty=len(empty),
                empty_abstain=float(np.mean([r["dir"] == 0 for r in empty])) if empty else float("nan"),
                empty_lin=float(np.mean([r["lin"] for r in empty])) if empty else float("nan"),
                dir_acc=float(np.mean([r["dir"] == r["want"] for r in trav])) if trav else float("nan"),
                dir_acc_decided=(float(np.mean([r["dir"] == r["want"]
                                                for r in trav if r["dir"] != 0]))
                                 if any(r["dir"] != 0 for r in trav) else float("nan")),
                trav_abstain=float(np.mean([r["dir"] == 0 for r in trav])) if trav else float("nan"),
                n_trav=len(trav))
    out["grid"] = grid
    # headline: how much worse is the gradient than the rigid model at each amp
    out["gradient_cost"] = {
        f"a{a}": {"false_retro_rigid": grid[f"a{a}_g0.0"]["false_retrograde"],
                  "false_retro_gradient": grid[f"a{a}_g1.0"]["false_retrograde"],
                  "dir_acc_rigid": grid[f"a{a}_g0.0"]["dir_acc"],
                  "dir_acc_gradient": grid[f"a{a}_g1.0"]["dir_acc"]}
        for a in AMPS}
    out["runtime_min"] = (time.time() - t0) / 60.0
    with open("metrics_motion2.json", "w") as f:
        json.dump(out, f, indent=1)
    print(f"[m2] done in {out['runtime_min']:.1f} min -> metrics_motion2.json", flush=True)
    print("[m2] FALSE-RETROGRADE on empty windows (the endpoint that matters):")
    for a in AMPS:
        row = "  ".join(f"grad {g}: {100*grid[f'a{a}_g{g}']['false_retrograde']:5.1f}%"
                        for g in GRADS)
        print(f"[m2]   amp {a} cm | {row}", flush=True)


if __name__ == "__main__":
    main()
