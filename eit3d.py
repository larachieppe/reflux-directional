"""
3-D Electrical Impedance forward model with the Complete Electrode Model (CEM),
built on scikit-fem. Geometry: a torso segment as an (elliptical) cylinder whose
axis is the body superior-inferior direction (z). Electrodes sit in one or two
transverse rings on the lateral surface; the ureter runs parallel to z, so a
refluxing bolus moves OUT of a single electrode plane, which is the whole point
of going 3-D (2-D EIT cannot see longitudinal transport).

CEM equations (Somersalo/Cheney):
    div(sigma grad u) = 0 in Omega
    u + z_l sigma du/dn = U_l on electrode E_l
    sigma du/dn = 0 off the electrodes
    int_{E_l} sigma du/dn dS = I_l
with sum(I_l)=0 and a grounding constraint sum(U_l)=0.

sigma may be complex (admittivity) for multi-frequency work.
"""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.spatial import Delaunay
from skfem import (MeshTet, Basis, ElementTetP1, ElementTetP0, FacetBasis,
                   BilinearForm, LinearForm, asm)
from skfem.helpers import dot, grad


# --------------------------------------------------------------------------
# Mesh: triangulate the 2-D disk ONCE, then extrude it into prisms and split
# each prism into three tetrahedra with a globally consistent rule.
#
# DEFECT 37, FIXED HERE. The previous version ran a 3-D Delaunay over the whole
# extruded point cloud and claimed that gave "a conforming tet mesh with no
# prism-split bookkeeping". It did not, and avoiding that bookkeeping is exactly
# what broke it.
#
# The cloud is structured: concentric rings repeated on nz identical z-planes, so
# it is massively cospherical. Qhull's Qt option triangulates those degenerate
# cells and emits thousands of exactly-flat tetrahedra (largest dropped volume
# measured at 3.7e-17). The old code then deleted them, commented as dropping
# "slivers ... for a clean stiffness matrix". They were not slivers -- the
# smallest KEPT volume was 0.1516 against a mean of 0.1744, so the mesh contained
# no slivers at all. Those flat tets were the only thing gluing together the two
# sides of each degenerate planar cell: the tets above used one diagonal, the
# tets below the other. Deleting the connector left both sides with faces having
# no matching partner.
#
# Measured on the production mesh (R=5.5, height=20, n_rings=6, nz=17):
#   10848 tets, 26344 distinct faces, 9296 with exactly ONE neighbouring tet
#   kept volume 1892.0148152770 vs the analytic 38-gon prism 1892.0148152770,
#   relative difference 0.0e+00 -- so the tets tile the solid with zero void and
#   zero overlap, and yet 7628 of those 9296 faces (82%) are strictly interior
#   (centroid radius 0.306-5.194 cm against a 5.481 cm apothem).
# Those are hanging faces. The P1 traces agree only at shared vertices, so the
# space was not H1-conforming: the solve was not a Galerkin solution of the CEM
# problem and refinement did not control the error. That is the most likely
# cause of the absolute |Z| non-convergence recorded in the report (11-76%,
# oscillating) and previously filed as an accepted limitation.
#
# It also corrupted boundary_facets(), which is just `f2t[1] == -1`, so ~63% of
# every electrode's area was interior tissue rather than skin (defect 38).
#
# The fix is the bookkeeping the comment boasted of skipping. A prism split into
# three tets is conforming across a shared vertical quad face if and only if the
# neighbouring prisms choose the SAME diagonal on it. Ordering each base triangle
# by global vertex index makes that choice depend only on the two node ids
# involved, which both neighbours agree on by construction.
# --------------------------------------------------------------------------
def _disk_points(R, n_rings, xscale=1.0):
    pts = [(0.0, 0.0)]
    for i in range(1, n_rings + 1):
        r = R * i / n_rings
        m = max(6, int(round(2 * np.pi * r / (R / n_rings))))
        for k in range(m):
            a = 2 * np.pi * k / m
            pts.append((xscale * r * np.cos(a), r * np.sin(a)))
    return np.array(pts)


