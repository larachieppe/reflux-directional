<!--TOC-->

> [!KEY]
> **What this is.** A finite-element study, done before hardware exists, of whether a surface bioimpedance device can detect pediatric vesicoureteral reflux by measuring the **direction** urine travels rather than by reconstructing an image.
>
> Two longitudinal electrode strips sit on the flanks, one per side. Each strip is read as a set of overlapping tetrapolar zones. A refluxing bolus of urine perturbs those zones in sequence as it climbs the ureter, and the **sign of the arrival-time-versus-height slope** is the diagnosis: later at higher zones means upward transport, which is reflux. One strip per flank gives laterality without any additional hardware.
>
> Six studies establish the design: how many electrodes, where the strips sit, how precisely they must be placed, how much misplacement and how much motion the method survives. A four-part numerical verification establishes that the forward solver is doing what it claims. &sect;3 derives the physics; &sect;2 states the shared model once so each study need only report what it changed.

> [!NOTE]
> **What this is not.** No phantom, animal or patient measurement stands behind any number here. The geometry is an idealised cylinder rather than segmented anatomy, the tissue properties are literature values, and the instrument noise budget is assumed rather than taken from a datasheet. These results bound whether the physics can work and how it degrades. They are a feasibility and robustness envelope, not clinical performance, and &sect;11 sets out exactly which claims they can and cannot support.
