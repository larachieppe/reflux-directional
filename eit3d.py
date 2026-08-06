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
# Mesh: extrude a 2-D disk of points along z, tetrahedralize by Delaunay.
# The disk is convex, so the convex hull of the extruded cloud is exactly the
# (polygonal) cylinder -> a conforming tet mesh with no prism-split bookkeeping.
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


def make_cylinder(R=5.5, height=14.0, n_rings=7, nz=17, xscale=1.0):
    """Return an skfem MeshTet for an (elliptical) cylinder, axis = z."""
    d = _disk_points(R, n_rings, xscale)
    zs = np.linspace(0, height, nz)
    P = np.vstack([np.column_stack([np.tile(d, (nz, 1)),
                                    np.repeat(zs, len(d))])])
    # P: (nz*ndisk, 3)
    tri = Delaunay(P, qhull_options="Qt Qbb Qc Qz")
    tets = tri.simplices
    # drop slivers (near-zero volume) for a clean stiffness matrix
    v = P[tets]
    vol = np.abs(np.einsum('ij,ij->i',
                           np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]),
                           v[:, 3] - v[:, 0])) / 6.0
    tets = tets[vol > 1e-9 * (R * R * height)]
    m = MeshTet(P.T, tets.T)
    return m


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
