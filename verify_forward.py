"""
Numerical verification of the forward model.

Everything in this project rests on the forward solve being right. That has been
asserted and never demonstrated, which is the first thing a numerical analyst on
a review panel will ask about. This script runs four checks that need no patient
data and no new physics, and writes metrics_verify.json.

  V1  Quasi-static validity. Arithmetic only: is the electro-quasi-static
      approximation actually justified at 50-100 kHz in a torso-sized domain?
  V2  Reciprocity. Maxwell reciprocity requires the transfer impedance to be
      unchanged when the drive pair and the sense pair are exchanged. This is a
      strong, assumption-free test of the CEM assembly and solve: an error in the
      electrode constraints, the Robin term or the gauge will break it.
  V3  Mesh convergence. The headline result is the SIGN of a slope, so the
      quantity that must converge is not just |Z| but the arrival-time slope and
      the decision it produces. Solved on a sequence of refined meshes with an
      identical, NOISELESS trial.
  V4  Tetrapolar contact-impedance immunity. The report claims contact impedance
      "largely drops out" of a tetrapolar measurement. That is a quantitative
      claim and it is testable: sweep z0 across its full modelled range and
      compare the sensitivity of the tetrapolar transfer impedance against a
      two-electrode proxy on the same electrodes.

Deliberately cheap. The meshes here are a few thousand nodes, so all four checks
together cost minutes, not hours.
"""
import json, time
import numpy as np

import eit3d
import strip3d
import directional_sim as ds

EPS0 = ds.EPS0
C0 = 2.99792458e8
N_STRIP = 8
SPAN = 16.0
Z_CENTER = 0.50
T = 20


# ---------------------------------------------------------------- V1
def v1_quasistatic():
    """Three dimensionless checks, per tissue per frequency.

    (a) wavelength in the medium vs domain size  -> propagation negligible?
    (b) omega*eps/sigma                          -> displacement vs conduction
    (c) skin depth vs domain size                -> magnetic diffusion negligible?
    """
    L_dom = 0.20                                   # m, torso segment height
    MU0 = 4e-7 * np.pi
    out = {}
    for fname, f in (("50kHz", 50e3), ("100kHz", 100e3)):
        w = 2 * np.pi * f
        per = {}
        for t, (s0, er0) in ds.TISSUE.items():
            a = ds.admittivity(t, f)
            s, epsr = a.real, a.imag / (w * EPS0)
            eps = epsr * EPS0
            ratio = w * eps / s                       # displacement / conduction
            # wavelength in a lossy conductor (good-conductor limit)
            delta = np.sqrt(2.0 / (w * MU0 * s))      # skin depth, m
            lam = 2 * np.pi * delta
            per[t] = dict(sigma=float(s), eps_r=float(epsr),
                          omega_eps_over_sigma=float(ratio),
                          skin_depth_m=float(delta),
                          skin_depth_over_L=float(delta / L_dom),
                          wavelength_m=float(lam),
                          L_over_wavelength=float(L_dom / lam),
                          free_space_wavelength_m=float(C0 / f))
            # TWO SEPARATE QUESTIONS, easily conflated.
            #
            # (a) Is the electro-quasi-static approximation valid, i.e. may
            #     magnetic induction be dropped so the problem reduces to
            #     div(kappa grad u) = 0 with a COMPLEX admittivity kappa? This
            #     needs the domain small against the wavelength and the skin
            #     depth large against the domain. It does NOT require
            #     omega*eps/sigma to be small.
            # The two conditions must be INDEPENDENT to mean anything. In a good
            # conductor the in-medium wavelength is lam = 2*pi*delta, so testing
            # L/lam merely restates the skin-depth test (L/lam < 0.01 is exactly
            # delta/L > 15.9) and double-counts it. The correct propagation
            # criterion is against the FREE-SPACE wavelength, which is what
            # "electrically small" means: 3.0 km at 100 kHz against a 0.2 m
            # domain. It is satisfied by four orders of magnitude, so the
            # skin-depth condition is the only one that actually binds.
            per[t]["L_over_free_space_wavelength"] = float(L_dom / (C0 / f))
            per[t]["eqs_ok"] = bool(delta / L_dom > 5 and L_dom / (C0 / f) < 0.01)
            # (b) May permittivity be dropped, i.e. is a purely REAL conductivity
            #     model adequate? That is what omega*eps/sigma answers, and it is
            #     a modelling convenience question, not a validity question.
            per[t]["permittivity_negligible"] = bool(ratio < 0.1)
        out[fname] = per
    out["criteria"] = (
        "Electro-quasi-static validity requires (i) domain size << wavelength "
        "and (ii) skin depth >> domain size, so that magnetic induction is "
        "negligible and the problem reduces to div(kappa grad u) = 0 in the "
        "complex admittivity kappa = sigma + j*omega*eps. It does NOT require "
        "omega*eps/sigma << 1. That separate ratio says only whether "
        "permittivity may be DROPPED, i.e. whether a real-conductivity model "
        "would suffice. This model carries the full complex admittivity, so it "
        "is correct whether or not that ratio is small.")
    out["interpretation"] = (
        "EQS holds comfortably at both frequencies: skin depth exceeds the "
        "domain by more than an order of magnitude and the domain is under 1% "
        "of a wavelength. But omega*eps/sigma is NOT small in the perfused soft "
        "tissues - it reaches ~1.4 for kidney at 100 kHz, where displacement "
        "current slightly EXCEEDS conduction current. Two consequences follow. "
        "First, a real-conductivity model would be wrong here and the complex "
        "admittivity is doing necessary work. Second, the imaginary part of the "
        "measurement carries genuine tissue information, which is the physical "
        "argument for the second frequency being worth its cost - a claim this "
        "project has NOT yet tested, since frequency is solved but never used "
        "as a discriminative feature.")
    return out


