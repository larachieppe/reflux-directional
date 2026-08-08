"""
Every number, table and figure the report displays, resolved from the metrics
files the studies actually wrote.

This exists so the PROSE and the DATA can live apart. The prose is Markdown in
report/*.md and is edited by hand; the data is here and is regenerated whenever a
study re-runs. Nothing in report/*.md is ever a typed-in number: it refers to a
value by name, and if the underlying study changes the report changes with it.

Placeholders understood in the Markdown:
    {{val:name}}            a single formatted value
    {{table:name}}          a complete table, header included
    {{fig:path|caption}}    a figure, embedded as base64
    {{methods:study}}       the Materials & Methods block for a study
    {{technical}}           the whole technical-foundations chapter
    {{defects}}             the defect log table
"""
import base64, json, os

import build_methods as bm
import build_technical as bt

# ------------------------------------------------------------------ metrics
def _load(p):
    return json.load(open(p)) if os.path.exists(p) else None


D = _load("metrics_design.json")
E = _load("metrics_directional.json")
P = _load("metrics_placement.json")
T = _load("metrics_tolerance.json")
PR = _load("metrics_precision.json")
M2 = _load("metrics_motion2.json")
VF = _load("metrics_verify.json")
OLD_E = _load("baseline_prefix/metrics_directional.json")
OLD_D = _load("baseline_prefix/metrics_design.json")
# alternative placements, characterised after Study 5 questioned the published one
ALT = {k: _load(f"metrics_design_{k}.json")
       for k in ("uvj", "z28", "12z30")}
ALT = {k: v for k, v in ALT.items() if v}

C = D["config"]; OP = D["operating"]; S = D["subject"]; G = D["grade"]; AB = D["ablation"]
EP = E["primary"]; EC = E["config"]; ECOUNTS = EC["counts"]
PG = P["grid"]; BEST = P["best_low_grade"]
MOT = C["motion"]; K = S["k_events"]; BK = str(S["best_k"])


# ------------------------------------------------------------------ format
def p0(x, d=0):
    return "n/a" if x is None or x != x else f"{100*x:.{d}f}%"


def n2(x):
    return "n/a" if x is None or x != x else f"{x:.2f}"


def ed(M, n, m):
    d = M["primary"][str(n)][str(m)]
    return float("nan") if d.get("undecidable", 0) > 0.99 else d["dir_acc"]


def _dec(n, m, k):
    return EP[str(n)][str(m)].get(k, float("nan"))


def figure(path, cap, width=700):
    if not os.path.exists(path):
        return f"<!-- missing figure: {path} -->"
    b = base64.b64encode(open(path, "rb").read()).decode()
    return (f'<p style="text-align:center;margin:18px 0 4px">'
            f'<img src="data:image/png;base64,{b}" width="{width}"></p>'
            f'<p class="cap">{cap}</p>')


# ------------------------------------------------------------------ values
def _gm(g, i):
    """mean over motion amplitudes of (false_retrograde, dir_acc) at gradient g"""
    if not M2:
        return float("nan")
    amps = M2["config"]["amps"]
    key = "false_retrograde" if i == 0 else "dir_acc"
    v = [M2["grid"][f"a{a}_g{g}"][key] for a in amps]
    return sum(v) / len(v)


def _defno(prefix):
    """1-based index of a defect in the log, looked up by title prefix."""
    for i, d in enumerate(DEFECTS, 1):
        if d[0].startswith(prefix):
            return i
    return "?"


