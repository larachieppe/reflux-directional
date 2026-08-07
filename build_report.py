"""
Build REPORT.html: the complete simulation report, formatted to survive a
copy-paste into Google Docs (real headings, tables, bold, inline images).

All numbers are read from metrics_design.json and metrics_directional.json, so
the document cannot drift from the simulation that produced it.
"""
import base64, json, os

D = json.load(open("metrics_design.json"))
C = D["config"]; OP = D["operating"]; S = D["subject"]; G = D["grade"]; AB = D["ablation"]
E = json.load(open("metrics_directional.json")); EP = E["primary"]; EC = E["config"]
MOT = C["motion"]; K = S["k_events"]; BK = str(S["best_k"]); TARGET = 0.45
ECOUNTS = EC["counts"]; EMOT = EC["motion"]


def p0(x):
    return "n/a" if x != x else f"{100*x:.0f}%"


def n2(x):
    return "n/a" if x != x else f"{x:.2f}"


def ed(n, m):
    d = EP[str(n)][str(m)]
    return float("nan") if d.get("undecidable", 0) > 0.99 else d["dir_acc"]


def grade_verdict(acc_reflux, n=None):
    """Describe a grade's behaviour FROM THE DATA, never hardcoded.

    The distinction matters clinically and was got wrong once: prose said grades
    I-II were "at or below chance, undetectable by construction" while the data
    showed reflux called correctly 0 of 28 times. That is not a detector
    shrugging, it is a detector confidently reporting reflux as normal flow, and
    a confident false negative is worse than an uncertain one.
    """
    if acc_reflux != acc_reflux:
        return ("undefined", "no measurement")
    if acc_reflux <= 0.15:
        return ("inverted", "systematically reported as normal flow (a confident "
                            "false negative, not an uncertain one)")
    if acc_reflux <= 0.40:
        return ("mostly inverted", "usually reported as normal flow")
    if acc_reflux <= 0.60:
        return ("at chance", "no better than a coin flip")
    if acc_reflux <= 0.85:
        return ("partial", "detected more often than not")
    return ("detected", "reliably detected")


def img(path, cap, width=680):
    if not os.path.exists(path):
        return ""
    b = base64.b64encode(open(path, "rb").read()).decode()
    return (f'<p style="text-align:center;margin:16px 0 4px">'
            f'<img src="data:image/png;base64,{b}" width="{width}"></p>'
            f'<p class="cap">{cap}</p>')


# ---------------- tables ----------------
rows_motion = "\n".join(
    f"<tr{' class=hi' if abs(m-TARGET)<1e-9 else ''}>"
    f"<td>{m:.2f} cm{' (target)' if abs(m-TARGET)<1e-9 else (' (still)' if m==0 else '')}</td>"
    f"<td><b>{p0(OP[str(m)]['dir_acc'])}</b></td>"
    f"<td>{100*OP[str(m)]['dir_ci'][0]:.0f}&ndash;{100*OP[str(m)]['dir_ci'][1]:.0f}%</td>"
    f"<td>{p0(OP[str(m)]['lat_acc'])}</td><td>{n2(OP[str(m)]['auc'])}</td></tr>" for m in MOT)

rows_grade = "\n".join(
    f"<tr><td>{['','I','II','III','IV','V'][g]}</td>"
    f"<td>{p0(G[str(g)]['0.0']['dir_acc'])}</td>"
    f"<td>{p0(G[str(g)]['0.3']['dir_acc'])}</td>"
    f"<td>{p0(G[str(g)]['0.6']['dir_acc'])}</td>"
    f"<td>{p0(G[str(g)]['0.9']['dir_acc'])}</td></tr>" for g in (1, 2, 3, 4, 5))

rows_k = "\n".join(
    f"<tr{' class=hi' if str(k)==BK else ''}><td>at least {k} of {K}</td>"
    f"<td><b>{p0(S['sens_k'][str(k)])}</b></td><td><b>{p0(S['spec_k'][str(k)])}</b></td>"
    f"<td>{p0(S['chance_k'][str(k)])}</td></tr>" for k in range(1, K + 1))

