"""
Electrode-count sweep for the directional bioimpedance design.

Primary question: how many electrodes per flank strip are needed, given that the
flank span is capped by anatomy? More electrodes buy more tetrapolar zones, but
over a FIXED span more electrodes also means tighter spacing, and tetrapolar
sensing depth scales with spacing. The optimum is therefore interior.

Primary endpoint is DIRECTION accuracy under injected motion, because motion is
what degraded the prior tomographic program from 73% to 44%.

Outputs metrics_directional.json
"""
import json, os, sys, time
import numpy as np
from multiprocessing import Pool

import inspect

import eit3d
import directional_sim as ds

# DEFECT 32. This line used to read `ds.FREQS = ds.FREQS[:1]`, commented "50 kHz
# only: halves solves". It was a NO-OP. `simulate_trial(..., freqs=FREQS)` binds
# its default at DEFINITION time, so rebinding the module attribute afterwards
# never reached the solver: this study has always run at BOTH 50 and 100 kHz,
# took twice the compute the comment claimed to save, and then recorded
# freqs=[50000.0] in its own config -- a figure that was simply false, and one
# the report quoted. The frequencies are left as they actually are and the config
# now records what the solver actually used.
# simulate_trial now resolves freqs at CALL time (freqs=None -> ds.FREQS), so
# the honest record of what the solver used is simply ds.FREQS. Reading the
# signature default returns None now and would raise.
FREQS_USED = [float(x) for x in ds.FREQS]

SPAN = 12.0                     # cm of usable flank (anatomy-capped)
COUNTS = [4, 5, 6, 8, 10, 12]   # electrodes per strip
MOTION = [0.0, 0.3, 0.6, 0.9]   # cm of common-mode body displacement
SNRS = [50, 60, 70, 80]
SPANS = [8.0, 10.0, 12.0, 14.0, 16.0]
T = 20

# POWER. The first run pooled all grades and was underpowered: grade sets how far
# reflux travels, so grades 1-2 barely enter the sensed span and are undetectable
# by construction, leaving only ~17 informative trials per cell (binomial SE ~11%,
# far larger than the electrode-count differences being tested).
# The primary endpoint is therefore measured where the device is meant to work
# (grade >= 3, which is also where Arena's miss-rate constraint binds), with every
# primary trial a travelling one so all of them inform the direction endpoint.
N_TRIAL = 96                   # travelling trials per (count, motion) cell
N_GRADE = 48                    # per grade, for the grade-tail curve
N_AUC = 64                      # 4-class trials per count, for AUC + ablation
N_SEC = 32                      # per cell, secondary sweeps

_W = {}                         # per-process world cache
# BOUNDED. Each StripWorld holds a full CEM3D solver (per-electrode mass matrices
# for up to 24 electrodes). Caching every (count, span) combination per worker
# exhausted an 8 GB machine and drove it into swap, collapsing throughput ~4x.
_WORLD_CACHE_MAX = 2


def _init():
    global _MESH
    _MESH = eit3d.make_cylinder(R=5.5, height=20.0, n_rings=6, nz=17)


def _world(n, span):
    key = (n, round(span, 3))
    if key not in _W:
        if len(_W) >= _WORLD_CACHE_MAX:
            _W.pop(next(iter(_W)))          # evict oldest
        _W[key] = ds.StripWorld(n, span=span, mesh=_MESH)
    return _W[key]


def _trial_spec(i, mode="primary", grade=None):
    """Deterministic trial definition, SHARED across electrode counts so the
    comparison is paired (same anatomy, same bolus, same motion realization).

    mode="primary": every trial travels (reflux / antegrade 50-50) at grade 3-5,
                    so all N_TRIAL trials inform the direction endpoint.
    mode="grade":   travelling trials at one fixed grade (the low-grade tail).
    mode="auc":     all four classes, for reflux-vs-rest AUC and the ablation.
    """
    rng = np.random.default_rng(10_000 + i)
    if mode == "auc":
        label = ds.CLASSES[i % len(ds.CLASSES)]
        g = int(rng.choice([3, 4, 5]))
    elif mode == "grade":
        label = "reflux" if i % 2 == 0 else "antegrade"
        g = int(grade)
    else:
        label = "reflux" if i % 2 == 0 else "antegrade"
        g = int(rng.choice([3, 4, 5]))
    side = +1 if rng.random() < 0.5 else -1
    return label, g, side, int(20_000 + i)


