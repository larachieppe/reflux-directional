## 9. Study 5: placement precision across a cohort

Study 4 asked how much misplacement the method survives on average. This asks the question that
actually decides the product: across a population where **every** child is imperfectly measured,
what fraction is detected, and what fraction is *systematically unmeasurable* &mdash; failing on
every void, so that no amount of repeat observation helps?

Each simulated child receives **one placement error, drawn once and shared across all of that
child's voids**, because a strip is applied once and not re-applied per void. That is what makes
failure correlated within a child, which is the entire question. Had the error been redrawn per
event, repeated voids would average it away and the study would report a reassuring and meaningless
number. Anatomy is likewise drawn once per child. Both placement arms are clipped to the same
offset limit, so they face an identical error distribution.

{{table:precision}}

{{fig:figs_new/n2_precision.png|Placement precision. The endpoint that matters is the right-hand panel: low-grade refluxers never detected on any of six voids.}}

The mechanism is the one Study 3 measured directly, arriving here by a different route. A strip
whose zones do not span the segment a low-grade bolus actually travels will miss that child on
every void, and repeat observation only compounds detection when failures are **independent**.
Placement failure is precisely the kind that is not: it is a fixed property of how the device was
applied to that child.

> [!NOTE]
> **Read the gap, not the individual cells.** With 24 refluxing children per cell (14 of them at
> grades I&ndash;II) the per-cell binomial noise is large, and neither arm's curve should be read
> as monotone in &sigma;. What the study supports is the persistent separation between the two
> placements across every error level, not the shape of either curve. The value of *k* in the
> screening rule is also chosen on these same children, so a pre-specified *k* is reported beside
> it for a comparison on a fixed rule.

{{methods:precision}}
