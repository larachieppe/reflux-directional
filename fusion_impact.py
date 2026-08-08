"""
Does the inverse-variance fusion (defect 52) change any DECISION?

The fix demonstrably stabilises the fused slope -- spread across the mesh
refinement sequence falls from 35.5% to 2.6%. But the studies already run tonight
used the old weighting, so the question that decides whether they must be re-run
is narrower: does the change flip the sign the device reports, or only the
magnitude behind it?

Both fusions are computed from the SAME forward solve, so this costs one solve
per trial rather than two runs, and the comparison is exactly paired.
"""
import sys
import numpy as np
import eit3d
import directional_sim as ds

N = int(sys.argv[1]) if len(sys.argv) > 1 else 96


def fuse(cands, mode):
    tot = lag_w = sl_w = 0.0
    use_iv = any(np.isfinite(c.get("se_slope", np.inf)) for c in cands)
    for c in cands:
        base = max(c.get("z_baseline", 0.0), 1e-6)
        if mode == "iv" and use_iv:
            se = c.get("se_slope", np.inf)
            w = 1.0 / max(se * se, 1e-12) if np.isfinite(se) else 0.0
        else:
            q = max(c["lin"], 0.0) if c["n_zones"] >= 3 else 0.35
            w = base * (0.25 + q) * np.sqrt(max(c["dif_energy"], 0.0))
        lag_w += w * c["lag"]
        sl_w += w * (c["slope"] if c["n_zones"] >= 3 else c["lag"])
        tot += w
    return None if tot <= 0 else (lag_w + sl_w) / tot


def decide(dZ, w, mode):
    best = None
    for s_i in (0, 1):
        cands = [c for c in (ds._strip_aperture_stats(dZ, w, s_i, m)
                             for m in w.apertures) if c and c.get("defined")]
        if not cands:
            continue
        en = sum(c["dif_energy"] for c in cands)
        if best is None or en > best[0]:
            best = (en, cands)
    if best is None:
        return 0, 0.0
    cands = best[1]
    ev = fuse(cands, mode)
    if ev is None:
        return 0, 0.0
    tw = sum(max(c.get("z_baseline", 0), 1e-6) * np.sqrt(max(c["dif_energy"], 0))
             for c in cands)
    lin = (sum(max(c.get("z_baseline", 0), 1e-6) * np.sqrt(max(c["dif_energy"], 0))
               * c["lin"] for c in cands) / tw) if tw > 0 else 0.0
    nz = max(c["n_zones"] for c in cands)
    if nz >= 3 and lin < ds.LIN_GATE:
        return 0, float(ev)
    return (1 if ev > 0 else -1), float(ev)


def main():
    mesh = eit3d.make_cylinder(R=5.5, height=20.0, n_rings=6, nz=17)
    w = ds.StripWorld(8, span=12.0, mesh=mesh, z_center=0.36)
    same = 0
    flips = []
    acc = {"old": 0, "iv": 0}
    ntrav = 0
    for i in range(N):
        rng = np.random.default_rng(3_100_000 + i)
        lab = ("reflux", "antegrade", "noflow", "bladder")[i % 4]
        g = ds.sample_grade(rng)
        side = +1 if rng.random() < 0.5 else -1
        mot = (0.0, 0.30, 0.60)[(i // 4) % 3]
        dZ = ds.simulate_trial(w, lab, np.random.default_rng(3_200_000 + i),
                               grade=g, side=side, T=20, snr_db=60,
                               motion_amp=mot)
        d_old, _ = decide(dZ, w, "old")
        d_iv, _ = decide(dZ, w, "iv")
        want = {"reflux": +1, "antegrade": -1}.get(lab, 0)
        if want != 0:
            ntrav += 1
            acc["old"] += (d_old == want)
            acc["iv"] += (d_iv == want)
        if d_old == d_iv:
            same += 1
        else:
            flips.append((lab, g, mot, d_old, d_iv, want))
        if (i + 1) % 24 == 0:
            print(f"  {i+1}/{N} ...", flush=True)
    print(f"\ndecisions identical: {same}/{N} ({100*same/N:.1f}%)")
    print(f"direction accuracy on travelling trials (n={ntrav}): "
          f"old {100*acc['old']/max(ntrav,1):.1f}%  "
          f"inverse-variance {100*acc['iv']/max(ntrav,1):.1f}%")
    print(f"flips: {len(flips)}")
    for f in flips[:14]:
        print(f"   label={f[0]:9s} grade={f[1]} motion={f[2]} "
              f"old={f[3]:+d} iv={f[4]:+d} truth={f[5]:+d}")


if __name__ == "__main__":
    main()
