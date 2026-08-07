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

{{methods:electrode-count}}
