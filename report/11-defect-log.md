## 11. Defect log

{{val:n_defects}} defects have been found and corrected: {{val:n_defects_code}} in the model, the
estimator or the statistics, {{val:n_defects_other}} in the physics or the tooling, and
{{val:n_defects_reporting}} in this report's own text, where a claim was stated more strongly than
the evidence supported. Six were caught by debugging when the detector sat at chance despite
correct forward physics, five by independent adversarial review of the code, and the rest by
successive audits. Several fixes introduced new defects, which is itself part of the record.

> [!WARN]
> **The most serious is #{{val:defno_mesh}}, and it invalidates every number produced before it.** The tetrahedral
> mesh was **non-conforming**: a 3-D Delaunay over a structured point cloud produced thousands of
> exactly-flat tetrahedra, and deleting them as "slivers" removed the only connectivity holding
> the two sides of each degenerate cell together. The result tiled the solid to a relative volume
> error of **0.0e+00** while 82% of its "boundary" faces were interior hanging faces. The finite
> element space was not H1-conforming, so no solve was a Galerkin solution and refinement never
> controlled the error &mdash; which is almost certainly why absolute impedance never converged, a
> symptom this report had already recorded and filed as an accepted limitation without finding its
> cause.
>
> It also meant **63% of every electrode was buried inside the tissue** (#{{val:defno_electrode}}), and separately the
> motion model **slid the subcutaneous fat out from under the electrodes** (#{{val:defno_fat}}), producing an
> artifact 16&ndash;320&times; larger than the real motion response. Motion is this project's
> primary endpoint.

{{table:defects}}

> [!NOTE]
> **The pattern.** Every one of these lived in code that had already passed a narrower test and been described as working. What caught them was looking at a fix from a different angle than the one that motivated it: forcing each aperture instead of trusting the selector, measuring a threshold distribution instead of choosing a plausible number, reading what the feature vector actually contained instead of trusting the function's return value. Simulation results here should be treated as hypotheses for a phantom to test, not as measurements.
