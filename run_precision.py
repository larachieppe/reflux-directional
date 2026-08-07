"""
Placement precision study: what fraction of children are unmeasurable?

NOT A PHANTOM STUDY. A phantom study is physical and cannot be run here. This is
its simulation analogue: instead of one perfectly placed strip, every simulated
child gets a RANDOM placement error drawn from a realistic distribution, on top of
randomized anatomy. It estimates the two quantities that decide the product:

  1. What fraction of children are detected once placement is imperfect.
  2. What fraction are systematically unmeasurable, i.e. fail on every event, for
     whom no amount of repeat observation helps.

It also asks whether a LONGER strip buys positional margin at the cost of peak
low-grade accuracy, which is the open trade after the tolerance sweep showed the
10 cm optimum collapsing beyond +/- 1 cm.

Outputs metrics_precision.json
"""
import json, math, os, time
import numpy as np
from multiprocessing import Pool

import eit3d
import directional_sim as ds
import analyze_subjects as asub

N_STRIP = 8
SNR = 60
T = 20
HEIGHT = 20.0
MOTION = 0.30
K_EVENTS = 6
N_CHILD = 48          # per (config, sigma)
SIGMAS = (0.0, 0.5, 1.0, 2.0)      # cm, std dev of placement error
# the low-grade optimum, and a longer strip that trades peak accuracy for margin
CONFIGS = [(10.0, 0.34, "short, over the UVJ"),
           (16.0, 0.50, "long, mid-torso")]

_W = {}
# ONE world per worker. With sigma > 0 every child has its own z_center, so a
# world is essentially never reused across children and a deeper cache buys
# nothing while holding several CEM factorizations resident per worker. A 3-deep
# cache across 4 workers kept 12 alive at once and the OS killed the run at
# trial 1000. Jobs are emitted child-major and chunked one child at a time, so
# a single slot already gives full locality.
_WORLD_CACHE_MAX = 1
CKPT = "metrics_precision.partial.jsonl"


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
    span, zc0, sigma, child, k, grade, refluxer = args
    # ONE placement error per child, shared by all their events: a strip is
    # applied once, not re-applied per void. This is what makes failure
    # correlated within a child, which is the whole question.
    off = float(np.random.default_rng(880_000 + child).normal(0.0, sigma)) if sigma > 0 else 0.0
    off = float(np.clip(off, -3.0, 3.0))
    zc = zc0 + off / HEIGHT
    zc = float(np.clip(zc, span / (2 * HEIGHT) + 0.005, 1.0 - span / (2 * HEIGHT) - 0.005))
    label = "reflux" if refluxer else "antegrade"
    side = +1 if (child // 2) % 2 == 0 else -1
    anat = ds.draw_anatomy(_world(span, zc), np.random.default_rng(890_000 + child))
    w = _world(span, zc)
    dZ = ds.simulate_trial(w, label, np.random.default_rng(900_000 + child * 10 + k),
                           grade=grade, side=side, T=T, snr_db=SNR,
                           motion_amp=MOTION, anat=anat)
    d, s, ev = ds.decide_direction(ds.direction_features(dZ, w))
    return dict(span=span, zc0=zc0, sigma=sigma, child=child, k=k, grade=grade,
                label=label, off=off, dir=int(d),
                want=(+1 if refluxer else -1),
                lat_ok=bool((s == 0) == (side > 0)))


def main():
    t0 = time.time()
    jobs = []
    for span, zc0, _ in CONFIGS:
        for sig in SIGMAS:
            for c in range(N_CHILD):
                refluxer = (c % 2 == 0)
                grade = int(np.random.default_rng(870_000 + c).choice([1, 2, 3, 4, 5]))
                for k in range(K_EVENTS):
                    jobs.append((span, zc0, sig, c, k, grade, refluxer))
    total = len(jobs)

    # Resume: a killed run must not cost its completed work. Records are appended
    # as they land, and anything already on disk is skipped on restart.
    recs, done = [], set()
    if os.path.exists(CKPT):
        with open(CKPT) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue          # torn final line from a kill mid-write
                recs.append(r)
                done.add((r["span"], r["sigma"], r["child"], r["k"]))
    if done:
        jobs = [j for j in jobs if (j[0], j[2], j[3], j[4]) not in done]
        print(f"[prec] resuming: {len(done)} trials already done, "
              f"{len(jobs)} remaining", flush=True)
    print(f"[prec] {total} trials  ({len(CONFIGS)} configs x {len(SIGMAS)} sigmas "
          f"x {N_CHILD} children x {K_EVENTS} events)", flush=True)

    nproc = max(1, min(3, (os.cpu_count() or 4) - 2))
    with open(CKPT, "a", buffering=1) as ck, Pool(nproc, initializer=_init) as pool:
        for i, r in enumerate(pool.imap_unordered(_run_one, jobs, chunksize=K_EVENTS)):
            recs.append(r)
            ck.write(json.dumps(r) + "\n")
            if (i + 1) % 200 == 0:
                el = time.time() - t0
                print(f"[prec] {len(recs)}/{total}  {el/60:.1f} min  "
                      f"eta {(el/(i+1)*(len(jobs)-i-1))/60:.1f} min", flush=True)

    out = {"config": dict(n_strip=N_STRIP, snr=SNR, motion=MOTION, T=T,
                          k_events=K_EVENTS, n_child=N_CHILD,
                          sigmas=list(SIGMAS), configs=CONFIGS)}
    grid = {}
    for span, zc0, name in CONFIGS:
        for sig in SIGMAS:
            key = f"{span:.0f}_{sig:.1f}"
            sub = [r for r in recs if r["span"] == span and r["sigma"] == sig]
            per_child = {}
            for r in sub:
                per_child.setdefault(r["child"], []).append(r)
            ps = []
            for c, evs in sorted(per_child.items()):
                hits = sum(1 for e in evs if e["dir"] == e["want"])
                ps.append(dict(label=evs[0]["label"], n_hit=hits,
                               grade=evs[0]["grade"], off=evs[0]["off"]))
            sa = asub.subject_analysis(ps, K_EVENTS)
            refl = [p for p in ps if p["label"] == "reflux"]
            lowg = [p for p in refl if p["grade"] <= 2]
            grid[key] = dict(
                span=span, z_center=zc0, sigma=sig, name=name,
                sens_k=sa["sens_k"], spec_k=sa["spec_k"], best_k=sa["best_k"],
                best_sens=sa["best_sens"], best_spec=sa["best_spec"],
                never_detected=sa["never_detected_reflux"],
                per_event_sens=sa["per_event_sens"],
                low_grade_never=(float(np.mean([p["n_hit"] == 0 for p in lowg]))
                                 if lowg else float("nan")),
                mean_abs_off=float(np.mean([abs(p["off"]) for p in ps])),
            )
    out["grid"] = grid
    out["runtime_min"] = (time.time() - t0) / 60.0
    with open("metrics_precision.json", "w") as f:
        json.dump(out, f, indent=1)
    if os.path.exists(CKPT):
        os.remove(CKPT)          # only on a complete, written run
    print(f"[prec] done in {out['runtime_min']:.1f} min -> metrics_precision.json",
          flush=True)
    for k, v in sorted(grid.items(), key=lambda t: (t[1]["span"], t[1]["sigma"])):
        print(f"[prec]  {v['span']:.0f}cm sigma={v['sigma']:.1f}cm : "
              f">={v['best_k']}of{K_EVENTS} sens {100*v['best_sens']:.0f}% "
              f"spec {100*v['best_spec']:.0f}%  never-detected {100*v['never_detected']:.0f}%",
              flush=True)


if __name__ == "__main__":
    main()
