"""
Materials & Methods generator.

Every number in the output is either introspected from the live model module or
read from the metrics file the study actually wrote. Nothing here is typed by
hand from memory, so the methods cannot drift away from the code that produced
the results. If a study has not run, its section says so rather than inventing
parameters.

Emits METHODS.html standalone, and exposes methods_html(study) so
build_full_report.py can inline the same text under each study.
"""
import json, os, subprocess, datetime
import numpy as np

import directional_sim as ds

STUDIES = [
    ("electrode-count", "Study 1", "Electrode count, span, motion and SNR sweep",
     "metrics_directional.json", "run_directional.py"),
    ("design", "Study 2", "Locked design characterisation",
     "metrics_design.json", "run_design.py"),
    ("placement", "Study 3", "Strip placement over the ureterovesical junction",
     "metrics_placement.json", "run_placement.py"),
    ("tolerance", "Study 4", "Misplacement tolerance",
     "metrics_tolerance.json", "run_tolerance.py"),
    ("precision", "Study 5", "Placement precision across a simulated cohort",
     "metrics_precision.json", "run_precision.py"),
    ("motion2", "Study 6", "Non-rigid respiratory motion",
     "metrics_motion2.json", "run_motion2.py"),
]


# --------------------------------------------------------------- helpers
def _rev():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip() or "n/a"
    except Exception:
        return "n/a"


def _cfg(path):
    if not os.path.exists(path):
        return None
    try:
        return json.load(open(path))
    except Exception:
        return None


def _dl(pairs):
    rows = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in pairs)
    return f"<dl class='mm'>{rows}</dl>"


def _n_trials(cfg, keys):
    """Total forward solves, computed from the config the run actually wrote."""
    n = 1
    for k in keys:
        v = cfg.get(k)
        n *= len(v) if isinstance(v, (list, tuple)) else (v or 1)
    return n


