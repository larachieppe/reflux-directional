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

> [!WARN]
> **Study 6 is grades III&ndash;V only.** `run_motion2.py` sets `GRADES = (3, 4, 5)`, so the whole
> motion curve below is computed on the easiest 40% of the modelled population, and the exclusion
> is recorded nowhere in the figures or the tables. Grades I and II are 60% of reflux under this
> project's own prevalence model and are exactly where the method is weakest, so the motion
> tolerance reported here is an upper bound.

### 10.1 The gradient hypothesis, tested

{{table:motion2_false_retrograde}}

*False-retrograde rate on non-travelling windows: how often the device invents reflux
while the child is merely breathing.*

> [!WARN]
> **What the confounded run showed, and why it proves nothing.** Averaged over amplitudes, false-retrograde ran {{val:m2_fr_rigid}} rigid, {{val:m2_fr_half}} at half gradient and {{val:m2_fr_full}} at full gradient, with direction accuracy {{val:m2_acc_rigid}}, {{val:m2_acc_half}} and {{val:m2_acc_full}}. The gradient arms look equal or slightly better &mdash; but they also received 75% and 50% of the rigid arm's displacement, and amplitude is what degrades accuracy. An easier arm scoring better is not evidence that gradients are harmless. The comparison is being re-run amplitude-matched.
>
> Two further reasons not to read these cells too closely. The averages **include a = 0.0**, where the gradient is mathematically a no-op, diluting any real effect by a fifth. And the 72 "empty" windows per cell are really **36 seed-matched pairs** &mdash; `noflow_i` and `bladder_i` share anatomy, displacement, contact impedance and noise &mdash; so every confidence interval on false-retrograde is narrower than it should be.

{{fig:figs_new/n3_gradient.png|Study 6. The three gradient curves lie on top of one another at every amplitude. The predicted craniocaudal false travelling wave does not appear.}}

The mechanism was predicted, the first measurement appeared to refute it, and the refutation then
turned out to rest on a confounded comparison. Nothing about craniocaudal gradients is established
either way until the amplitude-matched run lands.

### 10.2 What actually degrades the measurement

{{table:motion2_accuracy}}

Amplitude, not gradient. Raw accuracy falls from 100% to under 50% between 0 and 3 cm. But the
failure mode is **safe**: accuracy *on the calls actually made* holds at 84% at 2 cm and
62&ndash;69% at 3 cm, while the abstention rate climbs to roughly a third. The estimator degrades
into declining to answer, not into answering confidently and wrongly. That is the behaviour the
abstain gate was designed to produce, and this is the first study that genuinely tested it.

{{fig:figs_new/n4_abstain.png|Study 6. The gap between raw accuracy and accuracy-on-calls-made is the abstain gate working: under motion the estimator declines to answer rather than answering wrongly.}}

For scale, quiet-breathing renal excursion is about 1 cm. **But the reassuring figure previously
quoted here &mdash; {{val:m2_1cm_decided}} on calls made with only {{val:m2_1cm_abstain}}
abstention &mdash; came from the full-gradient cell, which under the confound received only about
half that displacement.** The rigid cell at the same nominal amplitude abstains 22.2%, four times
as often. The honest reading is that 1 cm of genuine motion costs materially more than the
gradient arms suggested, and the corrected run will say how much.

> [!WARN]
> **An unexplained floor.** False-retrograde on empty windows is {{val:m2_fr_zero_motion}} **at zero motion**. Motion does not explain it, so something else does. The leading candidate is the gate itself: `lin` is an *uncorrected* goodness-of-fit, whose null expectation for a three-zone aperture is well above zero, so `LIN_GATE = 0.35` may simply sit below the value pure noise produces. If so the floor is a property of the threshold, not of the physics, and an adjusted statistic would remove it. That is testable and has not been tested.
>
> Note also that this rate's denominator **includes abstained windows**, so it is an unconditional
> rate rather than a false-alarm rate among calls made. The non-monotonic dip at grad = 0.5 is an
> abstention artifact and is not significant at n = 72.

{{methods:motion2}}
