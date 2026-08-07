"""
Build FULL_REPORT.html: everything built since the two-strip decision.

Covers all four studies, the corrected numbers, and the complete defect log,
because three headline claims were published and then overturned and a reader
deciding whether to build hardware needs to see that history, not just the
current figures.
"""
import base64, json, os

import build_methods as bm

D = json.load(open("metrics_design.json"))
E = json.load(open("metrics_directional.json"))
P = json.load(open("metrics_placement.json"))
T = json.load(open("metrics_tolerance.json")) if os.path.exists("metrics_tolerance.json") else None
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
    f"<tr{' class=hi' if k == '10_0.34' else (' class=bad' if k == '16_0.50' else '')}>"
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
 ("Abstention scored as a wrong answer","stats","dir_acc penalised abstention, but the abstain gate needs >=3 zones, so N=5 was structurally exempt from it.","Made N=5 appear to beat N=8 under motion (79% vs 71%). On calls actually made, N=8 leads 93% to 79%. Same failure mode as defect 9: a pooled metric flattering the wrong option."),
]
rows_def = "\n".join(
    f"<tr><td>{i+1}</td><td><b>{t}</b></td><td>{c}</td><td>{w}</td><td>{e}</td></tr>"
    for i,(t,c,w,e) in enumerate(DEFECTS))

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
 .methods table.mm-t th,.methods table.mm-t td{{text-align:left}}
</style></head><body>

<h1>Directional bioimpedance sensing for pediatric vesicoureteral reflux</h1>
<p class="sub">Complete simulation report, covering all work since the two-strip design decision.
Live: https://larachieppe.github.io/reflux-directional/ &middot;
Source: https://github.com/larachieppe/reflux-directional</p>

<div class="key"><b>What this is.</b> A finite-element simulation testing, before hardware exists,
whether a surface bioimpedance device can detect vesicoureteral reflux by measuring the
<b>direction</b> urine travels rather than reconstructing an image. Four studies are reported:
electrode count, locked-design characterization, strip placement, and misplacement tolerance.
Two further studies, placement precision and non-rigid respiratory motion, are running or queued
and their methods are stated in section 7 ahead of their results.
Section 2 gives the shared forward model, the estimator, and the statistics, so that every study
below can be read as a statement of what it changed rather than a self-contained method.
<b>Fourteen defects were found and fixed along the way, and three published headline claims were
subsequently overturned by measurement.</b> That history is reported here alongside the results,
because it bears directly on how much weight the numbers can carry.</div>

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

<h2>3. Study 1: how many electrodes</h2>
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

<h2>4. Study 2: the locked design</h2>
<p>{C['n_strip']} electrodes per strip, {C['span']:.0f} cm span, {C['channels']} channels,
{C['snr']} dB, {C['freq_khz']} kHz.</p>
<table><tr><th>Motion</th><th>Direction (old &rarr; new)</th><th>Laterality</th><th>AUC</th><th>Abstain</th></tr>
{rows_design}</table>
{img("figs_design/d2_motion.png","Performance against motion at the locked design.")}
<h3>3.1 The multi-event screening rule</h3>
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

<h2>5. Study 3: where the strip sits</h2>
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

<h2>6. Study 4: misplacement tolerance</h2>
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

<h2>7. Studies 5 and 6: in progress</h2>
<p>Two further studies are running or queued at the time of writing. Their designs
are fixed and are stated in full below, so the methods can be reviewed before the
results exist. No results are reported for them here.</p>
{bm.methods_html("precision")}
{bm.methods_html("motion2")}

<h2>8. Defect log</h2>
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

<h2>9. What survived, what did not</h2>
<table><tr><th>Claim</th><th>Status</th></tr>
<tr class="bad"><td>More electrodes make direction accuracy worse</td><td><b>Overturned.</b> Artifact of greedy aperture selection.</td></tr>
<tr class="bad"><td>Span is the dominant lever; longer is better</td><td><b>Overturned.</b> Span was a proxy for placement; a shorter well-placed strip wins.</td></tr>
<tr class="bad"><td>Grades I-II are intrinsically undetectable</td><td><b>Overturned.</b> A placement default, not a limit of the method. Grade II reaches 100%.</td></tr>
<tr class="hi"><td>Direction beats amplitude</td><td>Holds. AUC {n2(AB['direction_only'])} against {n2(AB['amplitude_only'])}.</td></tr>
<tr class="hi"><td>50 dB instrument SNR is sufficient</td><td>Holds. Flat across 50-80 dB.</td></tr>
<tr class="hi"><td>The system is motion-limited, not noise-limited</td><td>Holds, and I predicted it would be retired. It was not.</td></tr>
<tr class="hi"><td>Multi-event capture beats single-void VCUG</td><td>Holds, now on separated sensitivity and specificity with the chance floor shown.</td></tr>
</table>

<h2>10. Open risks</h2>
<ol>
<li><b>Placement precision is the binding constraint.</b> &plusmn;1 cm on an invisible landmark, on a
child. This decides whether low-grade detection is real in practice.</li>
<li><b>No physical data.</b> No phantom, animal or clinical measurement stands behind any number
here. This is a feasibility envelope, not clinical performance.</li>
<li><b>Motion is modelled as a rigid translation</b>, which is the one perturbation across-zone mean
subtraction provably nulls. Real respiratory motion is a craniocaudal gradient and would not cancel
as cleanly. This is the most likely place the model flatters the design.</li>
<li><b>Single excitation frequency.</b> Multi-frequency is untested.</li>
<li><b>Structured anatomy</b>, not segmented CT; real variation is larger.</li>
</ol>
<div class="key"><b>Recommended next step.</b> A layered phantom with a tube analogue, measuring
depth against aperture and the fraction of placements that fail. Those are the two quantities that
decide the product and neither can be settled by more simulation.</div>

</body></html>"""

open("FULL_REPORT.html", "w").write(HTML)
print(f"wrote FULL_REPORT.html ({len(HTML)//1024} KB)")
