"""
Directional bioimpedance simulation for VUR detection (Arena, formulation 2).

WHAT CHANGED vs the tomographic version
---------------------------------------
The measured quantity is no longer a reconstructed conductivity image, it is the
DIRECTION of travel of a conductive bolus along the ureter axis, recovered from
the ordering of arrival times across tetrapolar zones on a short flank strip.
Two strips (one per flank) give laterality natively.

WHY THIS IS THE RIGHT EXPERIMENT
--------------------------------
The prior clinical program (Kite Medical) reported detection in 73% of cycles
without motion but only 44% with motion. Motion, not raw sensitivity, is what
killed it. So the PRIMARY endpoint here is direction accuracy as a function of
injected motion amplitude, and the motion model is common-mode by construction
(the body shifts relative to the electrodes) so that the common-mode rejection
claim is TESTED rather than assumed.

ELECTRODE-COUNT SWEEP
---------------------
The flank span is fixed (anatomy caps it); N electrodes are distributed over it.
More electrodes buy more zones but shrink the spacing, and tetrapolar sensing
depth scales with spacing. The optimum is therefore INTERIOR, and finding it is
the point of this study: maximize functionality, minimize complexity.

HONESTY
-------
Representative literature admittivities (Gabriel/IT'IS family), structured (not
segmented-CT) anatomy, and an assumed SNR budget. Establishes a feasibility and
robustness envelope, not clinical performance.
"""
import numpy as np
import eit3d
import strip3d

EPS0 = 8.8541878128e-12
FREQS = np.array([50e3, 100e3])

TISSUE = {
    "muscle":  (0.34, 2.6e4),
    "fat":     (0.043, 1.5e3),
    "kidney":  (0.11, 3.0e4),
    "bladder": (0.30, 4.0e3),   # wall only; the lumen is urine (see base_sigma)
    "urine":   (1.70, 80.0),
}

# grade -> (bolus semi-axis fraction of R, retrograde reach fraction of ureter)
GRADE_TABLE = {1: (0.10, 0.20), 2: (0.14, 0.38), 3: (0.19, 0.62),
               4: (0.24, 0.84), 5: (0.30, 1.00)}
GRADE_WEIGHTS = {1: 0.30, 2: 0.30, 3: 0.22, 4: 0.13, 5: 0.05}
CLASSES = ["noflow", "antegrade", "bladder", "reflux"]


def admittivity(name, f):
    s0, er0 = TISSUE[name]
    s = s0 * (1.0 + 0.04 * np.log10(f / 50e3))
    er = er0 * (50e3 / f) ** 0.10
    return s + 1j * (2 * np.pi * f) * EPS0 * er


def sample_grade(rng):
    g = list(GRADE_WEIGHTS)
    w = np.array(list(GRADE_WEIGHTS.values()))
    return int(rng.choice(g, p=w / w.sum()))