def make_cylinder(R=5.5, height=14.0, n_rings=7, nz=17, xscale=1.0, check=True):
    """Return a CONFORMING skfem MeshTet for an (elliptical) cylinder, axis = z.

    The 2-D disk is triangulated once. Each triangle is extruded through every
    z-layer as a prism, and each prism is cut into three tets by the canonical
    sorted-index rule, which guarantees neighbouring prisms pick the same
    diagonal on their shared quad face.

    With `check`, the result is verified: every interior face must have exactly
    two neighbouring tets, and the volume must match the extruded 2-D area. A
    silent non-conforming mesh is what defect 37 was, so it is now an exception.
    """
    d = _disk_points(R, n_rings, xscale)
    nd = len(d)
    # 2-D triangulation of the disk. Cocircular ring points are degenerate here
    # too, but in 2-D Qhull resolves them into a valid triangulation with no
    # zero-area cells to delete, which is precisely what went wrong in 3-D.
    tri2 = Delaunay(d, qhull_options="Qt Qbb Qc Qz").simplices
    a, b, c = (d[tri2[:, 0]], d[tri2[:, 1]], d[tri2[:, 2]])
    area2 = 0.5 * np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) -
                         (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1]))
    tri2 = tri2[area2 > 1e-12 * R * R]

    zs = np.linspace(0, height, nz)
    P = np.column_stack([np.tile(d, (nz, 1)), np.repeat(zs, nd)])

    # Sorting each base triangle's node indices makes the diagonal on every
    # vertical quad a function of the two node ids alone, so the two prisms
    # sharing that quad cannot disagree. This is the whole fix.
    tri2 = np.sort(tri2, axis=1)
    tets = []
    for k in range(nz - 1):
        lo, hi = k * nd, (k + 1) * nd
        for (i, j, l) in tri2:
            b0, b1, b2 = lo + i, lo + j, lo + l
            t0, t1, t2 = hi + i, hi + j, hi + l
            tets.append((b0, b1, b2, t2))
            tets.append((b0, b1, t1, t2))
            tets.append((b0, t0, t1, t2))
    tets = np.asarray(tets, dtype=np.int64)

    v = P[tets]
    vol = np.einsum('ij,ij->i', np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]),
                    v[:, 3] - v[:, 0]) / 6.0
    flip = vol < 0                      # keep every tet positively oriented
    tets[flip] = tets[flip][:, [0, 2, 1, 3]]
    if np.any(np.abs(vol) <= 0):
        raise AssertionError("make_cylinder: degenerate tetrahedron produced")

    mesh = MeshTet(P.T, tets.T)
    if check:
        _assert_conforming(mesh, expected_vol=area2[area2 > 1e-12 * R * R].sum() * height)
    return mesh


def make_cylinder_legacy(R=5.5, height=14.0, n_rings=7, nz=17, xscale=1.0):
    """The PRE-FIX mesher, kept ONLY so the ablation can attribute changes.

    This is defect 36 exactly as it was: 3-D Delaunay over the structured cloud,
    then drop the exactly-flat tets, which tears the mesh into ~9300 hanging
    faces. Do not use it for anything but the ablation.
    """
    d = _disk_points(R, n_rings, xscale)
    zs = np.linspace(0, height, nz)
    P = np.column_stack([np.tile(d, (nz, 1)), np.repeat(zs, len(d))])
    tri = Delaunay(P, qhull_options="Qt Qbb Qc Qz")
    tets = tri.simplices
    v = P[tets]
    vol = np.abs(np.einsum('ij,ij->i',
                           np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]),
                           v[:, 3] - v[:, 0])) / 6.0
    tets = tets[vol > 1e-9 * (R * R * height)]
    return MeshTet(P.T, tets.T)


