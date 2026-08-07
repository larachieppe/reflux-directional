"""
Build FULL_REPORT.html: everything built since the two-strip decision.

Covers all four studies, the corrected numbers, and the complete defect log,
because three headline claims were published and then overturned and a reader
deciding whether to build hardware needs to see that history, not just the
current figures.
"""
import base64, json, os

import build_methods as bm
import build_technical as bt

D = json.load(open("metrics_design.json"))
E = json.load(open("metrics_directional.json"))
P = json.load(open("metrics_placement.json"))
T = json.load(open("metrics_tolerance.json")) if os.path.exists("metrics_tolerance.json") else None
PR = json.load(open("metrics_precision.json")) if os.path.exists("metrics_precision.json") else None
M2 = json.load(open("metrics_motion2.json")) if os.path.exists("metrics_motion2.json") else None
VF = json.load(open("metrics_verify.json")) if os.path.exists("metrics_verify.json") else None
OLD_E = json.load(open("baseline_prefix/metrics_directional.json"))
OLD_D = json.load(open("baseline_prefix/metrics_design.json"))

C = D["config"]; OP = D["operating"]; S = D["subject"]; G = D["grade"]; AB = D["ablation"]
EP = E["primary"]; EC = E["config"]; EMOT = EC["motion"]; ECOUNTS = EC["counts"]
PG = P["grid"]; BEST = P["best_low_grade"]
MOT = C["motion"]; K = S["k_events"]; BK = str(S["best_k"])


def p0(x, d=0):
    return "n/a" if x is None or x != x else f"{100*x:.{d}f}%"


def n2(x):
    return "n/a" if x is None or x != x else f"{x:.2f}"


def ed(M, n, m):
    d = M["primary"][str(n)][str(m)]
    return float("nan") if d.get("undecidable", 0) > 0.99 else d["dir_acc"]


def img(path, cap, width=700):
    if not os.path.exists(path):
        return ""
    b = base64.b64encode(open(path, "rb").read()).decode()
    return (f'<p style="text-align:center;margin:18px 0 4px">'
            f'<img src="data:image/png;base64,{b}" width="{width}"></p>'
            f'<p class="cap">{cap}</p>')


# ---- tables ----
def _dec(n, m, k):
    return EP[str(n)][str(m)].get(k, float("nan"))


rows_count = "\n".join(
    f"<tr{' class=hi' if n == 8 else (' class=bad' if n == 5 else '')}>"
    f"<td>N = {n}</td><td>{2*n}</td>"
    f"<td>{p0(ed(E,n,0.3))}</td>"
    f"<td>{p0(ed(E,n,0.6))}</td>"
    f"<td><b>{p0(_dec(n,0.6,'dir_acc_decided'))}</b></td>"
    f"<td>{p0(_dec(n,0.6,'abstain_rate'))}</td>"
    f"<td>{p0(EP[str(n)]['0.6']['lat_acc'])}</td></tr>" for n in ECOUNTS)

rows_design = "\n".join(
    f"<tr><td>{m:.2f} cm</td>"
    f"<td>{p0(OLD_D['operating'].get(str(m),{}).get('dir_acc'))} &rarr; <b>{p0(OP[str(m)]['dir_acc'])}</b></td>"
    f"<td>{p0(OP[str(m)]['lat_acc'])}</td><td>{n2(OP[str(m)]['auc'])}</td>"
    f"<td>{p0(OP[str(m)].get('abstain_rate'))}</td></tr>" for m in MOT)

rows_k = "\n".join(
    f"<tr{' class=hi' if str(k)==BK else ''}><td>&ge; {k} of {K}</td>"
    f"<td><b>{p0(S['sens_k'][str(k)])}</b></td><td><b>{p0(S['spec_k'][str(k)])}</b></td>"
    f"<td>{p0(S['chance_k'][str(k)])}</td></tr>" for k in range(1, K+1))

pk = sorted(PG, key=lambda k: -(PG[k]["g1_m0.0"]["reflux_acc"]
                                if PG[k]["g1_m0.0"]["reflux_acc"] == PG[k]["g1_m0.0"]["reflux_acc"] else 0))
rows_place = "\n".join(
    f"<tr{' class=hi' if k == '10_0.28' else (' class=bad' if k == '16_0.50' else '')}>"
    f"<td>{PG[k]['span']:.0f} cm @ z={PG[k]['z_center']:.2f}</td>"
    f"<td>{PG[k]['g1_m0.0']['zones_crossed']}</td>"
    + "".join(f"<td>{p0(PG[k][f'g{g}_m0.0']['reflux_acc'])}</td>" for g in (1,2,3,4,5))
    + "</tr>" for k in pk)

rows_tol = ""
if T:
    TG = T["grid"]
    rows_tol = "\n".join(
        f"<tr{' class=hi' if o == 0.0 else ''}><td>{o:+.0f} cm</td>"
        + "".join(f"<td>{p0(TG[f'{o:+.0f}'][f'g{g}_m0.0']['reflux_acc'])}</td>" for g in (1,2,3,4,5))
        + f"<td>{p0(TG[f'{o:+.0f}']['low_grade_still']['abstain'])}</td></tr>"
        for o in T["config"]["offsets_cm"])

