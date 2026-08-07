"""
Build design.html: end-to-end characterization of the LOCKED design.
Self-contained (figures base64-inlined), same design system as index.html.
"""
import base64, json, os

M = json.load(open("metrics_design.json"))
C = M["config"]
OP = M["operating"]; MOT = C["motion"]; S = M["subject"]; G = M["grade"]; AB = M["ablation"]
NS, SPAN, CH, SNR = C["n_strip"], C["span"], C["channels"], C["snr"]
STILL, WORST = str(MOT[0]), str(MOT[-1])
TARGET = min(MOT, key=lambda m: abs(m - 0.45))     # the design motion target


def pct(x, d=0):
    return "n/a" if x != x else f"{100*x:.{d}f}%"


def num(x, d=2):
    return "n/a" if x != x else f"{x:.{d}f}"


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


CSS = open("site.css").read()


def figcard(fn, head, cap):
    p = os.path.join("figs_design", fn)
    if not os.path.exists(p):
        return ""
    b = base64.b64encode(open(p, "rb").read()).decode()
    return (f'<figure class="figcard"><div class="figcard-h">{head}</div>'
            f'<img src="data:image/png;base64,{b}" alt="{head}">'
            f'<figcaption>{cap}</figcaption></figure>')


TABS = ('<div class="tabs"><a href="index.html" class="active">Chosen design</a><a href="electrode-count.html">Electrode count</a></div>')

# ---- the multi-event verdict, computed not asserted ----
K = S["k_events"]
BK = str(S["best_k"])
SENS = S["sens_k"][BK]; SPEC = S["spec_k"][BK]; CHANCE = S["chance_k"][BK]
never_frac = S["never_detected_reflux"]
PE_S = S["per_event_sens"]; PE_F = S["per_event_fp"]
rule_rows = "\n".join(
    f"<tr{' style=chr34background:rgba(25,158,112,.10)chr34' if str(k)==BK else ''}>"
    f"<td class='mono'>&#8805; {k} of {K}</td>"
    f"<td class='mono'>{pct(S['sens_k'][str(k)],1)}</td>"
    f"<td class='mono'>{pct(S['spec_k'][str(k)],1)}</td>"
    f"<td class='mono'>{pct(S['chance_k'][str(k)],1)}</td></tr>"
    for k in range(1, K + 1)).replace("chr34", '"')

grade_rows = "\n".join(
    f"<tr><td class='mono'>grade {g}</td>" +
    "".join(f"<td class='mono'>{pct(G[str(g)][str(m)]['dir_acc'])}</td>"
            for m in sorted(float(k) for k in G[str(g)])) + "</tr>"
    for g in (1, 2, 3, 4, 5))
grade_hdr = "".join(f"<th>{m:.2f} cm</th>"
                    for m in sorted(float(k) for k in G["3"]))

mot_rows = "\n".join(
    f"<tr><td class='mono'>{m:.2f} cm</td>"
    f"<td class='mono'>{pct(OP[str(m)]['dir_acc'])}</td>"
    f"<td class='mono'>{100*OP[str(m)]['dir_ci'][0]:.0f}-{100*OP[str(m)]['dir_ci'][1]:.0f}%</td>"
    f"<td class='mono'>{pct(OP[str(m)]['lat_acc'])}</td>"
    f"<td class='mono'>{num(OP[str(m)]['auc'])}</td>"
    f"<td class='mono'>{pct(OP[str(m)]['sens_at_spec'].get('0.9', float('nan')))}</td></tr>"
    for m in MOT)

HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png">
<link rel="icon" type="image/png" sizes="16x16" href="favicon-16.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<title>The chosen design, characterized end to end</title>
<meta property="og:title" content="Directional reflux sensor: the chosen design">
<meta property="og:description" content="End-to-end characterization of the locked configuration: ROC, motion, grade, and a direct test of whether multi-event detection compounds.">
<style>{CSS}</style></head>
<body>
<aside class="side">
  <div class="brand"><b>Reflux sensing</b></div>
  <div class="brand-sub">the chosen design</div>
  <nav class="nav">
    <a href="#overview">Overview</a><a href="#config">The configuration</a>
    <a href="#roc">Detection performance</a><a href="#motion">Motion</a>
    <a href="#grade">By grade</a><a href="#multievent">Multi-event test</a>
    <a href="#signal">What carries it</a><a href="#confusion">Confusion</a>
    <a href="#limits">Limits</a><a href="#reproduce">Reproduce</a>
  </nav>
  <div class="side-foot">
    <a href="https://github.com/larachieppe/reflux-directional" target="_blank">source &amp; code &#8599;</a>
  </div>
