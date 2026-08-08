"""
Pre-flight every study's geometry before committing hours of compute.

Builds the StripWorld each study will construct, and runs ONE trial through the
full estimator, without doing the study. Catches an off-body placement, a torn
mesh, a shorted electrode array or an estimator crash in seconds rather than
three hours into an unattended run.

Exit code 0 = safe to run the chain, 1 = something would fail.
"""
import json, os, sys, traceback
import numpy as np

import eit3d
import directional_sim as ds

HEIGHT = 20.0
R = 5.5
MESH = None


def mesh():
    global MESH
    if MESH is None:
        MESH = eit3d.make_cylinder(R=R, height=HEIGHT, n_rings=6, nz=17)
    return MESH


def check(label, n_strip, span, z_center):
    """Build the world and push one trial through the estimator."""
    try:
        w = ds.StripWorld(n_strip, span=span, mesh=mesh(), z_center=z_center)
    except Exception as e:
        return False, f"world: {type(e).__name__}: {e}"
    try:
        dZ = ds.simulate_trial(w, "reflux", np.random.default_rng(1), grade=3,
                               side=+1, T=20, snr_db=60, motion_amp=0.3)
        d, s, ev = ds.decide_direction(ds.direction_features(dZ, w))
    except Exception as e:
        return False, f"estimator: {type(e).__name__}: {e}"
    return True, f"{len(w.zones)} zones, dir={d:+d}"


def best_placement():
    try:
        b = json.load(open("metrics_placement.json"))["best_low_grade"]
        return float(b["span"]), float(b["z_center"])
    except Exception:
        return 12.0, 0.36


def main():
    fails = []
    print("PRE-FLIGHT")

    print("\n  mesh")
    try:
        m = mesh()
        nb = m.boundary_facets().shape[0]
        print(f"    conforming, {m.t.shape[1]} tets, {nb} boundary facets")
    except Exception as e:
        print(f"    FAIL {e}"); fails.append("mesh"); return _end(fails)

    print("\n  Study 1: electrode count sweep")
    import run_directional as rd
    for n in rd.COUNTS:
        ok, msg = check(f"N={n}", n, rd.SPAN, 0.5)
        print(f"    N={n:<3} span={rd.SPAN:<5} {'ok ' if ok else 'FAIL'} {msg}")
        if not ok:
            fails.append(f"Study1 N={n}")
    for sp in rd.SPANS:
        ok, msg = check("span", 8, sp, 0.5)
        print(f"    N=8   span={sp:<5} {'ok ' if ok else 'FAIL'} {msg}")
        if not ok:
            fails.append(f"Study1 span={sp}")

    print("\n  Study 3: placement grid")
    import run_placement as rp
    feas = 0
    for sp, zc in rp.CONFIGS:
        if not rp._feasible(sp, zc, rp.N_STRIP, HEIGHT):
            print(f"    {sp:<5} z={zc:<5} skipped, off body (expected)")
            continue
        feas += 1
        ok, msg = check("place", rp.N_STRIP, sp, zc)
        print(f"    {sp:<5} z={zc:<5} {'ok ' if ok else 'FAIL'} {msg}")
        if not ok:
            fails.append(f"Study3 {sp}@{zc}")
    if feas == 0:
        fails.append("Study3 has NO feasible configs")

    bs, bz = best_placement()
    print(f"\n  Study 4: tolerance around {bs} cm @ z={bz}")
    import run_tolerance as rt
    any_t = 0
    for off in rt.OFFSETS_CM:
        if not rt._feasible(off, bs, bz, rt.N_STRIP, HEIGHT):
            print(f"    {off:+.0f} cm  skipped, off body (expected)")
            continue
        any_t += 1
        ok, msg = check("tol", rt.N_STRIP, bs, bz + off / HEIGHT)
        print(f"    {off:+.0f} cm  {'ok ' if ok else 'FAIL'} {msg}")
        if not ok:
            fails.append(f"Study4 {off:+.0f}")
    if any_t == 0:
        fails.append("Study4 has NO feasible offsets")

    print("\n  Study 5: precision arms")
    import run_precision as rpr
    for sp, zc, nm in rpr.CONFIGS:
        for s in (0.0, rpr.MAX_OFF):
            zz = zc + s / HEIGHT
            ok, msg = check("prec", rpr.N_STRIP, sp, zz)
            print(f"    {sp:<5} z={zz:.3f} {'ok ' if ok else 'FAIL'} {msg}")
            if not ok:
                fails.append(f"Study5 {sp}@{zz:.3f}")

    print("\n  Study 2 and Study 6")
    import run_design as rdg
    import run_motion2 as rm
    for lbl, n, sp, zc in (("design published", rdg.N_STRIP, 16.0, 0.50),
                           ("design optimum", rdg.N_STRIP, bs, bz),
                           ("motion", rm.N_STRIP, rm.SPAN, 0.50)):
        ok, msg = check(lbl, n, sp, zc)
        print(f"    {lbl:<18} {sp:<5} z={zc:<5} {'ok ' if ok else 'FAIL'} {msg}")
        if not ok:
            fails.append(lbl)

    return _end(fails)


def _end(fails):
    print()
    if fails:
        print(f"PRE-FLIGHT FAILED: {len(fails)} problems")
        for f in fails:
            print("   -", f)
        return 1
    print("PRE-FLIGHT CLEAN -- safe to run the chain unattended")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
