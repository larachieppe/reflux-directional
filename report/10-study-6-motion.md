## 10. Study 6: motion

Motion is what decides this device. The prior tomographic program fell from 73% detection at rest
to 44% with movement, and the whole argument for a differential inter-zone measurement is that it
should reject perturbations common to every zone. This study tests that claim rather than assuming
it, and separates two kinds of movement that behave very differently.

A **rigid** displacement moves the whole body relative to the array. It is common to every zone, so
subtracting the across-zone mean should null it almost exactly. A **craniocaudal gradient** is what
breathing actually does: the kidney travels 1&ndash;3 cm with the diaphragm while the bladder stays
nearly fixed. A displacement that varies with height does **not** cancel under mean subtraction, and
in principle it feeds straight into the arrival-time slope as a phase-locked false travelling wave
&mdash; the exact shape of the failure that ended the prior program.

The gradient is applied mean-preserving, so that changing it alters only the *shape* of the
displacement field and never its average magnitude. Without that, a gradient arm would simply
receive less total motion and any comparison against the rigid arm would be confounded.

### 10.1 Does the gradient break it?

{{table:motion2_false_retrograde}}

*False-retrograde rate on non-travelling windows: how often the device reports reflux while the
child is merely breathing. This, not accuracy, is the endpoint that decides viability &mdash; a
device that invents reflux during breathing is unusable however well it scores on real events.*

{{fig:figs_new/n3_gradient.png|False-retrograde rate and direction accuracy against displacement amplitude, at three gradient strengths.}}

### 10.2 What actually degrades the measurement

{{table:motion2_accuracy}}

{{fig:figs_new/n4_abstain.png|The gap between raw accuracy and accuracy on calls made is the abstain gate: under motion the estimator increasingly declines to answer rather than answering wrongly.}}

The failure mode matters as much as the failure rate. Raw accuracy counts an abstention as an
error, so it falls faster than the device's actual reliability: accuracy **on the calls it does
make** stays substantially higher, with the difference absorbed into a rising abstention rate. A
device that says "I do not know" during vigorous movement, and is asked to observe many voids
anyway, is in a far better position than one that answers confidently and wrongly.

For scale, quiet-breathing renal excursion is about 1 cm. Two to three centimetres corresponds to
deep breathing or crying.

> [!NOTE]
> **This study covers grades III&ndash;V.** The motion tolerance reported here is therefore an
> upper bound on what the full grade distribution would give. There is also a non-zero
> false-retrograde rate at **zero** motion, which motion cannot explain; it reflects the abstain
> gate's finite ability to separate a real travelling wave from noise, and it sets a floor on
> achievable specificity that is independent of how still the child is.

{{methods:motion2}}