class StripWorld:
    """Torso segment + two flank strips of n_per_strip electrodes over a FIXED
    span. The mesh is shared across electrode counts (built once by the caller
    via `mesh=`), only the electrode set and CEM solver differ."""

    def __init__(self, n_per_strip, span=12.0, R=5.5, height=20.0,
                 n_rings=6, nz=17, xscale=1.0, mesh=None, name="train",
                 z_center=0.5):
        self.name = name
        self.R, self.H, self.xscale = R, height, xscale
        self.n_per_strip = n_per_strip
        self.span = span
        self.spacing = span / max(n_per_strip - 1, 1)
        self.mesh = mesh if mesh is not None else eit3d.make_cylinder(
            R=R, height=height, n_rings=n_rings, nz=nz, xscale=xscale)
        # z_center was previously never forwarded, so every strip in every study
        # sat on the torso MIDPOINT rather than over the ureterovesical junction
        # where low-grade reflux actually occurs. That single unswept default is
        # what made grades I-II look undetectable.
        self.z_center = z_center
        self.elec_facets, self.elec_cent = strip3d.place_strips(
            self.mesh, R, height, n_per_strip, span, z_center=z_center,
            xscale=xscale)
        self.L = len(self.elec_facets)
        self.solver = eit3d.CEM3D(self.mesh, self.elec_facets)
        self.zones = strip3d.tetrapolar_zones(n_per_strip, 2)
        _g = [G for G in range(3, n_per_strip, 2)]
        self.n_zones_per_strip = sum(n_per_strip - G for G in _g)
        self.max_aperture_cm = (max(_g) * self.spacing) if _g else 0.0
        # zone centroid z (cm) for arrival-time slope fitting
        # Use the REALIZED facet centroids, not the requested positions. Facets
        # snap to the mesh, so realized pitch differs from nominal (measured 2.50
        # to 3.14 cm against a nominal 2.80). zone_z is the regressor x-axis for
        # the headline slope fit, so using requested positions injects error.
        ez = np.array([self.mesh.p[:, self.mesh.facets[:, f]].mean(axis=(1, 2))[2]
                       if len(f) else self.elec_cent[i, 2]
                       for i, f in enumerate(self.elec_facets)])
        self.elec_z_realized = ez
        self.zone_z = np.array([0.5 * (ez[z["sense"][0]] + ez[z["sense"][1]])
                                for z in self.zones])
        self.zone_strip = np.array([z["strip"] for z in self.zones])
        self.zone_m = np.array([z["m"] for z in self.zones])
        self.apertures = sorted(set(self.zone_m.tolist()))
        self.cent = self.mesh.p[:, self.mesh.t].mean(axis=1).T
        self.cent[:, 0] /= xscale
        # bilateral ureters at x = +/- 0.45R ; bladder low+central ; kidneys high
        self.ur_x = 0.45 * R
        self.z_bladder = 0.20 * height
        self.z_kidney = 0.80 * height

    # ---------------- conductivity map ----------------
    def base_sigma(self, f, anat, shift=(0.0, 0.0, 0.0)):
        x = self.cent[:, 0] - shift[0]
        y = self.cent[:, 1] - shift[1]
        z = self.cent[:, 2] - shift[2]
        r = np.hypot(x, y)
        sig = np.full(self.cent.shape[0], admittivity("muscle", f), complex)
        sig[r > 0.82 * self.R] = admittivity("fat", f)
        for sgn in (+1, -1):
            kx = sgn * anat["ur_x"] + anat["k_off"][0]
            ky = anat["k_off"][1]
            kz = anat["z_kidney"]
            kd = ((x - kx) / anat["k_r"][0])**2 + ((y - ky) / anat["k_r"][1])**2 \
                 + ((z - kz) / anat["k_r"][2])**2
            sig[kd < 1] = admittivity("kidney", f)
        # The bladder is a thin WALL around a URINE lumen. Filling the whole
        # ellipsoid with wall conductivity (0.30 S/m, below muscle at 0.34) made
        # the bladder-fill confounder ~14x too weak AND inverted in sign, so the
        # one confounder the whole design premise rests on was never actually
        # confounding.
        bx, by, bz = anat["bladder"]
        br = anat["b_r"]
        bd = ((x - bx) / br[0])**2 + ((y - by) / br[1])**2 + ((z - bz) / br[2])**2
        sig[bd < 1] = admittivity("bladder", f)          # wall
        wall = 0.82                                       # lumen fraction
        ld = ((x - bx) / (br[0]*wall))**2 + ((y - by) / (br[1]*wall))**2 \
             + ((z - bz) / (br[2]*wall))**2
        sig[ld < 1] = admittivity("urine", f)             # lumen
        return sig

    def add_bolus(self, sig, f, center, radii, shift=(0.0, 0.0, 0.0), frac=1.0):
        x = self.cent[:, 0] - shift[0]
        y = self.cent[:, 1] - shift[1]
        z = self.cent[:, 2] - shift[2]
        d = ((x - center[0]) / radii[0])**2 + ((y - center[1]) / radii[1])**2 \
            + ((z - center[2]) / radii[2])**2
        m = d < 1.0
        out = sig.copy()
        out[m] = (1 - frac) * out[m] + frac * admittivity("urine", f)
        return out