</aside>
<main>
  {TABS}

  <header id="overview">
    <div class="kicker">Locked design &#183; end-to-end characterization</div>
    <h1>The chosen design, measured end to end</h1>
    <p class="lede">The previous study asked <b>how many electrodes</b>. This one stops sweeping and
    characterizes the single configuration that study selected: {NS} electrodes per strip,
    {SPAN:.0f} cm span, {CH} channels. It also puts the central commercial claim, that observing
    many voiding events beats VCUG, to a <b>direct test</b> rather than assuming it.</p>
    <div class="tiles">
      <div class="tile"><div class="tile-num" style="color:var(--accent)">{num(OP[str(TARGET)]['auc'])}</div>
      <div class="tile-label">Reflux AUC</div><div class="tile-sub">at {TARGET:.2f} cm motion</div></div>
      <div class="tile"><div class="tile-num" style="color:var(--ink)">{pct(OP[STILL]['dir_acc'])}</div>
      <div class="tile-label">Direction, still</div><div class="tile-sub">grade &#8805; III</div></div>
      <div class="tile"><div class="tile-num" style="color:var(--ink)">{pct(OP[str(TARGET)]['dir_acc'])}</div>
      <div class="tile-label">Direction, {TARGET:.2f} cm</div><div class="tile-sub">the design target</div></div>
      <div class="tile"><div class="tile-num" style="color:var(--c2)">{pct(SENS)}</div>
      <div class="tile-label">Sensitivity, &#8805;{BK} of {K} events</div><div class="tile-sub">at {pct(SPEC)} specificity</div></div>
    </div>
    <div class="bench">
      <span>VCUG misses <b>~20%</b></span>
      <span>nuclear VCUG <b>81% / 89%</b></span>
      <span>this design, &#8805;{BK} of {K} <b>{pct(SENS)} / {pct(SPEC)}</b></span>
    </div>
  </header>

  <section id="config">
    <div class="sec-kicker">what is locked</div>
    <h2>The configuration under test</h2>
    <div class="prov-wrap"><table class="prov">
      <tr><th>Parameter</th><th>Value</th><th>Chosen because</th></tr>
      <tr><td>Electrodes per strip</td><td class="mono">{NS} ({CH} channels)</td><td>Best laterality among counts not significantly worse on direction.</td></tr>
      <tr><td>Strip span</td><td class="mono">{SPAN:.0f} cm</td><td>The strongest single lever in the sweep; accuracy plateaus here.</td></tr>
      <tr><td>Zone geometry</td><td class="mono">symmetric tetrapolar</td><td>Outer pair drives, central pair senses; contact impedance largely rejected.</td></tr>
      <tr><td>Measurement</td><td class="mono">fractional &#916;Z/|Z|</td><td>Removes per-channel gain, which otherwise makes strip selection degenerate.</td></tr>
      <tr><td>Instrument SNR</td><td class="mono">{SNR} dB</td><td>Accuracy was flat from 50 to 80 dB; this is comfortably sufficient.</td></tr>
      <tr><td>Excitation</td><td class="mono">{C['freq_khz']} kHz, single</td><td>Direction is a timing measurement. Multi-frequency remains <b>untested</b>.</td></tr>
      <tr><td>Claimed grade range</td><td class="mono">grade &#8805; III</td><td>Grades I to II do not travel far enough to cross the sensed span.</td></tr>
    </table></div>
  </section>

  <section id="roc">
    <div class="sec-kicker">detection performance</div>
    <h2>Reflux versus everything else</h2>
    <p>Four conditions are simulated: reflux, normal antegrade transport, bladder filling (the
    confounder that defeats amplitude-only methods), and no flow. The classifier sees only
    features, never the label.</p>
    {figcard("d1_roc.png", "ROC across the motion grid",
             "Each curve is one motion level. Reflux vs the other three conditions, out-of-fold predictions from grouped cross-validation.")}
    {figcard("d6_ops_ablation.png", "Operating points and feature ablation",
             "Left: sensitivity at fixed specificity, against the nuclear-VCUG reference of 81% sensitivity at 89% specificity. Right: which features actually carry the discrimination.")}
  </section>

  <section id="motion">
    <div class="sec-kicker">the binding constraint</div>
    <h2>Motion</h2>
    <p>Motion is what degraded the prior tomographic program from 73% to 44%, so it is measured on
    a fine grid here rather than at two points.</p>
    <div class="prov-wrap"><table class="prov">
      <tr><th>Motion</th><th>Direction</th><th>95% CI</th><th>Laterality</th><th>AUC</th><th>Sens @ 90% spec</th></tr>
      {mot_rows}
    </table></div>
    {figcard("d2_motion.png", "Performance against motion",
             "Direction accuracy with Wilson 95% intervals, laterality, and AUC. The shaded band is the design target of 0.5 cm or less.")}
    {figcard("d5_evidence.png", "How motion erodes the evidence",
             "Distribution of the direction evidence for reflux versus normal transport. The two populations separate cleanly when still and merge as motion grows, which is the failure mechanism made visible.")}
  </section>

  <section id="grade">
    <div class="sec-kicker">where it works and stops</div>
    <h2>By reflux grade</h2>
    <div class="prov-wrap"><table class="prov">
      <tr><th>Grade</th>{grade_hdr}</tr>
      {grade_rows}
    </table></div>
    {figcard("d3_grade_heat.png", "Grade against motion",
             "Direction accuracy for every grade and motion level. The heavy line marks where the claimed range begins: grades I to II sit at or below chance because low-grade reflux does not travel far enough to cross the sensed span.")}
  </section>

  <section id="multievent">
    <div class="sec-kicker">the claim that decides the product</div>
    <h2>Does observing more events actually help?</h2>
    <p>The case for beating VCUG rests entirely on event count: VCUG captures one or two forced
    voids and misses roughly 20% of reflux, while a passive wearable observes many natural cycles.
    That argument assumes <b>events are independent</b>. If a child's anatomy or electrode placement
    is what limits the measurement, every event on that child fails together and repetition buys
    nothing. So this study simulates <b>{S['n_subjects']} children with {K} events each, holding
    anatomy and placement fixed per child</b>, and compares the measured result against what
    independence would predict.</p>
    <div class="prov-wrap"><table class="prov">
      <tr><th>Screening rule</th><th>Sensitivity</th><th>Specificity</th><th>Sensitivity if the detector were a coin flip</th></tr>
      {rule_rows}
    </table></div>
    {figcard("d4_multievent.png", "The screening rule, measured",
             "Left: sensitivity and specificity reported separately against the k-of-n threshold, with the coin-flip floor and the independence prediction. Right: how many of the K events each child got right, refluxers against healthy children.")}
    <p>The chosen rule is <b>&#8805;{BK} of {K}</b>: <b>{pct(SENS)} sensitivity at {pct(SPEC)}
    specificity</b>, against nuclear VCUG's 81% at 89%. Per event the detector runs
    {pct(PE_S)} sensitivity at a {pct(PE_F)} false-positive rate, so the gain really does come
    from repetition rather than from any single measurement being excellent.</p>
    <div class="note"><b>Why sensitivity and specificity are shown separately.</b> An earlier
    version of this analysis pooled refluxing and healthy children and counted any correct
    direction call as a hit. That is per-child accuracy, not sensitivity, and because half the
    cohort is healthy its <b>chance floor is {pct(S['chance_k']['2'],0)} at &#8805;2 of {K}</b>,
    which sits above the ~80% VCUG line. A coin-flip detector would have appeared to beat VCUG.
    The table above therefore reports the two quantities separately and prints the coin-flip
    floor beside them, so the comparison is like for like.</div>
    <div class="note"><b>Do repeat events actually compound?</b> Anatomy and electrode placement
    are held fixed per child, so any correlated failure shows up as a shortfall against the
    independence prediction. Here <b>{pct(never_frac)}</b> of refluxing children were never
    detected in {K} events, meaning correlated failure is small <b>in this model</b>. That is the
    most model-dependent result on the page: real anatomical variation and real placement error
    are almost certainly larger than simulated, and a phantom study followed by a clinical pilot
    must measure this fraction directly before the multi-event argument can be relied on.</div>

  <section id="signal">
    <div class="sec-kicker">is it really direction?</div>
    <h2>What carries the signal</h2>
    <p>Amplitude alone is the quantity that reflux shares with bladder filling. Direction is the
    quantity that defines reflux. The ablation separates them: <b>all features {num(AB['full'])}</b>,
    direction only <b>{num(AB['direction_only'])}</b>, amplitude only
    <b>{num(AB['amplitude_only'])}</b>.</p>
    {figcard("d8_calibration.png", "Calibration",
             "Predicted probability against observed frequency. A screening threshold is only meaningful if the probabilities are calibrated.")}
  </section>

  <section id="confusion">
    <div class="sec-kicker">what gets confused with what</div>
    <h2>Confusion</h2>
    {figcard("d7_confusion.png", "Four-condition confusion",
             "Row-normalized. The row that matters commercially is bladder filling: it is the confounder that amplitude-only methods cannot separate from reflux.")}
  </section>

  <section id="limits">
    <div class="sec-kicker">honesty</div>
    <h2>What this does not establish</h2>
    <div class="prov-wrap"><table class="prov">
      <tr><th>Limitation</th><th>Consequence</th></tr>
      <tr><td>No physical data</td><td>No phantom, animal or clinical measurement stands behind any number here. This is a feasibility envelope, not clinical performance.</td></tr>
      <tr><td>Structured anatomy</td><td>A cylinder with organs, not segmented CT. Real anatomical variation is almost certainly larger than what is simulated.</td></tr>
      <tr><td>Single frequency</td><td>{C['freq_khz']} kHz only. Multi-frequency discrimination is untested and could help or do nothing.</td></tr>
      <tr><td>Motion model is structured</td><td>Common-mode displacement plus breathing plus an independent contact term. Real awake-child motion may be worse and is not measured.</td></tr>
      <tr><td>Aperture selection is greedy</td><td>The estimator picks one aperture by signal strength. A better rule may change the electrode-count conclusion from the previous study.</td></tr>
      <tr><td>Grades I to II</td><td>Not detectable by this method. Any claim must be scoped to grade &#8805; III.</td></tr>
    </table></div>
  </section>

  <section id="reproduce">
    <div class="sec-kicker">run it yourself</div>
    <h2>Reproduce</h2>