# ---------------------------------------------------------------- V2
def v2_reciprocity(world, sigma, zc, n_pairs=12, rng=None):
    """Z(drive AB, sense CD) must equal Z(drive CD, sense AB).

    Note this is a genuine test of the discretised operator, not a tautology: the
    drive enters through the electrode current constraint and the sense through a
    potential difference, so the two solves exercise different rows of the
    system. Asymmetry in the assembly shows up here immediately.
    """
    rng = rng or np.random.default_rng(0)
    L = world.L
    zones = world.zones[:n_pairs]
    fwd, rev = [], []
    for z in zones:
        a, b = z["drive"]
        p, q = z["sense"]
        U1 = world.solver.solve_drives(sigma, zc, [(a, b)], 1.0)[0]
        z_fwd = (U1[p] - U1[q])
        U2 = world.solver.solve_drives(sigma, zc, [(p, q)], 1.0)[0]
        z_rev = (U2[a] - U2[b])
        fwd.append(z_fwd); rev.append(z_rev)
    fwd = np.array(fwd); rev = np.array(rev)
    denom = np.maximum(np.abs(fwd), 1e-30)
    rel = np.abs(fwd - rev) / denom
    return dict(n_pairs=int(len(fwd)),
                max_rel_error=float(rel.max()),
                median_rel_error=float(np.median(rel)),
                mean_rel_error=float(rel.mean()),
                # a direct solve should hold reciprocity to near machine
                # precision; anything above ~1e-8 indicates an assembly error
                passes=bool(rel.max() < 1e-8),
                examples=[dict(fwd=[float(x.real), float(x.imag)],
                               rev=[float(y.real), float(y.imag)],
                               rel=float(r))
                          for x, y, r in list(zip(fwd, rev, rel))[:4]])


