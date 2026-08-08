## 5. Study 1: how many electrodes

The flank length available on a child is capped by anatomy, so the design question is not how long
the strip can be but how densely to populate a fixed span. More electrodes buy more tetrapolar
zones and a longer axial lever arm for the slope fit; they also cost channels, contact points and
cost. The optimum is therefore interior, and finding it is the point of this study.

Direction accuracy is reported at grade &ge; III. Two accuracy columns are shown because a single
one is misleading. The raw figure counts an **abstention** as a wrong answer, but the abstain gate
needs at least three zones on the firing strip, so N = 5 (two zones per strip) can never decline to
answer at all. Judged on the raw column alone, the one configuration that *cannot* abstain looks
the most robust, when in fact it is the least able to recognise that it does not know.

{{table:electrode_count}}

{{fig:figs_dir/figA_count.png|Direction accuracy against electrode count with Wilson 95% intervals.}}

Two structural facts set the floor. **N = 4 gives one zone per strip**, and a single zone has no
ordering to read, so direction is not merely hard there but undefined. **N = 5 gives two zones**,
which admits a lag but cannot reject common mode: subtracting the across-zone mean of exactly two
series makes them exact negatives, destroying the very signal the step is meant to clean. Three
zones is the true minimum for a design that can both reject common mode and fit a slope.

Above that floor, accuracy is governed by the axial **lever arm** of the zone centroids rather than
by electrode density as such. Slope precision improves with the spread of the regressor, so the
gain from N = 8 to N = 12 is modest and comes with 50% more channels.

### 5.1 How performance is measured

Two different numbers are reported and they answer different questions.

The **direction-rule AUC** is the ranking performance of the decision the device would actually
emit, scored as signed evidence, with no model fitted. This is the honest measure of the method.

The **classifier AUC** trains an elastic-net logistic regression over the full 15-feature vector
with five-fold cross-validation. It measures what a learned classifier could extract from the same
recordings, which is a useful upper bound but is *not* the sign-of-slope rule. The two ablation
columns separate its sources: direction features alone against amplitude features alone.

{{table:auc_corrected}}

> [!NOTE]
> **Read the chance floor carefully.** Reflux is scored against an equal mix of noflow, antegrade
> and bladder, and two of those three contain no travelling bolus at all. A detector that senses
> only "is a conductive bolus present", with no directional skill whatever, therefore separates
> reflux from noflow and from bladder almost perfectly and sits at chance only against antegrade:
> (1 + 1 + 0.5)/3 = **0.833**. Everything between 0.5 and 0.833 is dead scale. The relevant
> comparison for any AUC in that table is against 0.833, not 0.5.
>
> Each cell rests on 64 four-class trials, roughly 16 reflux against 48 rest, which by
> Hanley-McNeil gives a 95% interval of &plusmn;0.10 to &plusmn;0.16 &mdash; wider than the spread
> across electrode counts. **No electrode count is distinguishable from another on AUC**, and the
> choice rests on the direction accuracy and the structural argument above.

> [!NOTE]
> **Laterality is an amplitude statistic.** It scores which flank carries more signal energy, and
> it is credited whether or not a direction was reported. It should be read as "the signal is
> stronger on the correct side", not as an output the device emits on every trial.

{{methods:electrode-count}}