def _run_one(args):
    n, span, motion, snr, i, mode, fixed_grade = args
    label, grade, side, seed = _trial_spec(i, mode, fixed_grade)
    w = _world(n, span)
    dZ = ds.simulate_trial(w, label, np.random.default_rng(seed), grade=grade,
                           side=side, T=T, snr_db=snr, motion_amp=motion)
    fv, feat = ds.feature_vector(dZ, w)
    d, s, ev = ds.decide_direction(feat)
    want = {"reflux": +1, "antegrade": -1}.get(label, 0)
    return dict(n=n, span=span, motion=motion, snr=snr, i=i, mode=mode, label=label,
                grade=grade, side=side, x=fv.tolist(), dir=int(d),
                want=int(want), strip=int(s), ev=float(ev),
                lat_ok=bool((s == 0) == (side > 0)),
                n_zones=int(w.n_zones_per_strip))


# ---------------------------------------------------------------- metrics
def _auc(y, sc):
    y = np.asarray(y, int); sc = np.asarray(sc, float)
    p, q = sc[y == 1], sc[y == 0]
    if len(p) == 0 or len(q) == 0:
        return float("nan")
    r = np.argsort(np.argsort(np.concatenate([p, q]))) + 1
    return float((r[:len(p)].sum() - len(p) * (len(p) + 1) / 2) / (len(p) * len(q)))


