"""
Locked-design run: characterize the CHOSEN configuration end to end.

The electrode-count study answered "how many electrodes". This run stops sweeping
and instead characterizes the single configuration that study selected, at depth:

    6 electrodes per strip (12 channels)   <- best laterality, near-best direction
    14 cm span                             <- the strongest single lever measured
    tetrapolar Schlumberger zones, fractional dZ/|Z|
    60 dB instrument SNR                   <- 50 dB was already sufficient
    grade >= III as the claimed range

Three studies:
  A. OPERATING  - all four classes across a fine motion grid -> ROC, confusion,
                  calibration, operating points, evidence distributions.
  B. GRADE      - grades 1-5 across motion -> where the method works and stops.
  C. SUBJECT    - repeated events on the SAME simulated child (anatomy and
                  placement held fixed) -> tests whether multi-event detection
                  really compounds, which is the entire basis for beating VCUG.

Study C is the important one. The multi-event argument assumes events are
independent; if a child's anatomy or placement is what limits the measurement,
every event on that child fails together and no amount of repetition helps.

Outputs metrics_design.json and records_design.json
"""
import json, math, os, time
import numpy as np
from multiprocessing import Pool

import eit3d
import directional_sim as ds

# ---- the locked design -----------------------------------------------------
N_STRIP = 6
SPAN = 14.0
SNR = 60
T = 20
FREQ_KHZ = 50

MOTION = [0.0, 0.15, 0.30, 0.45, 0.60, 0.75, 0.90]
N_OP = 52          # per (class, motion) in study A
N_GRADE = 56       # per (grade, motion) in study B
N_SUBJ = 110       # subjects in study C
K_EVENTS = 6       # events observed per subject
SUBJ_MOTION = 0.45

_W = {}


def _init():
    global _MESH
    _MESH = eit3d.make_cylinder(R=5.5, height=20.0, n_rings=6, nz=17)


def _world():
    if "w" not in _W:
        _W["w"] = ds.StripWorld(N_STRIP, span=SPAN, mesh=_MESH)
    return _W["w"]


def _run_one(args):
    mode, motion, i, label, grade, side, seed, subj = args
    w = _world()
    anat = None
    if mode == "subject":
        # anatomy + placement fixed per subject; only noise and motion vary
        anat = ds.draw_anatomy(w, np.random.default_rng(500_000 + subj))
    dZ = ds.simulate_trial(w, label, np.random.default_rng(seed), grade=grade,
                           side=side, T=T, snr_db=SNR, motion_amp=motion, anat=anat)
    fv, feat = ds.feature_vector(dZ, w)
    d, s, ev = ds.decide_direction(feat)
    want = {"reflux": +1, "antegrade": -1}.get(label, 0)
    return dict(mode=mode, motion=motion, i=i, label=label, grade=grade, side=side,
                subj=subj, x=fv.tolist(), dir=int(d), want=int(want), strip=int(s),
                ev=float(ev), lat_ok=bool((s == 0) == (side > 0)),
                lin=float(feat[s].get("lin", 0.0)),
                m_ap=int(feat[s].get("m", 0)))


def _auc(y, sc):
    y = np.asarray(y, int); sc = np.asarray(sc, float)
    p, q = sc[y == 1], sc[y == 0]
    if len(p) == 0 or len(q) == 0:
        return float("nan")
    r = np.argsort(np.argsort(np.concatenate([p, q]))) + 1
    return float((r[:len(p)].sum() - len(p) * (len(p) + 1) / 2) / (len(p) * len(q)))


