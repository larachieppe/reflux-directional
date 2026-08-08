"""
Directional bioimpedance forward model: two longitudinal tetrapolar electrode
strips (one per flank) on a 3-D torso segment, built on the CEM solver in
eit3d.py.

The design question this file exists to answer is NOT "what does the conductivity
field look like" (tomography) but "which way did the conductive bolus travel".
Direction is recovered from the ORDERING of zone arrival times along the strip,
so the geometry is a short vertical strip, not a circumferential ring.

Zone = 4 electrodes on one strip in a SCHLUMBERGER arrangement (see defect 50;
this said "Wenner-style", which the code does not implement):
    outer pair (k, k+G)          -> inject current I,  G an odd number of pitches
    inner adjacent pair          -> sense voltage V,   always ONE pitch wide
    transfer impedance Z = V / I
Contact impedance is reduced but NOT rejected: measured tetrapolar rejection over
the modelled z0 range is 4.3x, a 16% residual (defect 18).

A strip of N electrodes yields sum over odd G in [3, N) of (N - G) zones, summed
over all apertures -- not N-3, which counts only the narrowest. At the narrowest
aperture G=3 alone:
    N = 4 -> 1 zone  -> NO lag is definable: direction is structurally unavailable
    N = 5 -> 2 zones -> a lag exists, but zones share 3 of 4 electrodes
    N = 6 -> 3 zones -> a lag AND a 3-point arrival-time slope (wave linearity)
Totals across apertures are larger: N=8 gives 9 zones per strip, not 5.
"""
import numpy as np
import eit3d


def place_strips(mesh, R, height, n_per_strip, span, z_center=0.5,
                 strip_phis=(0.0, np.pi), arc_half=0.30, band=None, xscale=1.0):
    """N electrodes per strip, equally spaced over a FIXED span (cm), at constant
    angle, varying z. Fixing the span and varying N is the honest engineering
    question: given the flank length anatomy allows, how densely populate it?"""
    bf = mesh.boundary_facets()
    fc = mesh.p[:, mesh.facets[:, bf]].mean(axis=1)
    x, y, z = fc[0] / xscale, fc[1], fc[2]
    rad = np.hypot(x, y)
    ang = np.arctan2(y, x) % (2 * np.pi)
    # DEFECT 51, FIXED. `rad > 0.80*R` admits END-CAP facets: a triangle on the
    # z=0 or z=height disc at radius above 0.8R passes the radial test even
    # though it faces along the axis, not outward. An electrode landing there is
    # not a flank patch at all. Nothing checked that the requested strip even
    # fits inside [0, height], so the -2 cm arm of the tolerance study pushed its
    # bottom electrode onto the inferior cap -- which is the most likely reason
    # that arm inverts the grade ordering (grade V worst of all five). Require a
    # genuinely lateral facet by its NORMAL, not merely its radius.
    zlo, zhi = float(z.min()), float(z.max())
    on_cap = (np.abs(z - zlo) < 1e-9) | (np.abs(z - zhi) < 1e-9)
    lateral = (rad > 0.80 * R) & (~on_cap)
    elecs, cents = [], []
    dz = span / max(n_per_strip - 1, 1)
    # The z acceptance window must scale with pitch. A fixed 0.6 cm half-height
    # exceeded the half-pitch once N reached 12 on a 12 cm span, so adjacent
    # electrodes claimed the SAME boundary facets and were welded together in the
    # CEM assembly (44 shared facets measured at N=12). Two physical electrodes
    # cannot occupy one patch of skin, so that array was not realizable.
    half = 0.40 * dz if band is None else band * height
    z0 = z_center * height - span / 2.0
    # Fail loudly if the requested strip runs off the body. Silently
    # accepting it is how the -2 cm tolerance arm ended up with an
    # electrode on the end cap (defect 51).
    if z0 - half < -1e-9 or z0 + span + half > height + 1e-9:
        raise ValueError(
            f"place_strips: strip spans [{z0 - half:.2f}, "
            f"{z0 + span + half:.2f}] cm which leaves the body "
            f"[0, {height:.2f}] -- span={span}, z_center={z_center}")
    for phi in strip_phis:
        for k in range(n_per_strip):
            zabs = z0 + k * dz
            da = np.angle(np.exp(1j * (ang - phi)))
            sel = lateral & (np.abs(da) < arc_half) & (np.abs(z - zabs) < half)
            if sel.sum() == 0:
                sel = lateral & (np.abs(da) < arc_half * 1.7) & (np.abs(z - zabs) < half * 1.8)
            if sel.sum() == 0:                       # last resort: nearest facet
                d2 = (np.angle(np.exp(1j * (ang - phi))))**2 + ((z - zabs) / height)**2
                d2[~lateral] = 1e9
                sel = np.zeros_like(lateral); sel[np.argmin(d2)] = True
            elecs.append(bf[sel])
            cents.append([R * np.cos(phi), R * np.sin(phi), zabs])
    # Reject any layout whose electrodes physically overlap, rather than silently
    # producing a shorted array.
    seen = {}
    for i, f in enumerate(elecs):
        for fac in f.tolist():
            if fac in seen:
                raise ValueError(
                    f"electrodes {seen[fac]} and {i} share boundary facet {fac}: "
                    f"N={n_per_strip}, span={span} produces physically "
                    f"overlapping electrodes (pitch {dz:.2f} cm)")
            seen[fac] = i
    return elecs, np.array(cents)