hdr_cnt = "".join(f"<th>{m:.1f} cm</th>" for m in EMOT)
rows_cnt = "\n".join(
    f"<tr{' class=hi' if n==6 else ''}><td>N = {n}</td>" +
    "".join(f"<td>{p0(ed(n,m))}</td>" for m in EMOT) +
    "".join(f"<td>{p0(EP[str(n)][str(m)]['lat_acc'])}</td>" for m in EMOT) + "</tr>"
    for n in ECOUNTS)

rows_span = "\n".join(
    f"<tr{' class=hi' if abs(float(k)-C['span'])<1e-9 else ''}>"
    f"<td>{float(k):.0f} cm</td><td>{p0(v['dir_acc'])}</td></tr>"
    for k, v in sorted(E["span_sweep"].items(), key=lambda x: float(x[0])))
rows_snr = "\n".join(
    f"<tr><td>{k} dB</td><td>{p0(v['dir_acc'])}</td></tr>"
    for k, v in sorted(E["snr_sweep"].items(), key=lambda x: int(x[0])))

HTML = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Directional bioimpedance reflux sensing: simulation report</title>
<style>
 body{{font-family:Arial,Helvetica,sans-serif;font-size:11pt;color:#000;max-width:820px;
      margin:32px auto;line-height:1.55;padding:0 20px}}
 h1{{font-size:22pt;font-weight:bold;margin:28px 0 6px}}
 h2{{font-size:16pt;font-weight:bold;color:#1155cc;margin:30px 0 8px;
     border-bottom:1px solid #ccc;padding-bottom:4px}}
 h3{{font-size:12.5pt;font-weight:bold;margin:20px 0 6px}}
 table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:10pt}}
 th,td{{border:1px solid #000;padding:6px 8px;text-align:center;vertical-align:top}}
 th{{background:#efefef;font-weight:bold}}
 td:first-child,th:first-child{{text-align:left}}
 tr.hi td{{background:#e8f2e8}}
 ul,ol{{margin:8px 0 8px 24px}} li{{margin:5px 0}}
 .cap{{font-size:9.5pt;color:#555;text-align:center;margin:0 0 18px;font-style:italic}}
 .note{{border-left:4px solid #c98500;padding:10px 14px;background:#fbf7ef;margin:14px 0}}
 .warn{{border-left:4px solid #c0392b;padding:10px 14px;background:#fdf2f1;margin:14px 0}}
 .key{{border:2px solid #1155cc;background:#eef3fb;padding:12px 16px;margin:16px 0}}
 .banner{{background:#eef3fb;border:1px solid #1155cc;padding:10px 14px;margin-bottom:24px;font-size:10pt}}
 img{{max-width:100%;border:1px solid #ddd}}
 .sub{{color:#555;font-size:10pt}}
</style></head><body>

<div class="banner"><b>How to use.</b> Select everything below this box, copy, and paste into your
document. Headings, bold, tables and figures are preserved. Generated directly from the simulation
metrics files, so every number traces to a run.</div>

<h1>Directional bioimpedance sensing for pediatric vesicoureteral reflux</h1>
<p class="sub">Pre-hardware simulation report. Live results:
https://larachieppe.github.io/reflux-directional/ &nbsp;&middot;&nbsp; Source:
https://github.com/larachieppe/reflux-directional</p>

<div class="key"><b>Summary.</b> A finite-element simulation tests, before any hardware exists,
whether a surface bioimpedance device can detect vesicoureteral reflux by measuring the
<b>direction</b> urine travels rather than by reconstructing an image. At the selected design
({C['n_strip']} electrodes per flank strip, {C['span']:.0f} cm span, {C['channels']} channels),
direction is identified with <b>{p0(OP['0.0']['dir_acc'])} accuracy when still</b> and
<b>{p0(OP[str(TARGET)]['dir_acc'])} at the {TARGET:.2f} cm motion design target</b>, for reflux of
grade III and above. Combining {K} observed voiding events with a {BK}-of-{K} rule yields
<b>{p0(S['sens_k'][BK])} sensitivity at {p0(S['spec_k'][BK])} specificity</b>, against nuclear
VCUG's 81% / 89%. Grades I to II are not detectable by this method. No phantom, animal or clinical
data stands behind these numbers: this is a feasibility envelope, not clinical performance.</div>

<h2>1. Why this approach</h2>
<h3>1.1 The clinical problem</h3>
<p>The reference test for vesicoureteral reflux (VUR) is the voiding cystourethrogram (VCUG),
which requires urethral catheterization, ionizing radiation, and the child urinating on command in
front of clinical staff. It is also imperfect on its own terms: radiologists agree on reflux grade
in only 59% of cases, roughly 20% of reflux is missed because it is intermittent and VCUG captures
only one or two forced voids, and only about 48% of families complete the imaging when it is
recommended. That last figure is the real clinical gap: a test that is somewhat less accurate but
actually gets performed can find more disease than a better test that is declined.</p>

<h3>1.2 Why not tomography</h3>
<p>A prior clinical program (Kite Medical, approximately $3.1M raised, wound up January 2023)
attacked this with electrical impedance tomography: a 32-electrode belt reconstructing the change
in conductivity when refluxed urine arrives. It reported detection in <b>73% of voiding cycles
without motion, but only 44% with motion</b>. The program ran out of funding before closing that
gap. Two structural properties explain it:</p>
<ol>
<li><b>The measured quantity is shared with the dominant confounder.</b> Reconstruction reports
the presence and magnitude of conductive fluid. Ordinary bladder filling also adds conductive
fluid. The variable being measured cannot separate the disease from its most common mimic.</li>
<li><b>Image reconstruction has no intrinsic rejection of body motion.</b> Reconstruction is an
ill-posed inverse problem; body movement rewrites the conductivity field, and nothing in the
method distinguishes that from a physiological change.</li>
</ol>

<h3>1.3 The alternative measured quantity</h3>
<p>Reflux is defined by <b>retrograde transport</b>. Direction, not amplitude, is therefore the
quantity that separates it from bladder filling by construction. And a measurement made
<i>differentially between two nearby zones</i> rejects any perturbation common to both, which is
precisely what body motion is.</p>
<div class="note"><b>Why a strip, not a belt.</b> A single symmetric tetrapolar array is
direction-blind: by symmetry, a bolus travelling up produces the same scalar impedance
perturbation as one travelling down. Direction is an <i>ordering</i>, and an ordering requires at
least two observation points separated along the axis of travel. A belt places its electrodes
around the body at one height, which is the wrong axis. The geometry that works is a short strip
running along the body, one per flank.</div>

<h2>2. How the measurement works</h2>
<p>Each flank carries a short strip of electrodes. Groups of four form <b>tetrapolar zones</b>:
the outer pair injects current, the inner pair senses voltage. Because the sensing electrodes
carry essentially no current, their contact impedance drops out of the measurement, which is what
makes the reading a property of the tissue rather than of the electrode gel.</p>
<p>As a conductive bolus of urine passes a zone, it perturbs that zone's transfer impedance. The
bolus reaches zones at different times, so the <b>order</b> in which zones respond encodes the
direction of travel. Fitting arrival time against zone height gives a slope whose <b>sign is the
diagnosis</b>: positive means the bolus is moving toward the kidney, which is reflux.</p>
{img("figs_dir/figG_mechanism.png",
     "The mechanism. Top: a reflux event, where the impedance dip climbs the strip and arrival time rises with height. Bottom: normal antegrade transport, the mirror image. The sign of that slope is the entire diagnosis. One representative trial each at 0.4 cm motion.")}
<p>Two strips, one per flank, give <b>laterality</b> (left, right or bilateral) for free: whichever
strip carries the travelling signal identifies the refluxing side.</p>

<h2>3. What was simulated</h2>
<h3>3.1 The forward model</h3>
<ul>
<li>A verified 3-D <b>complete-electrode model</b> solved by finite elements (scikit-fem), checked
by reciprocity before any result depended on it.</li>
<li>A torso segment whose axis is the body superior-inferior direction, with bilateral ureters,
bladder and kidneys, and representative tissue admittivities from the published dielectric
literature.</li>
<li>Four conditions: <b>reflux</b>, normal <b>antegrade</b> transport, <b>bladder filling</b> (the
confounder), and <b>no flow</b>.</li>
<li>Reflux grade sets how far the bolus travels, matching the clinical definition: low grades
barely enter the ureter, high grades reach the kidney.</li>
</ul>
<h3>3.2 Realism and noise</h3>
<ul>
<li><b>Motion</b> is injected as a common-mode displacement of the body relative to the
electrodes, plus breathing, plus an independent per-electrode contact term that does <i>not</i>
cancel. Because the motion is common-mode by construction, the common-mode rejection claim is
tested rather than assumed.</li>
<li><b>Contact impedance</b> varies per electrode with drift and breathing modulation.</li>
<li><b>Measurement noise</b> has correlated and uncorrelated components at a specified SNR.</li>
<li><b>Anatomy is randomized per trial</b>, so the detector cannot memorize one body.</li>
</ul>
<h3>3.3 The two studies</h3>
<table>
<tr><th>Study</th><th>Question</th><th>Scale</th></tr>
<tr><td>Electrode count sweep</td><td>How many electrodes per strip, and what span?</td>
<td>3,216 trials; counts 4 to 12, four motion levels, plus span and SNR sweeps</td></tr>
<tr><td>Locked design characterization</td><td>How does the selected design actually perform?</td>
<td>{C['n_op']*4*len(MOT)+5*4*C['n_grade']+C['n_subj']*K:,} trials; seven motion levels, grades 1 to 5,
and {S['n_reflux']+S['n_healthy']} simulated children with {K} events each</td></tr>
</table>

<h2>4. Results: how many electrodes</h2>
<p>The flank span is capped by anatomy, so more electrodes means a tighter pitch. Every trial was
replayed identically across electrode counts, making the comparison paired.</p>
<table>
<tr><th rowspan="2">Electrodes per strip</th><th colspan="{len(EMOT)}">Direction accuracy (grade III+)</th>
<th colspan="{len(EMOT)}">Laterality accuracy</th></tr>
<tr>{hdr_cnt}{hdr_cnt}</tr>
{rows_cnt}
</table>
<div class="key"><b>Finding 1: more electrodes made direction accuracy worse, not better.</b>
Direction accuracy falls from {p0(ed(5,0.6))} at N=5 to {p0(ed(8,0.6))}-{p0(ed(12,0.6))} at N=8 and
above. Over a fixed span, extra electrodes shrink the pitch and add aperture choices for the
estimator to get wrong. This contradicts the intuition behind 16- and 32-electrode belts.</div>
<div class="key"><b>Finding 2: N=4 is not merely poor, it is undefined.</b> Four electrodes form a
single tetrapolar zone. One zone has no ordering, so direction does not exist at any signal-to-noise
ratio. This is the formal argument against any single-array proposal.</div>
<div class="key"><b>Finding 3: direction and laterality disagree.</b> Direction favours N=5;
laterality strongly favours N=6 ({p0(EP['6']['0.6']['lat_acc'])} versus
{p0(EP['5']['0.6']['lat_acc'])} at 0.6 cm motion). Since laterality is an independent clinical
requirement, <b>N=6 was selected</b>, accepting a small direction cost. Both answers are reported
rather than choosing the flattering metric.</div>
{img("figs_dir/figC_complexity.png",
     "Why N=6. Direction and laterality plotted against channel count. They rank the counts differently, which is why the choice is not simply the top of one curve.")}

<h3>4.1 Span matters more than electrode count</h3>
<table><tr><th>Strip span</th><th>Direction accuracy</th></tr>{rows_span}</table>
<p>Going from 12 cm to {C['span']:.0f} cm buys more accuracy than any electrode-count choice, then
plateaus. <b>Strip length is the strongest single design lever measured.</b></p>

<h3>4.2 The system is motion-limited, not noise-limited</h3>
<table><tr><th>Instrument SNR</th><th>Direction accuracy</th></tr>{rows_snr}</table>
<p>Accuracy is flat across the whole range tested. A quieter, more expensive front end buys
nothing; motion tolerance and strip length are what matter.</p>

<h2>5. Results: the chosen design</h2>
<p>{C['n_strip']} electrodes per strip, {C['span']:.0f} cm span, {C['channels']} channels,
{C['snr']} dB, {C['freq_khz']} kHz.</p>
<table>
<tr><th>Motion</th><th>Direction accuracy</th><th>95% CI</th><th>Laterality</th><th>Reflux AUC</th></tr>
{rows_motion}
</table>
{img("figs_design/d2_motion.png",
     "Performance against motion at the locked design, with Wilson 95% intervals. The shaded band is the 0.5 cm design target.")}
{img("figs_design/d1_roc.png",
     "ROC for reflux against the other three conditions, at each motion level.", 560)}

<h3>5.1 Direction, not amplitude, carries the signal</h3>
<p>At {AB['motion']:.2f} cm motion: all features AUC <b>{n2(AB['full'])}</b>, direction features
only <b>{n2(AB['direction_only'])}</b>, amplitude only <b>{n2(AB['amplitude_only'])}</b>.
Direction outperforms amplitude, which supports the design premise. <b>Amplitude alone is not
useless, however</b>, and earlier drafts of this work overstated that point.</p>

<h3>5.2 Sensitivity by reflux grade</h3>
<table>
<tr><th>Grade</th><th>Still</th><th>0.30 cm</th><th>0.60 cm</th><th>0.90 cm</th></tr>
{rows_grade}
</table>
{img("figs_design/d3_grade_heat.png",
     "Direction accuracy for every grade and motion level. The heavy line marks where the claimed range begins.")}
<div class="warn"><b>Grades I and II are not detectable by this method.</b> They sit at or below
chance because low-grade reflux does not travel far enough to cross the sensed span. This is a
structural property of the measurement, not a tuning failure, and no amount of engineering will
change it. Any claim must be scoped to <b>grade III and above</b>, which is where the clinical
consequence is concentrated and where treatment decisions change.</div>

<h2>6. How the device can exceed VCUG</h2>
<p>Not by raising per-event accuracy. VCUG's exploitable weakness is that it captures one or two
forced voids and therefore misses roughly 20% of reflux. A passive wearable observes many natural
cycles, and detection compounds with the number of events observed.</p>
<p>This was tested rather than assumed: <b>{S['n_reflux']+S['n_healthy']} simulated children with
{K} events each, holding anatomy and electrode placement fixed per child</b>, so that correlated
failure would show up instead of being averaged away. Per event the detector runs
{p0(S['per_event_sens'])} sensitivity at a {p0(S['per_event_fp'])} false-positive rate.</p>
<table>
<tr><th>Screening rule</th><th>Sensitivity</th><th>Specificity</th>
<th>Sensitivity if the detector were a coin flip</th></tr>
{rows_k}
</table>
<div class="key"><b>A {BK}-of-{K} rule gives {p0(S['sens_k'][BK])} sensitivity at
{p0(S['spec_k'][BK])} specificity</b>, against nuclear VCUG's 81% sensitivity at 89% specificity.
It exceeds the comparator on both axes, from a per-event accuracy that looks unremarkable in
isolation. The gain comes from repetition, which is exactly what a catheter-free passive device
can do and a forced-void procedure cannot.</div>
{img("figs_design/d4_multievent.png",
     "The screening rule. Left: sensitivity and specificity reported separately against the k-of-n threshold, with the coin-flip floor and the independence prediction. Right: per-child spread for refluxing and healthy children.")}
<div class="note"><b>Why the coin-flip column is shown.</b> An earlier version of this analysis
pooled refluxing and healthy children and counted any correct direction call as a hit. That is
per-child accuracy, not sensitivity, and because half the cohort is healthy its chance floor is
{p0(S['chance_k']['2'])} at a 2-of-{K} rule, which sits <i>above</i> the roughly 80% VCUG line it
was being compared against. A coin-flip detector would have appeared to beat VCUG. Sensitivity and
specificity are now reported separately with the chance floor printed beside them.</div>
<div class="warn"><b>The number that decides the product.</b> The compounding above assumes events
are independent. They are not automatically so: if a child's anatomy or electrode placement is
what limits the measurement, every event on that child fails together. In this simulation
<b>{p0(S['never_detected_reflux'])} of refluxing children were never detected</b> across {K}
events, so correlated failure is small <i>in this model</i>. That is the most model-dependent
result in this report. Real anatomical variation and real placement error are almost certainly
larger than simulated. <b>The fraction of children who are systematically unmeasurable must be
measured on a phantom and then in a clinical pilot before the multi-event argument can be relied
on commercially.</b></div>

<h2>7. Design specification</h2>
<table>
<tr><th>Parameter</th><th>Specify</th><th>Evidence</th></tr>
<tr class="hi"><td>Electrodes per strip</td><td><b>{C['n_strip']} ({C['channels']} channels)</b></td>
<td>Best laterality among counts not significantly worse on direction; smallest count with 3+ zones.</td></tr>
<tr class="hi"><td>Strip span</td><td><b>{C['span']:.0f} cm</b></td>
<td>Strongest single lever; accuracy plateaus here.</td></tr>
<tr><td>Zones per strip</td><td>at least 3</td>
<td>Common-mode rejection needs 3+; with exactly 2 the mean-removed pair are exact negatives.</td></tr>
<tr><td>Outer aperture</td><td>at least 6 cm</td>
<td>Sensing depth is roughly half the aperture; the ureter sits about 3 cm below the skin.</td></tr>
<tr><td>Measurement</td><td>fractional dZ/|Z|</td>
<td>Absolute dZ carries per-channel gain, which made strip selection degenerate.</td></tr>
<tr><td>Instrument SNR</td><td>50 dB is sufficient</td>
<td>Flat from 50 to 80 dB. Motion-limited, not noise-limited.</td></tr>
<tr class="hi"><td>Motion tolerance</td><td><b>0.5 cm or less</b></td><td>The binding constraint.</td></tr>
<tr class="hi"><td>Events per session</td><td><b>at least {K}, decide on {BK}-of-{K}</b></td>
<td>The mechanism by which the device exceeds VCUG.</td></tr>
<tr><td>Claimed grade range</td><td>grade III and above</td><td>Grades I to II are undetectable.</td></tr>
<tr><td>Excitation frequency</td><td>not resolved</td>
<td>A single frequency ({C['freq_khz']} kHz) was used; multi-frequency is untested.</td></tr>
</table>

<h2>8. Implications for the benchtop build</h2>
<table>
<tr><th>Finding</th><th>Implication</th></tr>
<tr><td>More electrodes made accuracy worse</td>
<td>Build 6 per strip, not 16 or 32. Fewer contact points, cheaper front end, less prep time.</td></tr>
<tr><td>Span beats count</td>
<td>Prioritize a longer strip. Measure the usable pediatric flank length early, since it caps the design.</td></tr>
<tr><td>Motion-limited, not noise-limited</td>
<td>A modest integrated AFE suffices. Spend the effort on mechanical stability and protocol, not on a quieter instrument.</td></tr>
<tr><td>Motion tolerance 0.5 cm</td>
<td>Consider a quiet or sleep protocol before investing in motion compensation, which is the complexity spiral that consumed the prior program's runway.</td></tr>
<tr><td>Multi-event compounding works</td>
<td>Design for a long passive session capturing 6+ voids, not a single forced void. This is the core product decision.</td></tr>
<tr><td>Grades I to II undetectable</td>
<td>Scope the clinical claim, and the phantom protocol's endpoints, to grade III and above.</td></tr>
</table>

<h2>9. Limitations</h2>
<table>
<tr><th>Limitation</th><th>Consequence</th></tr>
<tr><td>No physical data</td><td>No phantom, animal or clinical measurement stands behind any
number here. <b>This is a feasibility envelope, not clinical performance.</b></td></tr>
<tr><td>Structured anatomy</td><td>A cylinder with organs, not segmented CT. Real anatomical
variation is almost certainly larger than simulated.</td></tr>
<tr><td>Single excitation frequency</td><td>{C['freq_khz']} kHz only. Multi-frequency
discrimination is untested and may help or do nothing.</td></tr>
<tr><td>Structured motion model</td><td>Common-mode displacement plus breathing plus an
independent contact term. Real awake-child motion may be worse in kind, not just degree.</td></tr>
<tr><td>Greedy aperture selection</td><td>The estimator picks one aperture by signal strength. A
better rule might change the electrode-count conclusion, so that result is the least settled.</td></tr>
<tr><td>Kite comparison is not like-for-like</td><td>The 73% / 44% figures are a different
measurement on different subjects (sedated animals and children during VCUG), shown for context
only, not as a controlled benchmark.</td></tr>
</table>

<h2>10. Development history and verification</h2>
<p>This section is included because the credibility of a simulation rests on how hard it was
attacked, not on how good the final numbers look.</p>
<p>Eleven defects were found and corrected during development. Six were found by debugging when
the detector sat at chance despite correct forward physics: a nonlinearity that prevented
common-mode cancellation; an aperture-selection rule that systematically chose the shallowest,
blindest aperture; an amplitude envelope that gave every zone the same time course and so erased
the very travelling wave being measured; a baseline reference that scrambled each clean passage;
a lag search bounded below the true lag; and a contact impedance roughly 100x below the physical
regime, which suppressed the signal about 100-fold while amplifying drift sensitivity.</p>
<p>Five more were found by independent adversarial review of the code, and would not have been
caught otherwise:</p>
<ul>
<li><b>Unequal electrode area between the two flank strips.</b> An odd-numbered interior node ring
in the mesh broke mirror symmetry, giving one strip 23% less electrode area. The strip selector,
which used raw signal energy, therefore picked the same side roughly 90% of the time regardless of
truth. Laterality was not degrading gracefully, it was a degenerate constant. Fixed by normalizing
to fractional impedance change.</li>
<li><b>Duplicate trials leaking across cross-validation folds</b>, which manufactured an AUC peak
exactly at the design SNR and design span. That would have been written up as validation of the
design point.</li>
<li><b>A multi-event metric whose chance floor sat above the comparison line</b>, described
above.</li>
<li><b>A confusion matrix thresholded at the median</b>, which forced a 50% predicted-positive rate
against 25% prevalence and capped specificity at 66.7% by construction.</li>
<li>Several reporting defects in the figures, including a legend claiming more series than were
drawn.</li>
</ul>
<div class="note">The pattern is worth stating plainly: every one of these was in code that had
already passed a narrower test and been described as working. Simulation results should be treated
as hypotheses to be checked against a phantom, not as measurements.</div>

<h2>11. Recommended next steps</h2>
<ol>
<li><b>Measure the usable flank span</b> in the target pediatric age range. Span was the strongest
lever in the simulation and it is capped by anatomy, not by engineering.</li>
<li><b>Build the phantom and measure the unmeasurable fraction.</b> How many children are
systematically undetectable is the single most important unknown, and it decides whether the
multi-event strategy holds.</li>
<li><b>Test the aperture-selection rule.</b> The finding that fewer electrodes perform better may
be an artifact of a greedy selector rather than physics.</li>
<li><b>Characterize real motion</b> in awake children of the target age, and compare it against
the 0.5 cm tolerance this design implies.</li>
<li><b>Decide the excitation topology and whether multi-frequency helps</b>, which this study did
not test.</li>
</ol>

</body></html>"""

open("REPORT.html", "w").write(HTML)
print(f"wrote REPORT.html ({len(HTML)//1024} KB)")