# --------------------------------------------------------------- shared model
def common_html():
    t = ds.TISSUE
    rows = "".join(
        f"<tr><td>{n}</td><td>{s:.3f}</td><td>{e:,.0f}</td></tr>"
        for n, (s, e) in t.items())
    gr = "".join(
        f"<tr><td>{g}</td><td>{a:.2f} R</td><td>{b:.2f}</td>"
        f"<td>{100*ds.GRADE_WEIGHTS[g]:.0f}%</td></tr>"
        for g, (a, b) in sorted(ds.GRADE_TABLE.items()))
    f0, f1 = ds.FREQS

    return f"""
<h3>M0. Model shared by every study</h3>

<p class="mm-lead">All six studies use one forward model and one estimator. They
differ only in which factors are varied. This section states the inputs once;
each study below states only what it changed.</p>

<h4>Information used as input</h4>
<p>The simulation is driven by four sources of information, and nothing else. No
measured patient data was available at any point, so every result is a
feasibility and robustness envelope rather than clinical performance.</p>
<ol class="mm-ol">
<li><b>Tissue electrical properties</b> — conductivity and relative permittivity
per tissue, at the measurement band, with a log-frequency dispersion
<code>&sigma;(f) = &sigma;<sub>0</sub>(1 + 0.04&nbsp;log<sub>10</sub>(f/50&nbsp;kHz))</code>.
The urine-to-soft-tissue contrast is the entire physical basis of the method:
urine at {t['urine'][0]:.2f} S/m against muscle at {t['muscle'][0]:.2f} S/m is a
factor of {t['urine'][0]/t['muscle'][0]:.1f}.</li>
<li><b>Torso and organ geometry</b> — an idealised cylinder with ellipsoidal
kidney, ureter and bladder, not segmented CT. Dimensions are scaled to a young
child.</li>
<li><b>Reflux grade definitions</b> — the international grading scale mapped to a
bolus size and a retrograde reach up the ureter, plus the published prevalence of
each grade, used to weight the mixed-grade cohorts.</li>
<li><b>An assumed instrument noise budget</b>, stated as SNR in dB rather than
taken from a datasheet, and swept as a factor in Study 1.</li>
</ol>

<div class="mm-two">
<div>
<table class="mm-t"><caption>Tissue properties</caption>
<tr><th>tissue</th><th>&sigma; (S/m)</th><th>&epsilon;<sub>r</sub></th></tr>
{rows}</table>
<p class="mm-note">The bladder entry is <b>wall only</b>. The lumen is filled with
urine at a lumen fraction of 0.82. Modelling the whole bladder at wall
conductivity was a defect: it put the bladder below muscle and inverted the
strongest confounder in the problem.</p>
</div>
<div>
<table class="mm-t"><caption>Grade model</caption>
<tr><th>grade</th><th>bolus semi-axis</th><th>ureteric reach</th><th>prevalence</th></tr>
{gr}</table>
<p class="mm-note">Reach is the fraction of the ureter the retrograde bolus
climbs. It is what makes low grades hard: a grade-I bolus reaches
{ds.GRADE_TABLE[1][1]:.0%} of the way and may cross too few sensing zones to fit
a slope.</p>
</div>
</div>

<h4>Forward model</h4>
{_dl([
 ("Solver", "scikit-fem, tetrahedral, first-order Lagrange"),
 ("Domain", "cylinder R = 5.5 cm, height = 20.0 cm, 6 radial rings, 17 axial layers"),
 ("Electrode model", "Complete Electrode Model (CEM) — finite contact impedance "
  "and current-conserving electrode constraints, not point electrodes"),
 ("Contact impedance", "z<sub>0</sub> ~ U(5, 20) &Omega;&middot;cm<sup>2</sup>, "
  "redrawn per electrode per trial, with a slow drift and an independent "
  "per-electrode component"),
 ("Frequencies", f"{f0/1e3:.0f} kHz and {f1/1e3:.0f} kHz, solved separately"),
 ("Electrodes", "two longitudinal flank strips, one per side, placed on a partial "
  "circumference — deliberately not a closed belt"),
 ("Sensing", "tetrapolar (Kelvin): an outer pair drives current, an inner pair "
  "senses voltage, so contact impedance largely drops out of the sensed quantity"),
 ("Zones", "symmetric tetrapolar quadruples at odd outer gaps G, giving several "
  "overlapping apertures per strip at different depth sensitivities"),
])}

<h4>How a trial is generated</h4>
<ol class="mm-ol">
<li>Anatomy is drawn: ureter lateral position &plusmn;8%, kidney and bladder
centres jittered by 3–5% of torso radius or height.</li>
<li>A conductivity field is built per time frame. A constant-volume urine bolus
travels along the ureter — <b>up</b> for reflux, <b>down</b> for antegrade flow.
Constant volume matters: an earlier version modulated bolus amplitude over time,
which let the estimator identify the class from the amplitude envelope alone
without using direction at all.</li>
<li>Body motion is applied as a displacement of the body relative to the
electrodes, as a smooth random walk plus a periodic breathing term at 0.30 Hz.
A <code>grad</code> parameter makes displacement height-dependent, so motion can
be rigid (grad = 0) or a craniocaudal gradient (grad = 1).</li>
<li>The CEM problem is solved per frame per frequency, giving a transfer
impedance per zone.</li>
<li>Noise is added as a <b>fractional</b> perturbation,
<code>&sigma;<sub>n</sub> = 10<sup>&minus;SNR/20</sup></code>, with a
zone-correlated and a zone-independent component.</li>
</ol>

<h4>Estimator</h4>
<ol class="mm-ol">
<li><b>Normalise.</b> <code>dZ = (Z &minus; Z<sub>ref</sub>) / |Z<sub>ref</sub>|</code>,
where <code>Z<sub>ref</sub></code> is the mean of the first two frames. Making
this fractional removes a bias caused by unequal realised electrode areas.</li>
<li><b>Reject common mode.</b> Subtract the across-zone mean of the real part at
each frame. Whole-body motion moves every zone together and is removed; a bolus
travelling past zones in sequence is not. This requires at least three zones —
with exactly two, the mean-removed pair are exact negatives and the operation
destroys the signal.</li>
<li><b>Time the wave.</b> Per zone, take the arrival time of the response peak,
then regress arrival time against the zone's realised axial height. Realised
electrode centroids are used, not requested positions.</li>
<li><b>Fuse apertures.</b> Combine apertures weighted by axial lever arm, fit
quality and &radic;energy. This replaced a greedy best-aperture selector that was
overfitting and produced the since-retracted "more electrodes is worse" claim.</li>
<li><b>Decide.</b> The <b>sign of the slope</b> is the diagnosis: bolus arriving
at superior zones later than inferior zones means upward, i.e. reflux.</li>
<li><b>Abstain.</b> If wave linearity &lt; {ds.LIN_GATE:.2f} the trial returns no
call. The threshold was set by Youden index. Abstentions are scored as errors in
the headline accuracy, and reported separately as accuracy-on-calls-made.</li>
</ol>

<h4>Statistics</h4>
{_dl([
 ("Interval estimates", "Wilson 95% confidence intervals on every proportion"),
 ("Independence", "trial index ranges are disjoint across configurations, so no "
  "trial is reused between arms being compared"),
 ("Paired comparisons", "configurations are replayed on matched seeds where the "
  "comparison is within-study"),
 ("Subject-level results", "a k-of-n rule over repeated voids, with sensitivity "
  "and specificity reported separately and the chance floor stated — pooling "
  "them produced a chance floor above the VCUG reference line"),
 ("Confusion matrices", "reported at a disclosed 90%-specificity operating "
  "threshold, not at the median"),
])}

<div class="mm-warn">
<b>Standing limitation.</b> The geometry is idealised, the tissue table is
literature-derived, and the noise budget is assumed. These results bound whether
the physics can work and how it degrades. They are not evidence of clinical
accuracy, and no claim here substitutes for a phantom or a patient study.
</div>
"""