VALS = {
    "n_strip":            lambda: C["n_strip"],
    "channels":           lambda: C["channels"],
    "span":               lambda: f"{C['span']:.0f}",
    "snr":                lambda: C["snr"],
    "freq_khz":           lambda: C["freq_khz"],
    "k_events":           lambda: K,
    "n_subjects":         lambda: S["n_reflux"] + S["n_healthy"],
    "per_event_sens":     lambda: p0(S["per_event_sens"]),
    "per_event_fp":       lambda: p0(S["per_event_fp"]),
    "ablation_direction": lambda: n2(AB["direction_only"]),
    "ablation_amplitude": lambda: n2(AB["amplitude_only"]),
    "tolerance_span":     lambda: f"{T['config']['span'] if T else 10:.0f}",
    # verification
    "recip_err":          lambda: f"{VF['v2_reciprocity']['max_rel_error']:.2e}",
    "recip_err_1":        lambda: f"{VF['v2_reciprocity']['max_rel_error']:.1e}",
    "recip_pairs":        lambda: VF["v2_reciprocity"]["n_pairs"],
    "tetra_spread":       lambda: f"{VF['v4_contact_immunity']['tetrapolar_rel_spread_modelled_range']:.4f}",
    "bipolar_spread":     lambda: f"{VF['v4_contact_immunity']['bipolar_rel_spread_modelled_range']:.4f}",
    "rejection_factor":   lambda: f"{VF['v4_contact_immunity']['rejection_factor_modelled_range']:.1f}",
    # study 6
    "m2_fr_rigid":        lambda: p0(_gm(0.0, 0), 1),
    "m2_fr_half":         lambda: p0(_gm(0.5, 0), 1),
    "m2_fr_full":         lambda: p0(_gm(1.0, 0), 1),
    "m2_acc_rigid":       lambda: p0(_gm(0.0, 1), 1),
    "m2_acc_half":        lambda: p0(_gm(0.5, 1), 1),
    "m2_acc_full":        lambda: p0(_gm(1.0, 1), 1),
    "m2_fr_zero_motion":  lambda: p0(M2["grid"]["a0.0_g0.0"]["false_retrograde"], 1),
    "m2_1cm_decided":     lambda: p0(M2["grid"]["a1.0_g1.0"]["dir_acc_decided"]),
    "m2_1cm_abstain":     lambda: p0(M2["grid"]["a1.0_g1.0"]["trav_abstain"]),
    # Counted from the log itself. The prose used to state these by hand and had
    # already drifted twice -- the front matter said fifteen while the table
    # listed sixteen, and the defect-log paragraph said fourteen.
    # Defect numbers cited in prose must be DERIVED, not typed. Hard-coding them
    # is how defect 48 happened, and the first draft of the paragraph that
    # describes defect 48 got its own cross-references off by one.
    "defno_mesh":         lambda: _defno("The mesh was non-conforming"),
    "defno_electrode":    lambda: _defno("Two thirds of every electrode"),
    "defno_fat":          lambda: _defno("Motion slid the fat layer"),
    "defno_gate":         lambda: _defno("Abstain gate statistic"),
    "n_defects":          lambda: len(DEFECTS),
    # DEFECT 42: this counted everything that was not "reporting" and the prose
    # described the remainder as "the model, the estimator or the statistics" --
    # but the log also carries "physics", "tooling" and "estimator" classes, so the
    # sentence named three categories while the number counted six.
    "n_defects_code":     lambda: sum(1 for d in DEFECTS
                                      if d[1] in ("model", "estimator", "stats")),
    "n_defects_other":    lambda: sum(1 for d in DEFECTS
                                      if d[1] in ("physics", "tooling")),
    "n_defects_reporting": lambda: sum(1 for d in DEFECTS if d[1] == "reporting"),
}


# ------------------------------------------------------------------ tables
def _t(head, rows):
    return f"<table>{head}{rows}</table>"


def _rows_count():
    return "\n".join(
        f"<tr{' class=hi' if n == 8 else (' class=bad' if n == 5 else '')}>"
        f"<td>N = {n}</td><td>{2*n}</td><td>{p0(ed(E,n,0.3))}</td>"
        f"<td>{p0(ed(E,n,0.6))}</td>"
        f"<td><b>{p0(_dec(n,0.6,'dir_acc_decided'))}</b></td>"
        f"<td>{p0(_dec(n,0.6,'abstain_rate'))}</td>"
        f"<td>{p0(EP[str(n)]['0.6']['lat_acc'])}</td></tr>" for n in ECOUNTS)


def _rows_design():
    return "\n".join(
        f"<tr><td>{m:.2f} cm</td>"
        f"<td>{p0(OLD_D['operating'].get(str(m),{}).get('dir_acc'))} &rarr; "
        f"<b>{p0(OP[str(m)]['dir_acc'])}</b></td>"
        f"<td>{p0(OP[str(m)]['lat_acc'])}</td><td>{n2(OP[str(m)]['auc'])}</td>"
        f"<td>{p0(OP[str(m)].get('abstain_rate'))}</td></tr>" for m in MOT)


def _rows_k():
    return "\n".join(
        f"<tr{' class=hi' if str(k)==BK else ''}><td>&ge; {k} of {K}</td>"
        f"<td><b>{p0(S['sens_k'][str(k)])}</b></td>"
        f"<td><b>{p0(S['spec_k'][str(k)])}</b></td>"
        f"<td>{p0(S['chance_k'][str(k)])}</td></tr>" for k in range(1, K + 1))


def _best_key():
    """Grid key of the CURRENT best placement, read from the study output.

    DEFECT 41: this was hard-coded to '10_0.28', so the only visual
    recommendation cue in the placement table kept green-highlighting a
    placement the project had already withdrawn as chosen by a gameable
    one-sided metric.
    """
    try:
        b = P["best_low_grade"]
        return f"{b['span']:.0f}_{b['z_center']:.2f}"
    except Exception:
        return ""


def _rows_place():
    pk = sorted(PG, key=lambda k: -(PG[k]["g1_m0.0"]["reflux_acc"]
                                    if PG[k]["g1_m0.0"]["reflux_acc"] ==
                                    PG[k]["g1_m0.0"]["reflux_acc"] else 0))
    return "\n".join(
        f"<tr{' class=hi' if k == _best_key() else (' class=bad' if k == '16_0.50' else '')}>"
        f"<td>{PG[k]['span']:.0f} cm @ z={PG[k]['z_center']:.2f}</td>"
        f"<td>{PG[k]['g1_m0.0']['zones_crossed']}</td>"
        + "".join(f"<td>{p0(PG[k][f'g{g}_m0.0']['reflux_acc'])}</td>" for g in (1, 2, 3, 4, 5))
        + "</tr>" for k in pk)


def _rows_tol():
    if not T:
        return ""
    TG = T["grid"]
    return "\n".join(
        f"<tr{' class=hi' if o == 0.0 else ''}><td>{o:+.0f} cm</td>"
        + "".join(f"<td>{p0(TG[f'{o:+.0f}'][f'g{g}_m0.0']['reflux_acc'])}</td>"
                  for g in (1, 2, 3, 4, 5))
        + f"<td>{p0(TG[f'{o:+.0f}']['low_grade_still']['abstain'])}</td></tr>"
        for o in T["config"]["offsets_cm"])