def draw_anatomy(world, rng):
    R, H = world.R, world.H
    return {
        "ur_x":      world.ur_x * rng.uniform(0.92, 1.08),
        "k_off":     (rng.normal(0, 0.04 * R), rng.normal(0, 0.04 * R)),
        "z_kidney":  world.z_kidney + rng.normal(0, 0.03 * H),
        "k_r":       (0.20 * R, 0.26 * R, 0.11 * H),
        "bladder":   (rng.normal(0, 0.05 * R), rng.normal(0, 0.05 * R),
                      world.z_bladder + rng.normal(0, 0.03 * H)),
        "b_r":       [0.30 * R, 0.30 * R, 0.12 * H],
    }


def draw_motion(world, rng, T, motion_amp):
    """Common-mode body displacement relative to the electrodes, plus breathing.
    This is COMMON across every zone and both strips, which is exactly the
    perturbation a differential inter-zone lag should reject. Returns (T,3) cm."""
    t = np.arange(T)
    # smooth random walk (posture / gross movement)
    steps = rng.normal(0, 1.0, size=(T, 3))
    walk = np.cumsum(steps, axis=0)
    walk -= walk.mean(axis=0)
    walk /= max(np.abs(walk).max(), 1e-9)
    # breathing: mostly superior-inferior + a little anterior-posterior
    ph = rng.uniform(0, 2 * np.pi)
    breath = np.zeros((T, 3))
    breath[:, 2] = np.sin(2 * np.pi * 0.30 * t / 4.0 + ph)
    breath[:, 1] = 0.35 * np.sin(2 * np.pi * 0.30 * t / 4.0 + ph + 0.6)
    disp = motion_amp * (0.65 * walk + 0.35 * breath)
    return disp


def draw_contact_z(world, rng, T, motion_amp):
    """Per-electrode contact impedance: slow drift + breathing, plus a
    motion-scaled INDEPENDENT component that does not cancel.

    Scale matters and was got wrong once already. In the CEM the meaningful
    quantity is the dimensionless group z*sigma/L. With sigma ~ 0.34 and a mesh
    in cm, that group reaches unity near z ~ 3, and real skin-electrode impedance
    is comparable to or larger than the tissue spreading resistance, so z0 of
    order 5-20 is the physical regime. Values ~100x smaller make the electrodes
    near-ideal shunts: they short out the surface potential (suppressing the
    bolus signal ~100x) while MAXIMISING sensitivity to contact drift, which is
    the opposite of how four-wire sensing behaves.
    """
    z0 = rng.uniform(5.0, 20.0, size=world.L)
    t = np.arange(T)
    breath = 0.03 * np.sin(2 * np.pi * 0.30 * t / 4.0 + rng.uniform(0, 6.28))
    drift = np.linspace(0, rng.normal(0, 0.03), T)
    phase = rng.uniform(0, 6.28, size=world.L)
    mod = 1.0 + (breath[:, None] + drift[:, None]) * (0.5 + 0.5 * np.cos(phase)[None, :])
    indep = 1.0 + (0.03 * motion_amp) * rng.normal(0, 1.0, size=(T, world.L))
    return z0[None, :] * np.clip(mod * indep, 0.7, 1.4)