def _fit_auc(recs, feat_idx=None, seed=0):
    """Reflux vs rest AUC, elastic-net logistic regression, 5-fold CV."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import StratifiedKFold
    X = np.array([r["x"] for r in recs], float)
    if feat_idx is not None:
        X = X[:, feat_idx]
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    y = np.array([r["label"] == "reflux" for r in recs], int)
    if y.sum() < 5 or (1 - y).sum() < 5:
        return float("nan")
    oof = np.zeros(len(y))
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=seed).split(X, y):
        clf = make_pipeline(StandardScaler(),
                            LogisticRegression(penalty="elasticnet", l1_ratio=0.5,
                                               C=1.0, solver="saga", max_iter=4000))
        clf.fit(X[tr], y[tr])
        oof[te] = clf.predict_proba(X[te])[:, 1]
    return _auc(y, oof)


def summarize(recs):
    trav = [r for r in recs if r["want"] != 0]
    dir_ok = [r["dir"] == r["want"] for r in trav]
    refl = [r for r in recs if r["label"] == "reflux"]
    undec = float(np.mean([r["dir"] == 0 for r in trav])) if trav else float("nan")
    # With an abstain gate, "no call" is not the same as a wrong call. Report
    # both: accuracy counting abstention as a miss (conservative, the headline),
    # and accuracy among trials where a call was actually made.
    decided = [r for r in trav if r["dir"] != 0]
    # A cell where EVERY trial is undecidable is not 0% accurate, it is undefined:
    # with one zone there is no ordering to read, so no answer exists to be wrong.
    acc = float(np.mean(dir_ok)) if dir_ok else float("nan")
    if undec == undec and undec > 0.99:
        acc = float("nan")
    out = dict(
        n_trials=len(recs),
        dir_acc=acc,
        dir_acc_decided=(float(np.mean([r["dir"] == r["want"] for r in decided]))
                         if decided else float("nan")),
        n_decided=len(decided),
        abstain_rate=(1.0 - len(decided) / len(trav)) if trav else float("nan"),
        dir_n=len(trav),
        undecidable=undec,
        lat_acc=float(np.mean([r["lat_ok"] for r in refl])) if refl else float("nan"),
        auc=_fit_auc(recs),
    )
    # amplitude-only ablation (the confounded variable): energy features only
    eidx = [i for i, nm in enumerate(ds.FEATURE_NAMES) if "energy" in nm]
    out["auc_energy_only"] = _fit_auc(recs, eidx)
    didx = [i for i, nm in enumerate(ds.FEATURE_NAMES)
            if any(k in nm for k in ("lag", "slope", "lin"))]
    out["auc_direction_only"] = _fit_auc(recs, didx)
    for g in (1, 2, 3, 4, 5):
        sub = [r["dir"] == r["want"] for r in trav if r["grade"] == g]
        out[f"dir_acc_g{g}"] = float(np.mean(sub)) if sub else float("nan")
    hi = [r["dir"] == r["want"] for r in trav if r["grade"] >= 3]
    lo = [r["dir"] == r["want"] for r in trav if r["grade"] <= 2]
    out["dir_acc_hi"] = float(np.mean(hi)) if hi else float("nan")
    out["dir_acc_lo"] = float(np.mean(lo)) if lo else float("nan")
    return out


def main():
    t0 = time.time()
    jobs = []
    for n in COUNTS:                                    # PRIMARY: electrode count
        for m in MOTION:
            for i in range(N_TRIAL):
                jobs.append((n, SPAN, m, 60, i, "primary", None))
    # Disjoint trial-index ranges per sweep. Previously SNRS contained 60 and
    # SPANS contained 12.0, so those jobs were byte-identical to primary-grid
    # jobs: one cell got 224 rows over 128 unique trials, over-weighting a plotted
    # point and putting exact duplicates on both sides of the CV split (which read
    # as "AUC peaks at the design SNR" when it was leakage).
    for g in (1, 2, 3, 4, 5):                           # grade tail, at N=8
        for m in (0.0,):
            for i in range(N_GRADE):
                jobs.append((8, SPAN, m, 60, 100_000 + g * 1000 + i, "grade", g))
    # AUC must be measured at each motion level. Previously one 4-class cell at
    # motion 0.3 was computed and written into EVERY motion key, so every
    # published motion-resolved AUC was the same number repeated.
    for n in COUNTS:                                    # AUC + ablation, 4 classes
        for m in MOTION:
            for i in range(N_AUC):
                jobs.append((n, SPAN, m, 60, 200_000 + i, "auc", None))
    for snr in SNRS:                                    # SNR, at N=8
        for i in range(N_SEC):
            jobs.append((8, SPAN, 0.6, snr, 300_000 + i, "snr", None))
    for sp in SPANS:                                    # span, at N=8
        for i in range(N_SEC):
            jobs.append((8, sp, 0.6, 60, 400_000 + i, "span", None))
    # Order jobs so each worker sees long runs of the same world, which keeps the
    # bounded cache hitting instead of rebuilding a CEM3D on every chunk.
    jobs.sort(key=lambda j: (j[0], j[1]))
    print(f"[run] {len(jobs)} trials", flush=True)

    nproc = int(os.environ.get('NPROC', '4'))
    recs = []
    with Pool(nproc, initializer=_init) as pool:
        for k, r in enumerate(pool.imap_unordered(_run_one, jobs, chunksize=4)):
            recs.append(r)
            if (k + 1) % 200 == 0:
                el = time.time() - t0
                print(f"[run] {k+1}/{len(jobs)}  {el/60:.1f} min  "
                      f"eta {(el/(k+1)*(len(jobs)-k-1))/60:.1f} min", flush=True)

    def sel(**kw):
        return [r for r in recs if all(r[k] == v for k, v in kw.items())]

    out = {"config": dict(model_version=ds.MODEL_VERSION, span=SPAN, counts=COUNTS, motion=MOTION, snrs=SNRS,
                          spans=SPANS, T=T, n_trial=N_TRIAL, n_grade=N_GRADE,
                          n_auc=N_AUC, n_sec=N_SEC, freqs=FREQS_USED,
                          feature_names=ds.FEATURE_NAMES,
                          primary_grades=[3, 4, 5], auc_n=8)}

    prim = {}
    for n in COUNTS:
        prim[str(n)] = {}
        for m in MOTION:
            sub = sel(n=n, span=SPAN, motion=m, snr=60, mode="primary")
            s = summarize(sub)
            a = sel(n=n, span=SPAN, motion=m, snr=60, mode="auc")
            s["auc"] = _fit_auc(a)
            eidx = [i for i, nm in enumerate(ds.FEATURE_NAMES) if "energy" in nm]
            didx = [i for i, nm in enumerate(ds.FEATURE_NAMES)
                    if any(k in nm for k in ("lag", "slope", "lin"))]
            s["auc_energy_only"] = _fit_auc(a, eidx)
            s["auc_direction_only"] = _fit_auc(a, didx)
            s["spacing"] = SPAN / max(n - 1, 1)
            s["zones_per_strip"] = sum(n - G for G in range(3, n, 2))
            s["channels"] = 2 * n
            prim[str(n)][str(m)] = s
    out["primary"] = prim

    out["grade_sweep"] = {str(g): {str(m): summarize(sel(n=8, span=SPAN, motion=m,
                                                        snr=60, mode="grade", grade=g))
                                   for m in (0.0,)}
                          for g in (1, 2, 3, 4, 5)}
    out["snr_sweep"] = {str(s): summarize(sel(n=8, span=SPAN, motion=0.6, snr=s,
                                              mode="snr")) for s in SNRS}
    out["span_sweep"] = {str(sp): summarize(sel(n=8, span=sp, motion=0.6, snr=60,
                                                mode="span")) for sp in SPANS}
    out["runtime_min"] = (time.time() - t0) / 60.0
    with open("metrics_directional.json", "w") as f:
        json.dump(out, f, indent=1)
    slim = [{k: r[k] for k in ("n", "span", "motion", "snr", "i", "mode", "label",
                               "grade", "side", "dir", "want", "strip", "ev", "lat_ok")}
            for r in recs]
    with open("records_directional.json", "w") as f:
        json.dump(slim, f)
    print(f"[run] done in {out['runtime_min']:.1f} min -> metrics_directional.json",
          flush=True)


if __name__ == "__main__":
    main()