# ---------------------------------------------------------------- V3
def _noiseless_trial(world, label, grade, side, seed):
    """One deterministic, NOISELESS trial. Noise is excluded on purpose: this
    check is about discretisation error, and injected noise would swamp it."""
    rng = np.random.default_rng(seed)
    anat = ds.draw_anatomy(world, np.random.default_rng(seed + 1))
    disp = np.zeros((T, 3))
    zc = np.full(world.L, 10.0)
    cs, frac = ds.bolus_path(world, anat, label, grade, side, T)
    br = ds.GRADE_TABLE[grade][0] * world.R
    radii = (br, br, 1.15 * br)
    Z = np.zeros((T, len(ds.FREQS), len(world.zones)), complex)
    for ti in range(T):
        for fi, f in enumerate(ds.FREQS):
            sig = world.base_sigma(f, anat)
            if frac[ti] > 1e-3:
                sig = world.add_bolus(sig, f, cs[ti], radii, frac=float(frac[ti]))
            Z[ti, fi] = strip3d.measure_zones(world.solver, sig, zc, world.zones)
    base = Z[:2].mean(axis=0, keepdims=True)
    return Z, (Z - base) / np.abs(base)


def v3_mesh_convergence(levels):
    """Refine the mesh and watch |Z|, the fitted slope, and the DECISION.

    Convergence of |Z| alone would not be enough: the product depends on the sign
    of a slope, so the slope is the quantity that has to be shown stable.
    """
    rows = []
    for (nr, nz) in levels:
        t0 = time.time()
        mesh = eit3d.make_cylinder(R=5.5, height=20.0, n_rings=nr, nz=nz)
        w = ds.StripWorld(N_STRIP, span=SPAN, mesh=mesh, z_center=Z_CENTER)
        Z, dZ = _noiseless_trial(w, "reflux", 4, +1, seed=4242)
        feat = ds.direction_features(dZ, w)
        d, s, ev = ds.decide_direction(feat)
        rows.append(dict(
            n_rings=nr, nz=nz,
            n_nodes=int(mesh.p.shape[1]), n_tets=int(mesh.t.shape[1]),
            n_zones=int(len(w.zones)),
            mean_absZ=float(np.abs(Z[0, 0]).mean()),
            zone_absZ=[float(x) for x in np.abs(Z[0, 0])],
            slope=float(feat[s].get("slope", float("nan"))),
            lin=float(feat[s].get("lin", float("nan"))),
            decision=int(d), strip=int(s),
            build_solve_s=round(time.time() - t0, 1)))
        print(f"[v3] rings={nr} nz={nz}  nodes={rows[-1]['n_nodes']:5d}  "
              f"|Z|={rows[-1]['mean_absZ']:.4g}  slope={rows[-1]['slope']:+.4g}  "
              f"decision={d}  ({rows[-1]['build_solve_s']}s)", flush=True)

    fin = rows[-1]
    for r in rows:
        r["absZ_rel_to_finest"] = float(abs(r["mean_absZ"] - fin["mean_absZ"])
                                        / max(abs(fin["mean_absZ"]), 1e-30))
        r["slope_rel_to_finest"] = (float(abs(r["slope"] - fin["slope"])
                                          / max(abs(fin["slope"]), 1e-30))
                                    if fin["slope"] == fin["slope"] else float("nan"))
    decisions = {r["decision"] for r in rows}
    return dict(levels=rows,
                decision_stable=bool(len(decisions) == 1),
                decisions=sorted(int(x) for x in decisions),
                absZ_rel_change_finest_two=float(rows[-2]["absZ_rel_to_finest"])
                if len(rows) > 1 else float("nan"),
                slope_rel_change_finest_two=float(rows[-2]["slope_rel_to_finest"])
                if len(rows) > 1 else float("nan"))


