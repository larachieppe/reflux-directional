"""
Visuals for the locked-design run. Reads metrics_design.json -> figs_design/*.png
Light background to sit on the site's white figure cards.
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

os.makedirs("figs_design", exist_ok=True)
ACCENT = "#2b7fd4"; C1 = "#199e70"; C2 = "#c98500"; C3 = "#e66767"; MUT = "#8a8a8a"
INK = "#1c2b30"
plt.rcParams.update({"font.size": 11, "axes.titleweight": "bold", "figure.dpi": 120,
                     "axes.edgecolor": "#c9d4d6", "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
                     "axes.titlecolor": INK})
BLUES = LinearSegmentedColormap.from_list("b", ["#ffffff", ACCENT])

M = json.load(open("metrics_design.json"))
C = M["config"]
MOT = C["motion"]
OP = M["operating"]
NS, SPAN, CH = C["n_strip"], C["span"], C["channels"]


def _fin(ax):
    ax.grid(alpha=.25); ax.set_axisbelow(True)


def mcol(i):
    return plt.cm.viridis(0.08 + 0.78 * i / max(len(MOT) - 1, 1))


# ------------------------------------------------- 1. ROC across motion
fig, ax = plt.subplots(figsize=(6.6, 6.0))
for i, m in enumerate(MOT):
    d = OP[str(m)]
    ax.plot(d["roc_fpr"], d["roc_tpr"], lw=2.1, color=mcol(i),
            label=f"{m:.2f} cm   AUC {d['auc']:.2f}")
ax.plot([0, 1], [0, 1], ls=":", color=MUT, lw=1.4)
ax.set_xlabel("false positive rate  (1 - specificity)")
ax.set_ylabel("true positive rate  (sensitivity)")
ax.set_title(f"ROC: reflux vs rest\nN={NS}/strip, {SPAN:.0f} cm span, {CH} channels")
ax.legend(title="motion", fontsize=9, title_fontsize=9, loc="lower right")
ax.set_xlim(-.02, 1.02); ax.set_ylim(-.02, 1.02); _fin(ax)
fig.tight_layout(); fig.savefig("figs_design/d1_roc.png", bbox_inches="tight")
plt.close(fig); print("[1] roc")

# ------------------------------------------------- 2. motion degradation
fig, ax = plt.subplots(figsize=(8.8, 4.8))
for key, lab, col, mk in (("dir_acc", "direction accuracy", ACCENT, "o"),
                          ("lat_acc", "laterality accuracy", C1, "s")):
    ys = [100 * OP[str(m)][key] for m in MOT]
    if key == "dir_acc":
        lo = [100 * (OP[str(m)][key] - OP[str(m)]["dir_ci"][0]) for m in MOT]
        hi = [100 * (OP[str(m)]["dir_ci"][1] - OP[str(m)][key]) for m in MOT]
        ax.errorbar(MOT, ys, yerr=[lo, hi], fmt=mk + "-", color=col, lw=2.3, ms=7,
                    capsize=3, label=lab)
    else:
        ax.plot(MOT, ys, mk + "--", color=col, lw=2.3, ms=7, label=lab)
ax.plot(MOT, [100 * OP[str(m)]["auc"] for m in MOT], "^:", color=C2, lw=2, ms=7,
        label="AUC x 100")
ax.axhline(50, ls=":", color=MUT); ax.text(MOT[0], 51, "chance", color=MUT, fontsize=9)
ax.axvspan(0, 0.5, color=C1, alpha=.07)
ax.text(0.25, 40, "design target\n<= 0.5 cm", ha="center", color=C1, fontsize=9.5)
ax.set_xlabel("common-mode motion amplitude (cm)")
ax.set_ylabel("percent")
ax.set_title("Performance against motion, at the locked design")
ax.set_ylim(35, 105); ax.legend(fontsize=9.5); _fin(ax)
fig.tight_layout(); fig.savefig("figs_design/d2_motion.png", bbox_inches="tight")
plt.close(fig); print("[2] motion")

# ------------------------------------------------- 3. grade x motion heatmap
G = M["grade"]
gl = [1, 2, 3, 4, 5]
gm = sorted({float(k) for g in G.values() for k in g})
A = np.array([[100 * G[str(g)][str(m)]["dir_acc"] for m in gm] for g in gl])
fig, ax = plt.subplots(figsize=(7.6, 4.8))
im = ax.imshow(A, cmap="RdYlGn", vmin=30, vmax=100, aspect="auto")
for i in range(A.shape[0]):
    for j in range(A.shape[1]):
        ax.text(j, i, f"{A[i,j]:.0f}", ha="center", va="center", fontsize=11,
                color=INK, fontweight="bold")
ax.set_xticks(range(len(gm))); ax.set_xticklabels([f"{m:.2f}" for m in gm])
ax.set_yticks(range(len(gl))); ax.set_yticklabels([f"grade {g}" for g in gl])
ax.set_xlabel("motion amplitude (cm)")
ax.set_title("Direction accuracy by grade and motion (%)")
ax.axhline(1.5, color=INK, lw=2.5)
ax.text(len(gm) - 0.45, 1.5, " claimed\n range\n starts", va="center", fontsize=9, color=INK)
fig.colorbar(im, ax=ax, label="accuracy (%)")
fig.tight_layout(); fig.savefig("figs_design/d3_grade_heat.png", bbox_inches="tight")
plt.close(fig); print("[3] grade heatmap")

# ------------------------------------------------- 4. THE KEY ONE: multi-event
S = M["subject"]
K = S["k_events"]
ks = list(range(1, K + 1))
sens = [100 * S["sens_k"][str(k)] for k in ks]
spec = [100 * S["spec_k"][str(k)] for k in ks]
chance = [100 * S["chance_k"][str(k)] for k in ks]
indep = [100 * S["indep_k"][str(k)] for k in ks]
bk = int(S["best_k"])

fig, axs = plt.subplots(1, 2, figsize=(12.4, 4.9))
axs[0].plot(ks, sens, "o-", color=ACCENT, lw=2.6, ms=9, label="sensitivity (reflux children)")
axs[0].plot(ks, spec, "s-", color=C1, lw=2.6, ms=8, label="specificity (healthy children)")
axs[0].plot(ks, chance, "--", color=MUT, lw=1.8, label="sensitivity if detector were a coin flip")
axs[0].plot(ks, indep, ":", color=ACCENT, lw=1.6, alpha=.8, label="sensitivity if events were independent")
axs[0].axhline(81, ls="--", color=C3, lw=1.5)
axs[0].axhline(89, ls=":", color=C3, lw=1.5)
axs[0].text(1.02, 82.4, "VCUG sens 81%", color=C3, fontsize=8.5, ha="left")
axs[0].text(1.02, 90.4, "VCUG spec 89%", color=C3, fontsize=8.5, ha="left")
axs[0].axvline(bk, color=C2, lw=2, ls="--")
axs[0].text(0.97, 0.30, f"chosen rule: >={bk} of {K}\nsens {sens[bk-1]:.0f}%  spec {spec[bk-1]:.0f}%",
            transform=axs[0].transAxes, color=C2, fontsize=10, ha="right",
            bbox=dict(fc="white", ec=C2, alpha=.9, boxstyle="round,pad=0.4"))
axs[0].set_xlabel(f"flag the child if at least k of {K} events read retrograde")
axs[0].set_ylabel("percent")
axs[0].set_title("The screening rule, sensitivity and specificity separately")
axs[0].set_xticks(ks); axs[0].set_ylim(0, 105)
axs[0].legend(fontsize=8.5, loc="lower left"); _fin(axs[0])

hr = S["hist_reflux_hits"]; ha = S["hist_healthy_falsepos"]
x = np.arange(len(hr)); w = 0.42
axs[1].bar(x - w/2, hr, w, color=C3, label="reflux children: events correctly called retrograde")
axs[1].bar(x + w/2, ha, w, color=C1, label="healthy children: events wrongly called retrograde")
axs[1].axvline(bk - 0.5 + 0.0, color=C2, lw=2, ls="--")
axs[1].text(bk - 0.42, max(max(hr), max(ha)) * 1.02, f"rule: >={bk}", color=C2,
            fontsize=9.5, ha="right")
axs[1].set_xlabel(f"events out of {K}")
axs[1].set_ylabel("number of children")
axs[1].set_title("Per-child spread: the two populations barely overlap")
axs[1].set_xticks(x); axs[1].legend(fontsize=8, loc="upper left"); _fin(axs[1])
nd = S["never_detected_reflux"]
axs[1].set_ylim(0, max(max(hr), max(ha)) * 1.30)
axs[1].text(0.5, 0.90, f"refluxers never detected: {100*nd:.0f}%",
            transform=axs[1].transAxes, fontsize=10, ha="center",
            color=(C1 if nd < 0.05 else C3),
            bbox=dict(fc="white", ec=(C1 if nd < 0.05 else C3), alpha=.9,
                      boxstyle="round,pad=0.35"))
fig.suptitle("Multi-event detection: the basis for beating VCUG, measured on repeat events per child",
             fontsize=12.5, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig("figs_design/d4_multievent.png", bbox_inches="tight")
plt.close(fig); print("[4] multi-event (sens/spec separated)")

# ------------------------------------------------- 5. evidence separability
fig, axs = plt.subplots(1, 3, figsize=(13.0, 4.0))
for ax, m in zip(axs, [MOT[0], MOT[len(MOT)//2], MOT[-1]]):
    d = OP[str(m)]
    r = np.array(d["ev_reflux"], float); a = np.array(d["ev_antegrade"], float)
    r = r[np.isfinite(r)]; a = a[np.isfinite(a)]
    if len(r) and len(a):
        lim = np.percentile(np.abs(np.concatenate([r, a])), 97) or 1
        bins = np.linspace(-lim, lim, 26)
        ax.hist(a, bins=bins, alpha=.7, color=C1, label="antegrade (normal)")
        ax.hist(r, bins=bins, alpha=.7, color=C3, label="reflux")
    ax.axvline(0, color=INK, lw=1.6)
    ax.set_title(f"motion {m:.2f} cm"); ax.set_xlabel("direction evidence (+ = retrograde)")
    _fin(ax)
axs[0].set_ylabel("events"); axs[0].legend(fontsize=9)
fig.suptitle("Direction evidence separates the two classes, and how motion erodes it",
             fontsize=12.5, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.92])
fig.savefig("figs_design/d5_evidence.png", bbox_inches="tight")
plt.close(fig); print("[5] evidence")

# ------------------------------------------------- 6. operating points + ablation
fig, axs = plt.subplots(1, 2, figsize=(12.0, 4.4))
specs = sorted(OP[str(MOT[0])]["sens_at_spec"], key=float)
for i, sp in enumerate(specs):
    axs[0].plot(MOT, [100 * OP[str(m)]["sens_at_spec"][sp] for m in MOT], "o-",
                lw=2.1, ms=6, color=plt.cm.plasma(0.15 + 0.6 * i / max(len(specs)-1,1)),
                label=f"at {100*float(sp):.0f}% specificity")
axs[0].axhline(81, ls="--", color=C3, lw=1.7)
axs[0].text(MOT[-1], 82.5, "nuclear VCUG 81% sens @ 89% spec", color=C3,
            fontsize=8.5, ha="right")
axs[0].set_xlabel("motion amplitude (cm)"); axs[0].set_ylabel("sensitivity (%)")
axs[0].set_title("Sensitivity at fixed specificity"); axs[0].legend(fontsize=8.5)
axs[0].set_ylim(0, 105); _fin(axs[0])

AB = M["ablation"]
ks2 = [("full", "all features", ACCENT), ("direction_only", "direction only", C1),
       ("amplitude_only", "amplitude only", C3)]
axs[1].bar([l for _, l, _ in ks2], [AB[k] for k, _, _ in ks2],
           color=[c for _, _, c in ks2], width=.6)
for i, (k, _, _) in enumerate(ks2):
    axs[1].text(i, AB[k] + .015, f"{AB[k]:.2f}", ha="center", fontsize=11, color=INK)
axs[1].axhline(.5, ls=":", color=MUT)
axs[1].set_ylabel("reflux AUC"); axs[1].set_ylim(0.3, 1.03)
axs[1].set_title(f"What carries the signal (motion {AB['motion']:.2f} cm)")
_fin(axs[1])
fig.tight_layout(); fig.savefig("figs_design/d6_ops_ablation.png", bbox_inches="tight")
plt.close(fig); print("[6] ops + ablation")

# ------------------------------------------------- 7. confusion matrix
CF = M["confusion"]["counts"]
rows = ["reflux", "antegrade", "bladder", "noflow"]
cols = ["reflux", "antegrade", "not-reflux"]
Mx = np.array([[CF.get(r, {}).get(c, 0) for c in cols] for r in rows], float)
Mn = Mx / np.clip(Mx.sum(axis=1, keepdims=True), 1, None) * 100
fig, ax = plt.subplots(figsize=(7.0, 4.6))
im = ax.imshow(Mn, cmap=BLUES, vmin=0, vmax=100)
for i in range(Mn.shape[0]):
    for j in range(Mn.shape[1]):
        ax.text(j, i, f"{Mn[i,j]:.0f}%\n({int(Mx[i,j])})", ha="center", va="center",
                fontsize=10, color=INK if Mn[i, j] < 55 else "white")
ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols)
ax.set_yticks(range(len(rows))); ax.set_yticklabels(rows)
ax.set_xlabel("predicted"); ax.set_ylabel("true condition")
ax.set_title(f"Confusion at motion {M['confusion']['motion']:.2f} cm (row %)")
fig.tight_layout(); fig.savefig("figs_design/d7_confusion.png", bbox_inches="tight")
plt.close(fig); print("[7] confusion")

# ------------------------------------------------- 8. calibration
fig, ax = plt.subplots(figsize=(6.2, 5.4))
for i, m in enumerate([MOT[0], MOT[len(MOT)//2], MOT[-1]]):
    d = OP[str(m)]
    y = np.array(d["labels"], int); s = np.array(d["scores"], float)
    bins = np.linspace(0, 1, 7)
    idx = np.digitize(s, bins) - 1
    xs, ys = [], []
    for b in range(len(bins) - 1):
        sel = idx == b
        if sel.sum() >= 4:
            xs.append(s[sel].mean()); ys.append(y[sel].mean())
    if xs:
        ax.plot(xs, ys, "o-", lw=2, ms=7, color=mcol(MOT.index(m)),
                label=f"motion {m:.2f} cm")
ax.plot([0, 1], [0, 1], ls=":", color=MUT)
ax.set_xlabel("predicted probability of reflux")
ax.set_ylabel("observed fraction")
ax.set_title("Calibration (reliability)")
ax.legend(fontsize=9); _fin(ax)
fig.tight_layout(); fig.savefig("figs_design/d8_calibration.png", bbox_inches="tight")
plt.close(fig); print("[8] calibration")

print("figures ->", len(os.listdir("figs_design")), "files in figs_design/")
