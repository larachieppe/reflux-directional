# 0. Simulation Summary

## 0.1 Approach

The simulation does **not** reconstruct a conductivity image. It measures the **direction** a conductive urine bolus travels along the ureter, recovered from the ordering of arrival times across tetrapolar zones on two short flank strips (one per flank, which gives laterality natively).

This is a deliberate departure from the tomographic approach. A prior clinical program (Kite Medical, ~$3.1M, wound up January 2023) reconstructed conductivity change from a 32-electrode belt and reported detection in **73% of cycles without motion but 44% with motion**. Two structural properties explain that gap:

- The measured quantity, presence and magnitude of conductive fluid, is **shared with the dominant confounder**, ordinary bladder filling.
- Image reconstruction has **no intrinsic rejection of body motion**.

Reflux is defined by retrograde transport, so direction, not amplitude, is the discriminating variable, and a differential measurement between zones rejects perturbations common to those zones. A single symmetric tetrapolar array is direction-blind by symmetry, which is why the geometry is a longitudinal strip rather than a ring.

**Model:** verified 3-D complete-electrode forward model (finite elements, scikit-fem) on a torso segment whose axis is the body superior-inferior direction, with bilateral ureters, bladder and kidneys. Four conditions are simulated: reflux, normal antegrade transport, bladder filling (the confounder), and no flow. Motion is injected as a common-mode displacement of the body relative to the electrodes, plus breathing and an independent per-electrode contact term, so the common-mode rejection claim is tested rather than assumed.

**Live results:** https://larachieppe.github.io/reflux-directional/

## 0.2 Design decisions

Every value below is set by a measurement in the simulation, not by intuition.

| Parameter | Specify | Evidence |
| :---: | :---: | :---: |
| Electrodes per strip | **6 (12 channels total)** | Direction favours 5, laterality favours 6 (88% vs 62% at 0.6 cm motion). 6 is also the smallest count giving 3+ zones. Beyond 8, direction accuracy degrades. |
| Strip span | **14 cm** | 59% (8 cm) rising to 88% (14 cm), then flat. The strongest single lever measured, worth more than any electrode-count choice. |
| Zones per strip | **at least 3** | Common-mode rejection subtracts the across-zone mean. With exactly 2 zones the mean-removed pair are exact negatives and the lag is destroyed. |
| Outer aperture | **at least 6 cm** | Tetrapolar sensing depth is roughly half the aperture; the ureter sits ~3 cm below the skin. |
| Measurement | **fractional dZ/\|Z\|** | Absolute dZ carries per-channel gain. Unequal gains made strip selection degenerate. |
| Instrument SNR | **50 dB is sufficient** | Accuracy flat from 50 to 80 dB. The design is motion-limited, not noise-limited. |
| Motion tolerance | **0.5 cm or less** | The binding constraint. See 0.3. |
| Events per session | **at least 6, decide on 3-of-6** | See 0.5. |
| Claimed grade range | **grade III and above** | Grades I to II are not detectable by this method. See 0.4. |
| Excitation frequency | **not resolved** | A single frequency (50 kHz) was used; multi-frequency is untested. |

## 0.3 Results at the chosen design

6 electrodes per strip, 14 cm span, 12 channels, 60 dB, 3,236 trials.

| Motion | Direction accuracy | 95% CI | Laterality | Reflux AUC |
| :---: | :---: | :---: | :---: | :---: |
| 0.00 cm (still) | **98%** | 93-99% | 100% | 0.92 |
| 0.15 cm | 97% | 92-99% | 100% | 0.90 |
| 0.30 cm | 97% | 92-99% | 100% | 0.89 |
| **0.45 cm (target)** | **90%** | 83-95% | 100% | **0.89** |
| 0.60 cm | 85% | 76-90% | 96% | 0.89 |
| 0.75 cm | 76% | 67-83% | 89% | 0.82 |
| 0.90 cm | 71% | 62-79% | 83% | 0.84 |

Motion is the dominant limiter and sets the engineering constraint: keep effective motion at or below **0.5 cm**, which favours a quiet or sleep context over motion compensation.