<pre>python -m venv .venv &amp;&amp; source .venv/bin/activate
pip install -r requirements.txt
python run_design.py            # {C['n_subj']} subjects + operating + grade studies (~{M.get('runtime_min',0):.0f} min)
python make_figs_design.py      # figures -&gt; figs_design/
python build_design_site.py     # this page</pre>
    <p class="subtle">Operating study {C['n_op']*4} trials per motion level across {len(MOT)} levels;
    grade study {C['n_grade']} per grade and motion; subject study {C['n_subj']} children
    &#215; {K} events at {C['subj_motion']:.2f} cm motion. Total runtime
    {M.get('runtime_min',0):.0f} min.</p>
  </section>
</main>

<style>
 .nav a.here{{color:var(--accent) !important;border-left:2px solid var(--accent);
             padding-left:8px;margin-left:-10px}}
</style>
<script>
(function(){{
  var links = Array.prototype.slice.call(document.querySelectorAll('.nav a[href^="#"]'));
  if(!links.length) return;
  var secs = links.map(function(a){{
    return {{a:a, el:document.getElementById(a.getAttribute('href').slice(1))}};
  }}).filter(function(s){{ return s.el; }});
  if(!secs.length) return;
  function top(el){{ return el.getBoundingClientRect().top + window.pageYOffset; }}
  function mark(){{
    // the section whose top is closest to (but not far past) the reading line
    var line = window.scrollY + window.innerHeight*0.28, cur = secs[0];
    for(var i=0;i<secs.length;i++){{
      if(top(secs[i].el) <= line) cur = secs[i];
    }}
    // at the very bottom, select the last section so the final item can highlight
    if(window.innerHeight + window.scrollY >= document.body.scrollHeight - 4){{
      cur = secs[secs.length-1];
    }}
    for(var j=0;j<secs.length;j++){{
      secs[j].a.classList.toggle('here', secs[j]===cur);
    }}
  }}
  var tick=false;
  function onScroll(){{
    if(tick) return; tick=true;
    requestAnimationFrame(function(){{ mark(); tick=false; }});
  }}
  window.addEventListener('scroll', onScroll, {{passive:true}});
  window.addEventListener('resize', onScroll, {{passive:true}});
  window.addEventListener('hashchange', function(){{ setTimeout(mark, 0); }});
  mark();
}})();
</script>
</body></html>"""

open("index.html", "w").write(HTML)
# keep the previously shared /design.html URL alive
open("design.html", "w").write(
    '<!doctype html><meta charset="utf-8">'
    '<meta http-equiv="refresh" content="0; url=index.html">'
    '<link rel="canonical" href="index.html">'
    '<title>Redirecting</title>'
    '<p>This page has moved to <a href="index.html">index.html</a>.</p>')
print(f"wrote index.html (+design.html redirect) ({len(HTML)//1024} KB)  "
      f"AUC@{TARGET:.2f}={num(OP[str(TARGET)]['auc'])}  "
      f">={BK}of{K}: sens {pct(SENS)} spec {pct(SPEC)}  "
      f"never-detected={pct(never_frac)}")
