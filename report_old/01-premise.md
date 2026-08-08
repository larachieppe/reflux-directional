## 1. Premise

The reference test, VCUG, requires catheterization, radiation, and voiding on command. It also
misses roughly 20% of reflux (intermittent, and only one or two voids are captured), radiologists
agree on grade in 59% of cases, and only about 48% of families complete the imaging. That
compliance gap, not accuracy, is the clinical opening.

A prior program (Kite Medical, ~$3.1M, wound up 2023) used 32-electrode tomography and reported
**73% detection without motion, 44% with motion**. Two structural reasons: the measured quantity
(presence of conductive fluid) is shared with the dominant confounder, ordinary bladder filling;
and image reconstruction has no intrinsic rejection of body motion.

Reflux is defined by **retrograde transport**, so direction separates it from bladder filling
by construction, and a differential measurement between nearby zones rejects perturbations common
to both, which is what motion is. A single symmetric tetrapolar array is direction-blind by
symmetry, so the geometry is a longitudinal strip, one per flank, which also gives laterality.

{{fig:figs_dir/figG_mechanism.png|The mechanism. Reflux: the impedance dip climbs the strip and arrival time rises with height. Antegrade: the mirror image. The SIGN of that slope is the diagnosis.}}
