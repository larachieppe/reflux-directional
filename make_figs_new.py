"""
Figures for the verification checks and for Studies 5 and 6.
-> figs_new/*.png

Each figure is built to make ONE point that the tables state but do not show:
  n1  the impedance does not converge but the decision does
  n2  the published 16 cm placement systematically loses low grades
  n3  the gradient hypothesis is refuted
  n4  motion degrades into abstention, not into confident error
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

os.makedirs("figs_new", exist_ok=True)
ACCENT = "#2b7fd4"; C1 = "#199e70"; C2 = "#c98500"; C3 = "#e66767"; MUT = "#8a8a8a"
INK = "#1c2b30"
plt.rcParams.update({"font.size": 11, "axes.titleweight": "bold", "figure.dpi": 120,
                     "axes.edgecolor": "#c9d4d6", "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
                     "axes.titlecolor": INK})

V = json.load(open("metrics_verify.json"))
P = json.load(open("metrics_precision.json"))
M = json.load(open("metrics_motion2.json"))


def _fin(ax):
    ax.grid(alpha=.25); ax.set_axisbelow(True)


# ------------------------------------------------ n1 mesh convergence
L_all = V["v3_mesh_convergence"]["levels"]
# The finest mesh is the REFERENCE, so its error is zero by construction. Plotting
# it would make |Z| appear to converge at the last point when it does no such
# thing. Compare only the coarser levels against it.
L, L_ref = L_all[:-1], L_all[-1]
n = [x["n_nodes"] for x in L]
ez = [100 * x["absZ_rel_to_finest"] for x in L]
es = [100 * x["slope_rel_to_finest"] for x in L]
fig, ax = plt.subplots(figsize=(8.0, 4.9))
ax.plot(n, ez, "o-", color=C3, lw=2.6, ms=9, label="absolute |Z|  (does not converge)")
ax.plot(n, es, "s-", color=C1, lw=2.6, ms=8, label="arrival-time slope  (converges)")
ax.set_yscale("symlog", linthresh=0.1)
ax.set_xlabel(f"mesh nodes   (error measured against the finest mesh, "
              f"{L_ref['n_nodes']:,} nodes, which is therefore not plotted)")
ax.set_ylabel("relative error vs finest mesh (%)")
ax.set_title("Mesh convergence: the impedance does not converge, the decision does\n"
             "all five meshes return the same diagnosis across an 8x range of node count")
for x, y in zip(n, es):
    ax.annotate(f"{y:.2f}%", (x, y), textcoords="offset points", xytext=(0, -16),
                ha="center", fontsize=8.5, color=C1)
ax.axhline(1.0, ls=":", color=MUT)
ax.text(n[0], 1.15, "1% error", color=MUT, fontsize=9)
ax.legend(fontsize=9.5, loc="upper right"); _fin(ax)
fig.tight_layout(); fig.savefig("figs_new/n1_mesh.png", bbox_inches="tight")
plt.close(fig); print("[n1] mesh convergence")

# ------------------------------------------------ n2 placement precision
G = P["grid"]
sig = P["config"]["sigmas"]
short = [G[f"10_{s:.1f}"] for s in sig]
long_ = [G[f"16_{s:.1f}"] for s in sig]
fig, axs = plt.subplots(1, 2, figsize=(11.4, 4.9))
for ax, key, ttl in ((axs[0], "never_detected", "Refluxing children never detected\non ANY of six voids"),
                     (axs[1], "low_grade_never", "Grade I-II refluxers\nnever detected")):
    ax.plot(sig, [100 * r[key] for r in short], "o-", color=C1, lw=2.8, ms=10,
            label="10 cm over the UVJ")
    ax.plot(sig, [100 * r[key] for r in long_], "s-", color=C3, lw=2.8, ms=9,
            label="16 cm mid-torso  (published)")
    ax.set_xlabel("placement error  $\\sigma$  (cm)")
    ax.set_ylabel("% of refluxing children")
    ax.set_title(ttl); ax.set_ylim(-3, 78); ax.set_xticks(sig)
    ax.legend(fontsize=9.5, loc="upper right"); _fin(ax)
axs[1].annotate("43% missed even at\nPERFECT placement",
                xy=(0.03, 43), xytext=(0.62, 30), fontsize=9.5, color=C3,
                ha="left", arrowprops=dict(arrowstyle="->", color=C3, lw=1.6))
# The 16 cm arm is non-monotonic in sigma, which is not physically sensible. Say
# so on the figure rather than letting a reader take the dip at face value: with
# 48 children per cell the per-cell noise is large, and the finding is the GAP
# between the two placements, not the shape of either curve.
for ax in axs:
    ax.text(0.5, -0.30, "16 cm arm is non-monotonic in $\\sigma$. Denominators are 24 refluxing children\n"
            "(left) and 14 with grades I-II (right), not the 48 per cell: per-cell noise is\n"
            "large. The finding is the persistent GAP between placements, not either curve's shape.",
            transform=ax.transAxes, ha="center", va="top", fontsize=8.2, color=MUT)
fig.suptitle("Study 5: the published placement systematically loses low-grade reflux",
             fontweight="bold", y=1.02)
fig.tight_layout(); fig.savefig("figs_new/n2_precision.png", bbox_inches="tight")
plt.close(fig); print("[n2] precision")

# ------------------------------------------------ n3 gradient refuted
GM = M["grid"]; C = M["config"]
fig, axs = plt.subplots(1, 2, figsize=(11.4, 4.7))
cols = {0.0: MUT, 0.5: ACCENT, 1.0: C3}
for g in C["grads"]:
    lab = {0.0: "rigid (grad 0)", 0.5: "half gradient", 1.0: "full gradient"}[g]
    axs[0].plot(C["amps"], [100 * GM[f"a{a}_g{g}"]["false_retrograde"] for a in C["amps"]],
                "o-", color=cols[g], lw=2.5, ms=8, label=lab)
    axs[1].plot(C["amps"], [100 * GM[f"a{a}_g{g}"]["dir_acc"] for a in C["amps"]],
                "o-", color=cols[g], lw=2.5, ms=8, label=lab)
axs[0].set_ylabel("false-retrograde rate (%)")
axs[0].set_title("Device inventing reflux while\nthe child merely breathes")
axs[0].set_ylim(0, 30)
axs[1].set_ylabel("direction accuracy (%)")
axs[1].set_title("Direction accuracy on real events")
axs[1].axhline(50, ls=":", color=MUT); axs[1].text(0.05, 52, "chance", color=MUT, fontsize=9)
axs[1].set_ylim(0, 105)
for ax in axs:
    ax.set_xlabel("displacement amplitude (cm)"); ax.set_xticks(C["amps"])
    ax.legend(fontsize=9); _fin(ax)
fig.suptitle("Study 6: the gradient hypothesis is refuted -- the curves lie on top of each other",
             fontweight="bold", y=1.02)
fig.tight_layout(); fig.savefig("figs_new/n3_gradient.png", bbox_inches="tight")
plt.close(fig); print("[n3] gradient refuted")

# ------------------------------------------------ n4 safe failure mode
fig, ax = plt.subplots(figsize=(8.4, 5.0))
amps = C["amps"]
raw = [100 * np.mean([GM[f"a{a}_g{g}"]["dir_acc"] for g in C["grads"]]) for a in amps]
dec = [100 * np.mean([GM[f"a{a}_g{g}"]["dir_acc_decided"] for g in C["grads"]]) for a in amps]
abst = [100 * np.mean([GM[f"a{a}_g{g}"]["trav_abstain"] for g in C["grads"]]) for a in amps]
ax.plot(amps, raw, "o-", color=C3, lw=2.8, ms=10, label="raw accuracy (abstention = error)")
ax.plot(amps, dec, "s-", color=C1, lw=2.8, ms=9, label="accuracy on the calls actually made")
ax.bar(amps, abst, width=0.16, color=ACCENT, alpha=.35, label="abstention rate")
ax.axhline(50, ls=":", color=MUT); ax.text(0.05, 52, "chance", color=MUT, fontsize=9)
ax.axvspan(0.7, 1.3, color=C1, alpha=.08)
ax.text(1.0, 8, "quiet\nbreathing", ha="center", fontsize=9, color=C1)
ax.set_xlabel("displacement amplitude (cm)")
ax.set_ylabel("percent")
ax.set_xticks(amps); ax.set_ylim(0, 105)
ax.set_title("Study 6: motion degrades the design into ABSTENTION, not into confident error\n"
             "the gap between the two curves is the abstain gate doing its job")
ax.legend(fontsize=9.5, loc="lower left"); _fin(ax)
fig.tight_layout(); fig.savefig("figs_new/n4_abstain.png", bbox_inches="tight")
plt.close(fig); print("[n4] safe failure mode")

print("figures ->", len(os.listdir("figs_new")), "files in figs_new/")