def tetrapolar_zones(n_per_strip, n_strips=2, max_m=None):
    """Multi-aperture sliding SCHLUMBERGER zones.

    DEFECT 50, FIXED (documentation). This docstring described a Wenner array,
    "electrodes (k, k+m, k+2m, k+3m)" with equal spacing, and gave the zone count
    as sum over m of (N - 3m). The code implements neither. It builds a
    SCHLUMBERGER array: drive on (k, k+G) for odd outer gaps G, sense on the
    single adjacent inner pair (k+c, k+c+1) where c = (G-1)//2. The sense dipole
    is therefore ONE pitch wide at every aperture, not G/3 as Wenner would give,
    and the count per strip is sum over odd G of (N - G). At N=8 the true count
    is (8-3)+(8-5)+(8-7) = 9; the docstring formula gives (8-3)+(8-6) = 7, off by
    two.

    The distinction is not cosmetic. Wenner and Schlumberger have different depth
    sensitivities and different signal magnitudes for the same footprint, so
    anyone sizing depth reach from the docstring geometry would get the wrong
    answer. The depth-scales-with-separation argument still holds -- it is the
    DRIVE separation G that sets penetration -- but the array is Schlumberger,
    whose fixed narrow sense dipole is exactly why the deep apertures stay usable
    on a short strip.
    """
    zones = []
    gaps = [G for G in range(3, n_per_strip, 2)]     # odd outer gaps
    if max_m is not None:
        gaps = gaps[:max_m]
    for s in range(n_strips):
        base = s * n_per_strip
        for G in gaps:
            c = (G - 1) // 2                        # inner sense pair offset
            for k in range(n_per_strip - G):
                zones.append({
                    "strip": s,
                    "m": G,                          # outer gap in electrode pitches
                    "drive": (base + k, base + k + G),
                    "sense": (base + k + c, base + k + c + 1),
                    "kpos": k + G / 2.0,
                })
    return zones


def measure_zones(solver, sigma, zc, zones, amp=1.0):
    """Complex transfer impedance Z = V/I for every tetrapolar zone.
    One factorization is shared across all drives in the frame."""
    drives = [z["drive"] for z in zones]
    Us = solver.solve_drives(sigma, zc, drives, amp)
    out = np.empty(len(zones), complex)
    for i, zd in enumerate(zones):
        p, q = zd["sense"]
        out[i] = (Us[i][p] - Us[i][q]) / amp
    return out
