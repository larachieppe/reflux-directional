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
    "n_defects":          lambda: len(DEFECTS),
    "n_defects_code":     lambda: sum(1 for d in DEFECTS if d[1] != "reporting"),
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


def _rows_place():
    pk = sorted(PG, key=lambda k: -(PG[k]["g1_m0.0"]["reflux_acc"]
                                    if PG[k]["g1_m0.0"]["reflux_acc"] ==
                                    PG[k]["g1_m0.0"]["reflux_acc"] else 0))
    return "\n".join(
        f"<tr{' class=hi' if k == '10_0.28' else (' class=bad' if k == '16_0.50' else '')}>"
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
    "defects": lambda: _t(
        "<tr><th>#</th><th>Defect</th><th>Class</th><th>What was wrong</th>"
        "<th>Effect on a published claim</th></tr>",
        "\n".join(f"<tr><td>{i+1}</td><td><b>{t}</b></td><td>{c}</td><td>{w}</td>"
                  f"<td>{e}</td></tr>" for i, (t, c, w, e) in enumerate(DEFECTS))),
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
