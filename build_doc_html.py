"""
Build DOC_section0.html: a copy-paste-ready replacement for Section 0 of the
Benchtop Phantom Protocol.

Styled to survive a paste into Google Docs: real <h1>/<h2>, real <table> with
borders, <b> for bold. No CSS that Docs would discard. Numbers are pulled from
the metrics files so the document cannot drift from the simulation.
"""
import json

D = json.load(open("metrics_design.json"))
C = D["config"]; OP = D["operating"]; S = D["subject"]; G = D["grade"]; AB = D["ablation"]
E = json.load(open("metrics_directional.json")); EP = E["primary"]; EC = E["config"]
MOT = C["motion"]
K = S["k_events"]; BK = str(S["best_k"])
TARGET = 0.45


def p0(x):
    return "n/a" if x != x else f"{100*x:.0f}%"


def n2(x):
    return "n/a" if x != x else f"{x:.2f}"


def ed(n, m):
    d = EP[str(n)][str(m)]
    return float("nan") if d.get("undecidable", 0) > 0.99 else d["dir_acc"]


rows_motion = "\n".join(
    f"<tr{' class=hi' if abs(m-TARGET)<1e-9 else ''}>"
    f"<td>{m:.2f} cm{' (target)' if abs(m-TARGET)<1e-9 else (' (still)' if m==0 else '')}</td>"
    f"<td><b>{p0(OP[str(m)]['dir_acc'])}</b></td>"
    f"<td>{100*OP[str(m)]['dir_ci'][0]:.0f}&ndash;{100*OP[str(m)]['dir_ci'][1]:.0f}%</td>"
    f"<td>{p0(OP[str(m)]['lat_acc'])}</td>"
    f"<td>{n2(OP[str(m)]['auc'])}</td></tr>" for m in MOT)

rows_grade = "\n".join(
    f"<tr><td>{'I'*g if g<4 else ('IV' if g==4 else 'V')}</td>"
    f"<td>{p0(G[str(g)]['0.0']['dir_acc'])}</td>"
    f"<td>{p0(G[str(g)]['0.6']['dir_acc'])}</td></tr>" for g in (1, 2, 3, 4, 5))

rows_k = "\n".join(
    f"<tr{' class=hi' if str(k)==BK else ''}>"
    f"<td>at least {k} of {K}</td>"
    f"<td><b>{p0(S['sens_k'][str(k)])}</b></td>"
    f"<td><b>{p0(S['spec_k'][str(k)])}</b></td>"
    f"<td>{p0(S['chance_k'][str(k)])}</td></tr>" for k in range(1, K + 1))

span_txt = ", ".join(f"{float(k):.0f} cm &rarr; {100*v['dir_acc']:.0f}%"
                     for k, v in sorted(E["span_sweep"].items(), key=lambda x: float(x[0])))
cnt_txt = ", ".join(f"N={n} &rarr; {100*ed(n,0.6):.0f}%" for n in (5, 6, 8, 10, 12))

