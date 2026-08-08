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

# Body-habitus variation, off by default so the published arm is unchanged.
# HABITUS=1 draws fat thickness, organ scale and urine conductivity per child,
# which is the difference between a "cohort" and 48 copies of one child.
HABITUS = os.environ.get("HABITUS", "0") == "1"
OUT = os.environ.get("PRECISION_OUT", "metrics_precision.json")
# Derive the checkpoint from OUT. A shared checkpoint would let the habitus arm
# resume from the non-habitus arm's completed trials -- silently mixing two
# different cohorts into one result, the same collision that let an alternative
# placement overwrite the published run's records.
CKPT_ENV = os.environ.get("PRECISION_CKPT",
                          OUT.replace(".json", ".partial.jsonl"))

N_STRIP = 8
SNR = 60
T = 20
HEIGHT = 20.0
MOTION = 0.30
K_EVENTS = 6
N_CHILD = 48          # per (config, sigma)
SIGMAS = (0.0, 0.5, 1.0, 2.0)      # cm, std dev of placement error
# Fixed screening rule, chosen BEFORE seeing the results, so the two arms are
# compared on the same rule. best_k is still reported, but it is selected by
# max Youden on the very children it is scored on and is therefore optimistic.
PRESPEC_K = 2
# The low-grade optimum, and the long mid-torso strip it is being compared
# against. The optimum is READ FROM metrics_placement.json rather than hard-coded,
# the way run_tolerance already does it, so this study cannot silently keep
# testing a placement that Study 3 has superseded. It twice did: it was pinned to
# 10 cm @ z=0.34 through both the defect-16 and defect-27 corrections.
def _best_placement():
    try:
        b = json.load(open("metrics_placement.json"))["best_low_grade"]
        return (float(b["span"]), float(b["z_center"]), "best low-grade placement")
    except Exception:
        return (10.0, 0.34, "fallback: metrics_placement.json unreadable")


CONFIGS = [_best_placement(),
           (16.0, 0.50, "long, mid-torso")]

# Largest axial offset EVERY config can physically accommodate. Clipping both
# arms to this makes the placement-error distribution identical across arms;
# previously each arm was limited only by its own span, which protected the long
# strip from exactly the large misplacements the study was meant to compare.
def _centre_margin(span, zc0):
    """How far this centre can move before the strip runs off the body, in cm.
    Includes the electrode acceptance half-window, which the span alone omits."""
    half = 0.40 * span / max(N_STRIP - 1, 1)
    lo = (span / 2.0 + half) / HEIGHT
    return min(zc0 - lo, (1.0 - lo) - zc0) * HEIGHT


MAX_OFF = min(_centre_margin(span, zc0) for span, zc0, _ in CONFIGS)

_W = {}
# ONE world per worker. With sigma > 0 every child has its own z_center, so a
# world is essentially never reused across children and a deeper cache buys
# nothing while holding several CEM factorizations resident per worker. A 3-deep
# cache across 4 workers kept 12 alive at once and the OS killed the run at
# trial 1000. Jobs are emitted child-major and chunked one child at a time, so
# a single slot already gives full locality.
_WORLD_CACHE_MAX = 1
CKPT = CKPT_ENV


