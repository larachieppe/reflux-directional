"""
Artifact check for the Study 5 placement conclusion.

The 10 cm strip beating the 16 cm strip is a load-bearing result, so the most
plausible way it could be an ESTIMATOR artifact rather than physics was tested
directly: xcorr_lag clips the inter-zone lag search at max_lag = 2T/3. If true
lags saturated that bound on the long strip but not the short one, the slope fit
would be biased in exactly the direction of the published conclusion.

RESULT: refuted. With T = 20 the clip sits at 13 frames; the largest lag observed
anywhere was 3.13 frames, and 0% of lags were at or near the bound in either
configuration. The conclusion is not a lag-window artifact.

The check also supports the mechanism: the 10 cm strip over the UVJ shows LARGER
lags (mean 1.57-1.98) than the 16 cm mid-torso strip (0.72-1.62), which is what a
real traverse looks like against zones the low-grade bolus barely reaches.
"""
import numpy as np, json, directional_sim as ds, eit3d
T=20; MAXLAG=max(3,(2*T)//3)
out={"T":T,"max_lag":MAXLAG,"configs":{}}
mesh = eit3d.make_cylinder(R=5.5, height=20.0, n_rings=6, nz=17)
for span,zc,name in ((16.0,0.50,"16cm_mid"),(10.0,0.34,"10cm_uvj")):
    w = ds.StripWorld(8, span=span, mesh=mesh, z_center=zc)
    per={}
    for g in (1,2,3,4):
        vals=[]
        for i in range(6):
            dZ = ds.simulate_trial(w,"reflux",np.random.default_rng(5000+i),grade=g,
                                   side=+1,T=T,snr_db=60,motion_amp=0.0)
            f = ds.direction_features(dZ,w)
            for s in (0,1):
                for k,v in f[s].items():
                    if k.startswith("lag"): vals.append(abs(float(v)))
        vals=np.array(vals)
        per[f"grade{g}"]=dict(n=len(vals),mean=float(vals.mean()),max=float(vals.max()),
            at_clip=float(np.mean(np.abs(vals-MAXLAG)<1e-6)),
            near_clip=float(np.mean(vals>0.9*MAXLAG)))
        print(f"[{name}] grade {g}: mean|lag|={vals.mean():5.2f} max={vals.max():5.2f} "
              f"at-clip={100*per[f'grade{g}']['at_clip']:.1f}% near={100*per[f'grade{g}']['near_clip']:.1f}%",flush=True)
    out["configs"][name]=per
json.dump(out,open("metrics_lagcheck.json","w"),indent=1)
print("done")