def _rows_verify():
    if not VF:
        return ""
    fin = VF["v3_mesh_convergence"]["levels"][-1]["n_nodes"]
    return "".join(
        f"<tr{' class=hi' if L['n_nodes'] == fin else ''}>"
        f"<td>{L['n_rings']} / {L['nz']}</td><td>{L['n_nodes']:,}</td><td>{L['n_tets']:,}</td>"
        f"<td>{L['mean_absZ']:.4g}</td><td>{100*L['absZ_rel_to_finest']:.1f}%</td>"
        f"<td>{L['slope']:+.4g}</td><td>{100*L['slope_rel_to_finest']:.2f}%</td>"
        f"<td>{'reflux' if L['decision'] > 0 else ('antegrade' if L['decision'] < 0 else 'abstain')}</td>"
        f"</tr>" for L in VF["v3_mesh_convergence"]["levels"])


def _rows_prec():
    if not PR:
        return ""
    out = ""
    for k, v in sorted(PR["grid"].items(), key=lambda t: (t[1]["span"], t[1]["sigma"])):
        cls = " class=hi" if v["span"] == 10.0 else (" class=bad" if v["low_grade_never"] > 0.35 else "")
        out += (f"<tr{cls}><td>{v['span']:.0f} cm @ z={v['z_center']:.2f}</td>"
                f"<td>{v['sigma']:.1f} cm</td>"
                f"<td>&ge;{v['best_k']} of {PR['config']['k_events']}</td>"
                f"<td>{p0(v['best_sens'])}</td><td>{p0(v['best_spec'])}</td>"
                f"<td>{p0(v['never_detected'])}</td><td>{p0(v['low_grade_never'])}</td></tr>")
    return out


def _rows_m2():
    if not M2:
        return ""
    G2, C2 = M2["grid"], M2["config"]
    out = ""
    for a in C2["amps"]:
        cells = ""
        for g in C2["grads"]:
            v = G2[f"a{a}_g{g}"]
            cells += (f"<td>{p0(v['dir_acc'])}</td><td>{p0(v['dir_acc_decided'])}</td>"
                      f"<td>{p0(v['trav_abstain'])}</td>")
        cls = " class=hi" if a <= 1.0 else (" class=bad" if a >= 3.0 else "")
        out += f"<tr{cls}><td>{a:.1f} cm</td>{cells}</tr>"
    return out


def _rows_m2fr():
    if not M2:
        return ""
    return "".join(
        f"<tr><td>{a:.1f} cm</td>" + "".join(
            f"<td>{p0(M2['grid'][f'a{a}_g{g}']['false_retrograde'],1)}</td>"
            for g in M2["config"]["grads"]) + "</tr>"
        for a in M2["config"]["amps"])


def _rows_auc():
    """Published classifier AUC beside the honest direction-rule AUC."""
    A = _load("metrics_auc_corrected.json")
    if not A:
        return ""
    out = ""
    for n in ECOUNTS:
        for m in EC["motion"]:
            v = A.get(f"{n}_{m}")
            if not v:
                continue
            cls = " class=bad" if n == 4 else (" class=hi" if n == 8 else "")
            ci = v["classifier_ci"]; rci = v["rule_ci"]
            out += (f"<tr{cls}><td>N = {n}</td><td>{m}</td>"
                    f"<td>{v['classifier']:.3f}<br>"
                    f"<span class='sub'>[{ci[0]:.2f}, {ci[1]:.2f}]</span></td>"
                    f"<td>{v['energy_only']:.3f}</td>"
                    f"<td>{v['direction_only']:.3f}</td>"
                    f"<td><b>{v['rule']:.3f}</b><br>"
                    f"<span class='sub'>[{rci[0]:.2f}, {rci[1]:.2f}]</span></td></tr>")
    return out


def _rows_altdesign():
    """Locked design characterised at each placement that has been run."""
    names = {"metrics_design.json": ("16 cm @ z=0.50", "published"),
             "uvj": ("10 cm @ z=0.34", "Study 3 pick, still-only rule"),
             "z28": ("10 cm @ z=0.28", "Study 3 pick, motion-aware rule"),
             "12z30": ("12 cm @ z=0.30", "lever-arm compromise")}
    out = ""
    for key, src in [("metrics_design.json", D)] + [(k, v) for k, v in ALT.items()]:
        label, note = names.get(key, (key, ""))
        cls = " class=bad" if key == "metrics_design.json" else ""
        g2 = src["grade"]["2"]["0.0"]["dir_acc"]
        g1 = src["grade"]["1"]["0.0"]["dir_acc"]
        out += (f"<tr{cls}><td>{label}<br><span class='sub'>{note}</span></td>"
                f"<td>{p0(g1)}</td><td>{p0(g2)}</td>"
                f"<td>{n2(src['operating']['0.0']['auc'])}</td>"
                f"<td>{n2(src['operating']['0.45']['auc'])}</td>"
                f"<td>{n2(src['operating']['0.9']['auc'])}</td>"
                f"<td>{p0(src['subject']['best_sens'])}</td>"
                f"<td>{p0(src['subject']['best_spec'])}</td></tr>")
    return out


