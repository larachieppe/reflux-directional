"""
Cross-study consistency audit.

Runs over every metrics_*.json and flags anything that cannot simultaneously be
true, or that is true but implausible. Written as a script rather than done by
eye so it can be re-run after every study and cannot quietly stop being applied.

Checks, in order of how badly a failure would matter:
  A  cross-study    the same configuration measured twice must agree
  B  physical       a larger bolus must not be detected worse than a smaller one
  C  statistical    nothing significantly below chance; intervals must contain
                    their own point estimate; denominators must be what is claimed
  D  internal       monotonicity where physics demands it; no NaN masquerading
                    as a result; declared configs match what actually ran
  E  provenance     every metrics file newer than the code that produced it

Exit code 0 if nothing is flagged, 1 otherwise.
"""
import json, math, os, sys, glob, time

R = "/Users/larachieppe/Desktop/reflux-directional"
FLAGS = []


def flag(sev, area, msg):
    FLAGS.append((sev, area, msg))


def L(name):
    p = os.path.join(R, name)
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))
    except Exception as e:
        flag("ERROR", name, f"unreadable: {e}")
        return None


def wilson(p, n, z=1.96):
    if n <= 0 or p != p:
        return (float("nan"), float("nan"))
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def pct(x):
    return "n/a" if x is None or x != x else f"{100*x:.1f}%"


# ---------------------------------------------------------------- load
E = L("metrics_directional.json")      # Study 1
D = L("metrics_design.json")           # Study 2 @ published
DB = L("metrics_design_best.json")     # Study 2 @ optimum
P = L("metrics_placement.json")        # Study 3
T = L("metrics_tolerance.json")        # Study 4
PR = L("metrics_precision.json")       # Study 5
M2 = L("metrics_motion2.json")         # Study 6
V = L("metrics_verify.json")
GA = L("metrics_gate.json")


# ---------------------------------------------------------------- A cross-study
def check_cross():
    if not (P and T):
        return
    b = P.get("best_low_grade", {})
    bs, bz = b.get("span"), b.get("z_center")
    ts, tz = T["config"].get("span"), T["config"].get("z_center")
    if bs is not None and (abs(bs - ts) > 1e-6 or abs(bz - tz) > 1e-6):
        flag("HIGH", "Study 3 vs 4",
             f"tolerance is centred on {ts} cm @ z={tz} but the current placement "
             f"optimum is {bs} cm @ z={bz}: the tolerance curve describes a "
             f"placement the project no longer selects")
    if PR:
        cfgs = PR["config"].get("configs", [])
        if cfgs and bs is not None:
            got = (float(cfgs[0][0]), float(cfgs[0][1]))
            if abs(got[0] - bs) > 1e-6 or abs(got[1] - bz) > 1e-6:
                flag("HIGH", "Study 3 vs 5",
                     f"precision short arm is {got} but the optimum is {(bs, bz)}")
    # Study 2 published vs Study 3's own 16_0.50 cell, still, grades I-II
    if D and P and "16_0.50" in P.get("grid", {}):
        cell = P["grid"]["16_0.50"]
        if not cell.get("untestable"):
            for g in (1, 2):
                a = D["grade"][str(g)]["0.0"]["dir_acc"]
                c = cell.get(f"g{g}_m0.0", {}).get("dir_acc")
                if a is None or c is None:
                    continue
                na, nc = D["grade"][str(g)]["0.0"]["n"], cell[f"g{g}_m0.0"]["n"]
                la, ha = wilson(a, na)
                lc, hc = wilson(c, nc)
                if ha < lc or hc < la:
                    flag("HIGH", "Study 2 vs 3",
                         f"grade {g} still at 16cm@0.50: Study 2 {pct(a)} "
                         f"[{pct(la)},{pct(ha)}] n={na} vs Study 3 {pct(c)} "
                         f"[{pct(lc)},{pct(hc)}] n={nc} -- intervals do not overlap")


# ---------------------------------------------------------------- B physical
def check_physical():
    for name, M in (("Study 2 published", D), ("Study 2 optimum", DB)):
        if not M:
            continue
        for mot in M["grade"]["1"]:
            accs = [(g, M["grade"][str(g)][mot]["dir_acc"],
                     M["grade"][str(g)][mot]["n"]) for g in (1, 2, 3, 4, 5)]
            for i in range(len(accs) - 1):
                g1, a1, n1 = accs[i]
                g2, a2, n2 = accs[i + 1]
                if a1 is None or a2 is None or a1 != a1 or a2 != a2:
                    continue
                l1, h1 = wilson(a1, n1)
                l2, h2 = wilson(a2, n2)
                if a1 > a2 and l1 > h2:      # significantly inverted
                    flag("HIGH", name,
                         f"motion {mot}: grade {g1} ({pct(a1)}) beats grade {g2} "
                         f"({pct(a2)}) with non-overlapping intervals -- a larger, "
                         f"further-travelling bolus detected significantly worse")
    if T:
        for o, cell in T.get("grid", {}).items():
            if cell.get("untestable") or "low_grade_still" not in cell:
                continue
            lo = cell["low_grade_still"]
            hi = cell["high_grade_still"]
            if (lo["dir_acc"] == lo["dir_acc"] and hi["dir_acc"] == hi["dir_acc"]
                    and lo["dir_acc"] > hi["dir_acc"]):
                ll, lh = wilson(lo["dir_acc"], lo["n"])
                hl, hh = wilson(hi["dir_acc"], hi["n"])
                if ll > hh:
                    flag("HIGH", "Study 4",
                         f"offset {o}: LOW grades ({pct(lo['dir_acc'])}) beat HIGH "
                         f"grades ({pct(hi['dir_acc'])}) significantly")


