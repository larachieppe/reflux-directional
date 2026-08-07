## 6. Study 3: where the strip sits

Low-grade reflux only traverses the lower ureter, so what matters is how many tetrapolar zone
centroids its bolus actually crosses. Reflux-only detection, still:

{{table:placement}}

> [!WARN]
> **Claims overturned #2 and #3.** Every previous version of this work stated that grades I-II are *intrinsically* undetectable, "the hard tail", "by construction". That was false. <code>z_center</code> was never forwarded to <code>place_strips</code>, so every strip in every study sat on the torso midpoint by default; nobody chose that position and nobody swept it. Moving the strip over the ureterovesical junction takes **grade II from 7% to 100%**. The same result overturns the earlier claim that *span is the dominant lever and longer is better*: a **shorter strip placed correctly beats a longer strip placed wrong**. Span was a proxy for coverage of the lower ureter.

{{fig:figs_place/p1_grade_placement.png|Detection by grade and placement. The published configuration is outlined in red.}}

{{fig:figs_place/p2_mechanism.png|The mechanism: a bolus crossing fewer than about three zone centroids cannot support a slope fit or common-mode rejection.}}

{{methods:placement}}

> [!WARN]
> **The accuracies in this table are reflux-only.** `reflux_acc` counts reflux trials and nothing
> else, so a detector that answers "reflux" every time scores 100% on it. That is not hypothetical
> here: the placement this rule originally selected, 10 cm @ z=0.28, scores 87.5% one-sided but
> **37.5% on antegrade trials** &mdash; below chance on healthy children &mdash; for a balanced
> accuracy of 62.5%, fifth of ten. On balanced accuracy the optimum is **12 cm @ z=0.36** (74.1%,
> with 78.6% on antegrade). The selector now scores both classes; the table above is retained as
> published and should be read alongside the balanced ranking.