DEFECTS = [
 ("Magnitude before common-mode removal", "estimator", "Taking |dZ| before subtracting the across-zone mean is nonlinear, so the common mode could never cancel.", "Direction sat at chance."),
 ("Aperture chosen by total energy", "estimator", "Total energy favours apertures with more zones, which are the shallowest.", "Systematically selected the aperture that cannot reach the ureter."),
 ("Amplitude envelope on the bolus", "model", "Gave every zone the same time course, so responses were separable as amplitude x one shared envelope.", "Erased the travelling wave the device measures."),
 ("Temporal median as baseline", "model", "The bolus passes every zone, so the median sits mid-event.", "Scrambled each clean passage into a bipolar trace."),
 ("Lag search clipped to n/3", "estimator", "Real lags spanned ~11 samples; the search was bounded at 6.", "Truncated genuine signal. Self-inflicted while fixing something else."),
 ("Contact impedance ~100x too low", "model", "Electrodes acted as near-ideal shunts.", "Suppressed the signal ~100x while amplifying drift sensitivity."),
 ("Unequal electrode area between strips", "physics", "An odd interior mesh ring broke mirror symmetry; one strip got 23% less area.", "Laterality was a degenerate always-one-side predictor, not a degrading one."),
 ("Duplicate trials across CV folds", "stats", "SNR and span sweeps re-emitted primary-grid trials verbatim.", "Manufactured an AUC peak exactly at the design SNR and span."),
 ("Multi-event metric pooled healthy and refluxing children", "stats", "Counted a correct negative as a 'hit'.", "Chance floor of 89% sat ABOVE the 80% VCUG line being compared against."),
 ("Confusion matrix thresholded at the median", "stats", "Forces 50% predicted-positive against 25% prevalence.", "Capped specificity at 66.7% by construction."),
 ("AUC computed once and copied", "stats", "One motion cell written into every motion key.", "Every motion-resolved AUC published was the same number."),
 ("z_center never forwarded", "physics", "StripWorld accepted it but never passed it to place_strips.", "Every strip in every study sat on the torso midpoint by default. Caused the 'grades I-II are undetectable' claim."),
 ("Electrodes sharing boundary facets", "physics", "A fixed z window exceeded half-pitch at N=12.", "44 shared facets welded electrodes together; that array was not physically realizable."),
 ("Noise added to a normalized quantity", "model", "Derived from raw |Z| but added to fractional dZ.", "Injected noise depended on the choice of length unit and sat ~10 dB low."),
 ("Abstention scored as a wrong answer", "stats", "dir_acc penalised abstention, but the abstain gate needs >=3 zones, so N=5 was structurally exempt from it.", "Made N=5 appear to beat N=8 under motion (79% vs 71%). On calls actually made, N=8 leads 93% to 79%. Same failure mode as defect 9: a pooled metric flattering the wrong option."),
 ("Placement chosen on the still arm only", "stats", "run_placement scored candidate placements by low-grade accuracy at motion 0.0, discarding the motion arm the same study had just measured.", "Selected 10 cm @ z=0.34 (92.9%/100% still, but 50.0% on grade I under motion) over 10 cm @ z=0.28 (equal still, 78.6% under motion). Propagated into Study 4, which centred its offsets on it, and Study 5, which adopted it as the short-strip arm."),
 ("Reciprocity described as assumption-free", "reporting", "The CEM system matrix is complex symmetric by construction, so reciprocity is an algebraic identity for an exact solve rather than an independent check of the physics.", "Overstated what the verification proved. Any error entering symmetrically -- wrong electrode area, wrong tissue value, mis-meshed geometry -- passes the test untouched."),
 ("Contact impedance said to 'largely drop out'", "reporting", "Measured tetrapolar rejection over the modelled z0 range is 4.3x, a 16% residual.", "Overstated tetrapolar immunity. The four-wire geometry is still right, but the residual has to be budgeted for in hardware."),
 ("Motion gradient confounded with motion amplitude", "model", "The displacement weight was w = (1-grad) + grad*(z/H). Since z/H spans 0..1, that weight has MEAN 0.50 at grad=1 and 0.75 at grad=0.5, so the gradient arms applied HALF and THREE-QUARTERS of the rigid arm's displacement rather than the same displacement redistributed.", "Invalidates Study 6's headline. The gradient arms were handed strictly less total motion, and Study 6's own finding is that AMPLITUDE is what degrades accuracy -- which is very likely why they scored slightly BETTER and why 'the gradient hypothesis is refuted' looked so clean. Fixed with a mean-preserving weight; re-running."),
 ("AUC measured a trained classifier, not the direction rule", "stats", "_fit_auc fits an elastic-net logistic regression over the WHOLE feature vector with 5-fold CV. N=4 abstains on 100% of trials with dir_acc = NaN yet reports AUC 0.852 -- identical to three decimals to its energy-only ablation at every motion level (0.852/0.720/0.449/0.260).", "Every 'the design achieves AUC x' statement described a learned classifier running largely on amplitude, reproducing the exact failure mode the project claims to avoid. The honest direction-rule AUC, scored as signed evidence with no model fitted, puts N=4 at 0.500 -- chance."),
 ("AUC published without confidence intervals", "stats", "Each AUC cell rests on N_AUC = 64 four-class trials, about 16 reflux against 48 rest. Hanley-McNeil gives a 95% interval of +/-0.10 to +/-0.16.", "The entire spread across electrode counts (0.852 to 0.979) fits inside a single cell's interval, so no between-count AUC comparison in Study 1 was ever meaningful. N=4 at motion 0.9 reads AUC 0.260, significantly BELOW chance even at this precision -- an out-of-fold model that inverts, i.e. small-n overfitting."),
 ("Alternative-placement runs overwrote the published records", "tooling", "run_design.py took its metrics path from the environment but wrote records_design.json to a hard-coded name, so each re-cut placement silently replaced the published 16 cm run's record-level data.", "The published run's per-trial records were destroyed and had to be recovered from git. Record paths now derive from the metrics path."),
 ("Placement error clipped asymmetrically between arms", "stats", "The drawn offset was limited only by keeping the strip on the body, and that limit depends on span: a 16 cm strip in a 20 cm torso can move only +/-1.9 cm, while a 10 cm strip at z=0.34 can move -1.7/+8.1 cm.", "Invalidates Study 5's central comparison. The two arms were never exposed to the same placement-error distribution, and at sigma = 2.0 the long strip was quietly protected from the large misplacements the short strip had to absorb. Both arms now clip to the same limit, and the REALIZED offset is recorded rather than the pre-clip draw."),
 ("Abstentions counted as false positives", "stats", "subject_analysis inferred false alarms on healthy children as (K - n_hit), i.e. every event not correctly called antegrade -- a set that includes every ABSTENTION -- while its own docstring said 'events wrongly read as retrograde'.", "Understated specificity everywhere it was used, by up to the abstention rate, which reaches 50% under motion. A device that declines to answer has not raised a false alarm. Callers now pass the retrograde-call count explicitly, and any run that cannot is flagged in its own output."),
 ("k-of-n threshold selected on the evaluation data", "stats", "best_k is chosen by maximum Youden index on the same children it is then scored on, with no held-out set and no interval.", "best_sens and best_spec are optimistically biased and are not out-of-sample estimates. A pre-specified k is now reported beside them so the two placements are compared on a fixed rule."),
 ("Placement selected on a one-sided metric", "stats", "run_placement scored candidates on reflux_acc, which counts REFLUX TRIALS ONLY. A detector that answers 'reflux' every time scores 100% on it. Balanced accuracy (dir_acc) scores both classes and cannot be gamed this way.", "The rule rewarded exactly the failure it should punish. It selected 10 cm @ z=0.28, which scores 87.5% one-sided but only 37.5% on antegrade trials -- below chance on healthy children -- for a balanced accuracy of 62.5%, fifth of ten. On balanced accuracy the optimum is 12 cm @ z=0.36 (74.1%, antegrade 78.6%). Studies 4 and 5 were both centred on placements chosen by the broken rule."),
 ("The published 95% CI annotated a different statistic", "reporting", "build_site printed the Wilson interval of `combined` -- a mean of direction AND laterality accuracy over motion 0.0 and 0.3 -- immediately beside direction accuracy at 0.9 cm, under a header reading '95% CI'. The denominator was also the single-motion direction n.", "Not one of the five published intervals contained the number it annotated. The N=8 row read, verbatim, '47%  95-100%'. The figure used the correct per-panel n, so the figure and the table disagreed."),
 ("The 'why N was chosen' figure chose a different N", "reporting", "figC ran its own selection rule at the WORST motion level (0.9 cm) and annotated N=6 as 'chosen', while build_site selected N=8 at the 0.3 cm design target. Both were published in the same section, the figure sitting directly under the 'N = 8 recommended' card.", "The stated basis for locking N=8 -- the configuration carried into every later study -- was contradicted by the figure printed beneath it."),
 ("AUC plotted against a 0.5 chance line", "stats", "Reflux is scored against an equal mix of noflow, antegrade and bladder, and two of those three contain no travelling bolus at all. A pure bolus-presence detector with zero directional skill therefore scores (1 + 1 + 0.5)/3 = 0.833.", "Everything between 0.5 and 0.833 is dead scale. Drawing the floor at 0.5 made an amplitude-only classifier look skilful: N=4, which cannot fit a slope at all, measures 0.852 -- barely above the no-direction floor, but presented as strong performance."),
 ("Grade changed bolus SPEED as well as size", "model", "Every path was traversed in exactly T frames regardless of length, and the reflux path length depends on grade through `reach`. Grade I covered 7.2 cm in the same 20 frames grade V used for 16.8 cm, a 2.33x velocity difference. The antegrade path ignored grade entirely and always ran the full 16.8 cm.", "The estimator's entire output is an arrival-time slope, and slope is inversely proportional to velocity, so grade was confounded with the measured quantity. 'Low grades are hard' could not be separated from 'slow boluses are hard'. And at grade I a reflux trial was a short slow bolus while its matched antegrade trial was a long fast one, so the two classes differed in extent and speed rather than only in direction. Fixed by holding velocity constant and letting grade set only how far the bolus travels."),
 ("Frequency override was a no-op", "model", "run_directional set `ds.FREQS = ds.FREQS[:1]` with the comment \"50 kHz only: halves solves\". simulate_trial binds `freqs=FREQS` as a DEFAULT ARGUMENT at definition time, so rebinding the module attribute afterwards never reached the solver.", "Study 1 has always run at BOTH 50 and 100 kHz, took twice the compute the comment claimed to save, and recorded freqs=[50000.0] in its own config -- a figure that was false and that the report quoted. The config now records what the solver actually used."),
 ("Laterality credited on trials with no call", "stats", "lat_acc is the mean of `lat_ok = (strip == 0) == (side > 0)` over reflux trials, computed whether or not the estimator abstained. A strip is always selected, by energy, even when no direction is reported.", "Laterality is scored on trials where the device output nothing, and it is an amplitude statistic rather than a directional one. At N=4, which abstains on 100% of trials, laterality still reads 100%."),
 ("breath_hz is a dead parameter", "model", "simulate_trial accepts breath_hz=0.30 but calls draw_motion(world, rng, T, motion_amp) without it. draw_motion hardcodes its own value, so the parameter has never influenced a single trial and no caller has ever set it.", "The breathing rate is not configurable and was never swept, while the report and the methods both described it as a model parameter. Distinct from the frequency no-op: a different parameter, a different function, and here the value is simply unreachable rather than shadowed by a bound default."),
 ("The breathing rate is not a rate", "model", "The term is sin(2*pi*0.30*t/4.0) with t indexed in FRAMES, giving 0.075 cycles per frame, and NO frame rate, timestep or trial duration is defined anywhere in the model. Over T=20 frames the trial contains 1.5 breathing cycles.", "The published figure of 0.30 Hz is unsupported -- it is a bare constant divided by 4, not a frequency. If a void is taken to be about 20 s, the modelled breathing is roughly 4.5 breaths per minute, some five times slower than a child at 20-30. Since Study 6 is entirely about respiratory motion, its stimulus may be far gentler than physiology."),
 ("Injected noise exceeds the stated SNR by ~1 dB", "model", "simulate_trial adds an independent term at sigma_n = 10^(-SNR/20) AND a zone-correlated term at 0.5*sigma_n. The real part therefore carries sqrt(1 + 0.25)*sigma_n = 1.118*sigma_n.", "Every SNR label is optimistic by 0.97 dB: the 60 dB arm actually runs at 59.03 dB. Small, but systematic across the whole SNR sweep, and it means the noise budget quoted for hardware is not the noise budget simulated. Distinct from the earlier defect where noise was derived from raw |Z| and added to a fractional quantity; this is the variance bookkeeping of the two components."),
 ('The mesh was non-conforming', 'physics', 'make_cylinder ran a 3-D Delaunay over a structured, massively cospherical point cloud, then deleted the resulting exactly-flat tetrahedra as slivers. Those flat tets were the only thing gluing together the two sides of each degenerate planar cell, whose upper and lower halves use opposite diagonals.',
  'THE most serious defect found. Measured: 10848 tets tiling the solid to a relative volume error of 0.0e+00 -- zero void, zero overlap -- yet 9296 faces had only ONE neighbouring tet, of which 7628 (82%) were strictly interior. Those are hanging faces, so the P1 space was not H1-conforming: the solve was not a Galerkin solution and refinement did not control the error. This is the likely cause of the absolute |Z| non-convergence previously recorded as an accepted limitation. Fixed by triangulating the disk once and splitting each extruded prism with a sorted-index rule; the mesh now has 1668 boundary facets, exactly the true prism surface, and zero interior.'),
 ('Two thirds of every electrode was buried in tissue', 'physics', 'boundary_facets() is f2t[1] == -1, so it returned all 9296 torn faces. place_strips filters on rad > 0.80*R, and the crack faces reach radius 5.194 cm against a 5.481 cm apothem, so they passed.',
  '61-63% of each electrode facet set, and 63-65% of its AREA, was interior tissue rather than skin. The CEM contact condition was imposed on a partly buried conductive slab shorting interior nodes, and electrode area diverged under refinement, so the mesh-convergence check could not converge in principle. Resolved by the conforming mesh: now 0% interior, and areas fall to a physical 2.6-12.5 cm2 from 7.2-35.1.'),
 ('Motion slid the fat layer out from under the electrodes', 'model', 'base_sigma evaluated the fat/muscle boundary from the SHIFTED coordinates, so a body shift thinned or deleted the 0.99 cm subcutaneous shell beneath one strip.',
  'The primary endpoint of the whole project is direction accuracy against motion, and the motion model was dominated by an artifact. The fat-boundary term alone produced a post-common-mode differential 16x to 320x larger than the entire corrected motion response, and at 0.3 cm it exceeded the whole grade-IV bolus signal by about sevenfold. Electrodes are mounted on skin and travel with it, so the boundary is now evaluated in the electrode-fixed frame and only the internal organs move.'),
 ('Abstain gate statistic was an unadjusted R-squared', 'estimator', 'lin used the raw coefficient of determination, whose null expectation is 1/(nz-1): 0.50 for a 3-zone aperture against 0.11 for a 10-zone one.',
  'A single fixed gate at 0.35 was a different test at every electrode count, sitting BELOW the noise expectation for small apertures and admitting empty windows roughly half the time at N=6. Now uses the adjusted R-squared, whose null expectation is 0 regardless of zone count, so one threshold means the same thing everywhere. Recalibrated on a dedicated seed block no study uses.'),
 ('The gate statistic was a self-weighted average', 'estimator', 'The aperture fusion weight is base*(0.25+lin)*sqrt(energy), and lin was then averaged using that same weight, so lin was weighted by a function of itself.',
  'Apertures that happened to fit well were given more say in deciding whether the fit was good, biasing the gate statistic upward by roughly Var(lin)/(0.25+mean(lin)) and letting through more empty windows than the same threshold on an honest mean. The lin fusion now uses a weight that cannot see lin.'),
 ('lag and slope are the same number at small apertures', 'estimator', 'lag is the endpoint slope and slope is the least-squares slope. For an aperture with three evenly spaced zones the centre point contributes nothing to a centred LS fit, so the two are algebraically identical.',
  'They were fused as two independent estimators, which double-counts one estimate at exactly the configurations where evidence is scarcest -- every contributing aperture at N=5 and N=6. The evidence is now averaged rather than summed when they are duplicates.'),
 ('Unidentifiable lags resolved to a confident antegrade call', 'estimator', 'A constant zone series left _norm unnormalised at all-zero, making every correlation 0.0; np.argmax on a flat array returns index 0, which is the MOST NEGATIVE lag. Any exact plateau in the correlation did the same.',
  'A degenerate window became a large negative lag, read downstream as a negative slope and therefore ANTEGRADE, rather than an abstention. The bias ran entirely toward calling children healthy, the direction that flatters specificity. Now returns NaN and the aperture is withdrawn.'),
 ('The peak feature averaged in its own self-correlation', 'estimator', 'peaks[0] is xcorr_lag(ser[0], ser[0]) = 1.0 exactly, and peak was the mean over all zones including it.',
  'Added a deterministic +1/nz offset that SHRANK with electrode count, so the published xcpeak feature carried a spurious inverse-N trend unrelated to the data. Now averages the cross terms only.'),
 ('place_strips accepted end-cap facets and never checked the strip fits', 'physics', 'The lateral test was rad > 0.80*R, which a triangle on the z=0 or z=height disc passes despite facing along the axis. Nothing checked that the requested span and centre lie inside the body.',
  'The -2 cm arm of the tolerance study pushed its bottom electrode onto the inferior cap, the most likely reason that arm inverts the grade ordering with grade V worst of all five. Cap facets are now excluded by normal, and an off-body request raises instead of silently degrading.'),
 ('The verification gate read a key that no longer existed', 'reporting', 'The V1 summary tested d.get(quasistatic_ok), a key renamed to eqs_ok when the criterion was corrected, so .get returned None for every tissue.',
  'The one automated gate in the forward-model verification reported EVERY tissue as failing quasi-static validity, the exact opposite of what the check computed.'),
 ('Figure n2 stated the wrong denominators', 'reporting', 'The on-plot caption said n=48 children per cell. The plotted rates are over 24 refluxing children (left panel) and 14 with grades I-II (right).',
  'The caption exists precisely to tell the reader how much per-cell noise to expect, and it understated the true n by 2x and 3.4x.'),
 ('The placement table highlighted the retracted placement', 'reporting', 'The green highlight was hard-coded to the grid key 10_0.28.',
  'The only visual recommendation cue in the placement table sat on the configuration the project had already withdrawn as chosen by a gameable one-sided metric. It now reads the current optimum from the study output.'),
 ('The derived defect breakdown counted the wrong classes', 'reporting', 'n_defects_code counted everything not classed reporting, while the prose described the remainder as the model, the estimator or the statistics -- but the log also carries physics and tooling classes.',
  'The one count advertised as counted-from-the-table-so-it-cannot-drift had itself drifted, naming three categories while summing six.'),
 ('tetrapolar_zones documented a Wenner array it does not build', 'reporting', 'The docstring described electrodes at (k, k+m, k+2m, k+3m) with a zone count of sum(N-3m). The code builds a Schlumberger array: drive on (k, k+G) for odd G, sense on the single adjacent inner pair, count sum(N-G).',
  'Wenner and Schlumberger have different depth sensitivities for the same footprint, so anyone sizing depth reach from the docstring got the wrong array. The stated count is also off by two at N=8, 9 actual against 7 claimed.'),
 ("The abstain gate was far weaker than claimed", "estimator",
  "The published justification for LIN_GATE=0.35 said it kept 96.4% of real events while rejecting 71.4% of empty ones, a Youden of 0.68. That rested on three defects at once: an unadjusted R-squared whose null expectation is 1/(nz-1), a fusion weight containing the statistic being fused, and a motion model dominated by the fat layer sliding under the electrodes, which is smooth and strip-wide and so looks far more linear than real motion.",
  "Recalibrated on the corrected statistic and the corrected motion model over 480 trials on a seed block no study uses, the best achievable Youden is 0.45, not 0.68. Travelling median is +0.293 against an empty median of -0.105, but travelling p10 is -0.490 against empty p90 of +0.598: the distributions overlap heavily and the Youden curve is flat across the whole usable range. The new optimum, 0.16, keeps 81% of correctly-signed events and rejects only 64% of empty windows. The abstain gate is a weak discriminator being asked to carry the abstain decision, and every abstention rate this project has published was produced by a gate whose measured separation was inflated."),
 ("Grade prevalence drawn uniformly", "stats", "run_precision drew grades with .choice([1,2,3,4,5]), giving 40% grades IV-V, while the project publishes GRADE_WEIGHTS (30/30/22/13/5, so 18% IV-V) as its prevalence model. sample_grade() existed but was never called anywhere in the repo.", "High grades are far easier to detect, so over-representing them by more than twice biased every sensitivity Study 5 reported UPWARD. Now draws from the declared model; re-running."),
]


