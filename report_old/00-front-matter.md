<!--TOC-->

> [!KEY]
> **What this is.** A finite-element simulation testing, before hardware exists, whether a surface bioimpedance device can detect vesicoureteral reflux by measuring the **direction** urine travels rather than reconstructing an image. **Six studies and a four-part numerical verification of the forward model** are reported: electrode count, locked-design characterization, strip placement, misplacement tolerance, placement precision across a simulated cohort, and non-rigid respiratory motion. Section 2 gives the shared forward model, the estimator, and the statistics, so that every study below can be read as a statement of what it changed rather than a self-contained method.
>
> **{{val:n_defects}} defects were found and fixed along the way, and six published headline claims were subsequently overturned by measurement** &mdash; most recently the locked design itself (&sect;9), the AUC metric (&sect;4.1), and the project's own stated existential risk (&sect;10), whose result is now withdrawn as confounded. That history is reported here alongside the results, because it bears directly on how much weight the numbers can carry.

> [!WARN]
> **Read this before quoting any number.** The design characterised in &sect;5 as "the locked design" is a 16 cm strip at mid-torso. Study 5 (&sect;9) has since shown that placement never detects 25&ndash;33% of refluxing children across six voids, and 43% of low-grade refluxers even when placed perfectly. That much is settled across two independent studies.
>
> **What replaces it is not yet settled.** A short 10 cm strip over the ureterovesical junction recovers the low grades &mdash; grade II detection rises from 55.4% to 83.9% when still &mdash; but it has a shorter axial lever arm, and re-characterising the whole design there cost accuracy on the grades that previously worked: at 0.6 cm of motion, grade IV fell from 98.2% to 46.4% and grade III from 78.6% to 60.7%. Placement is a genuine trade-off between low-grade coverage and motion robustness, not a strictly better choice &mdash; and the geometry forbids having both, since a 16 cm strip in a 20 cm torso cannot be centred below z = 0.40. Two better-balanced candidates are being characterised now. Until they land, **&sect;5 reports a placement known to be wrong for low grades, and no re-cut design has yet been validated to replace it.**
>
> These are per-grade detection rates, not AUC. AUC is deliberately avoided here: &sect;4.1 shows the AUC this report published was a trained classifier over all features, not the direction rule.