def _oof(recs, feat_idx=None, seed=0):
    """Out-of-fold reflux probability, elastic-net logistic regression."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import StratifiedKFold
    X = np.nan_to_num(np.array([r["x"] for r in recs], float))
    if feat_idx is not None:
        X = X[:, feat_idx]
    y = np.array([r["label"] == "reflux" for r in recs], int)
    if y.sum() < 5 or (1 - y).sum() < 5:
        return y, np.zeros(len(y))
    oof = np.zeros(len(y))
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=seed).split(X, y):
        clf = make_pipeline(StandardScaler(),
                            LogisticRegression(penalty="elasticnet", l1_ratio=0.5,
                                               C=1.0, solver="saga", max_iter=4000))
        clf.fit(X[tr], y[tr])
        oof[te] = clf.predict_proba(X[te])[:, 1]
    return y, oof


def roc_points(y, sc):
    o = np.argsort(-np.asarray(sc, float))
    y = np.asarray(y, int)[o]
    tp = np.cumsum(y); fp = np.cumsum(1 - y)
    P, Nn = max(int(y.sum()), 1), max(int((1 - y).sum()), 1)
    return ([0.0] + (fp / Nn).tolist(), [0.0] + (tp / P).tolist())


def wilson(p, n, z=1.96):
    if n <= 0 or p != p:
        return (float("nan"), float("nan"))
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main():
    t0 = time.time()
    jobs = []
    # ---- A. operating: four classes across the motion grid
    for m in MOTION:
        for i in range(N_OP * 4):
            rng = np.random.default_rng(700_000 + i)
            label = ds.CLASSES[i % 4]
            grade = int(rng.choice([3, 4, 5]))
            side = +1 if rng.random() < 0.5 else -1
            jobs.append(("op", m, i, label, grade, side, 700_000 + i, -1))
    # ---- B. grade: travelling events at each grade
    for g in (1, 2, 3, 4, 5):
        for m in (0.0, 0.30, 0.60, 0.90):
            for i in range(N_GRADE):
                rng = np.random.default_rng(800_000 + g * 10_000 + i)
                label = "reflux" if i % 2 == 0 else "antegrade"
                side = +1 if rng.random() < 0.5 else -1
                jobs.append(("grade", m, i, label, g, side,
                             800_000 + g * 10_000 + i, -1))
    # ---- C. subject: K events per subject, anatomy + placement FIXED
    for c in range(N_SUBJ):
        refluxer = (c % 2 == 0)
        side = +1 if (c // 2) % 2 == 0 else -1
        grade = int(np.random.default_rng(900_000 + c).choice([3, 4, 5]))
        for k in range(K_EVENTS):
            label = "reflux" if refluxer else "antegrade"
            jobs.append(("subject", SUBJ_MOTION, k, label, grade, side,
                         900_000 + c * 100 + k, c))
    print(f"[design] {len(jobs)} trials  (N={N_STRIP}, span={SPAN} cm, SNR={SNR} dB)",
          flush=True)

    nproc = max(1, min(6, (os.cpu_count() or 4) - 2))
    recs = []
    with Pool(nproc, initializer=_init) as pool:
        for k, r in enumerate(pool.imap_unordered(_run_one, jobs, chunksize=4)):
            recs.append(r)
            if (k + 1) % 200 == 0:
                el = time.time() - t0
                print(f"[design] {k+1}/{len(jobs)}  {el/60:.1f} min  "
                      f"eta {(el/(k+1)*(len(jobs)-k-1))/60:.1f} min", flush=True)

    out = {"config": dict(n_strip=N_STRIP, span=SPAN, snr=SNR, T=T,
                          channels=2 * N_STRIP, motion=MOTION, n_op=N_OP,
                          n_grade=N_GRADE, n_subj=N_SUBJ, k_events=K_EVENTS,
                          subj_motion=SUBJ_MOTION, freq_khz=FREQ_KHZ,
                          feature_names=ds.FEATURE_NAMES)}

    # ---------------- A. operating characteristics ----------------
    op = {}
    for m in MOTION:
        sub = [r for r in recs if r["mode"] == "op" and r["motion"] == m]
        y, sc = _oof(sub)
        fpr, tpr = roc_points(y, sc)
        trav = [r for r in sub if r["want"] != 0]
        refl = [r for r in sub if r["label"] == "reflux"]
        dacc = float(np.mean([r["dir"] == r["want"] for r in trav])) if trav else float("nan")
        # operating points at fixed specificity
        ops = {}
        for spec_t in (0.80, 0.85, 0.90, 0.95):
            neg = np.sort(sc[y == 0])
            if len(neg):
                thr = neg[min(int(spec_t * len(neg)), len(neg) - 1)]
                ops[str(spec_t)] = float(np.mean(sc[y == 1] >= thr))
        op[str(m)] = dict(auc=_auc(y, sc), roc_fpr=fpr, roc_tpr=tpr,
                          dir_acc=dacc, dir_n=len(trav),
                          dir_ci=wilson(dacc, len(trav)),
                          lat_acc=float(np.mean([r["lat_ok"] for r in refl])) if refl else float("nan"),
                          lat_n=len(refl), sens_at_spec=ops,
                          scores=sc.tolist(), labels=y.tolist(),
                          ev_reflux=[r["ev"] for r in sub if r["label"] == "reflux"],
                          ev_antegrade=[r["ev"] for r in sub if r["label"] == "antegrade"],
                          lin_reflux=[r["lin"] for r in sub if r["label"] == "reflux"],
                          lin_noflow=[r["lin"] for r in sub if r["label"] == "noflow"])
    out["operating"] = op

    # 4-class confusion at the design motion, using direction + strip
    mid = MOTION[len(MOTION) // 2]
    sub = [r for r in recs if r["mode"] == "op" and r["motion"] == mid]
    y, sc = _oof(sub)
    thr = float(np.median(sc))
    conf = {}
    for r, p in zip(sub, sc):
        pred = "reflux" if p >= thr else ("antegrade" if r["dir"] < 0 else "not-reflux")
        conf.setdefault(r["label"], {}).setdefault(pred, 0)
        conf[r["label"]][pred] += 1
    out["confusion"] = {"motion": mid, "counts": conf}

    # feature ablation at the design motion
    eidx = [i for i, nm in enumerate(ds.FEATURE_NAMES) if "energy" in nm]
    didx = [i for i, nm in enumerate(ds.FEATURE_NAMES)
            if any(k in nm for k in ("lag", "slope", "lin"))]
    ya, sa = _oof(sub, eidx); yb, sb = _oof(sub, didx)
    out["ablation"] = {"motion": mid, "full": _auc(y, sc),
                       "amplitude_only": _auc(ya, sa), "direction_only": _auc(yb, sb)}

    # ---------------- B. grade ----------------
    gr = {}
    for g in (1, 2, 3, 4, 5):
        gr[str(g)] = {}
        for m in (0.0, 0.30, 0.60, 0.90):
            sub = [r for r in recs if r["mode"] == "grade" and r["grade"] == g
                   and r["motion"] == m and r["want"] != 0]
            a = float(np.mean([r["dir"] == r["want"] for r in sub])) if sub else float("nan")
            gr[str(g)][str(m)] = dict(dir_acc=a, n=len(sub), ci=wilson(a, len(sub)))
    out["grade"] = gr

    # ---------------- C. subject-level multi-event ----------------
    subs = {}
    for r in recs:
        if r["mode"] == "subject":
            subs.setdefault(r["subj"], []).append(r)
    per_event, per_subject = [], []
    for c, evs in sorted(subs.items()):
        evs = sorted(evs, key=lambda r: r["i"])
        hits = [int(r["dir"] == r["want"]) for r in evs]
        per_event += hits
        per_subject.append(dict(subj=c, label=evs[0]["label"], grade=evs[0]["grade"],
                                hits=hits, n_hit=int(sum(hits))))
    pe = float(np.mean(per_event)) if per_event else float("nan")
    # k-of-K detection measured EMPIRICALLY, versus what independence would predict
    emp, ind = {}, {}
    for kk in range(1, K_EVENTS + 1):
        emp[str(kk)] = float(np.mean([s["n_hit"] >= kk for s in per_subject]))
        ind[str(kk)] = float(sum(
            math.comb(K_EVENTS, j) * pe ** j * (1 - pe) ** (K_EVENTS - j)
            for j in range(kk, K_EVENTS + 1))) if pe == pe else float("nan")
    hits_hist = [0] * (K_EVENTS + 1)
    for s in per_subject:
        hits_hist[s["n_hit"]] += 1
    out["subject"] = dict(per_event=pe, n_subjects=len(per_subject),
                          k_events=K_EVENTS, motion=SUBJ_MOTION,
                          empirical_k_of_K=emp, independent_k_of_K=ind,
                          hits_hist=hits_hist,
                          per_subject=[{k: s[k] for k in ("subj", "label", "grade", "n_hit")}
                                       for s in per_subject])

    out["runtime_min"] = (time.time() - t0) / 60.0
    with open("metrics_design.json", "w") as f:
        json.dump(out, f)
    slim = [{k: r[k] for k in ("mode", "motion", "i", "label", "grade", "side",
                               "subj", "dir", "want", "strip", "ev", "lat_ok",
                               "lin", "m_ap")} for r in recs]
    with open("records_design.json", "w") as f:
        json.dump(slim, f)
    print(f"[design] done in {out['runtime_min']:.1f} min -> metrics_design.json",
          flush=True)


if __name__ == "__main__":
    main()