TABLES = {
    "electrode_count": lambda: _t(
        "<tr><th>Config</th><th>Channels</th><th>Raw @0.3</th><th>Raw @0.6</th>"
        "<th>On calls made @0.6</th><th>Abstained @0.6</th><th>Laterality @0.6</th></tr>",
        _rows_count()),
    "design_motion": lambda: _t(
        "<tr><th>Motion</th><th>Direction (old &rarr; new)</th><th>Laterality</th>"
        "<th>AUC<br><span class='sub'>classifier, see &sect;4.1</span></th>"
        "<th>Abstain</th></tr>", _rows_design()),
    "multievent": lambda: _t(
        "<tr><th>Rule</th><th>Sensitivity</th><th>Specificity</th>"
        "<th>Chance floor</th></tr>", _rows_k()),
    "placement": lambda: _t(
        "<tr><th>Placement</th><th>Zones crossed<br><span class='sub'>grade I</span></th>"
        "<th>I</th><th>II</th><th>III</th><th>IV</th><th>V</th></tr>", _rows_place()),
    "tolerance": lambda: _t(
        "<tr><th>Offset</th><th>I</th><th>II</th><th>III</th><th>IV</th><th>V</th>"
        "<th>Abstain<br><span class='sub'>low grades</span></th></tr>", _rows_tol()),
    "mesh_convergence": lambda: _t(
        "<tr><th>rings / layers</th><th>nodes</th><th>tets</th><th>mean |Z|</th>"
        "<th>|Z| error</th><th>slope</th><th>slope error</th><th>decision</th></tr>",
        _rows_verify()),
    "contact_immunity": lambda: _t(
        "<tr><th>measurement</th><th>relative spread over z<sub>0</sub> &isin; U(5,20)</th></tr>",
        f"<tr><td>tetrapolar (this design)</td><td>{VALS['tetra_spread']()}</td></tr>"
        f"<tr><td>bipolar proxy</td><td>{VALS['bipolar_spread']()}</td></tr>"
        f"<tr class='hi'><td><b>rejection factor</b></td>"
        f"<td><b>{VALS['rejection_factor']()}&times;</b></td></tr>"),
    "precision": lambda: _t(
        "<tr><th>Placement</th><th>error &sigma;</th><th>rule</th><th>Sensitivity</th>"
        "<th>Specificity</th><th>Never detected<br><span class='sub'>on any of 6 voids</span></th>"
        "<th>Low grades<br>never detected</th></tr>", _rows_prec()),
    "motion2_false_retrograde": lambda: _t(
        "<tr><th>Displacement</th><th>rigid (grad 0)</th><th>half gradient</th>"
        "<th>full gradient</th></tr>", _rows_m2fr()),
    "motion2_accuracy": lambda: _t(
        "<tr><th rowspan='2'>Displacement</th><th colspan='3'>rigid</th>"
        "<th colspan='3'>half gradient</th><th colspan='3'>full gradient</th></tr>"
        "<tr><th>raw</th><th>on calls</th><th>abstain</th><th>raw</th><th>on calls</th>"
        "<th>abstain</th><th>raw</th><th>on calls</th><th>abstain</th></tr>", _rows_m2()),
    "auc_corrected": lambda: _t(
        "<tr><th>Config</th><th>Motion</th>"
        "<th>Published<br>classifier AUC</th><th>energy<br>features only</th>"
        "<th>direction<br>features only</th>"
        "<th>Direction-rule AUC<br><span class='sub'>no model fitted</span></th></tr>",
        _rows_auc()),
    "alt_designs": lambda: _t(
        "<tr><th>Placement</th><th>grade I<br><span class='sub'>still</span></th>"
        "<th>grade II<br><span class='sub'>still</span></th><th>AUC still</th>"
        "<th>AUC 0.45</th><th>AUC 0.90</th><th>Sens</th><th>Spec</th></tr>",
        _rows_altdesign()),
    # The engineering change log is deliberately NOT a report section. It lives
    # in git history and in the code comments, where it belongs. DEFECTS is kept
    # here only so the counts stay available to internal tooling.
}


def resolve(kind, arg):
    if kind == "val":
        if arg not in VALS:
            return f"<!-- unknown value: {arg} -->"
        return str(VALS[arg]())
    if kind == "table":
        if arg not in TABLES:
            return f"<!-- unknown table: {arg} -->"
        return TABLES[arg]()
    if kind == "methods":
        return bm.methods_html(arg)
    if kind == "common_methods":
        return bm.common_html()
    if kind == "technical":
        return bt.technical_html()
    if kind == "fig":
        path, _, cap = arg.partition("|")
        return figure(path.strip(), cap.strip())
    return f"<!-- unknown placeholder: {kind}:{arg} -->"