def _assert_conforming(mesh, expected_vol=None, tol=1e-9):
    """Fail loudly if the mesh is torn. See defect 37."""
    from collections import Counter
    cnt = Counter()
    for tet in mesh.t.T:
        for f in ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)):
            cnt[tuple(sorted(int(tet[i]) for i in f))] += 1
    bad = [f for f, n in cnt.items() if n > 2]
    if bad:
        raise AssertionError(f"make_cylinder: {len(bad)} faces shared by >2 tets")
    P = mesh.p.T
    surf = [f for f, n in cnt.items() if n == 1]
    # every single-neighbour face must lie ON the boundary of the solid
    R = np.hypot(P[:, 0], P[:, 1]).max()
    zlo, zhi = P[:, 2].min(), P[:, 2].max()
    hanging = 0
    for f in surf:
        cen = P[list(f)].mean(axis=0)
        on_cap = abs(cen[2] - zlo) < tol or abs(cen[2] - zhi) < tol
        on_side = np.hypot(cen[0], cen[1]) > 0.5 * R      # generous: lateral wall
        if not (on_cap or on_side):
            hanging += 1
    if hanging:
        raise AssertionError(
            f"make_cylinder: NON-CONFORMING -- {hanging} of {len(surf)} "
            f"single-neighbour faces are interior (hanging faces)")
    if expected_vol is not None:
        v = mesh.p[:, mesh.t]
        vol = np.abs(np.einsum(
            'ij,ij->i',
            np.cross((v[:, 1] - v[:, 0]).T, (v[:, 2] - v[:, 0]).T),
            (v[:, 3] - v[:, 0]).T)).sum() / 6.0
        if abs(vol - expected_vol) > 1e-6 * expected_vol:
            raise AssertionError(
                f"make_cylinder: volume {vol:.6f} != expected {expected_vol:.6f}")


# --------------------------------------------------------------------------
# Electrodes: pick lateral boundary facets inside angular x z windows.
# --------------------------------------------------------------------------
def place_electrodes(mesh, R, height, n_per_ring=8, ring_z=(0.38, 0.62),
                     arc_frac=0.55, band=0.06, xscale=1.0):
    bf = mesh.boundary_facets()
    fc = mesh.p[:, mesh.facets[:, bf]].mean(axis=1)   # (3, nbf) facet centroids
    x, y, z = fc[0] / xscale, fc[1], fc[2]
    rad = np.hypot(x, y)
    ang = np.arctan2(y, x) % (2 * np.pi)
    lateral = rad > 0.80 * R                            # exclude top/bottom caps
    elecs, cents = [], []
    dphi = 2 * np.pi / n_per_ring
    half = arc_frac * dphi / 2
    for zc in ring_z:
        zabs = zc * height
        for k in range(n_per_ring):
            phi = k * dphi
            da = np.angle(np.exp(1j * (ang - phi)))
            sel = lateral & (np.abs(da) < half) & (np.abs(z - zabs) < band * height)
            if sel.sum() == 0:                          # widen if a patch is empty
                sel = lateral & (np.abs(da) < half * 1.8) & (np.abs(z - zabs) < band * 1.8 * height)
            elecs.append(bf[sel])
            cents.append([R * np.cos(phi), R * np.sin(phi), zabs])
    return elecs, np.array(cents)


