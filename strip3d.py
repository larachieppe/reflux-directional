"""
Directional bioimpedance forward model: two longitudinal tetrapolar electrode
strips (one per flank) on a 3-D torso segment, built on the CEM solver in
eit3d.py.

The design question this file exists to answer is NOT "what does the conductivity
field look like" (tomography) but "which way did the conductive bolus travel".
Direction is recovered from the ORDERING of zone arrival times along the strip,
so the geometry is a short vertical strip, not a circumferential ring.

Zone = 4 consecutive electrodes on one strip, Wenner-style:
    outer pair  -> inject current I
    inner pair  -> sense voltage  V
    transfer impedance Z = V / I     (contact impedance largely rejected)

A strip of N electrodes yields N-3 sliding zones. Hence:
    N = 4 -> 1 zone  -> NO lag is definable: direction is structurally unavailable
    N = 5 -> 2 zones -> a lag exists, but zones share 3 of 4 electrodes
    N = 6 -> 3 zones -> a lag AND a 3-point arrival-time slope (wave linearity)
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
    lateral = rad > 0.80 * R
    elecs, cents = [], []
    dz = span / max(n_per_strip - 1, 1)
    # The z acceptance window must scale with pitch. A fixed 0.6 cm half-height
    # exceeded the half-pitch once N reached 12 on a 12 cm span, so adjacent
    # electrodes claimed the SAME boundary facets and were welded together in the
    # CEM assembly (44 shared facets measured at N=12). Two physical electrodes
    # cannot occupy one patch of skin, so that array was not realizable.
    half = 0.40 * dz if band is None else band * height
    z0 = z_center * height - span / 2.0
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
    """Multi-aperture sliding Wenner zones.

    A zone uses electrodes (k, k+m, k+2m, k+3m): drive on the outer pair, sense
    on the inner pair. The aperture multiple m matters because tetrapolar sensing
    DEPTH scales with electrode separation, so a dense strip is not restricted to
    shallow adjacent windows: it can synthesize wide (deep) apertures in software.
    This is the real benefit of more electrodes and it is why the sweep must allow
    every aperture rather than only m=1.

    Zone count per strip = sum over m of (N - 3m), which grows with N while the
    deepest available aperture stays reachable.
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