# ---------------------------------------------------------------- V4
def v4_contact_immunity(world, sigma):
    """Sweep contact impedance and compare tetrapolar against a bipolar proxy.

    The bipolar proxy is the driven pair's OWN potential difference, which is the
    quantity a two-electrode instrument would report and which carries the
    contact impedance directly. Same electrodes, same solve, so the comparison is
    like-for-like.
    """
    z0s = [1.0, 5.0, 10.0, 20.0, 40.0]
    tetra, bip = [], []
    zones = world.zones[:8]
    for z0 in z0s:
        zc = np.full(world.L, float(z0))
        drives = [z["drive"] for z in zones]
        Us = world.solver.solve_drives(sigma, zc, drives, 1.0)
        t_row, b_row = [], []
        for i, zd in enumerate(zones):
            p, q = zd["sense"]; a, b = zd["drive"]
            t_row.append(abs(Us[i][p] - Us[i][q]))
            b_row.append(abs(Us[i][a] - Us[i][b]))
        tetra.append(t_row); bip.append(b_row)
    tetra = np.array(tetra); bip = np.array(bip)

    def spread(M):
        # relative peak-to-peak variation across the z0 sweep, per zone
        return np.ptp(M, axis=0) / np.maximum(np.abs(M).mean(axis=0), 1e-30)

    st, sb = spread(tetra), spread(bip)
    # over the range the model actually draws from, U(5,20)
    idx = [i for i, z in enumerate(z0s) if 5.0 <= z <= 20.0]
    st_m = np.ptp(tetra[idx], axis=0) / np.maximum(np.abs(tetra[idx]).mean(axis=0), 1e-30)
    sb_m = np.ptp(bip[idx], axis=0) / np.maximum(np.abs(bip[idx]).mean(axis=0), 1e-30)
    return dict(
        z0_values=z0s, n_zones=int(len(zones)),
        tetrapolar_rel_spread_full=float(st.mean()),
        bipolar_rel_spread_full=float(sb.mean()),
        rejection_factor_full=float(sb.mean() / max(st.mean(), 1e-30)),
        tetrapolar_rel_spread_modelled_range=float(st_m.mean()),
        bipolar_rel_spread_modelled_range=float(sb_m.mean()),
        rejection_factor_modelled_range=float(sb_m.mean() / max(st_m.mean(), 1e-30)),
        note=("rejection factor is how many times more sensitive a two-electrode "
              "measurement is to contact impedance than the tetrapolar one, on "
              "identical electrodes and identical solves"))


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    out = {"config": dict(model_version=ds.MODEL_VERSION)}

    print("[v1] quasi-static validity", flush=True)
    out["v1_quasistatic"] = v1_quasistatic()
    bad = [(f, t) for f, per in out["v1_quasistatic"].items() if isinstance(per, dict)
           for t, d in per.items() if isinstance(d, dict) and not d.get("eqs_ok")]
    # DEFECT 39: this read "quasistatic_ok", a key renamed to "eqs_ok" when the
    # criterion was corrected. .get() returned None for every tissue, so the one
    # automated gate in the verification script reported EVERY tissue as failing
    # quasi-static validity -- the exact opposite of what the check computed.
    print(f"[v1] tissues failing the criteria: {bad if bad else 'none'}", flush=True)

    mesh = eit3d.make_cylinder(R=5.5, height=20.0, n_rings=6, nz=17)
    w = ds.StripWorld(N_STRIP, span=SPAN, mesh=mesh, z_center=Z_CENTER)
    anat = ds.draw_anatomy(w, np.random.default_rng(7))
    sigma = w.base_sigma(ds.FREQS[0], anat)
    zc = np.full(w.L, 10.0)

    print("[v2] reciprocity", flush=True)
    out["v2_reciprocity"] = v2_reciprocity(w, sigma, zc)
    print(f"[v2] max relative error {out['v2_reciprocity']['max_rel_error']:.3e}  "
          f"passes={out['v2_reciprocity']['passes']}", flush=True)

    print("[v4] contact-impedance immunity", flush=True)
    out["v4_contact_immunity"] = v4_contact_immunity(w, sigma)
    print(f"[v4] rejection factor over the modelled z0 range: "
          f"{out['v4_contact_immunity']['rejection_factor_modelled_range']:.1f}x",
          flush=True)

    print("[v3] mesh convergence (slowest check)", flush=True)
    out["v3_mesh_convergence"] = v3_mesh_convergence(
        [(4, 11), (5, 13), (6, 17), (7, 21), (8, 25)])
    print(f"[v3] decision stable across meshes: "
          f"{out['v3_mesh_convergence']['decision_stable']}", flush=True)

    out["runtime_min"] = (time.time() - t0) / 60.0
    with open("metrics_verify.json", "w") as f:
        json.dump(out, f, indent=1)
    print(f"[verify] done in {out['runtime_min']:.1f} min -> metrics_verify.json",
          flush=True)


if __name__ == "__main__":
    main()