def _init():
    global _MESH
    ds.HABITUS = HABITUS
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
    # DEFECT 25, FIXED. The drawn offset used to be clipped only by whether the
    # strip stayed on the body, and that limit DEPENDS ON SPAN: a 16 cm strip in
    # a 20 cm torso can only move +/-1.9 cm, while a 10 cm strip at z=0.34 can
    # move -1.7/+8.1 cm. So the two arms were never exposed to the same error
    # distribution -- which is the exact comparison this study exists to make. At
    # sigma = 2.0 the long arm was being quietly protected from the large
    # misplacements the short arm had to absorb.
    #
    # Both arms are now clipped to MAX_OFF, the largest offset every config in
    # CONFIGS can physically accommodate, so the error distribution is identical
    # across arms by construction.
    off = float(np.random.default_rng(880_000 + child).normal(0.0, sigma)) if sigma > 0 else 0.0
    off = float(np.clip(off, -MAX_OFF, MAX_OFF))
    zc = zc0 + off / HEIGHT
    # The legal centre range must include the electrode acceptance half-window,
    # not just the span: place_strips raises if the outermost electrode's window
    # runs off the body, and the old clip ignored that margin.
    _half = 0.40 * span / max(N_STRIP - 1, 1)
    _lo = (span / 2.0 + _half) / HEIGHT
    zc = float(np.clip(zc, _lo + 1e-4, 1.0 - _lo - 1e-4))
    # the REALIZED offset after every clip, which is what was actually applied.
    # mean_abs_off previously reported the pre-clip nominal draw and so was wrong
    # in most cells, and it was the only placement diagnostic saved.
    off_realized = (zc - zc0) * HEIGHT
    label = "reflux" if refluxer else "antegrade"
    side = +1 if (child // 2) % 2 == 0 else -1
    anat = ds.draw_anatomy(_world(span, zc), np.random.default_rng(890_000 + child))
    w = _world(span, zc)
    dZ = ds.simulate_trial(w, label, np.random.default_rng(900_000 + child * 10 + k),
                           grade=grade, side=side, T=T, snr_db=SNR,
                           motion_amp=MOTION, anat=anat)
    feat = ds.direction_features(dZ, w)
    d, s, ev = ds.decide_direction(feat)
    # `lin` is what the abstain gate thresholds. It was not saved, so LIN_GATE
    # could not be swept without re-running the whole study -- and the gate is a
    # single hand-set constant that dominates the error budget. Saving it makes
    # the operating point a post-hoc sweep instead of another hour of compute.
    return dict(span=span, zc0=zc0, sigma=sigma, child=child, k=k, grade=grade,
                label=label, off=off_realized, off_nominal=off,
                clipped=bool(abs(off_realized - off) > 1e-9), dir=int(d),
                want=(+1 if refluxer else -1),
                lin=float(feat[s].get("lin", 0.0)), ev=float(ev),
                lat_ok=bool((s == 0) == (side > 0)))


def main():
    t0 = time.time()
    jobs = []
    for span, zc0, _ in CONFIGS:
        for sig in SIGMAS:
            for c in range(N_CHILD):
                refluxer = (c % 2 == 0)
                # DEFECT 23, FIXED. This drew grades UNIFORMLY, giving 40% grades
                # IV-V, while the project publishes GRADE_WEIGHTS
                # (30/30/22/13/5, so 18% IV-V) as its prevalence model and never
                # called sample_grade() anywhere in the repo. High grades are far
                # easier to detect, so over-representing them by more than 2x
                # biased every reported sensitivity UPWARD. Now uses the declared
                # model, so the cohort matches the prevalence the report claims.
                grade = ds.sample_grade(np.random.default_rng(870_000 + c))
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

    out = {"config": dict(model_version=ds.MODEL_VERSION, n_strip=N_STRIP, snr=SNR, motion=MOTION, T=T,
                          habitus=HABITUS,
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
                # Events actually CALLED retrograde. On a healthy child these are
                # the true false positives; inferring them as (K - n_hit) counted
                # every abstention as a false alarm (defect 26).
                n_retro = sum(1 for e in evs if e["dir"] > 0)
                n_abstain = sum(1 for e in evs if e["dir"] == 0)
                ps.append(dict(label=evs[0]["label"], n_hit=hits, n_retro=n_retro,
                               n_abstain=n_abstain, clipped=evs[0]["clipped"],
                               grade=evs[0]["grade"], off=evs[0]["off"]))
            sa = asub.subject_analysis(ps, K_EVENTS)
            refl = [p for p in ps if p["label"] == "reflux"]
            lowg = [p for p in refl if p["grade"] <= 2]
            grid[key] = dict(
                span=span, z_center=zc0, sigma=sig, name=name,
                sens_k=sa["sens_k"], spec_k=sa["spec_k"], best_k=sa["best_k"],
                best_sens=sa["best_sens"], best_spec=sa["best_spec"],
                # best_k is chosen by max Youden ON THESE SAME CHILDREN, so
                # best_sens/best_spec are optimistically biased and are not an
                # out-of-sample estimate. A PRE-SPECIFIED k is reported beside
                # them so the comparison between arms uses a fixed rule.
                prespec_k=PRESPEC_K,
                prespec_sens=sa["sens_k"][str(PRESPEC_K)],
                prespec_spec=sa["spec_k"][str(PRESPEC_K)],
                best_k_selected_in_sample=True,
                fp_counts_abstentions=sa.get("fp_counts_abstentions"),
                mean_abstain=float(np.mean([p["n_abstain"] for p in ps])) / K_EVENTS,
                never_detected=sa["never_detected_reflux"],
                per_event_sens=sa["per_event_sens"],
                low_grade_never=(float(np.mean([p["n_hit"] == 0 for p in lowg]))
                                 if lowg else float("nan")),
                mean_abs_off=float(np.mean([abs(p["off"]) for p in ps])),
                # A 12 cm strip at z=0.36 can only move +/-0.51 cm on a 20 cm
                # torso before an electrode leaves the flank, so the larger sigma
                # arms are heavily clipped and are NOT sampling the distribution
                # they are labelled with. Report how much, rather than let the
                # label imply an error spread the geometry cannot deliver.
                max_off_cm=float(MAX_OFF),
                clipped_fraction=float(np.mean([p["clipped"] for p in ps])),
            )
    out["grid"] = grid
    out["grade_hist"] = {str(g): sum(1 for r in recs if r["grade"] == g)
                         for g in (1, 2, 3, 4, 5)}
    out["runtime_min"] = (time.time() - t0) / 60.0
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    # per-trial records, so the abstain gate can be swept post hoc
    with open(OUT.replace("metrics_", "records_"), "w") as f:
        json.dump(recs, f)
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
