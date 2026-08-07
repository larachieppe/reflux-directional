## 10. Study 6: non-rigid respiratory motion &mdash; result withdrawn, re-running

> [!WARN]
> **This study's headline is withdrawn.** It previously concluded that the gradient hypothesis was
> refuted. An audit of the results found the comparison was confounded, so the conclusion is not
> established either way. The design and the method below stand; the numbers do not. A corrected
> run is in progress.
>
> The displacement weight was `w = (1 - grad) + grad*(z/H)`. Because `z/H` runs from 0 to 1 across
> the torso, that weight has **mean 0.50 at grad = 1.0** and 0.75 at grad = 0.5. The "gradient"
> arms were therefore not applying the same displacement redistributed with height &mdash; they
> were applying **half, and three-quarters, of the total motion** of the rigid arm.
>
> That wrecks the comparison, because this study's own second result is that motion **amplitude**
> is what degrades accuracy. The gradient arms were handed a strictly easier problem, which is the
> most likely reason they scored slightly *better* (79.4% against 71.9%) and why the refutation
> looked so clean.
>
> The fix centres the weight on its own mean, `w = 1 + grad*(z/H &minus; mean(z/H))`, so `grad`
> changes only the *shape* of the displacement field and never its average magnitude. The
> kidney-minus-bladder differential is unchanged (+0.30 at grad = 0.5, +0.60 at grad = 1.0) and
> `grad = 0` still gives `w = 1` exactly, so no other study's numbers move. Before concluding this
> was a confound rather than a dead parameter, `grad` was confirmed to reach the measurement: at
> 2 cm displacement it changes the sensed transfer impedance by up to 1.5%.
>
> The figures below are the **confounded** run, kept so the correction is auditable. Read them as a
> record of what was measured, not as evidence about gradients.

Every motion result before this one used a **rigid** translation, which is exactly the
perturbation that subtracting the across-zone mean provably nulls. A rigid-only model can only ever
*confirm* the common-mode rejection claim; it cannot test it. This report previously named
non-rigid motion the single most likely place the model flatters the design, on the argument that a
craniocaudal gradient survives mean subtraction and injects a phase-locked false travelling wave
&mdash; the exact shape of the failure that took the prior tomographic program from 73% to 44%.

### 10.1 The gradient hypothesis, tested

{{table:motion2_false_retrograde}}

*False-retrograde rate on non-travelling windows: how often the device invents reflux
while the child is merely breathing.*

> [!KEY]
> **The hypothesis is refuted.** Averaged over amplitudes, false-retrograde runs {{val:m2_fr_rigid}} rigid, {{val:m2_fr_half}} at half gradient and {{val:m2_fr_full}} at full gradient, and direction accuracy runs {{val:m2_acc_rigid}}, {{val:m2_acc_half}} and {{val:m2_acc_full}}. There is no gradient penalty at any amplitude. The full-gradient arm is, if anything, slightly better. The predicted false travelling wave did not appear.

{{fig:figs_new/n3_gradient.png|Study 6. The three gradient curves lie on top of one another at every amplitude. The predicted craniocaudal false travelling wave does not appear.}}

That makes five confident claims in this project overturned by measurement, and this one was the
authors' own stated existential risk. Candidate explanations &mdash; that the gradient displaces
kidney and bladder differentially in a way that reinforces rather than mimics the true bolus
signature, or that the induced slope is simply small against the bolus-induced slope at these
amplitudes &mdash; are **post hoc and untested**. The honest statement is that the mechanism was
predicted, the prediction was wrong, and why it was wrong is not yet established.

### 10.2 What actually degrades the measurement

{{table:motion2_accuracy}}

Amplitude, not gradient. Raw accuracy falls from 100% to under 50% between 0 and 3 cm. But the
failure mode is **safe**: accuracy *on the calls actually made* holds at 84% at 2 cm and
62&ndash;69% at 3 cm, while the abstention rate climbs to roughly a third. The estimator degrades
into declining to answer, not into answering confidently and wrongly. That is the behaviour the
abstain gate was designed to produce, and this is the first study that genuinely tested it.

{{fig:figs_new/n4_abstain.png|Study 6. The gap between raw accuracy and accuracy-on-calls-made is the abstain gate working: under motion the estimator declines to answer rather than answering wrongly.}}

For scale: quiet-breathing renal excursion is about 1 cm, where the design holds
{{val:m2_1cm_decided}} on calls made with only
{{val:m2_1cm_abstain}} abstention. Two to three centimetres is deep
breathing or crying.

> [!WARN]
> **An unexplained floor.** False-retrograde on empty windows is {{val:m2_fr_zero_motion}} **at zero motion**. Motion does not explain it, so something else does &mdash; noise passing the gate, a residual in the common-mode step, or a bladder-filling confounder leaking into the slope. It is a floor on achievable specificity and it has not been chased down.

{{methods:motion2}}
