"""
Figures for the strip placement sweep (and tolerance arm, if present).
-> figs_place/*.png
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

os.makedirs("figs_place", exist_ok=True)
ACCENT = "#2b7fd4"; C1 = "#199e70"; C2 = "#c98500"; C3 = "#e66767"; MUT = "#8a8a8a"
INK = "#1c2b30"
plt.rcParams.update({"font.size": 11, "axes.titleweight": "bold", "figure.dpi": 120,
                     "axes.edgecolor": "#c9d4d6", "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
                     "axes.titlecolor": INK})

P = json.load(open("metrics_placement.json"))
G = P["grid"]
H = P["config"]["height"]
BEST = P["best_low_grade"]
SHIPPED = "16_0.50"


def _fin(ax):
    ax.grid(alpha=.25); ax.set_axisbelow(True)


# ---------------------------------------------- 1. grade x placement heat
keys = sorted(G, key=lambda k: -(G[k]["g1_m0.0"]["reflux_acc"]
                                 if G[k]["g1_m0.0"]["reflux_acc"] ==
                                 G[k]["g1_m0.0"]["reflux_acc"] else 0))
A = np.array([[100 * G[k][f"g{g}_m0.0"]["reflux_acc"] for g in (1, 2, 3, 4, 5)]
              for k in keys])
labels = [f"{G[k]['span']:.0f} cm @ z={G[k]['z_center']:.2f}" for k in keys]
fig, ax = plt.subplots(figsize=(8.2, 5.4))
im = ax.imshow(A, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
for i in range(A.shape[0]):
    for j in range(A.shape[1]):
        ax.text(j, i, f"{A[i,j]:.0f}", ha="center", va="center",
                fontsize=10.5, fontweight="bold", color=INK)
ax.set_xticks(range(5)); ax.set_xticklabels([f"grade {r}" for r in "I II III IV V".split()])
ax.set_yticks(range(len(keys)))
for i, k in enumerate(keys):
    if k == SHIPPED:
        ax.add_patch(plt.Rectangle((-.5, i-.5), 5, 1, fill=False, ec=C3, lw=3))
        labels[i] = labels[i] + "   <- published"
    if k == f"{BEST['span']:.0f}_{BEST['z_center']:.2f}":
        ax.add_patch(plt.Rectangle((-.5, i-.5), 5, 1, fill=False, ec=C1, lw=3))
        labels[i] = labels[i] + "   <- best"
ax.set_yticklabels(labels, fontsize=9.5)
ax.set_title("Reflux detection by grade and strip placement (still)\n"
             "low grades are a PLACEMENT problem, not a limit of the method")
fig.colorbar(im, ax=ax, label="reflux correctly detected (%)", pad=0.13)
fig.tight_layout(); fig.savefig("figs_place/p1_grade_placement.png", bbox_inches="tight")
plt.close(fig); print("[1] grade x placement")

# ---------------------------------------------- 2. mechanism: zones crossed
fig, ax = plt.subplots(figsize=(7.6, 4.8))
zc = [G[k]["g1_m0.0"]["zones_crossed"] for k in G]
ac = [100 * G[k]["g1_m0.0"]["reflux_acc"] for k in G]
sz = [G[k]["span"] for k in G]
cols = {10.0: C1, 12.0: ACCENT, 16.0: C2}
for s in sorted(set(sz)):
    xs = [z for z, q in zip(zc, sz) if q == s]
    ys = [a for a, q in zip(ac, sz) if q == s]
    ax.scatter(xs, ys, s=110, color=cols.get(s, MUT), label=f"{s:.0f} cm span",
               edgecolor="white", zorder=3)
ax.axvline(3, ls="--", color=C3, lw=1.8)
ax.text(3.15, 8, "3 zones: the minimum for\ncommon-mode rejection and\na slope fit",
        fontsize=9, color=C3)
ax.set_xlabel("zone centroids the grade-I bolus actually crosses")
ax.set_ylabel("grade-I reflux detected (%)")
ax.set_title("The mechanism: low grades fail when too few zones see them")
ax.legend(fontsize=9.5); _fin(ax)
fig.tight_layout(); fig.savefig("figs_place/p2_mechanism.png", bbox_inches="tight")
plt.close(fig); print("[2] mechanism")

# ---------------------------------------------- 3. tolerance (if available)
if os.path.exists("metrics_tolerance.json"):
    T = json.load(open("metrics_tolerance.json"))
    TG = T["grid"]
    offs = T["config"]["offsets_cm"]
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    lo = [100 * TG[f"{o:+.0f}"]["low_grade_still"]["dir_acc"] for o in offs]
    hi = [100 * TG[f"{o:+.0f}"]["high_grade_still"]["dir_acc"] for o in offs]
    ax.plot(offs, lo, "o-", color=C3, lw=2.6, ms=9, label="grades I-II")
    ax.plot(offs, hi, "s-", color=C1, lw=2.6, ms=8, label="grades III-V")
    ax.axhline(50, ls=":", color=MUT); ax.text(offs[0], 51.5, "chance", color=MUT, fontsize=9)
    ax.axvline(0, color=C2, ls="--", lw=1.6)
    ax.text(0.06, 12, "intended position", color=C2, fontsize=9, rotation=90)
    ax.set_xlabel("strip misplacement along the body axis (cm)")
    ax.set_ylabel("direction accuracy (%)")
    ax.set_title(f"Misplacement tolerance\n{T['config']['span']:.0f} cm strip at "
                 f"z={T['config']['z_center']:.2f}")
    ax.set_ylim(0, 105); ax.set_xticks(offs); ax.legend(fontsize=9.5); _fin(ax)
    fig.tight_layout(); fig.savefig("figs_place/p3_tolerance.png", bbox_inches="tight")
    plt.close(fig); print("[3] tolerance")
else:
    print("[3] tolerance: metrics_tolerance.json not present yet, skipped")

print("figures ->", len(os.listdir("figs_place")), "files in figs_place/")
