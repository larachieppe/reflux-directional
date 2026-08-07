## 4. Study 1: how many electrodes

Direction accuracy at grade &ge; III. Two accuracy columns are shown at 0.6 cm because a
single one is misleading: the raw figure counts an **abstention** as a wrong answer, while the
abstain gate requires at least three zones, so N=5 (two zones) is **structurally exempt** from
it. Judged on the raw column alone, the only configuration that cannot decline to answer looks the
most robust.

{{table:electrode_count}}

> [!WARN]
> **Claim overturned #4.** An earlier version of this report showed N=5 outperforming N=8 under motion (79% against 71% at 0.6 cm). That was an artifact of the metric, not a property of the design. On the calls actually made, **N=8 leads 93% to 79%**, and it declines to answer on 24% of cases rather than guessing. N=5 also cannot perform common-mode rejection at all, because mean removal across exactly two zones makes them exact negatives. N=5 has neither the gate nor the rejection: it is the configuration that *cannot fail to answer*, which reads as robustness and is the opposite.

> [!WARN]
> **Claim overturned #1.** An earlier version of this report stated that *more electrodes made accuracy worse*. That was an artifact of a greedy aperture-selection rule, not physics. Forcing each aperture on identical data showed the selector losing at every N &ge; 8. Replacing selection with fusion across apertures reversed the result: N=8/10/12 now reach 100% when still, where they previously read 76-93%. Slope precision scales with the axial *lever arm* of the zone centroids, not with electrode separation.

{{fig:figs_dir/figA_count.png|Direction accuracy against electrode count with Wilson 95% intervals.}}

### 4.1 The AUC column was measuring the wrong thing

> [!WARN]
> **Claim overturned #6.** Every AUC this report has published came from `_fit_auc`, which trains an elastic-net logistic regression over the **entire feature vector** with 5-fold cross-validation. It describes a learned classifier, not the sign-of-slope rule the whole design is premised on. So "the design achieves AUC 0.96" was never a statement about the direction method.

The proof is N = 4. That configuration has one zone per strip, cannot fit a slope, and **abstains
on 100% of trials with `dir_acc` undefined** &mdash; yet it posted AUC 0.852. That figure is
identical to three decimals to its own energy-only ablation at *every* motion level (0.852, 0.720,
0.449, 0.260). At N = 4 the classifier is running purely on amplitude.

That is precisely the failure mode this project exists to avoid. Scoring the *presence* of
conductive fluid rather than its *direction* is what leaves a device unable to separate reflux from
ordinary bladder filling, and it is the mechanism behind the prior program's collapse from 73% to
44% under motion.

The last column below is the honest metric: the ranking performance of the direction decision
itself, scored as signed evidence with **no model fitted at all**. It puts N = 4 at exactly 0.500.

{{table:auc_corrected}}

> [!NOTE]
> **And none of the AUC differences were ever significant.** Each cell rests on 64 four-class
> trials, roughly 16 reflux against 48 rest. By Hanley-McNeil that is a 95% interval of &plusmn;0.10
> to &plusmn;0.16, shown above and never previously reported. The entire spread across electrode
> counts, 0.852 to 0.979, **fits inside a single cell's confidence interval**. No electrode count
> was ever distinguishable from another on AUC.
>
> The same small-sample weakness explains N = 4 at motion 0.9 reading **0.260** &mdash;
> significantly *below* chance even at this precision. An out-of-fold AUC that low is not
> uninformative noise, it is a model that inverts out of sample.

Read on the direction rule instead, the ordering is what the rest of the study already said:
N &ge; 8 sits near 0.90 when still and degrades gracefully, N = 4 is chance by construction, and
N = 5 scores well only because it can never abstain.

{{methods:electrode-count}}
