"""Conversion helpers for Anymove's mocap.solve detection contract."""
import numpy as np
def to_anymove(front_uv, side_uv, front_conf=None, side_conf=None, fps=24.0, names=None, calib=None):
    f=np.asarray(front_uv,dtype=np.float32); s=np.asarray(side_uv,dtype=np.float32)
    if f.shape != s.shape or f.ndim != 3 or f.shape[-1] != 2: raise ValueError('views must both be [T,J,2]')
    T,J,_=f.shape; fc=np.ones((T,J),np.float32) if front_conf is None else np.asarray(front_conf,dtype=np.float32); sc=np.ones((T,J),np.float32) if side_conf is None else np.asarray(side_conf,dtype=np.float32)
    if fc.shape!=(T,J) or sc.shape!=(T,J): raise ValueError('confidence must be [T,J]')
    return {'front_uv':f,'side_uv':s,'front_conf':np.clip(fc,0,1),'side_conf':np.clip(sc,0,1),'fps':float(fps),'names':np.asarray(names if names is not None else [f'joint_{i}' for i in range(J)]),'calib':np.eye(2,3,dtype=np.float32) if calib is None else np.asarray(calib,dtype=np.float32)}
def save_npz(path,data): np.savez(path,**data)