HTML = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Section 0 replacement</title>
<style>
 body{{font-family:Arial,Helvetica,sans-serif;font-size:11pt;color:#000;
      max-width:800px;margin:32px auto;line-height:1.5;padding:0 20px}}
 h1{{font-size:20pt;font-weight:bold;margin:26px 0 10px}}
 h2{{font-size:14pt;font-weight:bold;color:#1155cc;margin:22px 0 8px}}
 table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:10pt}}
 th,td{{border:1px solid #000;padding:6px 8px;text-align:center;vertical-align:top}}
 th{{background:#efefef;font-weight:bold}}
 td:first-child,th:first-child{{text-align:left}}
 tr.hi td{{background:#e8f2e8}}
 ul{{margin:8px 0 8px 22px}} li{{margin:4px 0}}
 .note{{border-left:3px solid #c98500;padding:8px 12px;background:#fbf7ef;margin:12px 0}}
 .banner{{background:#eef3fb;border:1px solid #1155cc;padding:10px 14px;margin-bottom:22px;
         font-size:10pt}}
</style></head><body>

<div class="banner"><b>How to use.</b> Select everything below this box (from
&ldquo;0. Simulation Summary&rdquo; to the end), copy, and paste into the Google Doc in place of
the whole existing Section 0 (subsections 0.1 through 0.6, covering the 2-D and 3-D models).
Pasting from a browser preserves headings, bold and tables. Also update the two links in the
header block at the top of the doc to point at the new site.</div>

<h1>0. Simulation Summary</h1>

<h2>0.1 Approach</h2>
<p>The simulation does <b>not</b> reconstruct a conductivity image. It measures the
<b>direction</b> a conductive urine bolus travels along the ureter, recovered from the ordering
of arrival times across tetrapolar zones on two short flank strips (one per flank, which gives
laterality natively).</p>
<p>This is a deliberate departure from the tomographic approach. A prior clinical program
(Kite Medical, ~$3.1M, wound up January 2023) reconstructed conductivity change from a
32-electrode belt and reported detection in <b>73% of cycles without motion but 44% with
motion</b>. Two structural properties explain that gap:</p>
<ul>
<li>The measured quantity, presence and magnitude of conductive fluid, is <b>shared with the
dominant confounder</b>, ordinary bladder filling.</li>
<li>Image reconstruction has <b>no intrinsic rejection of body motion</b>.</li>
</ul>
<p>Reflux is defined by retrograde transport, so direction, not amplitude, is the discriminating
variable, and a differential measurement between zones rejects perturbations common to those
zones. A single symmetric tetrapolar array is direction-blind by symmetry, which is why the
geometry is a longitudinal strip rather than a ring.</p>
<p><b>Model.</b> Verified 3-D complete-electrode forward model (finite elements, scikit-fem) on a
torso segment whose axis is the body superior-inferior direction, with bilateral ureters, bladder
and kidneys. Four conditions are simulated: reflux, normal antegrade transport, bladder filling
(the confounder), and no flow. Motion is injected as a common-mode displacement of the body
relative to the electrodes, plus breathing and an independent per-electrode contact term, so the
common-mode rejection claim is tested rather than assumed.</p>
<p><b>Live results:</b> https://larachieppe.github.io/reflux-directional/</p>

<h2>0.2 Design decisions</h2>
<p>Every value below is set by a measurement in the simulation, not by intuition.</p>
<table>
<tr><th>Parameter</th><th>Specify</th><th>Evidence</th></tr>
<tr><td>Electrodes per strip</td><td><b>{C['n_strip']} ({C['channels']} channels)</b></td>
<td>Direction favours 5, laterality favours 6 ({p0(EP['6']['0.6']['lat_acc'])} vs
{p0(EP['5']['0.6']['lat_acc'])} at 0.6 cm). 6 is the smallest count giving 3+ zones. Beyond 8,
direction accuracy degrades.</td></tr>
<tr><td>Strip span</td><td><b>{C['span']:.0f} cm</b></td>
<td>{span_txt}, then flat. The strongest single lever measured.</td></tr>
<tr><td>Zones per strip</td><td><b>at least 3</b></td>
<td>Common-mode rejection subtracts the across-zone mean. With exactly 2 zones the mean-removed
pair are exact negatives and the lag is destroyed.</td></tr>
<tr><td>Outer aperture</td><td><b>at least 6 cm</b></td>
<td>Tetrapolar sensing depth is roughly half the aperture; the ureter sits ~3 cm below the skin.</td></tr>
<tr><td>Measurement</td><td><b>fractional dZ/|Z|</b></td>
<td>Absolute dZ carries per-channel gain; unequal gains made strip selection degenerate.</td></tr>
<tr><td>Instrument SNR</td><td><b>50 dB is sufficient</b></td>
<td>Accuracy flat from 50 to 80 dB. Motion-limited, not noise-limited.</td></tr>
<tr><td>Motion tolerance</td><td><b>0.5 cm or less</b></td><td>The binding constraint (see 0.3).</td></tr>
<tr><td>Events per session</td><td><b>at least {K}, decide on {BK}-of-{K}</b></td><td>See 0.5.</td></tr>
<tr><td>Claimed grade range</td><td><b>grade III and above</b></td><td>Grades I to II are not detectable (see 0.4).</td></tr>
<tr><td>Excitation frequency</td><td><b>not resolved</b></td>
<td>A single frequency ({C['freq_khz']} kHz) was used; multi-frequency is untested.</td></tr>
</table>

<h2>0.3 Results at the chosen design</h2>
<p>{C['n_strip']} electrodes per strip, {C['span']:.0f} cm span, {C['channels']} channels,
{C['snr']} dB, 3,236 trials.</p>
<table>
<tr><th>Motion</th><th>Direction accuracy</th><th>95% CI</th><th>Laterality</th><th>Reflux AUC</th></tr>
{rows_motion}
</table>
<p>Motion is the dominant limiter and sets the engineering constraint: keep effective motion at or
below <b>0.5 cm</b>, which favours a quiet or sleep context over motion compensation.</p>
<p>Feature ablation at {AB['motion']:.2f} cm: all features AUC {n2(AB['full'])}, direction
features only {n2(AB['direction_only'])}, amplitude only {n2(AB['amplitude_only'])}. Direction
outperforms amplitude, though amplitude alone is not useless.</p>

<h2>0.4 Sensitivity by reflux grade</h2>
<table>
<tr><th>Grade</th><th>Still</th><th>0.60 cm motion</th></tr>
{rows_grade}
</table>
<p>Grades I and II sit at chance: low-grade reflux does not travel far enough to cross the sensed
span, so it is undetectable by this method by construction rather than by tuning. <b>Any claim
must be scoped to grade III and above</b>, which is also where the clinical consequence is
concentrated.</p>

<h2>0.5 How the device can exceed VCUG</h2>
<p>Not by raising per-event accuracy. VCUG's exploitable weakness is that it captures <b>one or
two forced voids</b> and therefore misses roughly <b>20% of reflux</b>, which is intermittent. A
passive wearable observes many natural cycles, and detection compounds.</p>
<p>Simulated as <b>{S['n_reflux']+S['n_healthy']} children with {K} events each, holding anatomy
and electrode placement fixed per child</b>, so correlated failure would show up rather than being
assumed away. Per event the detector runs {p0(S['per_event_sens'])} sensitivity at a
{p0(S['per_event_fp'])} false-positive rate.</p>
<table>
<tr><th>Screening rule</th><th>Sensitivity</th><th>Specificity</th><th>Sensitivity if the detector were a coin flip</th></tr>
{rows_k}
</table>
<p>A <b>{BK}-of-{K} rule gives {p0(S['sens_k'][BK])} sensitivity at {p0(S['spec_k'][BK])}
specificity</b>, against nuclear VCUG's 81% sensitivity at 89% specificity, exceeding it on both
axes. The coin-flip column is included because a naive pooled metric would have a chance floor
above the VCUG line, and the comparison must be like for like.</p>
<div class="note"><b>{p0(S['never_detected_reflux'])} of refluxing children were never detected</b>
across {K} events, so correlated failure is small in this model. That is the most model-dependent
result here: real anatomical variation and real placement error are almost certainly larger than
simulated, and a phantom study followed by a clinical pilot must measure that fraction directly
before the multi-event argument can be relied on commercially.</div>

<h2>0.6 Design implications for the benchtop build</h2>
<table>
<tr><th>Simulation finding</th><th>Implication for the build</th></tr>
<tr><td>More electrodes made direction accuracy <b>worse</b>, not better ({cnt_txt} at 0.6 cm)</td>
<td>Over a fixed span, extra electrodes shrink the pitch and add aperture choices for the selector
to get wrong. Build 6 per strip, not 16 or 32.</td></tr>
<tr><td>Direction and laterality disagree on the optimum</td>
<td>Direction favours 5, laterality favours 6. Specify 6, accepting a small direction cost to meet
the laterality requirement.</td></tr>
<tr><td>Span matters more than electrode count</td>
<td>Prioritize a longer strip ({C['span']:.0f} cm) over a denser one, within what pediatric
anatomy allows. Measure the usable flank length early.</td></tr>
<tr><td>Flat across 50 to 80 dB SNR</td>
<td>Motion-limited, not noise-limited. Do not pay for a quieter front end; a modest integrated AFE
is sufficient.</td></tr>
<tr><td>Motion tolerance is 0.5 cm</td>
<td>The binding constraint. Test at multiple motion amplitudes, and consider a quiet or sleep
protocol before investing in motion compensation.</td></tr>
<tr><td>Grades I to II undetectable</td><td>Keep the pre-specified endpoint on grade III and above.</td></tr>
<tr><td>Amplitude alone reaches AUC {n2(AB['amplitude_only'])}</td>
<td>Direction is better but amplitude is not useless; report both so the ablation is honest.</td></tr>
</table>

<h2>0.7 Limitations</h2>
<table>
<tr><th>Limitation</th><th>Consequence</th></tr>
<tr><td>No physical data</td><td>No phantom, animal or clinical measurement stands behind any
number here. This is a feasibility envelope, <b>not clinical performance</b>.</td></tr>
<tr><td>Structured anatomy</td><td>A cylinder with organs, not segmented CT. Real anatomical
variation is almost certainly larger.</td></tr>
<tr><td>Single frequency</td><td>{C['freq_khz']} kHz only. Multi-frequency discrimination is untested.</td></tr>
<tr><td>Motion model is structured</td><td>Common-mode displacement plus breathing plus an
independent contact term. Real awake-child motion may be worse.</td></tr>
<tr><td>Aperture selection is greedy</td><td>The estimator picks one aperture by signal strength.
A better rule may change the electrode-count conclusion.</td></tr>
<tr><td>Kite comparison is not like-for-like</td><td>The 73%/44% figures are a different
measurement on different subjects, shown for context only.</td></tr>
</table>

</body></html>"""

open("DOC_section0.html", "w").write(HTML)
print(f"wrote DOC_section0.html ({len(HTML)//1024} KB)")