# --------------------------------------------------------------------------
# CEM forward solver
# --------------------------------------------------------------------------
class CEM3D:
    def __init__(self, mesh, elec_facets):
        self.mesh = mesh
        self.basis = Basis(mesh, ElementTetP1())
        self.p0 = self.basis.with_element(ElementTetP0())
        self.N = self.basis.N
        self.L = len(elec_facets)
        # per-electrode boundary mass M_l and load c_l (= int phi_i dS)
        self._M, self._c, self.area = [], [], []
        for f in elec_facets:
            fb = FacetBasis(mesh, ElementTetP1(), facets=f)
            M = asm(BilinearForm(lambda u, v, w: u * v), fb)
            c = asm(LinearForm(lambda v, w: 1.0 * v), fb)
            self._M.append(M.tocsr()); self._c.append(c); self.area.append(float(c.sum()))
        self.area = np.array(self.area)

    def _stiff_real(self, sig):
        a = BilinearForm(lambda u, v, w: w['s'] * dot(grad(u), grad(v)))
        return asm(a, self.basis, s=self.p0.interpolate(np.asarray(sig, float)))

    def _stiffness(self, sigma):
        # stiffness is linear in sigma; for complex admittivity assemble the real
        # and imaginary parts separately (avoids skfem casting away the imag part)
        if np.iscomplexobj(sigma):
            return self._stiff_real(sigma.real) + 1j * self._stiff_real(sigma.imag)
        return self._stiff_real(sigma)

    def _assemble(self, sigma, zc):
        """Augmented CEM system A (with sum(U)=0 Lagrange row). Constant across
        drive patterns, so factorize once and back-substitute per drive."""
        dt = complex if (np.iscomplexobj(sigma) or np.iscomplexobj(zc)) else float
        N, L = self.N, self.L
        Ktl = self._stiffness(sigma).astype(dt).tocsr()
        add = sp.csr_matrix((N, N), dtype=dt)
        Bcols = np.zeros((N, L), dtype=dt); Cdiag = np.zeros(L, dtype=dt)
        for l in range(L):
            add = add + self._M[l].astype(dt) * (1.0 / zc[l])
            Bcols[:, l] = -(self._c[l] / zc[l]); Cdiag[l] = self.area[l] / zc[l]
        Ktl = Ktl + add
        B = sp.csr_matrix(Bcols); C = sp.diags(Cdiag)
        gL = np.ones(L, dtype=dt)
        top = sp.hstack([Ktl, B, sp.csr_matrix((N, 1), dtype=dt)])
        mid = sp.hstack([B.T, C, sp.csr_matrix(gL[:, None])])
        bot = sp.hstack([sp.csr_matrix((1, N), dtype=dt), sp.csr_matrix(gL[None, :]),
                         sp.csr_matrix((1, 1), dtype=dt)])
        return sp.vstack([top, mid, bot]).tocsc(), N, L, dt

    def solve(self, sigma, currents, zc):
        A, N, L, dt = self._assemble(sigma, zc)
        rhs = np.concatenate([np.zeros(N, dtype=dt), currents.astype(dt), [0]])
        return spla.spsolve(A, rhs)[N:N + L]

    def solve_drives(self, sigma, zc, drives, amp=1.0):
        """Electrode potentials for every drive pair, one factorization."""
        A, N, L, dt = self._assemble(sigma, zc)
        lu = spla.splu(A)
        Us = np.zeros((len(drives), L), dtype=dt)
        for i, (a, b) in enumerate(drives):
            rhs = np.zeros(N + L + 1, dtype=dt); rhs[N + a] = amp; rhs[N + b] = -amp
            Us[i] = lu.solve(rhs)[N:N + L]
        return Us


# --------------------------------------------------------------------------
# Measurement protocol: adjacent drive / adjacent measure within each ring,
# plus cross-ring drives so longitudinal (z) transport is observable.
# --------------------------------------------------------------------------
def adjacent_protocol(n_per_ring, n_rings=2):
    L = n_per_ring * n_rings
    drives = []
    for r in range(n_rings):                       # in-ring adjacent drives
        base = r * n_per_ring
        for k in range(n_per_ring):
            drives.append((base + k, base + (k + 1) % n_per_ring))
    if n_rings == 2:                               # a few cross-ring drives
        for k in range(n_per_ring):
            drives.append((k, n_per_ring + k))
    meas = []
    for (a, b) in drives:
        mm = []
        for r in range(n_rings):
            base = r * n_per_ring
            for k in range(n_per_ring):
                p, q = base + k, base + (k + 1) % n_per_ring
                if len({p, q} & {a, b}) == 0:
                    mm.append((p, q))
        meas.append(mm)
    return drives, meas


def measure_frame(solver, sigma, zc, drives, meas, amp=1.0):
    """Flattened differential-voltage vector (one factorization for the frame)."""
    Us = solver.solve_drives(sigma, zc, drives, amp)
    out = []
    for i, mm in enumerate(meas):
        U = Us[i]
        for (p, q) in mm:
            out.append(U[p] - U[q])
    return np.array(out)
