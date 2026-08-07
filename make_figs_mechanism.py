"""
Mechanism figure: what the detector actually reads.

Left column  - zone impedance traces for a retrograde (reflux) event and an
               antegrade (normal) event on the same strip.
Right column - per-zone arrival time against zone height. The SIGN of that slope
               is the entire decision. Reflux tilts one way, normal the other.

This is the figure that shows the device is reading ORDERING, not amplitude.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import eit3d
import directional_sim as ds

os.makedirs("figs_dir", exist_ok=True)
ACCENT = "#2b7fd4"; C1 = "#199e70"; C3 = "#e66767"; MUT = "#8a8a8a"; INK = "#1c2b30"
plt.rcParams.update({"font.size": 10.5, "axes.titleweight": "bold",
                     "figure.dpi": 120, "axes.edgecolor": "#c9d4d6",
                     "text.color": INK, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.titlecolor": INK})

N = 8
mesh = eit3d.make_cylinder(R=5.5, height=20.0, n_rings=6, nz=17)
W = ds.StripWorld(N, span=16.0, mesh=mesh)
print(f"world N={N}: {W.L} electrodes, {len(W.zones)} zones, pitch {W.spacing:.2f} cm")

fig, axs = plt.subplots(2, 2, figsize=(11.5, 7.0))
for row, (label, title, col) in enumerate([
        ("reflux", "Retrograde (reflux): bolus travels UP", C3),
        ("antegrade", "Antegrade (normal): bolus travels DOWN", C1)]):
    dZ = ds.simulate_trial(W, label, np.random.default_rng(7), grade=4, side=+1,
                           T=20, snr_db=60.0, motion_amp=0.4)
    feat = ds.direction_features(dZ, W)
    s = 0 if feat[0]["dif_energy"] >= feat[1]["dif_energy"] else 1
    m = feat[s]["m"]
    ser, idx = ds.zone_series(dZ, W, s, m)
    zz = W.zone_z[idx]
    order = np.argsort(zz)
    ser, zz = ser[order], zz[order]
    ser = ser - ser.mean(axis=0, keepdims=True)      # common-mode rejection
    ser = ser - ser.mean(axis=1, keepdims=True)
    t = np.arange(ser.shape[1])

    ax = axs[row, 0]
    sh = 1.15 * np.abs(ser).max()
    for j in range(ser.shape[0]):
        ax.plot(t, ser[j] + j * sh, color=col, lw=1.9)
        ax.text(-0.4, j * sh, f"z={zz[j]:.1f}", ha="right", va="center",
                fontsize=9, color=MUT)
        pk = int(np.argmax(np.abs(ser[j])))
        ax.plot([pk], [ser[j][pk] + j * sh], "o", color=INK, ms=5)
    ax.set_yticks([]); ax.set_xlabel("time sample")
    ax.set_title(title + "\n(zone traces, common mode removed)", fontsize=10.5)
    ax.grid(alpha=.2, axis="x"); ax.set_axisbelow(True)
    ax.set_xlim(-2.2, len(t) - 0.5)

    tarr = np.array([ds.xcorr_lag(ser[0], ser[j])[0] for j in range(ser.shape[0])])
    ax2 = axs[row, 1]
    ax2.plot(tarr, zz, "o", color=col, ms=9)
    A = np.vstack([zz, np.ones_like(zz)]).T
    coef, *_ = np.linalg.lstsq(A, tarr, rcond=None)
    zl = np.linspace(zz.min() - .4, zz.max() + .4, 20)
    ax2.plot(coef[0] * zl + coef[1], zl, "-", color=INK, lw=1.6, alpha=.75)
    ax2.set_xlabel("arrival time (samples, relative)")
    ax2.set_ylabel("zone height z (cm)")
    sign = "positive" if coef[0] > 0 else "negative"
    verdict = "REFLUX" if coef[0] > 0 else "normal"
    ax2.set_title(f"Arrival time vs height: slope {sign}  ->  {verdict}", fontsize=10.5)
    ax2.grid(alpha=.25); ax2.set_axisbelow(True)

fig.suptitle("What the detector reads: the ORDER zones light up, not how much",
             fontsize=12.5, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig("figs_dir/figG_mechanism.png", bbox_inches="tight")
plt.close(fig)
print("[G] mechanism -> figs_dir/figG_mechanism.png")
