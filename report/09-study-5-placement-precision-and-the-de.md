## 9. Study 5: placement precision, and the design this overturns

48 simulated children per cell, six voids each, with **one placement error drawn per child and
shared across all of that child's voids** &mdash; a strip is applied once, not re-applied per
void. That is what makes failure correlated within a child, which is the entire question. Had the
error been redrawn per event, repeated voids would average it away and the study would have
reported a reassuring, meaningless number.

{{table:precision}}

> [!WARN]
> **Claim overturned #5, and it is the big one.** This report publishes a locked design of a **16 cm strip at z = 0.50**, and Study 2 characterises that configuration. Study 5 shows it never detects **25% of refluxing children on any of six voids at perfect placement**, rising to 33% with realistic placement error, and misses **43% of low-grade refluxers even when placed perfectly**. The 10 cm strip over the ureterovesical junction misses **0%** at perfect placement and 8% at 2 cm of error. **The published locked design is wrong for low grades.**

> [!NOTE]
> **But the short strip is not simply the answer**, and an earlier version of this section said it was. Re-characterising the full design at 10 cm @ z = 0.34 recovered grade II (55.4% &rarr; 83.9% still) and cost accuracy on the grades that already worked, and the gap widens as motion grows: at 0.6 cm of motion grade IV fell 98.2% &rarr; 46.4% and grade III 78.6% &rarr; 60.7%, while grade V went 98.2% &rarr; 80.4%. (Per-grade detection rates, not AUC &mdash; see &sect;4.1 for why the AUC this report published is not a measure of the direction rule.) The mechanism is the same lever-arm argument that explains the electrode-count result (&sect;3.6): slope precision scales with the axial spread of the zone centroids, and a 10 cm strip has 62% of the lever arm of a 16 cm one, so its slope estimate is noisier and degrades faster under motion.

 The two studies are not in conflict &mdash; they measure different things. Study 2 measures the *marginal* per-event rate with fresh anatomy each trial. Study 5 holds anatomy and placement fixed per child, so it measures *correlated* failure: whether a given child is ever detectable at all. A placement can have the better average per-event accuracy while completely failing a subset of children, and only the second metric sees that. Both are real, and the design has to satisfy both.

{{fig:figs_new/n2_precision.png|Study 5. The published 16 cm mid-torso placement loses a quarter of all refluxing children and 43% of low-grade refluxers even when placed perfectly. The 10 cm strip over the ureterovesical junction misses none.}}

This is the same lesson as Study 3, arriving a second time by a different route: low-grade
reflux is a **placement** problem. A long mid-torso strip spreads its zones over anatomy where
the low-grade bolus never travels, and no amount of repeat observation recovers a child whose
strip never covered the relevant segment. Repeat voids only help when failure is independent
across voids, and placement failure is precisely the kind that is not.

### 9.1 The most likely artifact, tested and ruled out

A result this load-bearing deserves an attempt to break it. The most plausible way "10 cm beats
16 cm" could be an *estimator* artifact rather than physics is lag-window saturation:
<code>xcorr_lag</code> clips the inter-zone lag search at <code>max_lag = 2T/3</code>. If true lags
saturated that bound on the long strip but not the short one, the slope fit would be biased in
exactly the direction of the published conclusion.

<table><tr><th>Configuration</th><th>grade I</th><th>grade II</th><th>grade III</th><th>grade IV</th>
<th>at clip</th></tr>
<tr><td>16 cm mid-torso &mdash; mean |lag|</td><td>1.01</td><td>0.72</td><td>1.37</td><td>1.62</td><td>0%</td></tr>
<tr class="hi"><td>10 cm over the UVJ &mdash; mean |lag|</td><td>1.87</td><td>1.98</td><td>1.84</td><td>1.57</td><td>0%</td></tr></table>

*Inter-zone lag in frames, against a clip boundary of 13 frames at T = 20.*

> [!KEY]
> **Refuted.** The largest lag observed anywhere was 3.13 frames against a bound of 13, and **0% of lags sat at or near the clip** in either configuration. The conclusion is not a lag-window artifact.

The check also *supports* the mechanism. The 10 cm strip shows **larger** lags than the
16 cm strip at every low grade, which is what a genuine traverse looks like: the short strip sits
where the bolus actually travels, while the long mid-torso strip spreads its zones over anatomy the
low-grade bolus barely reaches, so its zones see a weak and nearly simultaneous perturbation. That
is the same mechanism Study 3 measured by counting zone crossings, arriving here independently.

> [!NOTE]
> **Do not over-read the individual cells.** With 48 children per cell the confidence intervals are wide, and the 16 cm arm is non-monotonic in &sigma; (75%, 67%, 88%, 83%), which is not physically sensible and indicates large per-cell noise. The *never-detected* gap between the two placements is large and consistent across every &sigma;, and that is the finding. The individual sensitivity figures are not precise enough to rank.

{{methods:precision}}