def bolus_path(world, anat, label, grade, side, T):
    """Return (T,3) bolus centres and (T,) presence fraction.

    The bolus is a slug of urine of ESSENTIALLY CONSTANT volume that MOVES. It is
    deliberately not modulated by a rise/fall envelope: an envelope imposes the
    same time course on every zone, which makes the response separable as
    (amplitude per zone) x (one shared envelope). Separable responses have no
    meaningful relative lag, so an envelope would erase the very travelling-wave
    signature the device is built to read. The bolus instead starts outside the
    sensed span and exits the far side, so each zone lights up as it passes.
    """
    H = world.H
    z_b, z_k = anat["bladder"][2], anat["z_kidney"]
    ux = side * anat["ur_x"]
    reach = GRADE_TABLE[grade][1]
    margin = 0.12 * H                       # start/end clear of the sensed span
    cs = np.zeros((T, 3))
    frac = np.zeros(T)
    tt = np.linspace(0.0, 1.0, T)
    if label == "reflux":                   # bladder -> kidney (retrograde, up)
        z0 = z_b - margin
        z1 = z_b + (z_k - z_b) * reach + margin
        zs = z0 + (z1 - z0) * tt
        frac[:] = 1.0
    elif label == "antegrade":              # kidney -> bladder (normal, down)
        z1 = z_b - margin
        z0 = z_k + margin
        zs = z0 + (z1 - z0) * tt
        frac[:] = 1.0
    else:
        zs = np.full(T, 0.5 * (z_b + z_k))
    cs[:, 0] = ux
    cs[:, 1] = 0.0
    cs[:, 2] = zs
    return cs, frac


def simulate_trial(world, label, rng, grade=3, side=+1, T=16, freqs=FREQS,
                   snr_db=60.0, motion_amp=0.0, amp=1.0, anat=None):
    """Return Z tensor (T, F, n_zones) complex, baseline-subtracted + noisy.

    `anat` may be supplied to hold the body and electrode placement FIXED across
    several events on the same subject. That distinction matters: the multi-event
    argument for beating VCUG assumes repeated events are independent, and they
    are only independent to the extent that anatomy and placement are not the
    thing limiting the measurement. Passing a fixed anat lets that assumption be
    tested rather than asserted.
    """
    if anat is None:
        anat = draw_anatomy(world, rng)
    disp = draw_motion(world, rng, T, motion_amp)
    zc_t = draw_contact_z(world, rng, T, motion_amp)
    cs, frac = bolus_path(world, anat, label, grade, side, T)
    br = GRADE_TABLE[grade][0] * world.R
    radii = (br, br, 1.15 * br)

    Z = np.zeros((T, len(freqs), len(world.zones)), complex)
    for ti in range(T):
        anat_t = dict(anat)
        if label == "bladder":               # confounder: bladder grows over time
            g = 1.0 + 0.45 * (ti / max(T - 1, 1))
            anat_t["b_r"] = [anat["b_r"][0] * g, anat["b_r"][1] * g,
                             anat["b_r"][2] * g]
        for fi, f in enumerate(freqs):
            sig = world.base_sigma(f, anat_t, shift=disp[ti])
            if label in ("reflux", "antegrade") and frac[ti] > 1e-3:
                sig = world.add_bolus(sig, f, cs[ti], radii, shift=disp[ti],
                                      frac=float(frac[ti]))
            Z[ti, fi] = strip3d.measure_zones(world.solver, sig, zc_t[ti],
                                              world.zones, amp)
    # Baseline: a RESTING reference from before the bolus enters the sensed span
    # (first frames), which is what a real device subtracts. The temporal MEDIAN
    # is wrong here: the bolus sweeps past every zone, so the median sits
    # mid-event, and subtracting it turns each clean unipolar passage into a
    # scrambled bipolar trace and destroys the arrival ordering entirely.
    base = Z[:2].mean(axis=0, keepdims=True)
    # Normalize to a FRACTIONAL change (dZ/|Z|). Absolute dZ carries each zone's
    # standing impedance as a gain factor, and those gains are not equal: the
    # mesh's interior node ring has an odd count, so the two flank strips do not
    # receive mirror-image electrode area (~23% less on one side, 25-57% higher
    # |Z|). With absolute dZ the strip selector saw ~7x more "energy" on the
    # smaller-area strip WITH NO BOLUS PRESENT, making laterality a degenerate
    # always-one-side predictor. Fractional change is also what real hardware
    # reports after per-channel calibration.
    dZ = (Z - base) / np.abs(base)
    # dZ is a FRACTIONAL change, so the noise must be fractional too. Deriving
    # sigma from the raw |Z| and adding it to a normalized quantity made the
    # injected noise depend on the choice of length unit and sat ~10 dB below
    # the stated SNR.
    sigma_n = 10 ** (-snr_db / 20.0)
    noise = (rng.normal(0, sigma_n, dZ.shape) + 1j * rng.normal(0, sigma_n, dZ.shape))
    corr = (rng.normal(0, sigma_n, (T, len(freqs), 1))
            + 1j * rng.normal(0, sigma_n, (T, len(freqs), 1)))
    return dZ + noise + 0.5 * corr


