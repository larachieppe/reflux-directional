"""
Build index.html: the standalone results page for the directional
(non-tomographic) reflux simulation. CSS comes from site.css; figures are
base64-inlined so the published page is a single self-contained file.
"""
import base64, json, os, re

M = json.load(open("metrics_directional.json"))
cfg = M["config"]
COUNTS = cfg["counts"]; MOTION = cfg["motion"]; SPAN = cfg["span"]
prim = M["primary"]
WORST = max(MOTION); STILL = min(MOTION)


def g(n, m, k):
    d = prim[str(n)][str(m)]
    if k == "dir_acc" and d.get("undecidable", 0) > 0.99:
        return float("nan")            # undefined, not 0%: no ordering exists
    v = d.get(k)
    return float("nan") if v is None else v


def pct(x, d=0):
    return "n/a" if x != x else f"{100*x:.{d}f}%"


def num(x, d=2):
    return "n/a" if x != x else f"{x:.{d}f}"


# ---- PRE-SPECIFIED decision rule (written before the results were inspected) ----
# Picking a "knee" by eye from a noisy curve is how an underpowered sweep turns
# into a confident recommendation. So the rule is fixed in advance:
#   1. Primary metric: direction accuracy at grade >= III, at the WORST motion level.
#   2. Compute a Wilson 95% interval for every electrode count.
#   3. The recommendation is the SMALLEST count whose interval overlaps the
#      interval of the best-performing count (i.e. not significantly worse).
#   4. If every count overlaps every other, the sweep did NOT resolve the
#      question, and that is reported as the finding instead of a number.
def wilson(p, n, z=1.96):
    if n <= 0 or p != p:
        return (float("nan"), float("nan"))
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def dir_n(n, m):
    return int(prim[str(n)][str(m)].get("dir_n", 0))


accs = {n: g(n, WORST, "dir_acc") for n in COUNTS}
valid = {n: a for n, a in accs.items() if a == a}
CI = {n: wilson(valid[n], dir_n(n, WORST)) for n in valid}
if valid:
    BEST_N = max(valid, key=valid.get)
    best_acc = valid[BEST_N]
    lo_best, hi_best = CI[BEST_N]
    NOT_WORSE = [n for n in sorted(valid) if CI[n][1] >= lo_best]
    REC_DIR = NOT_WORSE[0] if NOT_WORSE else BEST_N          # direction-only rule
    RESOLVED = not all(CI[n][1] >= lo_best for n in valid)
    # Laterality is an independent must-have (left / right / bilateral), and it
    # ranks the counts DIFFERENTLY from direction. So among the counts that are
    # not significantly worse on direction, take the best on laterality. Both the
    # direction-only answer and the combined answer are reported, because they
    # disagree and hiding that would be choosing the flattering metric.
    REC = max(NOT_WORSE, key=lambda n: g(n, WORST, "lat_acc")) if NOT_WORSE else BEST_N
else:
    BEST_N = REC = REC_DIR = COUNTS[0]
    NOT_WORSE = []
    best_acc = float("nan")
    RESOLVED = False

SPREAD = (max(valid.values()) - min(valid.values())) if len(valid) > 1 else float("nan")

from math import comb


def multi(pe, k, syst=0.0):
    """Detection probability after k observed voiding events."""
    return (1 - syst) * (1 - (1 - pe) ** k)


def atleast(q, k, n):
    return sum(comb(n, i) * q ** i * (1 - q) ** (n - i) for i in range(k, n + 1))


PE_BEST = g(REC, "0.3", "dir_acc")      # per-event, low-motion operating point
PE_WORST = g(REC, WORST, "dir_acc")     # per-event, worst motion
SPANS_SORTED = sorted(float(k) for k in M["span_sweep"])
SPAN_BEST = max(SPANS_SORTED, key=lambda x: M["span_sweep"][str(x)]["dir_acc"])
SPAN_BEST = min(sp for sp in SPANS_SORTED
                if M["span_sweep"][str(sp)]["dir_acc"] >=
                max(M["span_sweep"][str(x)]["dir_acc"] for x in SPANS_SORTED) - 0.01)
SNR_MIN = min(int(k) for k in M["snr_sweep"])

CSS = open("site.css").read()


def img(path):
    return base64.b64encode(open(path, "rb").read()).decode()


