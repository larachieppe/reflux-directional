## 13. Open risks

- **Placement precision is the binding constraint**, and Study 5 has now confirmed it twice
over. &plusmn;1 cm on a landmark that is not externally visible, on a child who will not hold
still. It decides whether low-grade detection is real in practice, and it has just invalidated the
published locked design.
- **No physical data.** No phantom, animal or clinical measurement stands behind any number
here. This is a feasibility envelope, not clinical performance.
- **Motion above about 1 cm.** Non-rigid motion turned out *not* to be the threat
(&sect;10), but displacement amplitude is: beyond 2 cm the device spends a third of its time
abstaining. The residual question is how often a real child exceeds that during a void.
- **An unexplained {{val:m2_fr_zero_motion}} false-retrograde floor
at zero motion**, which caps achievable specificity and has no identified cause.
- **Absolute impedance magnitudes are not mesh-converged** (&sect;8.2). Any hardware sizing
taken from this model inherits that, and more trials will not fix it &mdash; only a finer mesh or a
convergence-corrected estimate will.
- **Contact impedance is rejected only 4.3&times;**, not eliminated, leaving 16% residual
sensitivity to budget for.
- **Single excitation frequency in the estimator.** Two are solved but frequency is never used
discriminatively &mdash; and &sect;8.4 shows the imaginary part carries real information, so this is
a missed lever rather than a neutral omission.
- **Bilateral reflux is structurally unreportable**: the estimator selects one strip, so it
cannot express "both sides", which is a stated clinical requirement.
- **Structured anatomy**, not segmented CT; real variation is larger.
- **Freedom to operate.** The prior-art patent's independent claims are disjunctive over
bioimpedance *or* tomography, so "we do not reconstruct an image" defeats only two of twelve
claims. The position rests entirely on never estimating a volume nor comparing one to a control
value &mdash; and the resting-reference baseline currently used reads onto the broadest claim's
language. That is an engineering constraint, not just a legal one.

> [!KEY]
> **Recommended next step.** A layered phantom with a tube analogue, measuring depth against aperture and the fraction of placements that fail. Those are the two quantities that decide the product and neither can be settled by more simulation.