# --------------------------------------------------------------------------
# Direction estimation
# --------------------------------------------------------------------------
def _norm(a):
    a = a - a.mean()
    s = a.std()
    return a / s if s > 1e-12 else a


def xcorr_lag(a, b, max_lag=None, upsample=8):
    """Lag (in samples, positive => b lags a) by parabolic-interpolated peak."""
    a, b = _norm(np.asarray(a, float)), _norm(np.asarray(b, float))
    n = len(a)
    if max_lag is None:
        # A bolus traversing the whole strip produces lags of order half the
        # window, so the bound must be generous or real signal gets clipped.
        max_lag = max(3, (2 * n) // 3)
    lags = np.arange(-max_lag, max_lag + 1)
    # BIASED estimator: divide by n, not by the overlap (n - |L|). Dividing by
    # the overlap inflates correlations at large |L| where only a few samples
    # overlap, which is how noise wins at the extremes. The biased form tapers
    # naturally with |L| and is the standard choice for lag estimation.
    c = np.array([np.dot(a[max(0, -L):n - max(0, L)],
                         b[max(0, L):n - max(0, -L)]) / n
                  for L in lags])
    k = int(np.argmax(c))
    if 0 < k < len(c) - 1:                  # parabolic refinement
        y0, y1, y2 = c[k - 1], c[k], c[k + 1]
        d = y0 - 2 * y1 + y2
        off = 0.5 * (y0 - y2) / d if abs(d) > 1e-12 else 0.0
        return float(lags[k] + off), float(c[k])
    return float(lags[k]), float(c[k])


def zone_series(dZ, world, strip, m=None):
    """Per-zone time series for one strip (optionally one aperture).

    Uses the REAL part of the complex transfer impedance, not its magnitude.
    This matters: the perturbation is linear in the real part, so a common-mode
    term adds linearly and can be cancelled exactly by subtracting the across-zone
    mean. Taking |dZ| first is a nonlinearity that leaves a positive residual for
    every zone, which no amount of averaging removes, and which then dominates the
    cross-correlation. (A conductive bolus lowers impedance, so the excursion is
    negative; only its timing is used.)
    """
    sel = (world.zone_strip == strip)
    if m is not None:
        sel = sel & (world.zone_m == m)
    idx = np.where(sel)[0]
    if len(idx) == 0:
        return np.zeros((0, dZ.shape[0])), idx
    ser = dZ.real.mean(axis=1)                       # (T, n_zones), linear
    return ser[:, idx].T, idx


def _strip_aperture_stats(dZ, world, strip, m):
    """Direction statistics for one strip at one aperture multiple m."""
    ser, idx = zone_series(dZ, world, strip, m)
    nz = ser.shape[0]
    raw_e = float(np.sum(ser**2)) if nz else 0.0
    if nz < 2:
        return None
    zz = world.zone_z[idx]
    order = np.argsort(zz)
    ser, zz = ser[order], zz[order]
    # ---- common-mode rejection --------------------------------------------
    # ser[j,t] = c(t) + b(t - tau_j) + noise. c(t) is shared by every zone
    # (contact drift, breathing, correlated instrument noise, bulk body motion)
    # and contributes a cross-correlation peak at lag 0 that masks the travelling
    # term. Removing the across-zone mean suppresses c. This REQUIRES >= 3 zones:
    # with exactly 2 the mean-removed series are exact negatives and the lag is
    # destroyed, so a 2-zone aperture cannot reject common mode. That is a
    # structural property of the geometry, not a tuning choice.
    if nz >= 3:
        ser = ser - ser.mean(axis=0, keepdims=True)
    ser = ser - ser.mean(axis=1, keepdims=True)
    tarr = np.zeros(nz); peaks = np.zeros(nz)
    for j in range(nz):
        tarr[j], peaks[j] = xcorr_lag(ser[0], ser[j])
    dz = float(zz[-1] - zz[0])
    A = np.vstack([zz, np.ones_like(zz)]).T
    coef, *_ = np.linalg.lstsq(A, tarr, rcond=None)
    slope = float(coef[0])
    if nz >= 3:
        pred = A @ coef
        ss_res = float(((tarr - pred) ** 2).sum())
        ss_tot = float(((tarr - tarr.mean()) ** 2).sum())
        lin = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    else:
        lin = 0.0                              # 2 points are trivially collinear
    # Quality must be energy PER ZONE, not total. A shallow aperture has more
    # zones, so its total energy is larger even when each zone sees less signal;
    # selecting on the total would systematically pick the shallowest aperture,
    # which is exactly the one that cannot reach the ureter.
    per_zone = float(np.mean(np.sum(ser ** 2, axis=1)))
    z_baseline = float(zz[-1] - zz[0])          # lever arm available to the fit
    return dict(lag=float((tarr[-1] - tarr[0]) / max(dz, 1e-9)), slope=slope,
                lin=float(np.clip(lin, -1, 1)), peak=float(peaks.mean()),
                energy=raw_e, dif_energy=per_zone, z_baseline=z_baseline,
                n_zones=nz, m=m, defined=True)


def direction_features(dZ, world):
    """Direction evidence per strip, FUSED across apertures.

    The previous version picked a single aperture by per-zone energy. That was
    measurably wrong: forcing each aperture on identical data showed the greedy
    pick losing accuracy at every N >= 8 (N=8: 0.81 greedy vs 1.00 for the best
    fixed aperture; N=12: 0.81 vs 1.00), which is what produced the earlier
    "more electrodes is worse" result. That finding was an artifact of this
    selector, not physics.

    The reason is that slope precision scales with the LEVER ARM of the fit, the
    axial baseline spanned by the zone centroids, not with electrode separation.
    On a fixed span a wide aperture spends the very baseline the fit needs: at
    N=12 the widest aperture (9.8 cm) has a 2.2 cm baseline and scores 0.19,
    while the narrowest (3.3 cm) has an 8.7 cm baseline and scores 0.94.

    So instead of selecting, every aperture with >= 2 zones contributes, weighted
    by its baseline and its fit quality. Nothing is discarded and there is no
    selection step left to go wrong.

    Sign convention: POSITIVE => later arrival at LARGER z => travelling superior
    => retrograde => reflux.
    """
    out = {}
    for s_i in (0, 1):
        allser, _ = zone_series(dZ, world, s_i)
        raw_e = float(np.sum(allser ** 2)) if allser.shape[0] else 0.0
        cands = [c for c in (_strip_aperture_stats(dZ, world, s_i, m)
                             for m in world.apertures) if c is not None]
        if not cands:
            out[s_i] = dict(lag=0.0, slope=0.0, lin=0.0, peak=0.0, energy=raw_e,
                            dif_energy=0.0, n_zones=allser.shape[0], m=0,
                            n_apertures=0, defined=False)
            continue
        # weight: axial lever arm x fit quality x signal strength
        # Fuse lag and slope SEPARATELY. They are two independent estimators of
        # the same sign (end-to-end lag, and the least-squares arrival-time
        # slope); collapsing both to one fused scalar would emit duplicate
        # columns into the feature vector and distort the direction-only ablation.
        tot_w, lag_w, slope_w, lin_w, dif_e = 0.0, 0.0, 0.0, 0.0, 0.0
        for c in cands:
            base = max(c.get("z_baseline", 0.0), 1e-6)
            q = max(c["lin"], 0.0) if c["n_zones"] >= 3 else 0.35
            w = base * (0.25 + q) * np.sqrt(max(c["dif_energy"], 0.0))
            lag_w += w * c["lag"]
            slope_w += w * (c["slope"] if c["n_zones"] >= 3 else c["lag"])
            lin_w += w * c["lin"]
            dif_e += c["dif_energy"]
            tot_w += w
        if tot_w <= 0:
            best = max(cands, key=lambda c: c["dif_energy"])
            out[s_i] = dict(best, energy=raw_e, n_apertures=len(cands))
            continue
        best = max(cands, key=lambda c: c.get("z_baseline", 0.0) * max(c["lin"], 0.0))
        out[s_i] = dict(lag=lag_w / tot_w, slope=slope_w / tot_w,
                        lin=lin_w / tot_w, peak=best["peak"], energy=raw_e,
                        dif_energy=dif_e, n_zones=best["n_zones"], m=best["m"],
                        n_apertures=len(cands), defined=True,
                        fused_ev=(lag_w + slope_w) / tot_w)
    return out


# Calibrated, not guessed. Measured lin distributions at 0.45 cm motion:
# travelling events median ~0.95 (p10 0.40), empty windows median ~0.12-0.25.
# Youden-optimal threshold is 0.35, which keeps 96.4% of real events while
# rejecting 71.4% of empty ones. An earlier hand-picked 0.55 discarded 37.5% of
# genuine events, because the fused lin is a weighted average across apertures
# and sits lower than the single-aperture value that number was chosen against.
LIN_GATE = 0.35


def decide_direction(feat, lin_gate=LIN_GATE):
    """Return (+1 retrograde, -1 antegrade, 0 ABSTAIN) and the strip that fired.

    The abstain state is not optional. Without it an EMPTY window is forced to a
    call, and measured on no-flow windows the detector said "retrograde" 53.8% of
    the time. That silently made the published specificity conditional on every
    healthy window containing a full antegrade bolus. Wave linearity separates a
    real travelling event from an empty window cleanly (mean ~0.88 vs ~0.24), so
    it is used as the gate.
    """
    s = max((0, 1), key=lambda k: feat[k].get("dif_energy", 0.0)
            if feat[k]["defined"] else feat[k]["energy"])
    f = feat[s]
    if not f["defined"]:
        return 0, s, 0.0                       # N=4: structurally undecidable
    if f.get("n_zones", 0) >= 3 and f.get("lin", 0.0) < lin_gate:
        return 0, s, 0.0                       # no coherent travelling wave
    ev = f["lag"] + (f["slope"] if f["n_zones"] >= 3 else 0.0)
    return (1 if ev > 0 else -1), s, float(ev)


def feature_vector(dZ, world):
    """Flat feature vector for the classifier (direction + amplitude + shape)."""
    feat = direction_features(dZ, world)
    v = []
    for s in (0, 1):
        f = feat[s]
        v += [f["lag"], f["slope"], f["lin"], f["peak"], np.log1p(f["energy"]),
              np.log1p(f.get("dif_energy", 0.0))]
    a, b = feat[0], feat[1]
    v += [np.log1p(a["energy"]) - np.log1p(b["energy"]),
          a["lag"] - b["lag"],
          max(abs(a["lag"]), abs(b["lag"]))]
    return np.array(v, float), feat


FEATURE_NAMES = ([f"{side}_{k}" for side in ("R", "L")
                  for k in ("lag", "slope", "lin", "xcpeak", "log_energy",
                            "log_dif_energy")]
                 + ["energy_asym", "lag_asym", "abs_lag_max"])