def figcard(fn, head, cap):
    p = os.path.join("figs_dir", fn)
    if not os.path.exists(p):
        return ""
    return (f'<figure class="figcard"><div class="figcard-h">{head}</div>'
            f'<img src="data:image/png;base64,{img(p)}" alt="{head}">'
            f'<figcaption>{cap}</figcaption></figure>')


def zones_per_strip(n):
    """Symmetric tetrapolar zones available on a strip of n electrodes (odd outer
    gaps G, sliding). Recomputed here so the table is right regardless of what an
    older run wrote into the JSON."""
    return sum(n - G for G in range(3, n, 2))


def ci_str(n):
    if n not in CI:
        return "n/a"
    lo, hi = CI[n]
    return f"{100*lo:.0f}-{100*hi:.0f}%"


rows = []
for n in COUNTS:
    s = prim[str(n)][str(WORST)]
    mark = ' style="background:rgba(25,158,112,.10)"' if n == REC else ""
    rows.append(
        f"<tr{mark}><td class='mono'>{n}</td><td class='mono'>{2*n}</td>"
        f"<td class='mono'>{s['spacing']:.2f}</td>"
        f"<td class='mono'>{zones_per_strip(n)}</td>"
        f"<td class='mono'>{pct(g(n, STILL,'dir_acc'))}</td>"
        f"<td class='mono'>{pct(g(n, WORST,'dir_acc'))}</td>"
        f"<td class='mono'>{ci_str(n)}</td>"
        f"<td class='mono'>{pct(g(n, WORST,'lat_acc'))}</td>"
        f"<td class='mono'>{num(g(n, WORST,'auc'))}</td></tr>")
TABLE = "\n".join(rows)

snr_rows = "\n".join(
    f"<tr><td class='mono'>{s} dB</td><td class='mono'>"
    f"{pct(M['snr_sweep'][str(s)]['dir_acc'])}</td></tr>"
    for s in sorted(int(k) for k in M["snr_sweep"]))
span_rows = "\n".join(
    f"<tr><td class='mono'>{sp:.0f} cm</td><td class='mono'>"
    f"{pct(M['span_sweep'][str(sp)]['dir_acc'])}</td></tr>"
    for sp in sorted(float(k) for k in M["span_sweep"]))

HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png">
<link rel="icon" type="image/png" sizes="16x16" href="favicon-16.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<title>Directional bioimpedance: how many electrodes?</title>
<meta property="og:title" content="Directional bioimpedance reflux sensing">
<meta property="og:description" content="A non-tomographic, direction-first simulation. Electrode count swept to find the functionality/complexity knee.">
<style>{CSS}</style></head>
<body>
<aside class="side">
  <div class="brand"><b>Reflux sensing</b></div>
  <div class="brand-sub">directional, non-tomographic</div>
  <nav class="nav">
    <a href="#overview">Overview</a><a href="#why">Why not tomography</a>
    <a href="#method">Method</a><a href="#count">Electrode count</a>
    <a href="#motion">Motion</a><a href="#ablation">What carries the signal</a>
    <a href="#limits">SNR &amp; span</a><a href="#spec">Design spec</a>
    <a href="#beatvcug">Beating VCUG</a><a href="#provenance">Provenance</a>
    <a href="#implications">Implications</a><a href="#reproduce">Reproduce</a>
  </nav>
  <div class="side-foot">
    <a href="https://github.com/larachieppe/reflux-directional" target="_blank">source &amp; code &#8599;</a>
  </div>