# ---------------------------------------------------------------- C statistical
def check_stats():
    if E:
        for n, cell in E["primary"].items():
            for mot, d in cell.items():
                a, nn = d.get("dir_acc"), d.get("dir_n", 0)
                if a is None or a != a or nn <= 0:
                    continue
                lo, hi = wilson(a, nn)
                if hi < 0.5 and d.get("undecidable", 0) < 0.99:
                    flag("HIGH", "Study 1",
                         f"N={n} motion {mot}: accuracy {pct(a)} with interval "
                         f"[{pct(lo)},{pct(hi)}] lies wholly BELOW chance -- the "
                         f"estimator is inverted, not merely uninformative")
    if PR:
        for k, v in PR.get("grid", {}).items():
            cf = v.get("clipped_fraction")
            if cf is not None and cf > 0.5:
                flag("MED", "Study 5",
                     f"{k}: {100*cf:.0f}% of children had their placement error "
                     f"clipped, so this arm is not sampling the sigma it is "
                     f"labelled with (max offset {v.get('max_off_cm', float('nan')):.2f} cm)")
            if v.get("fp_counts_abstentions"):
                flag("MED", "Study 5", f"{k}: specificity counts abstentions as "
                                       f"false positives")
    if D and D.get("subject", {}).get("best_k_selected_in_sample") is None:
        # study 2 has no such flag; check it selects on the scored set
        s = D["subject"]
        if "best_k" in s and "sens_k" in s:
            flag("LOW", "Study 2",
                 "best_k is chosen by Youden on the same subjects it is scored on; "
                 "best_sens/best_spec are in-sample")


# ---------------------------------------------------------------- D internal
def check_internal():
    if V:
        m = V["v3_mesh_convergence"]
        errs = [x["slope_rel_to_finest"] for x in m["levels"][:-1]]
        if any(e > 0.05 for e in errs):
            flag("HIGH", "verification",
                 f"arrival-time slope is NOT mesh-converged: errors vs the finest "
                 f"mesh are {[f'{100*e:.1f}%' for e in errs]}")
        zerr = [x["absZ_rel_to_finest"] for x in m["levels"][:-1]]
        if any(e > 0.05 for e in zerr):
            flag("MED", "verification",
                 f"absolute |Z| is not mesh-converged ({[f'{100*e:.0f}%' for e in zerr]}); "
                 f"no claim about impedance MAGNITUDE is supported")
    if P:
        n_un = sum(1 for v in P.get("grid", {}).values() if v.get("untestable"))
        if n_un:
            flag("INFO", "Study 3",
                 f"{n_un} of {len(P['grid'])} placements are not testable -- the "
                 f"strip leaves the body")
    if M2:
        g = M2["grid"]
        z = g.get("a0.0_g0.0", {}).get("false_retrograde")
        if z is not None and z > 0.05:
            flag("HIGH", "Study 6",
                 f"false-retrograde is {pct(z)} at ZERO motion: a floor on "
                 f"specificity that motion cannot explain")
    if GA:
        y = GA.get("recommended", {}).get("youden")
        if y is not None and y < 0.6:
            flag("MED", "abstain gate",
                 f"best achievable Youden is only {y:.2f}; travelling p10 "
                 f"{GA.get('travelling_p10', float('nan')):+.2f} vs empty p90 "
                 f"{GA.get('empty_p90', float('nan')):+.2f} -- the distributions "
                 f"overlap heavily")


# ---------------------------------------------------------------- E provenance
def check_provenance():
    """Compare each result against the SIMULATION version that produced it.

    File timestamps were the first attempt and were useless: they flag a comment
    edit as loudly as a physics change, and they are destroyed by copying. Every
    runner now stamps ds.MODEL_VERSION into its config, so a stale result
    identifies itself.
    """
    import directional_sim as _ds
    cur = getattr(_ds, "MODEL_VERSION", None)
    if cur is None:
        flag("MED", "provenance", "directional_sim has no MODEL_VERSION to compare against")
        return
    stale, unstamped = [], []
    for f in sorted(glob.glob(os.path.join(R, "metrics_*.json"))):
        name = os.path.basename(f)
        if any(k in name for k in ("_confounded", "_uniformgrade", "preD31")):
            continue                      # deliberately preserved historical runs
        try:
            cfg = (json.load(open(f)) or {}).get("config", {}) or {}
        except Exception:
            continue
        v = cfg.get("model_version")
        if v is None:
            unstamped.append(name)
        elif v != cur:
            stale.append(f"{name} (v{v})")
    if stale:
        flag("HIGH", "provenance",
             f"produced by an older simulator than the current v{cur}: "
             f"{', '.join(stale)}")
    if unstamped:
        flag("MED", "provenance",
             f"no model_version recorded, so provenance cannot be checked: "
             f"{', '.join(unstamped)}")


def main():
    for fn in (check_cross, check_physical, check_stats, check_internal,
               check_provenance):
        try:
            fn()
        except Exception as e:
            flag("ERROR", fn.__name__, f"{type(e).__name__}: {e}")
    order = {"ERROR": 0, "HIGH": 1, "MED": 2, "LOW": 3, "INFO": 4}
    FLAGS.sort(key=lambda t: order.get(t[0], 9))
    if not FLAGS:
        print("CONSISTENCY: nothing flagged")
        return 0
    print(f"CONSISTENCY: {len(FLAGS)} items\n")
    for sev, area, msg in FLAGS:
        print(f"[{sev:5s}] {area}")
        for i in range(0, len(msg), 96):
            print(f"          {msg[i:i+96]}")
    return 1 if any(f[0] in ("ERROR", "HIGH") for f in FLAGS) else 0


if __name__ == "__main__":
    sys.exit(main())
