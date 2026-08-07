## 11. Defect log

{{val:n_defects}} defects were found and corrected: {{val:n_defects_code}} in the model, the
estimator or the statistics, and {{val:n_defects_reporting}} in this report's own text, where a
claim was stated more strongly than the evidence supported. Six were caught by debugging when the
detector sat at chance despite correct forward physics, five by independent adversarial review of
the code, and the rest by later audits. Several fixes introduced new defects, which is itself part
of the record.

{{table:defects}}

> [!NOTE]
> **The pattern.** Every one of these lived in code that had already passed a narrower test and been described as working. What caught them was looking at a fix from a different angle than the one that motivated it: forcing each aperture instead of trusting the selector, measuring a threshold distribution instead of choosing a plausible number, reading what the feature vector actually contained instead of trusting the function's return value. Simulation results here should be treated as hypotheses for a phantom to test, not as measurements.