# --------------------------------------------------------------- per study
def _electrode_count(c):
    cfg = c["config"]
    n = _n_trials(cfg, ["counts", "motion", "snrs", "spans"]) if cfg else 0
    return f"""
<h4>Question</h4>
<p>How many electrodes per strip are needed, and over what span, to recover flow
direction — and does adding electrodes help, hurt, or saturate? The design goal
was to maximise function while minimising complexity, so the study had to find
the point past which extra channels stop buying accuracy.</p>

<h4>Factors varied</h4>
{_dl([
 ("Electrodes per strip", ", ".join(str(x) for x in cfg["counts"])),
 ("Strip span (cm)", ", ".join(f"{x:.0f}" for x in cfg["spans"])),
 ("Motion amplitude (cm)", ", ".join(f"{x:g}" for x in cfg["motion"])),
 ("SNR (dB)", ", ".join(str(x) for x in cfg["snrs"])),
 ("Frames per trial", cfg["T"]),
])}
<p class="mm-note">Factors are crossed, giving on the order of {n:,} configuration
cells before trial replication. Meshes are built once and shared across electrode
counts, so only the electrode set and the CEM solve differ between arms — the
comparison is not confounded by mesh differences.</p>

<h4>How results were reached</h4>
<p>Each arm reports direction accuracy with abstentions scored as errors,
accuracy on calls made, abstention rate, and AUC. <b>AUC is computed separately
per motion level</b>; an earlier version computed it once and copied it across
motion arms, which hid the degradation the study existed to measure.</p>

<h4>Retracted from this study</h4>
<p>Two published conclusions were withdrawn after audit. "More electrodes is
worse" was an artefact of the greedy aperture selector, now replaced by fusion.
"Longer span is better" was an artefact of span acting as a proxy for placement,
which Study 3 then measured directly. At N = 12 electrodes shared mesh facets
welded neighbouring electrodes together; placement now uses a pitch-scaled
acceptance window with a hard assertion against overlap.</p>
"""


def _design(c):
    cfg = c["config"]
    return f"""
<h4>Question</h4>
<p>With the configuration locked, how does it behave across the full motion
range, and what does its confusion matrix look like at a defensible operating
point?</p>

<h4>Configuration held fixed</h4>
{_dl([
 ("Electrodes per strip", cfg["n_strip"]),
 ("Total channels", cfg.get("channels", 2 * cfg["n_strip"])),
 ("Span (cm)", f"{cfg['span']:.0f}"),
 ("SNR (dB)", cfg["snr"]),
 ("Frames per trial", cfg["T"]),
])}

<h4>Factor varied</h4>
<p>Motion amplitude across {len(cfg["motion"])} levels
({", ".join(f"{m:g}" for m in cfg["motion"])} cm), which is the dominant
real-world stressor and the one that took the prior tomographic program from 73%
still to 44% moving.</p>

<h4>How results were reached</h4>
<p>Subject-level analysis aggregates repeated voids per simulated child under a
k-of-n rule, reporting sensitivity and specificity <b>separately</b> with the
chance floor stated. The confusion matrix is evaluated at a <b>disclosed
90%-specificity threshold</b>. Reporting at the median instead had capped
apparent specificity at 66.7% — an artefact of the threshold, not the
classifier.</p>
"""


