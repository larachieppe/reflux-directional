## 4. Verification of the forward model

Everything above rests on the forward solve being correct, and until now that had been
*asserted* rather than demonstrated. Four checks were run. They need no patient data and no
new physics, and they are the first thing a numerical analyst asks for.

### 4.1 Reciprocity

Maxwell reciprocity requires the transfer impedance to be unchanged when the drive pair and the
sense pair are exchanged. Exchanging them exercises different rows of the assembled system, so an
asymmetry in the assembly, the contact-impedance Robin term or the gauge condition shows up at
once.

> [!KEY]
> Maximum relative error **{{val:recip_err}}** over {{val:recip_pairs}} tetrapolar zones &mdash; machine precision.

That still makes it worth running. It would immediately catch a transposed or mis-signed
coupling block, a non-symmetric quadrature on the electrode mass matrix, an inconsistent
<code>1/z<sub>l</sub></code> between the two blocks, or a broken gauge row, and it confirms the
direct solve is numerically clean. But it is **necessary, not sufficient**: any error that
enters *symmetrically* &mdash; a wrong Robin coefficient applied consistently to both blocks,
a wrong electrode area, a mis-meshed geometry, a wrong tissue value &mdash; passes this test
untouched. 

### 4.2 Mesh convergence: the impedance does not converge, but the decision does

An identical, deterministic, **noiseless** trial solved on five meshes spanning an eightfold
range of node count.

{{table:mesh_convergence}}

> [!WARN]
> **Read this table carefully, because it says two opposite things.** The absolute transfer impedance **does not converge**: the error against the finest mesh oscillates between 11% and 76% with no monotone trend. But the arrival-time slope converges cleanly and monotonically &mdash; 6.80%, 2.84%, 0.97%, 0.11% &mdash; and the **decision is invariant across every mesh tested**.

The mechanism is electrode discretisation. |Z| scales with realised electrode area, and
electrodes snap to mesh facets, so their area changes discontinuously under refinement. The slope
is a *differential timing* quantity: it depends on when each zone peaks relative to the
others, which is insensitive to a common area scaling. This is why the estimator normalises to a
fractional change <code>dZ/|Z<sub>ref</sub>|</code> and reads timing rather than magnitude: the
quantity it depends on is the one that converges.

{{fig:figs_new/n1_mesh.png|Mesh convergence. The arrival-time slope converges monotonically by nearly two orders of magnitude; the absolute impedance plateaus near 11% and never converges. The decision is invariant across all five meshes.}}

> [!NOTE]
> **What this forbids.** No claim about an absolute impedance magnitude is supported by this model &mdash; including any figure quoted to size hardware. Only differential and timing claims survive. The headline result is a slope sign, so it is on the right side of that line, but the limitation is real and is not narrowed by running more trials.

### 4.3 Contact-impedance immunity is 4.3&times;, not "largely eliminated"

Sweeping contact impedance across the modelled range and comparing the tetrapolar transfer
impedance against a bipolar proxy on the *same electrodes and the same solves*:

{{table:contact_immunity}}

### 4.4 Quasi-statics: valid, but permittivity is not negligible

Two *independent* conditions must hold to reduce Maxwell to
<code>&nabla;&middot;(&kappa;&nabla;u) = 0</code>: the domain must be electrically small against
the **free-space** wavelength (here 6.7&times;10<sup>&minus;5</sup>), and the skin depth must
exceed the domain (here by 6&times; to 54&times;). Both hold comfortably at both frequencies.

But <code>&omega;&epsilon;/&sigma;</code> reaches **1.40 for kidney at 100 kHz** and 0.39 for
muscle, so displacement current *exceeds* conduction current in perfused tissue at the top of
the band. A real-valued conductivity model would be wrong here; carrying the full complex
admittivity is load-bearing, and the imaginary part carries genuine tissue information &mdash;
which is the physical argument for the second frequency being worth its cost, a claim this project
has still not tested.

> [!NOTE]
> **A trap worth naming**, because the first version of this check fell into it: testing the domain against the *in-medium* wavelength is not an independent condition. In a good conductor &lambda; = 2&pi;&delta;, so it merely restates the skin-depth test. And <code>&omega;&epsilon;/&sigma;</code> does not bear on quasi-static validity at all &mdash; it answers the separate question of whether permittivity may be dropped.

{{methods:verify}}