Feature ablation at 0.45 cm: all features AUC 0.89, direction features only 0.85, amplitude only 0.82. Direction outperforms amplitude, though amplitude alone is not useless.

## 0.4 Sensitivity by reflux grade

| Grade | Still | 0.60 cm motion |
| :---: | :---: | :---: |
| I | 52% | 55% |
| II | 50% | 54% |
| III | **93%** | 70% |
| IV | **100%** | 84% |
| V | **100%** | 89% |

Grades I and II sit at chance: low-grade reflux does not travel far enough to cross the sensed span, so it is undetectable by this method by construction rather than by tuning. **Any claim must be scoped to grade III and above**, which is also where the clinical consequence is concentrated.

## 0.5 How the device can exceed VCUG

Not by raising per-event accuracy. VCUG's exploitable weakness is that it captures **one or two forced voids** and therefore misses roughly **20% of reflux**, which is intermittent. A passive wearable observes many natural cycles, and detection compounds.

Simulated as **110 children with 6 events each, holding anatomy and electrode placement fixed per child**, so correlated failure would show up rather than being assumed away. Per event the detector runs 88% sensitivity at a 9% false-positive rate.

| Screening rule | Sensitivity | Specificity | Sensitivity if the detector were a coin flip |
| :---: | :---: | :---: | :---: |
| at least 1 of 6 | 100% | 58% | 98% |
| at least 2 of 6 | 98% | 87% | 89% |
| **at least 3 of 6** | **96%** | **98%** | 66% |
| at least 4 of 6 | 91% | 100% | 34% |
| at least 5 of 6 | 80% | 100% | 11% |

**A 3-of-6 rule gives 96% sensitivity at 98% specificity**, against nuclear VCUG's 81% sensitivity at 89% specificity, exceeding it on both axes. The coin-flip column is included because a naive pooled metric would have a chance floor above the VCUG line, and the comparison must be like for like.

**0% of refluxing children were never detected** across 6 events, so correlated failure is small in this model. That is the most model-dependent result here: real anatomical variation and real placement error are almost certainly larger than simulated, and a phantom study followed by a clinical pilot must measure that fraction directly before the multi-event argument can be relied on commercially.

## 0.6 Design implications for the benchtop build

| Simulation finding | Implication for the build |
| :---: | :---: |
| More electrodes made direction accuracy **worse**, not better | Over a fixed span, extra electrodes shrink the pitch and add aperture choices for the selector to get wrong. Build 6 per strip, not 16 or 32. |
| Direction and laterality disagree on the optimum | Direction favours 5, laterality favours 6. Specify 6, accepting a small direction cost to meet the laterality requirement. |
| Span matters more than electrode count | Prioritize a longer strip (14 cm) over a denser one, within what pediatric anatomy allows. Measure the usable flank length early. |
| Flat across 50 to 80 dB SNR | Motion-limited, not noise-limited. Do not pay for a quieter front end; a modest integrated AFE is sufficient. |
| Motion tolerance is 0.5 cm | The binding constraint. Test at multiple motion amplitudes, and consider a quiet or sleep protocol before investing in motion compensation. |
| Grades I to II undetectable | Keep the pre-specified endpoint on grade III and above. |
| Amplitude alone reaches AUC 0.82 | Direction is better but amplitude is not useless; report both so the ablation is honest. |

## 0.7 Limitations

| Limitation | Consequence |
| :---: | :---: |
| No physical data | No phantom, animal or clinical measurement stands behind any number here. This is a feasibility envelope, **not clinical performance**. |
| Structured anatomy | A cylinder with organs, not segmented CT. Real anatomical variation is almost certainly larger. |
| Single frequency | 50 kHz only. Multi-frequency discrimination is untested. |
| Motion model is structured | Common-mode displacement plus breathing plus an independent contact term. Real awake-child motion may be worse. |
| Aperture selection is greedy | The estimator picks one aperture by signal strength. A better rule may change the electrode-count conclusion. |
| Kite comparison is not like-for-like | The 73%/44% figures are a different measurement on different subjects, shown for context only. |