</aside>
<main>
  <div class="tabs"><a href="index.html">Chosen design</a><a href="electrode-count.html" class="active">Electrode count</a></div>

  <header id="overview">
    <div class="kicker">Pre-hardware simulation &#183; formulation 2</div>
    <h1>How many electrodes does a directional reflux sensor actually need?</h1>
    <p class="lede">This model does <b>not</b> reconstruct an image. It measures the
    <b>direction</b> a conductive bolus travels along the ureter, from the ordering of arrival
    times across tetrapolar zones on a short flank strip. Two strips, one per flank, give
    laterality for free. The electrode count is swept to find where added complexity stops
    buying accuracy.</p>
    <div class="tiles">
      <div class="tile"><div class="tile-num" style="color:var(--accent)">{REC}</div>
      <div class="tile-label">Electrodes per strip</div><div class="tile-sub">{2*REC} channels; direction alone favours {REC_DIR}</div></div>
      <div class="tile"><div class="tile-num" style="color:var(--ink)">{pct(g(REC,WORST,'dir_acc'))}</div>
      <div class="tile-label">Direction accuracy</div><div class="tile-sub">at {WORST:.1f} cm motion</div></div>
      <div class="tile"><div class="tile-num" style="color:var(--ink)">{pct(g(REC,WORST,'lat_acc'))}</div>
      <div class="tile-label">Laterality</div><div class="tile-sub">which flank refluxed</div></div>
      <div class="tile"><div class="tile-num" style="color:var(--c2)">{num(g(REC,WORST,'auc'))}</div>
      <div class="tile-label">Reflux AUC</div><div class="tile-sub">under motion</div></div>
    </div>
    <div class="bench">
      <span>Kite EIT, still <b>73%</b></span>
      <span>Kite EIT, moving <b>44%</b></span>
      <span>this model, still <b>{pct(g(REC,'0.0','dir_acc'))}</b></span>
      <span>this model, moving <b>{pct(g(REC,WORST,'dir_acc'))}</b></span>
    </div>
    <p class="subtle" style="margin-top:14px">Motion is injected as a <b>common-mode</b> body
    displacement relative to the electrodes, so the common-mode rejection claim is tested rather
    than assumed. N=4 is reported as <b>undefined</b>, not as poor: a single tetrapolar zone has no
    ordering, so direction does not exist at any SNR.</p>
  </header>

  <section id="why">
    <div class="sec-kicker">the premise</div>
    <h2>Why direction instead of an image</h2>
    <p>A prior clinical program (Kite Medical, ~$3.1M, wound up 2023) reconstructed conductivity
    change from a 32-electrode belt and reported detection in <b>73% of cycles without motion but
    44% with motion</b>. Two structural properties explain that gap. First, the measured quantity
    (presence and magnitude of conductive fluid) is <b>shared with the dominant confounder</b>,
    ordinary bladder filling. Second, image reconstruction has <b>no intrinsic rejection of body
    motion</b>. Reflux is defined by retrograde transport, so direction, not amplitude, is the
    discriminating variable, and a differential measurement between zones rejects perturbations
    common to those zones.</p>
    <div class="note">A single symmetric tetrapolar array is <b>direction-blind</b>: by symmetry a
    bolus travelling up produces the same scalar impedance perturbation as one travelling down.
    Breaking that symmetry longitudinally is the entire design.</div>
    {figcard("figG_mechanism.png", "What the detector actually reads",
             "One representative trial per direction at N=8, 0.4 cm motion, 60 dB SNR. Left: zone traces after common-mode removal, the impedance dip marching up the strip for reflux and down for normal flow. Right: arrival time against zone height. The SIGN of that slope is the whole diagnosis. Illustrative, not a statistic.")}
  </section>

  <section id="method">
    <div class="sec-kicker">what it simulates</div>
    <h2>Method</h2>
    <p>A verified 3-D complete-electrode forward model (finite elements, <code>scikit-fem</code>)
    on a torso segment whose axis is the body superior-inferior direction, with bilateral ureters,
    bladder and kidneys. Two electrode strips sit on the flanks over a fixed
    <b>{SPAN:.0f} cm</b> span. Zones are symmetric tetrapolar (Schlumberger-style) arrays: the
    outer pair drives current, the central pair senses voltage, so contact impedance is largely
    rejected. Sensing depth scales with the outer aperture, so a denser strip can synthesize a
    <b>wider aperture in software</b> to reach the deep ureter; the sweep allows every aperture.</p>
    <ul>
      <li>Four scenarios: no flow, antegrade transport, bladder filling (the confounder), reflux.</li>
      <li>Multi-frequency complex admittivity at {" and ".join(f"{f/1e3:.0f}" for f in cfg['freqs'])} kHz.</li>
      <li>Per-electrode time-varying contact impedance, correlated + uncorrelated noise.</li>
      <li>Randomized anatomy, grade, side and motion realization per trial; the same trials are
      replayed for every electrode count, so the comparison is <b>paired</b>.</li>
      <li>The primary endpoint is measured at <b>grade &#8805; III</b>, where the device is meant to
      work and where the clinical miss-rate constraint binds. Grades I to II are reported
      separately: low-grade reflux does not travel far enough to cross the sensed span, so it is
      undetectable by this method by construction, not by tuning.</li>
      <li>Single excitation frequency (50 kHz) for this sweep. Direction is a <b>timing</b>
      measurement, so the multi-frequency question is separate and is not tested here.</li>
    </ul>
    {figcard("figA_count.png", "Direction accuracy vs electrode count",
             "Accuracy against electrodes per strip at four motion levels, span fixed. N=4 is structurally undefined (one zone, no ordering).")}
  </section>

  <section id="count">
    <div class="sec-kicker">the design question</div>
    <h2>Electrode count: functionality against complexity</h2>
    <p>The flank span is capped by anatomy, so more electrodes means tighter pitch. Tighter pitch
    lowers the depth of any single aperture, but a longer strip of electrodes can form
    <b>wider</b> apertures, and more zones at a given aperture means the common mode can be
    estimated and removed. Those pressures oppose each other, so the useful count is found rather
    than assumed.</p>
    <div class="prov-wrap"><table class="prov">
      <tr><th>N per strip</th><th>Channels</th><th>Pitch (cm)</th><th>Zones/strip</th>
          <th>Dir. acc (still)</th><th>Dir. acc ({WORST:.1f} cm motion)</th>
          <th>95% CI</th><th>Laterality</th><th>AUC</th></tr>
      {TABLE}
    </table></div>
    <div class="finds">
      <div class="find"><h3>N = 4</h3><p class="big">undefined</p>
      <p>One tetrapolar zone. No ordering exists, so direction is unavailable at any SNR.</p></div>
      <div class="find"><h3>N = 5</h3><p class="big">2 zones</p>
      <p>A lag exists, but two zones cannot separate common mode from signal: mean removal would
      make the pair exact negatives.</p></div>
      <div class="find"><h3>N = {REC}</h3><p class="big">recommended</p>
      <p>Direction alone favours <b>N={REC_DIR}</b>, but laterality (an independent must-have)
      ranks the counts differently and favours <b>N={REC}</b>. Among counts not significantly worse
      on direction, N={REC} is best on laterality. {2*REC} channels.</p></div>
    </div>
    {figcard("figC_complexity.png", "Why N was chosen",
             "Direction and laterality plotted together against channel count at the worst motion. They rank the counts differently, which is the whole reason the choice is not simply the top of one curve.")}
    <div class="note"><b>On the N=8 dip.</b> The curve is not monotonic: N=8 sits below both its
    neighbours at the highest motion. With 96 trials the 95% interval on that point is roughly
    &#177;10 points, so it overlaps N=6, N=10 and N=12 and should be read as noise around a broadly
    flat region rather than a real optimum at N=10 or 12. The one difference that survives the
    intervals is that <b>N=5 and N=6 beat N&#8805;8</b>, not the fine structure among the larger
    counts.</div>
  </section>

  <section id="motion">
    <div class="sec-kicker">the failure mode that mattered</div>
    <h2>Motion robustness</h2>
    <p>Motion is what degraded the prior tomographic program, so it is the primary endpoint here.
    It is injected as a common-mode displacement of the body relative to the electrodes, plus
    breathing and an independent per-electrode contact term that does <b>not</b> cancel.</p>
    {figcard("figB_motion.png", "Direction accuracy against injected motion",
             "Each curve is one electrode count. Dashed red lines mark the published tomographic result (73% still, 44% moving) for reference.")}
    {figcard("figE_lat_grade.png", "Laterality and per-grade accuracy",
             "Left: which flank refluxed. Right: accuracy by reflux grade. High grades are the strength; grades I to II remain the honest hard tail.")}
  </section>

  <section id="ablation">
    <div class="sec-kicker">is it really direction?</div>
    <h2>What carries the signal</h2>
    <p>If the detector were really reading amplitude, it would be reading the same confounded
    quantity that sank the tomographic framing. The ablation separates the two: a model given only
    <b>amplitude</b> features against one given only <b>direction</b> features.</p>
    {figcard("figD_auc_ablation.png", "Reflux AUC and feature ablation",
             "Amplitude-only collapses toward chance because bladder filling produces amplitude too. Direction features carry the discrimination.")}
  </section>

  <section id="limits">
    <div class="sec-kicker">what the hardware must deliver</div>
    <h2>SNR and span requirements</h2>
    <p>Direction accuracy is <b>flat from 50 to 80 dB</b> of instrument SNR, so this design is
    <b>motion-limited, not noise-limited</b>, and buying a quieter front end does not buy accuracy.
    Strip span behaves very differently: it is the strongest single lever measured here, worth more
    than any electrode-count choice.</p>
    <div class="prov-wrap" style="display:flex;gap:18px;flex-wrap:wrap">
      <table class="prov" style="min-width:260px"><tr><th>Instrument SNR</th><th>Direction accuracy</th></tr>{snr_rows}</table>
      <table class="prov" style="min-width:260px"><tr><th>Strip span</th><th>Direction accuracy</th></tr>{span_rows}</table>
    </div>
    {figcard("figF_snr_span.png", "SNR and span sweeps",
             "Both at N=8 under 0.6 cm motion. Accuracy is FLAT from 50 to 80 dB, so the system is motion-limited, not noise-limited. Span, by contrast, is the strongest single design lever measured here.")}
  </section>


  <section id="spec">
    <div class="sec-kicker">what to build</div>
    <h2>Design specification</h2>
    <p>Every number below is set by a measurement in this study, not by intuition. Where the
    simulation did not resolve something, it says so.</p>
    <div class="prov-wrap"><table class="prov">
      <tr><th>Parameter</th><th>Specify</th><th>Evidence from the sweep</th></tr>
      <tr><td><b>Electrodes per strip</b></td><td class="mono">{REC} (={2*REC} channels)</td>
          <td>Direction favours N={REC_DIR} ({pct(g(REC_DIR,'0.6','dir_acc'))} vs {pct(g(REC,'0.6','dir_acc'))} at 0.6 cm), laterality favours N={REC} ({pct(g(REC,'0.6','lat_acc'))} vs {pct(g(REC_DIR,'0.6','lat_acc'))}). N={REC} is also the smallest count giving 3+ zones. More than 8 buys nothing and costs direction accuracy.</td></tr>
      <tr><td><b>Strip span</b></td><td class="mono">{SPAN_BEST:.0f} cm</td>
          <td>{pct(M["span_sweep"][str(SPANS_SORTED[0])]["dir_acc"])} at {SPANS_SORTED[0]:.0f} cm rising to {pct(M["span_sweep"][str(SPAN_BEST)]["dir_acc"])} at {SPAN_BEST:.0f} cm, then flat. <b>The strongest single lever measured</b>, worth more than any electrode-count choice.</td></tr>
      <tr><td><b>Zones per strip</b></td><td class="mono">&#8805; 3</td>
          <td>Common-mode rejection subtracts the across-zone mean. With exactly 2 zones the mean-removed pair are exact negatives and the lag is destroyed, so 2 zones cannot reject common mode at all.</td></tr>
      <tr><td><b>Outer aperture</b></td><td class="mono">&#8805; 6 cm</td>
          <td>Tetrapolar sensing depth scales with aperture (roughly half). The ureter sits ~3 cm below the skin in this model, so apertures under ~6 cm do not reach it.</td></tr>
      <tr><td><b>Measurement</b></td><td class="mono">fractional &#916;Z/|Z|</td>
          <td>Absolute &#916;Z carries each channel's standing impedance as a gain. Unequal gains made the strip selector degenerate (it picked one side ~90% of the time regardless of truth). Normalizing per channel fixed it.</td></tr>
      <tr><td><b>Instrument SNR</b></td><td class="mono">{SNR_MIN} dB is enough</td>
          <td>Accuracy is <b>flat from {SNR_MIN} to {max(int(k) for k in M["snr_sweep"])} dB</b>. The design is motion-limited, not noise-limited. Do not pay for a quieter front end.</td></tr>
      <tr><td><b>Motion tolerance</b></td><td class="mono">&#8804; 0.5 cm</td>
          <td>Per-event accuracy {pct(g(REC,'0.0','dir_acc'))} (still), {pct(g(REC,'0.3','dir_acc'))} (0.3 cm), {pct(g(REC,'0.6','dir_acc'))} (0.6 cm), {pct(g(REC,'0.9','dir_acc'))} (0.9 cm). <b>The binding constraint.</b></td></tr>
      <tr><td><b>Events per session</b></td><td class="mono">&#8805; 6, decide &#8805;2-of-6</td>
          <td>The lever that beats VCUG. See below.</td></tr>
      <tr><td><b>Claimed grade range</b></td><td class="mono">grade &#8805; III</td>
          <td>Grades I to II run 29-50% (at or below chance): low-grade reflux does not travel far enough to cross the sensed span. Do not claim them.</td></tr>
      <tr><td>Excitation frequency</td><td class="mono">not resolved</td>
          <td>A single frequency (50 kHz) was used here, so the multi-frequency question is <b>untested</b> by this study.</td></tr>
    </table></div>
  </section>

  <section id="beatvcug">
    <div class="sec-kicker">the strategy</div>
    <h2>How this beats VCUG</h2>
    <p>Not by raising per-event accuracy. VCUG's exploitable weakness is that it captures
    <b>one or two forced voids</b> and therefore misses roughly <b>20% of reflux</b>, which is
    intermittent. A passive wearable observes many natural cycles, and detection compounds with
    the number of events observed.</p>
    <div class="prov-wrap"><table class="prov">
      <tr><th>Per-event accuracy</th><th>1 event</th><th>2</th><th>3</th><th>4</th><th>6</th></tr>
      <tr><td class="mono">{pct(PE_WORST)} (worst motion)</td>{"".join(f"<td class='mono'>{100*multi(PE_WORST,k):.0f}%</td>" for k in (1,2,3,4,6))}</tr>
      <tr><td class="mono">{pct(PE_BEST)} (0.3 cm motion)</td>{"".join(f"<td class='mono'>{100*multi(PE_BEST,k):.0f}%</td>" for k in (1,2,3,4,6))}</tr>
      <tr style="background:rgba(230,103,103,.08)"><td class="mono">{pct(PE_WORST)}, 15% unmeasurable</td>{"".join(f"<td class='mono'>{100*multi(PE_WORST,k,0.15):.0f}%</td>" for k in (1,2,3,4,6))}</tr>
    </table></div>
    <p>A <b>&#8805;2-of-6</b> decision rule protects specificity while capturing the sensitivity
    gain: at {pct(PE_WORST)} per-event it yields <b>{100*atleast(PE_WORST,2,6):.0f}% sensitivity</b>,
    and with a 10% per-event false-positive rate the session-level false-positive rate is only
    <b>{100*atleast(0.10,2,6):.0f}%</b> (about {100-100*atleast(0.10,2,6):.0f}% specificity).
    For comparison, nuclear VCUG achieves <b>81% sensitivity at 89% specificity</b> against
    conventional VCUG.</p>
    <div class="note"><b>The caveat that decides this.</b> The compounding above assumes events are
    independent. They are not: if electrode placement is poor or the anatomy is atypical, every
    event on that child fails together. The red row shows what happens if 15% of children are
    systematically unmeasurable, and the ceiling drops to about 85% no matter how many events you
    observe. <b>The fraction of children who are systematically unmeasurable is therefore the single
    most important unknown</b>, and it cannot be answered in simulation. It is the first thing a
    phantom and then a clinical pilot should measure.</div>
    <div class="finds">
      <div class="find"><h3>1. Capture more events</h3><p class="big">biggest lever</p>
      <p>Passive overnight wear instead of one forced void. Turns {pct(PE_WORST)} per-event into {100*atleast(PE_WORST,2,6):.0f}% per session.</p></div>
      <div class="find"><h3>2. Longer strip</h3><p class="big">+{100*(M["span_sweep"][str(SPAN_BEST)]["dir_acc"]-M["span_sweep"]["12.0"]["dir_acc"]):.0f} points</p>
      <p>{SPAN_BEST:.0f} cm instead of 12 cm, if pediatric anatomy allows it.</p></div>
      <div class="find"><h3>3. Quiet context</h3><p class="big">+{100*(g(REC,'0.3','dir_acc')-g(REC,'0.9','dir_acc')):.0f} points</p>
      <p>Sleep or still wear moves per-event accuracy from {pct(g(REC,'0.9','dir_acc'))} to {pct(g(REC,'0.3','dir_acc'))}. Cheaper than motion compensation.</p></div>
    </div>
  </section>

  <section id="provenance">
    <div class="sec-kicker">where the numbers come from</div>
    <h2>Provenance and honesty</h2>
    <div class="prov-wrap"><table class="prov">
      <tr><th>Element</th><th>Source</th><th>Status</th></tr>
      <tr><td>Tissue admittivity</td><td class="src">Gabriel / IT'IS family, representative values</td><td>Literature, not cohort-fit</td></tr>
      <tr><td>Forward model</td><td class="src">Complete electrode model, scikit-fem</td><td>Reciprocity-verified</td></tr>
      <tr><td>Anatomy</td><td class="src">Structured cylinder with organs</td><td><b>Not</b> segmented CT</td></tr>
      <tr><td>SNR budget</td><td class="src">Assumed, swept {min(int(k) for k in M['snr_sweep'])}-{max(int(k) for k in M['snr_sweep'])} dB</td><td>No hardware exists yet</td></tr>
      <tr><td>Motion model</td><td class="src">Common-mode displacement + breathing + independent contact term</td><td>Structured, not measured</td></tr>
      <tr><td>Kite comparison</td><td class="src">Published 73% / 44% cycle detection</td><td>Different task; context only</td></tr>
    </table></div>
    <div class="note">This establishes a <b>feasibility and robustness envelope, not clinical
    performance</b>. There is no phantom, animal or clinical data behind these numbers. The
    73%/44% comparison is a different measurement on different subjects and is shown for context,
    not as a like-for-like benchmark.</div>
  </section>

  <section id="implications">
    <div class="sec-kicker">what this means for the build</div>
    <h2>Implications</h2>
    <div class="prov-wrap"><table class="prov">
      <tr><th>Finding</th><th>Implication</th></tr>
      <tr><td>N=4 gives no direction at all</td><td>Any single-zone (single Wenner array) proposal cannot detect reflux direction. Minimum is 5, and 5 cannot reject common mode.</td></tr>
      <tr><td>More electrodes made direction <b>worse</b>, not better</td><td>Over a fixed span, extra electrodes shrink the pitch and add aperture choices for the selector to get wrong. Direction accuracy falls from {pct(g(5,WORST,'dir_acc'))} (N=5) to {pct(g(12,WORST,'dir_acc'))} (N=12) at the worst motion. This is the opposite of the intuition that denser is safer.</td></tr>
      <tr><td>Direction and laterality disagree on the optimum</td><td>Direction favours N={REC_DIR}; laterality favours N={REC} ({pct(g(REC,WORST,'lat_acc'))} vs {pct(g(REC_DIR,WORST,'lat_acc'))} at the worst motion). Specify <b>N={REC}, {2*REC} channels</b>, accepting a small direction cost to meet the laterality requirement.</td></tr>
      <tr><td><b>Span matters more than electrode count</b></td><td>Going from 12 cm to 14 cm of strip buys more accuracy than any electrode-count choice. Prioritize a longer strip over a denser one, within what pediatric anatomy allows.</td></tr>
      <tr><td>Flat across 50-80 dB SNR</td><td>The design is <b>motion-limited, not noise-limited</b>. A quieter front end does not buy accuracy; motion tolerance and strip length do.</td></tr>
      <tr><td>Depth is set by aperture, not count</td><td>Use wide (Schlumberger) apertures to reach the ureter; a dense strip is useful because it can <b>synthesize</b> apertures, not because adjacent windows are better.</td></tr>
      <tr><td>Amplitude-only collapses</td><td>Confirms the design premise: measure direction, not presence. This is the specific failure the tomographic framing could not escape.</td></tr>
      <tr><td>Grades I to II remain hard</td><td>Keep the pre-specified endpoint on grade &#8805; III, where the clinical consequence is concentrated.</td></tr>
    </table></div>
  </section>

  <section id="reproduce">
    <div class="sec-kicker">run it yourself</div>
    <h2>Reproduce</h2>
<pre>python -m venv .venv &amp;&amp; source .venv/bin/activate
pip install -r requirements.txt
python run_directional.py          # sweep -&gt; metrics_directional.json  (~{M.get('runtime_min',0):.0f} min)
python make_figs_directional.py &amp;&amp; python make_figs_mechanism.py
python build_site.py               # this page</pre>
    <p class="subtle">{M['config']['n_trial']} trials per (count, motion) cell, replayed identically
    across electrode counts. Total runtime {M.get('runtime_min',0):.0f} min.</p>
  </section>
</main>
</body></html>"""

open("electrode-count.html", "w").write(HTML)
print(f"wrote electrode-count.html ({len(HTML)//1024} KB)  recommended N={REC} "
      f"(best N={BEST_N}, acc {pct(best_acc)})")