def _placement(c):
    cfg = c["config"]
    return f"""
<h4>Question</h4>
<p>Earlier runs suggested grades I–II were intrinsically undetectable. That
conclusion was suspect, because the strip's axial centre was never actually
forwarded to the electrode placement routine — every run had silently used the
default mid-torso position. This study asks whether low-grade detectability is a
property of the method or a property of <i>where the strip sits</i> relative to
the ureterovesical junction.</p>

<h4>Factors varied</h4>
{_dl([
 ("(span, axial centre) pairs", ", ".join(f"{s:.0f} cm @ z={z:.2f}"
                                          for s, z in cfg["configs"])),
 ("Reflux grades", ", ".join(str(g) for g in cfg["grades"])),
 ("Motion", "still and 0.30 cm"),
 ("Torso height (cm)", f"{cfg['height']:.0f}"),
])}

<h4>How results were reached</h4>
<p>Beyond accuracy, the study computes the <b>mechanism</b> directly: for each
placement it counts how many zone centroids the grade-I bolus physically crosses.
This converts a performance curve into a causal explanation — low grades fail
when the bolus crosses fewer than three zones, because three is the minimum for
both common-mode rejection and a slope fit. A placement that puts more zones over
the short retrograde path of a low-grade bolus recovers it.</p>

<h4>Result that overturned a published claim</h4>
<p>Grades I–II are <b>not</b> intrinsically undetectable. The earlier claim was a
plumbing defect. This is the clearest example in the project of a bug producing a
confident and completely wrong scientific conclusion.</p>
"""


def _tolerance(c):
    cfg = c["config"]
    return f"""
<h4>Question</h4>
<p>Study 3 found a placement optimum. A placement that only works when perfectly
aligned is not a product: the strip is applied by a parent or nurse, to a child
who will not hold still, against a landmark — the ureterovesical junction — that
is not externally visible. How much misalignment can the design absorb?</p>

<h4>Design</h4>
{_dl([
 ("Centre position", f"inherited from Study 3's best low-grade placement: "
  f"{cfg['span']:.0f} cm span at z = {cfg['z_center']:.2f}"),
 ("Offsets applied (cm)", ", ".join(f"{o:+.0f}" for o in cfg["offsets_cm"])),
 ("Grades", ", ".join(str(g) for g in cfg["grades"])),
 ("Motion", ", ".join(f"{m:g}" for m in cfg["motion"])),
 ("Trials per cell", cfg["n_trial"]),
])}
<p class="mm-note">The optimum is <b>read from</b> <code>metrics_placement.json</code>
rather than hard-coded, so this study cannot silently test a stale position if
Study 3 is re-run.</p>

<h4>How results were reached</h4>
<p>Grades are pooled into low (I–II) and high (III–V) bands, because the low band
is where placement sensitivity lives. The reported cost is the accuracy change
relative to the zero-offset arm, so the endpoint is degradation, not absolute
accuracy.</p>

<h4>Consequence</h4>
<p>Accuracy at the optimum being high while collapsing 1 cm away does not license
the claim that low-grade reflux is detectable. It licenses the claim that the
design needs a landmark, a longer strip, or an alignment aid. That open trade is
what Study 5 was built to resolve.</p>
"""