DEFECTS = [
 ("Magnitude before common-mode removal","estimator","Taking |dZ| before subtracting the across-zone mean is nonlinear, so the common mode could never cancel.","Direction sat at chance."),
 ("Aperture chosen by total energy","estimator","Total energy favours apertures with more zones, which are the shallowest.","Systematically selected the aperture that cannot reach the ureter."),
 ("Amplitude envelope on the bolus","model","Gave every zone the same time course, so responses were separable as amplitude x one shared envelope.","Erased the travelling wave the device measures."),
 ("Temporal median as baseline","model","The bolus passes every zone, so the median sits mid-event.","Scrambled each clean passage into a bipolar trace."),
 ("Lag search clipped to n/3","estimator","Real lags spanned ~11 samples; the search was bounded at 6.","Truncated genuine signal. Self-inflicted while fixing something else."),
 ("Contact impedance ~100x too low","model","Electrodes acted as near-ideal shunts.","Suppressed the signal ~100x while amplifying drift sensitivity."),
 ("Unequal electrode area between strips","physics","An odd interior mesh ring broke mirror symmetry; one strip got 23% less area.","Laterality was a degenerate always-one-side predictor, not a degrading one."),
 ("Duplicate trials across CV folds","stats","SNR and span sweeps re-emitted primary-grid trials verbatim.","Manufactured an AUC peak exactly at the design SNR and span."),
 ("Multi-event metric pooled healthy and refluxing children","stats","Counted a correct negative as a 'hit'.","Chance floor of 89% sat ABOVE the 80% VCUG line being compared against."),
 ("Confusion matrix thresholded at the median","stats","Forces 50% predicted-positive against 25% prevalence.","Capped specificity at 66.7% by construction."),
 ("AUC computed once and copied","stats","One motion cell written into every motion key.","Every motion-resolved AUC published was the same number."),
 ("z_center never forwarded","physics","StripWorld accepted it but never passed it to place_strips.","Every strip in every study sat on the torso midpoint by default. Caused the 'grades I-II are undetectable' claim."),
 ("Electrodes sharing boundary facets","physics","A fixed z window exceeded half-pitch at N=12.","44 shared facets welded electrodes together; that array was not physically realizable."),
 ("Noise added to a normalized quantity","model","Derived from raw |Z| but added to fractional dZ.","Injected noise depended on the choice of length unit and sat ~10 dB low."),
 ("Placement chosen on the still arm only","stats","run_placement scored candidate placements by low-grade accuracy at motion 0.0, silently discarding the motion arm the same study had just measured.","Selected 10 cm @ z=0.34 (92.9%/100% still, but 50.0% on grade I under motion) over 10 cm @ z=0.28 (equal still, 78.6% under motion). That choice propagated into Study 4, which centred its offsets on it, and Study 5, which adopted it as the short-strip arm."),
 ("Abstention scored as a wrong answer","stats","dir_acc penalised abstention, but the abstain gate needs >=3 zones, so N=5 was structurally exempt from it.","Made N=5 appear to beat N=8 under motion (79% vs 71%). On calls actually made, N=8 leads 93% to 79%. Same failure mode as defect 9: a pooled metric flattering the wrong option."),
]
rows_def = "\n".join(
    f"<tr><td>{i+1}</td><td><b>{t}</b></td><td>{c}</td><td>{w}</td><td>{e}</td></tr>"
    for i,(t,c,w,e) in enumerate(DEFECTS))

# ---------------------------------------------------------------- new results
def _pct(x, d=1):
    return "n/a" if x != x else f"{100*x:.{d}f}%"


rows_verify = "".join(
    f"<tr{' class=hi' if L['n_nodes'] == VF['v3_mesh_convergence']['levels'][-1]['n_nodes'] else ''}>"
    f"<td>{L['n_rings']} / {L['nz']}</td><td>{L['n_nodes']:,}</td><td>{L['n_tets']:,}</td>"
    f"<td>{L['mean_absZ']:.4g}</td><td>{100*L['absZ_rel_to_finest']:.1f}%</td>"
    f"<td>{L['slope']:+.4g}</td><td>{100*L['slope_rel_to_finest']:.2f}%</td>"
    f"<td>{'reflux' if L['decision'] > 0 else ('antegrade' if L['decision'] < 0 else 'abstain')}</td></tr>"
    for L in VF["v3_mesh_convergence"]["levels"]) if VF else ""

rows_prec = ""
if PR:
    for k, v in sorted(PR["grid"].items(), key=lambda t: (t[1]["span"], t[1]["sigma"])):
        cls = " class=hi" if v["span"] == 10.0 else (" class=bad" if v["low_grade_never"] > 0.35 else "")
        rows_prec += (
            f"<tr{cls}><td>{v['span']:.0f} cm @ z={v['z_center']:.2f}</td>"
            f"<td>{v['sigma']:.1f} cm</td><td>&ge;{v['best_k']} of {PR['config']['k_events']}</td>"
            f"<td>{_pct(v['best_sens'],0)}</td><td>{_pct(v['best_spec'],0)}</td>"
            f"<td>{_pct(v['never_detected'],0)}</td><td>{_pct(v['low_grade_never'],0)}</td></tr>")

rows_m2 = ""
if M2:
    G2, C2 = M2["grid"], M2["config"]
    for a in C2["amps"]:
        cells = ""
        for g in C2["grads"]:
            v = G2[f"a{a}_g{g}"]
            cells += (f"<td>{_pct(v['dir_acc'],0)}</td><td>{_pct(v['dir_acc_decided'],0)}</td>"
                      f"<td>{_pct(v['trav_abstain'],0)}</td>")
        cls = " class=hi" if a <= 1.0 else (" class=bad" if a >= 3.0 else "")
        rows_m2 += f"<tr{cls}><td>{a:.1f} cm</td>{cells}</tr>"

rows_m2fr = ""
if M2:
    for a in M2["config"]["amps"]:
        cells = "".join(
            f"<td>{_pct(M2['grid'][f'a{a}_g{g}']['false_retrograde'],1)}</td>"
            for g in M2["config"]["grads"])
        rows_m2fr += f"<tr><td>{a:.1f} cm</td>{cells}</tr>"

_gm = {}
if M2:
    import statistics as _st
    for g in M2["config"]["grads"]:
        _gm[g] = (_st.mean(M2["grid"][f"a{a}_g{g}"]["false_retrograde"] for a in M2["config"]["amps"]),
                  _st.mean(M2["grid"][f"a{a}_g{g}"]["dir_acc"] for a in M2["config"]["amps"]))

