# Directional bioimpedance reflux sensing

A pre-hardware simulation of a **non-tomographic** approach to detecting pediatric
vesicoureteral reflux (VUR). It does not reconstruct a conductivity image. It
measures the **direction** a conductive urine bolus travels along the ureter, from
the ordering of arrival times across tetrapolar zones on two short flank strips.
Two strips, one per flank, give laterality natively.

**Live results:** https://larachieppe.github.io/reflux-directional/

## Why direction instead of an image

A prior clinical program (Kite Medical, ~$3.1M, wound up 2023) reconstructed
conductivity change from a 32-electrode belt and reported detection in **73% of
cycles without motion but 44% with motion**. Two structural properties explain
that gap:

1. The measured quantity (presence and magnitude of conductive fluid) is **shared
   with the dominant confounder**, ordinary bladder filling.
2. Image reconstruction has **no intrinsic rejection of body motion**.

Reflux is defined by retrograde transport, so direction is the discriminating
variable, and a differential measurement between zones rejects perturbations
common to those zones. A single symmetric tetrapolar array is direction-blind by
symmetry, which is why the geometry is a longitudinal strip rather than a ring.

## Findings

96 trials per cell, grade >= III, Wilson 95% confidence intervals.

- **Direction accuracy decreases with electrode count**: 80% (N=5) down to 62-64%
  (N=8 to 12) at 0.6 cm motion. Over a fixed span, more electrodes shrink the
  pitch and add aperture choices for the selector to get wrong.
- **Laterality ranks the counts differently** and favours N=6 (88% vs 62% for N=5
  at 0.6 cm). The recommendation of **N=6 (12 channels)** trades a little
  direction accuracy to meet the laterality requirement. Both answers are
  reported because they disagree.
- **Strip span dominates**: 59% (8 cm) to 88% (14-16 cm), worth more than any
  electrode-count choice.
- **Motion-limited, not noise-limited**: accuracy is flat from 50 to 80 dB SNR.
- **Grades 1-2 are undetectable** (29-50%); grades 3-5 run 81-90%. Low-grade
  reflux does not travel far enough to cross the sensed span.
- Direction features beat amplitude (AUC 0.87-0.90 vs 0.75-0.81), though
  amplitude alone is not useless.

## Caveats

Representative (not cohort-fit) tissue admittivities, a structured (not
segmented-CT) anatomy, and an assumed noise budget. A **single excitation
frequency** was used for this sweep, so the multi-frequency question is untested
here. The forward physics uses a complete-electrode FEM model, but nothing is
validated against real data: there is no phantom, animal or clinical dataset
behind these numbers. This establishes a **feasibility and robustness envelope,
not clinical performance**. The 73%/44% comparison is a different measurement on
different subjects and is shown for context, not as a like-for-like benchmark.

One open question behind the recommendation: the "fewer electrodes is better"
result may be an artifact of the greedy aperture-selection rule rather than
physics. A fixed-aperture or combine-across-apertures rule should be tested.

## Files

- `eit3d.py`: 3-D complete-electrode forward solver (mesh, CEM assembly), reciprocity-verified.
- `strip3d.py`: flank-strip geometry and symmetric (Schlumberger) tetrapolar zones.
- `directional_sim.py`: the model, common-mode motion injection, and the cross-correlation direction estimator.
- `run_directional.py`: electrode-count sweep -> `metrics_directional.json`.
- `make_figs_directional.py`, `make_figs_mechanism.py`: figures -> `figs_dir/`.
- `build_site.py`: builds the self-contained `index.html` from `site.css` + figures.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run_directional.py          # sweep -> metrics_directional.json (~80 min)
python make_figs_directional.py
python make_figs_mechanism.py
python build_site.py               # -> index.html
```