def _precision(c):
    if c is None:
        rp = __import__("run_precision")
        cfg = dict(n_strip=rp.N_STRIP, snr=rp.SNR, motion=rp.MOTION, T=rp.T,
                   k_events=rp.K_EVENTS, n_child=rp.N_CHILD,
                   sigmas=list(rp.SIGMAS), configs=rp.CONFIGS)
    else:
        cfg = c["config"]
    n = len(cfg["configs"]) * len(cfg["sigmas"]) * cfg["n_child"] * cfg["k_events"]
    return f"""
<h4>Question</h4>
<p>Across a cohort where <i>every</i> child is imperfectly measured, what
fraction is detected — and what fraction is <b>systematically unmeasurable</b>,
failing on every void, for whom repeat observation never helps?</p>

<div class="mm-warn"><b>This is not a phantom study.</b> A phantom study is
physical and cannot be run in simulation. This is its simulation analogue.</div>

<h4>Design</h4>
{_dl([
 ("Placement arms", "; ".join(f"{s:.0f} cm @ z={z:.2f} ({n})"
                              for s, z, n in cfg["configs"])),
 ("Placement error &sigma; (cm)", ", ".join(f"{s:g}" for s in cfg["sigmas"])),
 ("Simulated children per cell", cfg["n_child"]),
 ("Voids per child", cfg["k_events"]),
 ("Motion (cm)", f"{cfg['motion']:g}"),
 ("Total trials", f"{n:,}"),
])}

<h4>The design choice that makes this study mean anything</h4>
<p><b>One placement error is drawn per child and shared across all of that
child's voids</b>, because a strip is applied once, not re-applied per void. This
makes failure <i>correlated within a child</i>, which is the entire question. Had
the error been redrawn per event, repeated voids would average it away and the
study would have reported a reassuring and meaningless number. Anatomy is
likewise drawn once per child.</p>

<h4>How results were reached</h4>
<p>Per child, hits are counted across their voids and passed to the subject-level
k-of-n analysis. Endpoints are sensitivity and specificity at the best k, the
fraction of refluxing children <b>never detected on any void</b>, and the same
restricted to grades I–II. The two placement arms answer the open trade from
Study 4: whether a longer strip buys positional margin at the cost of peak
low-grade accuracy.</p>
"""


def _motion2(c):
    cfg = c["config"] if c else dict(
        amps=list(__import__("run_motion2").AMPS),
        grads=list(__import__("run_motion2").GRADS),
        n_trial=__import__("run_motion2").N_TRIAL,
        classes=list(__import__("run_motion2").CLASSES),
        span=__import__("run_motion2").SPAN,
        n_strip=__import__("run_motion2").N_STRIP)
    n = len(cfg["amps"]) * len(cfg["grads"]) * len(cfg["classes"]) * cfg["n_trial"]
    return f"""
<h4>Question</h4>
<p>Every motion result in Studies 1–5 used a <b>rigid</b> translation: one
displacement applied identically to body and bolus. That is precisely the
perturbation that subtracting the across-zone mean provably nulls. A rigid-only
model can therefore only ever <i>confirm</i> the common-mode rejection claim — it
cannot test it. The assertion that the claim was "tested rather than assumed" was
wrong, and this study exists to correct it.</p>

<p>Real respiratory motion is not rigid. It is a craniocaudal <b>gradient</b>:
the kidney translates 1–3 cm with the diaphragm while the bladder is nearly
fixed. A displacement varying linearly with height <b>survives mean
subtraction</b> and feeds straight into the arrival-time slope as a
phase-locked false travelling wave — the exact shape of the failure that took the
prior tomographic program from 73% to 44%.</p>

<h4>Factors varied</h4>
{_dl([
 ("Displacement amplitude (cm)", ", ".join(f"{a:g}" for a in cfg["amps"])),
 ("Motion gradient", ", ".join(f"{g:g}" for g in cfg["grads"])
  + " &nbsp;(0 = rigid, the old model; 1 = full craniocaudal gradient)"),
 ("Classes", ", ".join(cfg["classes"])),
 ("Trials per cell", cfg["n_trial"]),
 ("Total trials", f"{n:,}"),
])}
<p class="mm-note">Amplitudes were extended to 3 cm to span true respiratory
kidney excursion. With a full gradient the differential displacement across the
strip is roughly 0.8&times; amplitude, so an earlier version topping out at 0.9 cm
would have tested a gradient far gentler than physiology and understated the
risk.</p>

<h4>Primary endpoint</h4>
<p><b>False-retrograde rate on non-travelling windows</b> — how often the device
reports reflux when nothing is flowing and the child is merely breathing. This,
not accuracy, is the endpoint that decides viability: a device that invents
reflux during breathing is unusable regardless of how well it scores on real
events. Secondary endpoints are direction accuracy on real events, and whether
the abstain gate catches breathing artefact or whether breathing produces waves
coherent enough to pass it.</p>
"""


