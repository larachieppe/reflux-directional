## 7. Study 4: misplacement tolerance

The optimum is only useful if it survives imperfect placement by a parent, against a landmark
that is not externally visible. Reflux-only detection, still, offsetting the
{{val:tolerance_span}} cm strip along the body axis:

{{table:tolerance}}

{{fig:figs_place/p3_tolerance.png|Accuracy against misplacement, low grades versus high grades.}}

> [!WARN]
> **It does not survive &plusmn;2 cm.** Within &plusmn;1 cm, grades II-V hold at 94-100% and grade II detection is real, which is the prize: grade II+ is roughly 70% of refluxers against 40% for grade III+. At &plusmn;2 cm it collapses (grade II 100% &rarr; 31%) and abstention reaches 42%. **Grade I is not robust at any offset** and its apparent peak at &minus;2 cm is noise at n=16. The engineering consequence is that a 10 cm strip needs a landmark or an alignment aid, or a longer strip should be used to buy positional margin at the cost of peak low-grade accuracy.

{{methods:tolerance}}

> [!WARN]
> **"Holds within &plusmn;1 cm" is a +1 cm statement.** The tolerance table is not symmetric: at
> **&minus;1 cm** grade III drops to 81.2% and grade V to 50.0%, while at **+1 cm** grades II&ndash;V
> are still 94&ndash;100%. Quoting a symmetric tolerance averages a good direction with a bad one.
>
> At **&minus;2 cm** the grade ordering inverts outright: grade V scores 31.2%, the *worst* of all
> five grades, while grade I scores 87.5%. A larger bolus performing worse than a smaller one is
> not physical, and the likely cause is mechanical rather than physiological &mdash; at that offset
> the requested strip runs past the end of the mesh and `place_strips` silently falls back to a
> wider acceptance window, so the &minus;2 cm arm may not be the geometry it claims to be. Treat
> that row as unverified.

> [!NOTE]
> This study is centred on a placement that Study 3 has since superseded twice, and it reports
> **reflux-only** accuracy, which cannot distinguish a good detector from one that simply answers
> "reflux" more often (see &sect;6). Both are corrected in the re-run now in progress.
