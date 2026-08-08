## 6. Study 2: the chosen design, characterised

{{val:n_strip}} electrodes per strip, {{val:span}} cm span, {{val:channels}} channels,
{{val:snr}} dB, at 50 and 100 kHz. This study stops sweeping and characterises that one
configuration end to end: across the motion range, across the five reflux grades, and across
repeated voids on the same simulated child.

{{table:design_motion}}

{{fig:figs_design/d2_motion.png|Performance against motion at the chosen design.}}

> [!NOTE]
> **The operating and subject arms cover grades III&ndash;V only.** Both draw their grade from
> `{3, 4, 5}`. Grades I and II are 60% of reflux under the prevalence model used here, and they are
> where the method is weakest, so the headline figures in this section describe the easier
> two-fifths of the disease. The grade arm below spans all five and is the number to quote for
> anything clinical.

### 6.1 Performance by grade

Grade sets how far a refluxing bolus climbs the ureter: grade I reaches 20% of the way, grade V the
whole distance. Since the estimator needs the bolus to cross enough zones to fit a slope, grade is
the dominant determinant of detectability &mdash; far more so than motion at the levels tested.

### 6.2 The multi-event screening rule

VCUG captures one or two forced voids. A passive wearable observes many, and detection compounds.
Simulated as {{val:n_subjects}} children with {{val:k_events}} events each, **anatomy and placement
held fixed per child** so that correlated failure shows rather than averaging away. Per event:
{{val:per_event_sens}} sensitivity at a {{val:per_event_fp}} false-positive rate.

{{table:multievent}}

{{fig:figs_design/d4_multievent.png|Sensitivity and specificity reported separately, with the chance floor.}}

> [!NOTE]
> **Three things bound how far this result generalises.** The chance-floor column is the floor for
> *sensitivity* under a coin-flip detector; it does not bound specificity. The value of *k* is
> chosen to maximise Youden on the same children it is scored on, so the paired sensitivity and
> specificity are in-sample. And electrode placement is identical for all {{val:n_subjects}}
> children, so this arm cannot exhibit the placement-driven correlated failure that &sect;9 is built
> to measure &mdash; which is why no child here fails every void.

> [!NOTE]
> **Bladder filling is the confounder that matters.** At the disclosed operating point the device
> reads ordinary bladder filling as antegrade flow on 31% of events and as reflux on 10%. A
> filling bladder is a large, slow, genuinely conductive change, and separating it from transport
> is the single hardest discrimination the design has to make. The threshold quoted as
> 90% specificity delivers 89.7%.

{{methods:design}}