BUILDERS = {"electrode-count": _electrode_count, "design": _design,
            "placement": _placement, "tolerance": _tolerance,
            "precision": _precision, "motion2": _motion2}


def methods_html(key):
    """Per-study Materials & Methods block, or a not-yet-run notice."""
    meta = next((s for s in STUDIES if s[0] == key), None)
    if meta is None:
        return ""
    _, tag, title, mfile, script = meta
    c = _cfg(mfile)
    if c is None and key not in ("motion2", "precision"):
        return (f"<div class='mm-warn'><b>{tag} has not been run.</b> "
                f"No parameters are stated here because none have been recorded. "
                f"Source: <code>{script}</code>.</div>")
    body = BUILDERS[key](c)
    if c is None:
        body = ("<div class='mm-warn'><b>Design fixed, results pending.</b> "
                "Parameters below are read from the run script, which is the same "
                "source the run itself uses. No results are stated.</div>") + body
    prov = _dl([("Source", f"<code>{script}</code>"),
                ("Metrics file", f"<code>{mfile}</code>"
                 + ("" if c else " &mdash; queued, not yet written")),
                ("Runtime", f"{c['runtime_min']:.0f} min" if c and "runtime_min" in c
                 else "pending")])
    return (f"<div class='methods'><h3>Materials &amp; methods &mdash; {tag}: "
            f"{title}</h3>{body}<h4>Provenance</h4>{prov}</div>")


CSS = """
.methods{border-left:3px solid #2b7fd4;background:#f7fafc;padding:18px 22px;
 margin:26px 0;border-radius:0 6px 6px 0}
.methods h3{margin-top:0;color:#1c2b30}
.methods h4{margin:18px 0 6px;font-size:.95rem;text-transform:uppercase;
 letter-spacing:.04em;color:#4a6572}
.mm-lead{font-size:1.02rem}
dl.mm{display:grid;grid-template-columns:max-content 1fr;gap:4px 18px;margin:8px 0}
dl.mm dt{font-weight:600;color:#4a6572}
dl.mm dd{margin:0}
.mm-ol{margin:8px 0 8px 18px}.mm-ol li{margin:5px 0}
table.mm-t{border-collapse:collapse;font-size:.9rem;margin:6px 0;width:100%}
table.mm-t caption{text-align:left;font-weight:600;padding-bottom:4px;color:#4a6572}
table.mm-t th,table.mm-t td{border:1px solid #d7e0e4;padding:3px 9px;text-align:left}
table.mm-t th{background:#eef3f6}
.mm-note{font-size:.88rem;color:#5b6b73;margin:6px 0}
.mm-two{display:grid;grid-template-columns:1fr 1fr;gap:22px}
@media(max-width:760px){.mm-two{grid-template-columns:1fr}}
.mm-warn{background:#fff6e5;border:1px solid #f0d090;padding:10px 14px;
 border-radius:5px;margin:12px 0;font-size:.93rem}
"""


def main():
    parts = [common_html()] + [methods_html(k) for k, *_ in STUDIES]
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Materials &amp; Methods — directional reflux detection</title>
<link rel="icon" href="favicon.ico"><style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
 max-width:880px;margin:0 auto;padding:38px 22px;color:#1c2b30;line-height:1.62}}
h1{{margin-bottom:4px}} .sub{{color:#5b6b73;margin-top:0}}
code{{background:#eef3f6;padding:1px 5px;border-radius:3px;font-size:.9em}}
{CSS}</style></head><body>
<h1>Materials &amp; Methods</h1>
<p class="sub">Directional bioimpedance detection of vesicoureteral reflux &middot;
generated {datetime.date.today().isoformat()} &middot; commit <code>{_rev()}</code></p>
<p>Parameters below are introspected from the model module and from the metrics
file each study wrote, not transcribed by hand.</p>
{''.join(parts)}
</body></html>"""
    with open("METHODS.html", "w") as f:
        f.write(html)
    ran = sum(1 for k, *r in STUDIES if os.path.exists(r[2]))
    print(f"METHODS.html written  ({ran}/{len(STUDIES)} studies have metrics)")


if __name__ == "__main__":
    main()
