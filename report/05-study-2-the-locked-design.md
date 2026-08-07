## 5. Study 2: the locked design

{{val:n_strip}} electrodes per strip, {{val:span}} cm span, {{val:channels}} channels,
{{val:snr}} dB, at 50 and 100 kHz.

> [!WARN]
> **Every number in this section is grades III&ndash;V only, and that was disclosed nowhere.**
> Both the operating arm and the subject arm draw their grade from `rng.choice([3, 4, 5])`. Grades
> I and II are excluded entirely &mdash; and they are 60% of real reflux under this project's own
> prevalence model, and precisely the grades the method struggles with. The same study's grade arm,
> which does span all five, reports **57.1%** at grade I and **57.1%** at grade II under the same
> motion where the headline reads 98%.
>
> So "the locked design reaches 98% direction accuracy" means *on the easiest 40% of the disease*.
> Read the grade table, not the operating table, for anything resembling a clinical figure.

{{table:design_motion}}

{{fig:figs_design/d2_motion.png|Performance against motion at the locked design.}}

### 5.1 The multi-event screening rule

VCUG captures one or two forced voids. A passive wearable observes many, and detection compounds.
Simulated as {{val:n_subjects}} children with {{val:k_events}} events each, **anatomy and placement
held fixed per child** so correlated failure would show rather than average away. Per event:
{{val:per_event_sens}} sensitivity at a {{val:per_event_fp}} false-positive rate.

{{table:multievent}}

{{fig:figs_design/d4_multievent.png|Sensitivity and specificity reported separately, with the chance floor.}}

> [!NOTE]
> The coin-flip column exists because an earlier version of this metric pooled healthy and refluxing children and counted a correct negative as a hit. Its chance floor was 89%, *above* the ~80% VCUG line it was being compared against, so a coin-flip detector would have appeared to beat VCUG.
>
> **That column is the chance floor for SENSITIVITY only.** It is printed beside the specificity
> column, where it does not apply: it is the rate at which a coin-flip detector *flags* a child,
> which bounds sensitivity from below and specificity from above. Do not read it as a floor under
> both.

> [!WARN]
> **Three further caveats on the 100% / 100% result.**
>
> The control group contains **no empty windows**. Healthy children here always produce a real
> antegrade void; a child observed while nothing is flowing is never simulated. Study 6, which does
> simulate empty windows, puts the false-retrograde rate at 11.1% even at zero motion. A
> specificity measured against controls that always contain a clean signal is not the specificity
> a screening device would see.
>
> **`best_k` is chosen by maximum Youden index on the same 110 children it is then scored on**, so
> the reported sensitivity and specificity are in-sample and optimistically biased. There is no
> held-out estimate.
>
> **Placement is identical for all 110 children.** Only anatomy varies. The study is presented as
> testing whether repeated voids compound, but the failure mode Study 5 measures &mdash; a child
> whose strip simply never covered the relevant segment &mdash; cannot occur here by construction,
> which is why `never_detected` is exactly 0.0%.

> [!NOTE]
> **The dominant clinical confounder is not reported in the headline.** At the disclosed operating
> point the confusion matrix calls bladder filling **antegrade on 31% of events and reflux on
> 10%**. Ordinary bladder filling being read as flow is the exact failure that limited the prior
> tomographic program, and it belongs beside the accuracy figures rather than only in the matrix.
>
> The operating point labelled "90% specificity" delivers **89.7%**: the quantile index truncates
> rather than rounding up.

{{methods:design}}