HTML = f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>Directional reflux sensing: complete simulation report</title>
<style>
 body{{font-family:Arial,Helvetica,sans-serif;font-size:11pt;color:#000;max-width:860px;
      margin:32px auto;line-height:1.55;padding:0 22px}}
 h1{{font-size:23pt;margin:28px 0 6px}}
 h2{{font-size:16pt;color:#1155cc;margin:32px 0 8px;border-bottom:1px solid #ccc;padding-bottom:4px}}
 h3{{font-size:12.5pt;margin:20px 0 6px}}
 table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:9.5pt}}
 th,td{{border:1px solid #000;padding:5px 7px;text-align:center;vertical-align:top}}
 th{{background:#efefef}} td:first-child,th:first-child{{text-align:left}}
 tr.hi td{{background:#e8f2e8}} tr.bad td{{background:#fdecea}}
 ul,ol{{margin:8px 0 8px 24px}} li{{margin:5px 0}}
 .cap{{font-size:9.5pt;color:#555;text-align:center;margin:0 0 18px;font-style:italic}}
 .key{{border:2px solid #1155cc;background:#eef3fb;padding:12px 16px;margin:16px 0}}
 .warn{{border-left:4px solid #c0392b;padding:10px 14px;background:#fdf2f1;margin:14px 0}}
 .note{{border-left:4px solid #c98500;padding:10px 14px;background:#fbf7ef;margin:14px 0}}
 img{{max-width:100%;border:1px solid #ddd}} .sub{{color:#555;font-size:10pt}}
{bm.CSS}
{bt.CSS}
 .toc{{border:1px solid #ccd6da;background:#fbfcfd;padding:14px 20px;margin:22px 0;
  border-radius:5px;font-size:10pt;column-count:2;column-gap:28px}}
 .toc ul{{margin:8px 0 0 0;padding:0;list-style:none}}
 .toc li{{margin:2px 0;break-inside:avoid}}
 .toc li.t3{{padding-left:16px;font-size:9.5pt;color:#555}}
 .toc a{{color:#1155cc;text-decoration:none}} .toc a:hover{{text-decoration:underline}}
 h2[id],h3[id]{{scroll-margin-top:12px}}
 @media(max-width:700px){{.toc{{column-count:1}}}}
 .methods table.mm-t th,.methods table.mm-t td{{text-align:left}}
 .techsec table.mm-t th,.techsec table.mm-t td{{text-align:left;border:1px solid #d7e0e4}}
</style></head><body>

<h1>Directional bioimpedance sensing for pediatric vesicoureteral reflux</h1>
<p class="sub">Complete simulation report, covering all work since the two-strip design decision.
Live: https://larachieppe.github.io/reflux-directional/ &middot;
Source: https://github.com/larachieppe/reflux-directional</p>

<div class="key"><b>What this is.</b> A finite-element simulation testing, before hardware exists,
whether a surface bioimpedance device can detect vesicoureteral reflux by measuring the
<b>direction</b> urine travels rather than reconstructing an image. <b>Six studies and a
four-part numerical verification of the forward model</b> are reported: electrode count,
locked-design characterization, strip placement, misplacement tolerance, placement precision
across a simulated cohort, and non-rigid respiratory motion.
Section 2 gives the shared forward model, the estimator, and the statistics, so that every study
below can be read as a statement of what it changed rather than a self-contained method.
<b>Fifteen defects were found and fixed along the way, and five published headline claims were
subsequently overturned by measurement</b> &mdash; most recently the locked design itself
(&sect;9) and the project's own stated existential risk (&sect;10). That history is reported here
alongside the results, because it bears directly on how much weight the numbers can carry.</div>
<div class="warn"><b>Read this before quoting any number.</b> The design characterised in
&sect;5 as "the locked design" is a 16 cm strip at mid-torso. Study 5 (&sect;9) has since shown
that placement never detects 25&ndash;33% of refluxing children across six voids, and 43% of
low-grade refluxers even when placed perfectly. That much is settled across two independent
studies.<br><br>
<b>What replaces it is not yet settled.</b> A short 10 cm strip over the ureterovesical junction
recovers the low grades, but it has a shorter axial lever arm, and re-characterising the whole
design there cost AUC at <i>every</i> motion level (0.961&rarr;0.883 still, 0.893&rarr;0.665 at
0.9 cm). Placement is a genuine trade-off between low-grade coverage and motion robustness, not a
strictly better choice &mdash; and the geometry forbids having both, since a 16 cm strip in a
20 cm torso cannot be centred below z = 0.40. Two better-balanced candidates are being
characterised now. Until they land, <b>&sect;5 reports a placement known to be wrong for low
grades, and no re-cut design has yet been validated to replace it.</b></div>

<h2>1. Premise</h2>
<p>The reference test, VCUG, requires catheterization, radiation, and voiding on command. It also
misses roughly 20% of reflux (intermittent, and only one or two voids are captured), radiologists
agree on grade in 59% of cases, and only about 48% of families complete the imaging. That
compliance gap, not accuracy, is the clinical opening.</p>
<p>A prior program (Kite Medical, ~$3.1M, wound up 2023) used 32-electrode tomography and reported
<b>73% detection without motion, 44% with motion</b>. Two structural reasons: the measured quantity
(presence of conductive fluid) is shared with the dominant confounder, ordinary bladder filling;
and image reconstruction has no intrinsic rejection of body motion.</p>
<p>Reflux is defined by <b>retrograde transport</b>, so direction separates it from bladder filling
by construction, and a differential measurement between nearby zones rejects perturbations common
to both, which is what motion is. A single symmetric tetrapolar array is direction-blind by
symmetry, so the geometry is a longitudinal strip, one per flank, which also gives laterality.</p>
{img("figs_dir/figG_mechanism.png","The mechanism. Reflux: the impedance dip climbs the strip and arrival time rises with height. Antegrade: the mirror image. The SIGN of that slope is the diagnosis.")}

<h2>2. Materials and methods</h2>
<p>Every study below shares one forward model and one estimator, and differs only in
which factors it varies. The shared model is stated once here; each study then states
only what it changed, what it held fixed, and how its endpoint was computed. All
parameters are introspected from the model module and from the metrics file each run
wrote, so they cannot drift from the code that produced the results.</p>
{bm.common_html()}

<h2>3. Technical foundations</h2>
{bt.technical_html()}

<h2>4. Study 1: how many electrodes</h2>
<p>Direction accuracy at grade &ge; III. Two accuracy columns are shown at 0.6 cm because a
single one is misleading: the raw figure counts an <b>abstention</b> as a wrong answer, while the
abstain gate requires at least three zones, so N=5 (two zones) is <b>structurally exempt</b> from
it. Judged on the raw column alone, the only configuration that cannot decline to answer looks the
most robust.</p>
<table><tr><th>Config</th><th>Channels</th><th>Raw @0.3</th><th>Raw @0.6</th>
<th>On calls made @0.6</th><th>Abstained @0.6</th><th>Laterality @0.6</th></tr>
{rows_count}</table>
<div class="warn"><b>Claim overturned #4.</b> An earlier version of this report showed N=5
outperforming N=8 under motion (79% against 71% at 0.6 cm). That was an artifact of the metric, not
a property of the design. On the calls actually made, <b>N=8 leads 93% to 79%</b>, and it declines
to answer on 24% of cases rather than guessing. N=5 also cannot perform common-mode rejection at
all, because mean removal across exactly two zones makes them exact negatives. N=5 has neither the
gate nor the rejection: it is the configuration that <i>cannot fail to answer</i>, which reads as
robustness and is the opposite.</div>
<div class="warn"><b>Claim overturned #1.</b> An earlier version of this report stated that
<i>more electrodes made accuracy worse</i>. That was an artifact of a greedy aperture-selection
rule, not physics. Forcing each aperture on identical data showed the selector losing at every
N &ge; 8. Replacing selection with fusion across apertures reversed the result: N=8/10/12 now reach
100% when still, where they previously read 76-93%. Slope precision scales with the axial
<i>lever arm</i> of the zone centroids, not with electrode separation.</div>
{img("figs_dir/figA_count.png","Direction accuracy against electrode count with Wilson 95% intervals.")}

{bm.methods_html("electrode-count")}

<h2>5. Study 2: the locked design</h2>
<p>{C['n_strip']} electrodes per strip, {C['span']:.0f} cm span, {C['channels']} channels,
{C['snr']} dB, {C['freq_khz']} kHz.</p>
<table><tr><th>Motion</th><th>Direction (old &rarr; new)</th><th>Laterality</th><th>AUC</th><th>Abstain</th></tr>
{rows_design}</table>
{img("figs_design/d2_motion.png","Performance against motion at the locked design.")}
<h3>5.1 The multi-event screening rule</h3>
<p>VCUG captures one or two forced voids. A passive wearable observes many, and detection compounds.
Simulated as {S['n_reflux']+S['n_healthy']} children with {K} events each, <b>anatomy and placement
held fixed per child</b> so correlated failure would show rather than average away. Per event:
{p0(S['per_event_sens'])} sensitivity at a {p0(S['per_event_fp'])} false-positive rate.</p>
<table><tr><th>Rule</th><th>Sensitivity</th><th>Specificity</th><th>If detector were a coin flip</th></tr>
{rows_k}</table>
{img("figs_design/d4_multievent.png","Sensitivity and specificity reported separately, with the chance floor.")}
<div class="note">The coin-flip column exists because an earlier version of this metric pooled
healthy and refluxing children and counted a correct negative as a hit. Its chance floor was 89%,
<i>above</i> the ~80% VCUG line it was being compared against, so a coin-flip detector would have
appeared to beat VCUG.</div>

{bm.methods_html("design")}

<h2>6. Study 3: where the strip sits</h2>
<p>Low-grade reflux only traverses the lower ureter, so what matters is how many tetrapolar zone
centroids its bolus actually crosses. Reflux-only detection, still:</p>
<table><tr><th>Placement</th><th>Zones crossed (grade I)</th><th>I</th><th>II</th><th>III</th><th>IV</th><th>V</th></tr>
{rows_place}</table>
<div class="warn"><b>Claims overturned #2 and #3.</b> Every previous version of this work stated
that grades I-II are <i>intrinsically</i> undetectable, "the hard tail", "by construction". That was
false. <code>z_center</code> was never forwarded to <code>place_strips</code>, so every strip in
every study sat on the torso midpoint by default; nobody chose that position and nobody swept it.
Moving the strip over the ureterovesical junction takes <b>grade II from 7% to 100%</b>. The same
result overturns the earlier claim that <i>span is the dominant lever and longer is better</i>: a
<b>shorter strip placed correctly beats a longer strip placed wrong</b>. Span was a proxy for
coverage of the lower ureter.</div>
{img("figs_place/p1_grade_placement.png","Detection by grade and placement. The published configuration is outlined in red.")}
{img("figs_place/p2_mechanism.png","The mechanism: a bolus crossing fewer than about three zone centroids cannot support a slope fit or common-mode rejection.")}

{bm.methods_html("placement")}

<h2>7. Study 4: misplacement tolerance</h2>
<p>The optimum is only useful if it survives imperfect placement by a parent, against a landmark
that is not externally visible. Reflux-only detection, still, offsetting the
{T['config']['span'] if T else 10:.0f} cm strip along the body axis:</p>
<table><tr><th>Offset</th><th>I</th><th>II</th><th>III</th><th>IV</th><th>V</th><th>Abstain</th></tr>
{rows_tol}</table>
{img("figs_place/p3_tolerance.png","Accuracy against misplacement, low grades versus high grades.")}
<div class="warn"><b>It does not survive &plusmn;2 cm.</b> Within &plusmn;1 cm, grades II-V hold at
94-100% and grade II detection is real, which is the prize: grade II+ is roughly 70% of refluxers
against 40% for grade III+. At &plusmn;2 cm it collapses (grade II 100% &rarr; 31%) and abstention
reaches 42%. <b>Grade I is not robust at any offset</b> and its apparent peak at &minus;2 cm is
noise at n=16. The engineering consequence is that a 10 cm strip needs a landmark or an alignment
aid, or a longer strip should be used to buy positional margin at the cost of peak low-grade
accuracy.</div>

{bm.methods_html("tolerance")}

<h2>8. Verification of the forward model</h2>
<p>Everything above rests on the forward solve being correct, and until now that had been
<i>asserted</i> rather than demonstrated. Four checks were run. They need no patient data and no
new physics, and they are the first thing a numerical analyst asks for.</p>

<h3>8.1 Reciprocity: passes at machine precision, and what that is worth</h3>
<p>Maxwell reciprocity requires the transfer impedance to be unchanged when the drive pair and the
sense pair are exchanged. Exchanging them exercises different rows of the assembled system, so an
asymmetry in the assembly, the contact-impedance Robin term or the gauge condition shows up at
once.</p>
<div class="key">Maximum relative error <b>{VF['v2_reciprocity']['max_rel_error']:.2e}</b> over
{VF['v2_reciprocity']['n_pairs']} tetrapolar zones &mdash; machine precision.</div>
<div class="warn"><b>Do not oversell this, as an earlier draft of this report did.</b> The CEM
system matrix is <b>complex symmetric by construction</b>: the stiffness and electrode mass
matrices are symmetric, the coupling block is inserted once as <code>B</code> and once as
<code>B<sup>T</sup></code> from the same array, and the gauge row and column are the same vector of
ones. Reciprocity is therefore an <i>algebraic identity</i> for an exact solve, and
{VF['v2_reciprocity']['max_rel_error']:.1e} is essentially the condition-scaled residual of the
sparse LU.</div>
<p>That still makes it worth running. It would immediately catch a transposed or mis-signed
coupling block, a non-symmetric quadrature on the electrode mass matrix, an inconsistent
<code>1/z<sub>l</sub></code> between the two blocks, or a broken gauge row, and it confirms the
direct solve is numerically clean. But it is <b>necessary, not sufficient</b>: any error that
enters <i>symmetrically</i> &mdash; a wrong Robin coefficient applied consistently to both blocks,
a wrong electrode area, a mis-meshed geometry, a wrong tissue value &mdash; passes this test
untouched. This report previously called it an assumption-free validation of the forward operator.
It is not, and the difference matters.</p>

<h3>8.2 Mesh convergence: the impedance does not converge, but the decision does</h3>
<p>An identical, deterministic, <b>noiseless</b> trial solved on five meshes spanning an eightfold
range of node count.</p>
<table><tr><th>rings / layers</th><th>nodes</th><th>tets</th><th>mean |Z|</th><th>|Z| error</th>
<th>slope</th><th>slope error</th><th>decision</th></tr>{rows_verify}</table>
<div class="warn"><b>Read this table carefully, because it says two opposite things.</b> The
absolute transfer impedance <b>does not converge</b>: the error against the finest mesh oscillates
between 11% and 76% with no monotone trend. But the arrival-time slope converges cleanly and
monotonically &mdash; 6.80%, 2.84%, 0.97%, 0.11% &mdash; and the <b>decision is invariant across
every mesh tested</b>.</div>
<p>The mechanism is electrode discretisation. |Z| scales with realised electrode area, and
electrodes snap to mesh facets, so their area changes discontinuously under refinement. The slope
is a <i>differential timing</i> quantity: it depends on when each zone peaks relative to the
others, which is insensitive to a common area scaling. This is independent, post-hoc justification
for the fractional normalisation <code>dZ/|Z<sub>ref</sub>|</code> that was introduced to fix an
unrelated defect.</p>
{img("figs_new/n1_mesh.png","Mesh convergence. The arrival-time slope converges monotonically by nearly two orders of magnitude; the absolute impedance plateaus near 11% and never converges. The decision is invariant across all five meshes.")}
<div class="note"><b>What this forbids.</b> No claim about an absolute impedance magnitude is
supported by this model &mdash; including any figure quoted to size hardware. Only differential and
timing claims survive. The headline result is a slope sign, so it is on the right side of that
line, but the limitation is real and is not narrowed by running more trials.</div>

<h3>8.3 Contact-impedance immunity is 4.3&times;, not "largely eliminated"</h3>
<p>Sweeping contact impedance across the modelled range and comparing the tetrapolar transfer
impedance against a bipolar proxy on the <i>same electrodes and the same solves</i>:</p>
<table><tr><th>measurement</th><th>relative spread over z<sub>0</sub> &isin; U(5,20)</th></tr>
<tr><td>tetrapolar (this design)</td><td>{VF['v4_contact_immunity']['tetrapolar_rel_spread_modelled_range']:.4f}</td></tr>
<tr><td>bipolar proxy</td><td>{VF['v4_contact_immunity']['bipolar_rel_spread_modelled_range']:.4f}</td></tr>
<tr class="hi"><td><b>rejection factor</b></td><td><b>{VF['v4_contact_immunity']['rejection_factor_modelled_range']:.1f}&times;</b></td></tr></table>
<div class="warn"><b>Claim corrected.</b> This report previously said contact impedance "largely
drops out" of a tetrapolar measurement. It does not. A <b>16% residual sensitivity</b> is not
negligible, and tetrapolar sensing buys a factor of about four, not immunity. The four-wire
geometry remains the right choice &mdash; four times is a large gain and the alternative is
four times worse &mdash; but the language was wrong and the residual has to be budgeted for in
hardware.</div>

<h3>8.4 Quasi-statics: valid, but permittivity is not negligible</h3>
<p>Two <i>independent</i> conditions must hold to reduce Maxwell to
<code>&nabla;&middot;(&kappa;&nabla;u) = 0</code>: the domain must be electrically small against
the <b>free-space</b> wavelength (here 6.7&times;10<sup>&minus;5</sup>), and the skin depth must
exceed the domain (here by 6&times; to 54&times;). Both hold comfortably at both frequencies.</p>
<p>But <code>&omega;&epsilon;/&sigma;</code> reaches <b>1.40 for kidney at 100 kHz</b> and 0.39 for
muscle, so displacement current <i>exceeds</i> conduction current in perfused tissue at the top of
the band. A real-valued conductivity model would be wrong here; carrying the full complex
admittivity is load-bearing, and the imaginary part carries genuine tissue information &mdash;
which is the physical argument for the second frequency being worth its cost, a claim this project
has still not tested.</p>
<div class="note"><b>A trap worth naming</b>, because the first version of this check fell into it:
testing the domain against the <i>in-medium</i> wavelength is not an independent condition. In a
good conductor &lambda; = 2&pi;&delta;, so it merely restates the skin-depth test. And
<code>&omega;&epsilon;/&sigma;</code> does not bear on quasi-static validity at all &mdash; it
answers the separate question of whether permittivity may be dropped.</div>
{bm.methods_html("verify")}

<h2>9. Study 5: placement precision, and the design this overturns</h2>
<p>48 simulated children per cell, six voids each, with <b>one placement error drawn per child and
shared across all of that child's voids</b> &mdash; a strip is applied once, not re-applied per
void. That is what makes failure correlated within a child, which is the entire question. Had the
error been redrawn per event, repeated voids would average it away and the study would have
reported a reassuring, meaningless number.</p>
<table><tr><th>Placement</th><th>error &sigma;</th><th>rule</th><th>Sensitivity</th>
<th>Specificity</th><th>Never detected<br><span class="sub">on any of 6 voids</span></th>
<th>Low grades<br>never detected</th></tr>{rows_prec}</table>
<div class="warn"><b>Claim overturned #5, and it is the big one.</b> This report publishes a locked
design of a <b>16 cm strip at z = 0.50</b>, and Study 2 characterises that configuration. Study 5
shows it never detects <b>25% of refluxing children on any of six voids at perfect placement</b>,
rising to 33% with realistic placement error, and misses <b>43% of low-grade refluxers even when
placed perfectly</b>. The 10 cm strip over the ureterovesical junction misses <b>0%</b> at perfect
placement and 8% at 2 cm of error. <b>The published locked design is wrong for low grades.</b></div>
<div class="note"><b>But the short strip is not simply the answer</b>, and an earlier version of
this section said it was. Re-characterising the full design at 10 cm @ z = 0.34 recovered grade II
(55.4% &rarr; 83.9% still) and cost accuracy everywhere else, with AUC falling at every motion
level and the gap widening as motion grows: 0.961&rarr;0.883 still, 0.954&rarr;0.836 at 0.45 cm,
0.893&rarr;0.665 at 0.9 cm. The mechanism is the same lever-arm argument that explains the
electrode-count result (&sect;3.6): slope precision scales with the axial spread of the zone
centroids, and a 10 cm strip has 62% of the lever arm of a 16 cm one, so its slope estimate is
noisier and degrades faster under motion.<br><br>
The two studies are not in conflict &mdash; they measure different things. Study 2 measures the
<i>marginal</i> per-event rate with fresh anatomy each trial. Study 5 holds anatomy and placement
fixed per child, so it measures <i>correlated</i> failure: whether a given child is ever detectable
at all. A placement can have the better average per-event accuracy while completely failing a
subset of children, and only the second metric sees that. Both are real, and the design has to
satisfy both.</div>
{img("figs_new/n2_precision.png","Study 5. The published 16 cm mid-torso placement loses a quarter of all refluxing children and 43% of low-grade refluxers even when placed perfectly. The 10 cm strip over the ureterovesical junction misses none.")}
<p>This is the same lesson as Study 3, arriving a second time by a different route: low-grade
reflux is a <b>placement</b> problem. A long mid-torso strip spreads its zones over anatomy where
the low-grade bolus never travels, and no amount of repeat observation recovers a child whose
strip never covered the relevant segment. Repeat voids only help when failure is independent
across voids, and placement failure is precisely the kind that is not.</p>
<h3>9.1 The most likely artifact, tested and ruled out</h3>
<p>A result this load-bearing deserves an attempt to break it. The most plausible way "10 cm beats
16 cm" could be an <i>estimator</i> artifact rather than physics is lag-window saturation:
<code>xcorr_lag</code> clips the inter-zone lag search at <code>max_lag = 2T/3</code>. If true lags
saturated that bound on the long strip but not the short one, the slope fit would be biased in
exactly the direction of the published conclusion.</p>
<table><tr><th>Configuration</th><th>grade I</th><th>grade II</th><th>grade III</th><th>grade IV</th>
<th>at clip</th></tr>
<tr><td>16 cm mid-torso &mdash; mean |lag|</td><td>1.01</td><td>0.72</td><td>1.37</td><td>1.62</td><td>0%</td></tr>
<tr class="hi"><td>10 cm over the UVJ &mdash; mean |lag|</td><td>1.87</td><td>1.98</td><td>1.84</td><td>1.57</td><td>0%</td></tr></table>
<p class="cap">Inter-zone lag in frames, against a clip boundary of 13 frames at T = 20.</p>
<div class="key"><b>Refuted.</b> The largest lag observed anywhere was 3.13 frames against a bound
of 13, and <b>0% of lags sat at or near the clip</b> in either configuration. The conclusion is not
a lag-window artifact.</div>
<p>The check also <i>supports</i> the mechanism. The 10 cm strip shows <b>larger</b> lags than the
16 cm strip at every low grade, which is what a genuine traverse looks like: the short strip sits
where the bolus actually travels, while the long mid-torso strip spreads its zones over anatomy the
low-grade bolus barely reaches, so its zones see a weak and nearly simultaneous perturbation. That
is the same mechanism Study 3 measured by counting zone crossings, arriving here independently.</p>
<div class="note"><b>Do not over-read the individual cells.</b> With 48 children per cell the
confidence intervals are wide, and the 16 cm arm is non-monotonic in &sigma; (75%, 67%, 88%, 83%),
which is not physically sensible and indicates large per-cell noise. The <i>never-detected</i> gap
between the two placements is large and consistent across every &sigma;, and that is the finding.
The individual sensitivity figures are not precise enough to rank.</div>
{bm.methods_html("precision")}

<h2>10. Study 6: non-rigid respiratory motion &mdash; the predicted failure did not happen</h2>
<p>Every motion result before this one used a <b>rigid</b> translation, which is exactly the
perturbation that subtracting the across-zone mean provably nulls. A rigid-only model can only ever
<i>confirm</i> the common-mode rejection claim; it cannot test it. This report previously named
non-rigid motion the single most likely place the model flatters the design, on the argument that a
craniocaudal gradient survives mean subtraction and injects a phase-locked false travelling wave
&mdash; the exact shape of the failure that took the prior tomographic program from 73% to 44%.</p>
<h3>10.1 The gradient hypothesis, tested</h3>
<table><tr><th>Displacement</th><th>rigid (grad 0)</th><th>half gradient</th><th>full gradient</th></tr>
{rows_m2fr}</table>
<p class="cap">False-retrograde rate on non-travelling windows: how often the device invents reflux
while the child is merely breathing.</p>
<div class="key"><b>The hypothesis is refuted.</b> Averaged over amplitudes, false-retrograde runs
{_pct(_gm[0.0][0],1)} rigid, {_pct(_gm[0.5][0],1)} at half gradient and {_pct(_gm[1.0][0],1)} at
full gradient, and direction accuracy runs {_pct(_gm[0.0][1],1)}, {_pct(_gm[0.5][1],1)} and
{_pct(_gm[1.0][1],1)}. There is no gradient penalty at any amplitude. The full-gradient arm is, if
anything, slightly better. The predicted false travelling wave did not appear.</div>
{img("figs_new/n3_gradient.png","Study 6. The three gradient curves lie on top of one another at every amplitude. The predicted craniocaudal false travelling wave does not appear.")}
<p>That makes five confident claims in this project overturned by measurement, and this one was the
authors' own stated existential risk. Candidate explanations &mdash; that the gradient displaces
kidney and bladder differentially in a way that reinforces rather than mimics the true bolus
signature, or that the induced slope is simply small against the bolus-induced slope at these
amplitudes &mdash; are <b>post hoc and untested</b>. The honest statement is that the mechanism was
predicted, the prediction was wrong, and why it was wrong is not yet established.</p>

<h3>10.2 What actually degrades the measurement</h3>
<table><tr><th rowspan="2">Displacement</th><th colspan="3">rigid</th><th colspan="3">half gradient</th>
<th colspan="3">full gradient</th></tr>
<tr><th>raw</th><th>on calls</th><th>abstain</th><th>raw</th><th>on calls</th><th>abstain</th>
<th>raw</th><th>on calls</th><th>abstain</th></tr>{rows_m2}</table>
<p>Amplitude, not gradient. Raw accuracy falls from 100% to under 50% between 0 and 3 cm. But the
failure mode is <b>safe</b>: accuracy <i>on the calls actually made</i> holds at 84% at 2 cm and
62&ndash;69% at 3 cm, while the abstention rate climbs to roughly a third. The estimator degrades
into declining to answer, not into answering confidently and wrongly. That is the behaviour the
abstain gate was designed to produce, and this is the first study that genuinely tested it.</p>
{img("figs_new/n4_abstain.png","Study 6. The gap between raw accuracy and accuracy-on-calls-made is the abstain gate working: under motion the estimator declines to answer rather than answering wrongly.")}
<p>For scale: quiet-breathing renal excursion is about 1 cm, where the design holds
{_pct(M2['grid']['a1.0_g1.0']['dir_acc_decided'],0)} on calls made with only
{_pct(M2['grid']['a1.0_g1.0']['trav_abstain'],0)} abstention. Two to three centimetres is deep
breathing or crying.</p>
<div class="warn"><b>An unexplained floor.</b> False-retrograde on empty windows is
{_pct(M2['grid']['a0.0_g0.0']['false_retrograde'],1)} <b>at zero motion</b>. Motion does not explain
it, so something else does &mdash; noise passing the gate, a residual in the common-mode step, or a
bladder-filling confounder leaking into the slope. It is a floor on achievable specificity and it
has not been chased down.</div>
{bm.methods_html("motion2")}

<h2>11. Defect log</h2>
<p>Fourteen defects were found and corrected. Six by debugging when the detector sat at chance
despite correct forward physics, five by independent adversarial review of the code, and three by
a later audit. Several fixes introduced new defects, which is itself part of the record.</p>
<table><tr><th>#</th><th>Defect</th><th>Area</th><th>What went wrong</th><th>What it corrupted</th></tr>
{rows_def}</table>
<div class="note"><b>The pattern.</b> Every one of these lived in code that had already passed a
narrower test and been described as working. What caught them was looking at a fix from a different
angle than the one that motivated it: forcing each aperture instead of trusting the selector,
measuring a threshold distribution instead of choosing a plausible number, reading what the feature
vector actually contained instead of trusting the function's return value. Simulation results here
should be treated as hypotheses for a phantom to test, not as measurements.</div>

<h2>12. What survived, what did not</h2>
<table><tr><th>Claim</th><th>Status</th></tr>
<tr class="bad"><td>More electrodes make direction accuracy worse</td><td><b>Overturned.</b> Artifact of greedy aperture selection.</td></tr>
<tr class="bad"><td>Span is the dominant lever; longer is better</td><td><b>Overturned.</b> Span was a proxy for placement; a shorter well-placed strip wins.</td></tr>
<tr class="bad"><td>Grades I-II are intrinsically undetectable</td><td><b>Overturned.</b> A placement default, not a limit of the method. Grade II reaches 100%.</td></tr>
<tr class="hi"><td>Direction beats amplitude</td><td>Holds. AUC {n2(AB['direction_only'])} against {n2(AB['amplitude_only'])}.</td></tr>
<tr class="hi"><td>50 dB instrument SNR is sufficient</td><td>Holds. Flat across 50-80 dB.</td></tr>
<tr class="hi"><td>The system is motion-limited, not noise-limited</td><td>Holds, and I predicted it would be retired. It was not.</td></tr>
<tr class="hi"><td>Multi-event capture beats single-void VCUG</td><td>Holds, now on separated sensitivity and specificity with the chance floor shown.</td></tr>
</table>

<h2>13. Open risks</h2>
<ol>
<li><b>Placement precision is the binding constraint</b>, and Study 5 has now confirmed it twice
over. &plusmn;1 cm on a landmark that is not externally visible, on a child who will not hold
still. It decides whether low-grade detection is real in practice, and it has just invalidated the
published locked design.</li>
<li><b>No physical data.</b> No phantom, animal or clinical measurement stands behind any number
here. This is a feasibility envelope, not clinical performance.</li>
<li><b>Motion above about 1 cm.</b> Non-rigid motion turned out <i>not</i> to be the threat
(&sect;10), but displacement amplitude is: beyond 2 cm the device spends a third of its time
abstaining. The residual question is how often a real child exceeds that during a void.</li>
<li><b>An unexplained {_pct(M2['grid']['a0.0_g0.0']['false_retrograde'],1)} false-retrograde floor
at zero motion</b>, which caps achievable specificity and has no identified cause.</li>
<li><b>Absolute impedance magnitudes are not mesh-converged</b> (&sect;8.2). Any hardware sizing
taken from this model inherits that, and more trials will not fix it &mdash; only a finer mesh or a
convergence-corrected estimate will.</li>
<li><b>Contact impedance is rejected only 4.3&times;</b>, not eliminated, leaving 16% residual
sensitivity to budget for.</li>
<li><b>Single excitation frequency in the estimator.</b> Two are solved but frequency is never used
discriminatively &mdash; and &sect;8.4 shows the imaginary part carries real information, so this is
a missed lever rather than a neutral omission.</li>
<li><b>Bilateral reflux is structurally unreportable</b>: the estimator selects one strip, so it
cannot express "both sides", which is a stated clinical requirement.</li>
<li><b>Structured anatomy</b>, not segmented CT; real variation is larger.</li>
<li><b>Freedom to operate.</b> The prior-art patent's independent claims are disjunctive over
bioimpedance <i>or</i> tomography, so "we do not reconstruct an image" defeats only two of twelve
claims. The position rests entirely on never estimating a volume nor comparing one to a control
value &mdash; and the resting-reference baseline currently used reads onto the broadest claim's
language. That is an engineering constraint, not just a legal one.</li>
</ol>
<div class="key"><b>Recommended next step.</b> A layered phantom with a tube analogue, measuring
depth against aperture and the fraction of placements that fail. Those are the two quantities that
decide the product and neither can be settled by more simulation.</div>

</body></html>"""

# ---------------------------------------------------------------- navigation
# The report is now ~1.6 MB across 13 sections and 20-odd subsections. Without
# anchors it can only be read by scrolling, which is not a realistic way to use
# it in a review. Ids and the contents list are generated from the headings
# themselves so they cannot fall out of step with the document.
import re as _re


def _slug(n):
    return "s" + n.replace(".", "_")


def _anchor(m):
    lvl, num, rest = m.group(1), m.group(2), m.group(3)
    return f'<h{lvl} id="{_slug(num)}">{num}{rest}</h{lvl}>'


HTML = _re.sub(r'<h([23])>(\d+(?:\.\d+)?)((?:\.|&nbsp;)[^<]*)</h\1>', _anchor, HTML)

_toc = []
for _m in _re.finditer(r'<h([23]) id="([^"]+)">(\d+(?:\.\d+)?)((?:\.|&nbsp;)[^<]*)</h\1>', HTML):
    _lvl, _id, _num, _rest = _m.groups()
    _title = _re.sub(r"&mdash;.*$", "", _rest.lstrip(". ").replace("&nbsp;", "")).strip()
    _cls = "t2" if _lvl == "2" else "t3"
    _toc.append(f'<li class="{_cls}"><a href="#{_id}"><b>{_num}</b> {_title}</a></li>')

HTML = HTML.replace("<!--TOC-->", f"""
<div class="toc"><b>Contents</b><ul>{''.join(_toc)}</ul></div>""")

# cross-references like &sect;9 become links to the section they name
HTML = _re.sub(r'&sect;(\d+(?:\.\d+)?)',
               lambda m: f'<a href="#{_slug(m.group(1))}">&sect;{m.group(1)}</a>', HTML)

open("FULL_REPORT.html", "w").write(HTML)
print(f"wrote FULL_REPORT.html ({len(HTML)//1024} KB, "
      f"{len(_toc)} headings linked)")
