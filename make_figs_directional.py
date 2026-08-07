"""
Figures for the directional (non-tomographic) simulation. Reads
metrics_directional.json and writes figs_dir/*.png. Light background to sit on
the site's white figure cards.
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

os.makedirs("figs_dir", exist_ok=True)
ACCENT = "#2b7fd4"; C1 = "#199e70"; C2 = "#c98500"; C3 = "#e66767"; MUT = "#8a8a8a"
INK = "#1c2b30"
plt.rcParams.update({"font.size": 11, "axes.titleweight": "bold",
                     "figure.dpi": 120, "axes.edgecolor": "#c9d4d6",
                     "text.color": INK, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK,
                     "axes.titlecolor": INK})

M = json.load(open("metrics_directional.json"))
cfg = M["config"]
COUNTS = cfg["counts"]; MOTION = cfg["motion"]; SPAN = cfg["span"]
prim = M["primary"]
MCOL = {m: c for m, c in zip(MOTION, [C1, ACCENT, C2, C3])}


def g(n, m, k):
    d = prim[str(n)][str(m)]
    if k == "dir_acc" and d.get("undecidable", 0) > 0.99:
        return float("nan")            # undefined, not 0%: no ordering exists
    return d.get(k, float("nan"))


def wilson(p, n, z=1.96):
    """Wilson 95% interval. Plotted so the reader can see whether the electrode
    counts actually separate, rather than inferring a knee from a noisy line."""
    if n <= 0 or p != p:
        return (float("nan"), float("nan"))
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def dn(n, m):
    return int(prim[str(n)][str(m)].get("dir_n", 0))


def _fin(ax):
    ax.grid(alpha=.25); ax.set_axisbelow(True)


# ---------------------------------------------------- A. count sweep (headline)
# TWO panels, because a single number here is misleading. dir_acc counts an
# ABSTENTION as a wrong answer, and the abstain gate requires >= 3 zones, so N=5
# (2 zones) is structurally exempt from it. Judging on dir_acc alone therefore
# rewards the one configuration that is forced to guess.
fig, axs = plt.subplots(1, 2, figsize=(12.6, 4.8), sharey=True)
for ax, key, ttl in (
        (axs[0], "dir_acc", "Abstention counted as an error"),
        (axs[1], "dir_acc_decided", "Accuracy on the calls actually made")):
    for m in MOTION:
        xs, ys, lo, hi = [], [], [], []
        for n in COUNTS:
            a = g(n, m, "dir_acc")
            v = prim[str(n)][str(m)].get(key, float("nan"))
            if a != a or v != v:
                continue
            nn = int(prim[str(n)][str(m)].get(
                "n_decided" if key == "dir_acc_decided" else "dir_n", 0))
            l, h = wilson(v, nn)
            xs.append(n); ys.append(100 * v)
            lo.append(max(0.0, 100 * (v - l))); hi.append(max(0.0, 100 * (h - v)))
        if xs:
            ax.errorbar(xs, ys, yerr=[lo, hi], fmt="o-", color=MCOL[m], lw=2.2,
                        ms=6, capsize=3, elinewidth=1.2,
                        label=f"motion {m:.1f} cm" + (" (still)" if m == 0 else ""))
    ax.axhline(50, ls=":", color=MUT)
    ax.axvspan(3.6, 4.4, color=C3, alpha=.09)
    ax.axvspan(4.6, 5.4, color=C2, alpha=.10)
    ax.set_xlabel("electrodes per strip (N)")
    ax.set_xticks(COUNTS); ax.set_ylim(35, 105); _fin(ax)
    ax.set_title(ttl, fontsize=11.5)
axs[0].set_ylabel("direction accuracy, grade >= III (%)")
axs[0].text(4, 88, "N=4\nundefined", ha="center", fontsize=8.5, color=C3)
axs[0].text(5, 40, "N=5: 2 zones,\nexempt from the\nabstain gate", ha="center",
            fontsize=8.5, color=C2)
axs[1].legend(fontsize=9, loc="lower right")
fig.suptitle(f"Direction accuracy vs electrode count (span {SPAN:.0f} cm, Wilson 95% CI)",
             fontsize=12.5, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig("figs_dir/figA_count.png", bbox_inches="tight")
plt.close(fig); print("[A] count sweep (both views)")

# ---------------------------------------------------- B. motion robustness
fig, ax = plt.subplots(figsize=(8.4, 4.6))
# Only plot counts that HAVE data. N=4 is undefined at every motion level (one
# zone, no ordering), so including it in the legend promises a curve that cannot
# exist and leaves the legend claiming more series than are drawn.
PLOT_N = [n for n in COUNTS if any(g(n, m, "dir_acc") == g(n, m, "dir_acc") for m in MOTION)]
cols = plt.cm.viridis(np.linspace(0.1, 0.85, len(PLOT_N)))
for n, c in zip(PLOT_N, cols):
    ax.plot(MOTION, [100 * g(n, m, "dir_acc") for m in MOTION], "o-",
            color=c, lw=2, ms=6, label=f"N={n}")
ax.plot([], [], " ", label="N=4: undefined")
ax.axhline(73, ls="--", color=C3, lw=1.6)
ax.axhline(44, ls="--", color=C3, lw=1.6)
ax.fill_between([min(MOTION), max(MOTION)], 44, 73, color=C3, alpha=.07)
ax.text(max(MOTION), 74.5, "Kite EIT, still (73%)", color=C3, fontsize=9, ha="right")
ax.text(max(MOTION), 39.5, "Kite EIT, with motion (44%)", color=C3, fontsize=9, ha="right")
ax.axhline(50, ls=":", color=MUT)
ax.set_xlabel("injected common-mode motion amplitude (cm)")
ax.set_ylabel("direction accuracy (%)")
ax.set_title("Motion robustness: the axis the tomographic approach failed on")
ax.set_ylim(30, 103); ax.legend(fontsize=9, ncol=2); _fin(ax)
fig.tight_layout(); fig.savefig("figs_dir/figB_motion.png", bbox_inches="tight")
plt.close(fig); print("[B] motion")

# ---------------------------------------------------- C. why the chosen N
worst = max(MOTION)
fig, ax = plt.subplots(figsize=(9.0, 4.8))
PLOT_N = [n for n in COUNTS if g(n, worst, "dir_acc") == g(n, worst, "dir_acc")]
ch = [2 * n for n in PLOT_N]
dirv = [100 * g(n, worst, "dir_acc") for n in PLOT_N]
latv = [100 * g(n, worst, "lat_acc") for n in PLOT_N]
ax.plot(ch, dirv, "o-", color=ACCENT, lw=2.4, ms=9, label="direction accuracy")
ax.plot(ch, latv, "s--", color=C1, lw=2.4, ms=8, label="laterality accuracy")
for n, x, y in zip(PLOT_N, ch, dirv):
    ax.annotate(f"N={n}", (x, y), textcoords="offset points", xytext=(0, -16),
                ha="center", fontsize=9.5, color=MUT)
# the recommendation: best laterality among counts not significantly worse on direction
best = max(dirv)
ok = [(n, x, d, l) for n, x, d, l in zip(PLOT_N, ch, dirv, latv)]
lo = min(wilson(best/100, dn(PLOT_N[int(np.argmax(dirv))], worst))[0]*100, best)
cand = [t for t in ok if wilson(t[2]/100, dn(t[0], worst))[1]*100 >= lo]
rec = max(cand, key=lambda t: t[3]) if cand else ok[0]
ax.axvline(rec[1], color=C2, ls="--", lw=2)
ax.annotate(f"chosen: N={rec[0]}\nbest laterality ({rec[3]:.0f}%) among counts\nnot significantly worse on direction",
            (rec[1], min(min(dirv), min(latv)) + 2), textcoords="offset points",
            xytext=(10, 0), fontsize=9.5, color=C2, va="bottom")
ax.set_xlabel("total channels (2 strips x N)   ->   complexity, cost, contact points")
ax.set_ylabel(f"accuracy (%) at {worst:.1f} cm motion")
ax.set_title("Why N was chosen: direction and laterality rank the counts differently")
ax.legend(fontsize=9.5, loc="upper center"); _fin(ax)
fig.tight_layout(); fig.savefig("figs_dir/figC_complexity.png", bbox_inches="tight")
plt.close(fig); print("[C] chosen-N rationale")

# ---------------------------------------------------- D. AUC + ablation
fig, axs = plt.subplots(1, 2, figsize=(11, 4.3))
for m in MOTION:
    axs[0].plot(COUNTS, [g(n, m, "auc") for n in COUNTS], "o-", color=MCOL[m],
                lw=2, ms=6, label=f"motion {m:.1f} cm")
axs[0].axhline(.5, ls=":", color=MUT); axs[0].set_xticks(COUNTS)
axs[0].set_xlabel("electrodes per strip (N)"); axs[0].set_ylabel("reflux AUC")
axs[0].set_title("Reflux vs rest (AUC)"); axs[0].legend(fontsize=8.5); _fin(axs[0])

nb = COUNTS[min(2, len(COUNTS) - 1)]
keys = [("auc", "all features"), ("auc_direction_only", "direction only"),
        ("auc_energy_only", "amplitude only")]
w = 0.26
for i, (k, lab) in enumerate(keys):
    axs[1].bar(np.arange(len(MOTION)) + (i - 1) * w,
               [g(nb, m, k) for m in MOTION], w,
               color=[ACCENT, C1, C3][i], label=lab)
axs[1].axhline(.5, ls=":", color=MUT)
axs[1].set_xticks(range(len(MOTION)))
axs[1].set_xticklabels([f"{m:.1f}" for m in MOTION])
axs[1].set_xlabel("motion amplitude (cm)"); axs[1].set_ylabel("reflux AUC")
axs[1].set_title(f"Feature ablation (N={nb}): direction carries it")
axs[1].legend(fontsize=8.5); axs[1].set_ylim(0.3, 1.02); _fin(axs[1])
fig.tight_layout(); fig.savefig("figs_dir/figD_auc_ablation.png", bbox_inches="tight")
plt.close(fig); print("[D] auc + ablation")

# ---------------------------------------------------- E. laterality + grade
fig, axs = plt.subplots(1, 2, figsize=(11, 4.3))
for m in MOTION:
    axs[0].plot(COUNTS, [100 * g(n, m, "lat_acc") for n in COUNTS], "o-",
                color=MCOL[m], lw=2, ms=6, label=f"motion {m:.1f} cm")
axs[0].axhline(50, ls=":", color=MUT); axs[0].set_xticks(COUNTS)
axs[0].set_xlabel("electrodes per strip (N)"); axs[0].set_ylabel("laterality accuracy (%)")
axs[0].set_title("Laterality (which flank refluxed)"); axs[0].legend(fontsize=8.5); _fin(axs[0])

gl = [1, 2, 3, 4, 5]
gs = M.get("grade_sweep", {})
if gs:
    ys = [100 * gs[str(k)]["0.0"]["dir_acc"] for k in gl if str(k) in gs]
    xs = [k for k in gl if str(k) in gs]
    axs[1].plot(xs, ys, "o-", color=ACCENT, lw=2.2, ms=8)
    axs[1].axhspan(35, 55, color=C3, alpha=.07)
    axs[1].text(1.05, 57, "chance band", color=C3, fontsize=9)
    axs[1].axvspan(2.5, 5.5, color=C1, alpha=.06)
    axs[1].text(4, 40, "device design point\n(grade >= III)", color=C1,
                fontsize=9, ha="center")
axs[1].axhline(50, ls=":", color=MUT)
axs[1].set_xticks(gl); axs[1].set_xlabel("reflux grade")
axs[1].set_ylabel("direction accuracy (%)")
axs[1].set_title("By grade (N=8, still): the low-grade tail is real")
axs[1].set_ylim(30, 103); _fin(axs[1])
fig.tight_layout(); fig.savefig("figs_dir/figE_lat_grade.png", bbox_inches="tight")
plt.close(fig); print("[E] laterality + grade")

# ---------------------------------------------------- F. SNR + span
fig, axs = plt.subplots(1, 2, figsize=(11, 4.3))
sn = sorted(int(k) for k in M["snr_sweep"])
axs[0].plot(sn, [100 * M["snr_sweep"][str(s)]["dir_acc"] for s in sn], "o-",
            color=ACCENT, lw=2.2, ms=8)
axs[0].axhline(50, ls=":", color=MUT)
axs[0].set_xlabel("instrument SNR (dB, re standing impedance)")
axs[0].set_ylabel("direction accuracy (%)")
axs[0].set_title("SNR requirement (N=8, 0.6 cm motion)"); _fin(axs[0])

sp = sorted(float(k) for k in M["span_sweep"])
axs[1].plot(sp, [100 * M["span_sweep"][str(s)]["dir_acc"] for s in sp], "o-",
            color=C1, lw=2.2, ms=8)
axs[1].axhline(50, ls=":", color=MUT)
axs[1].set_xlabel("strip span along the flank (cm)")
axs[1].set_ylabel("direction accuracy (%)")
axs[1].set_title("Span requirement (N=8, 0.6 cm motion)"); _fin(axs[1])
fig.tight_layout(); fig.savefig("figs_dir/figF_snr_span.png", bbox_inches="tight")
plt.close(fig); print("[F] snr + span")

print("figures ->", len(os.listdir("figs_dir")), "files in figs_dir/")
