"""Compare restricted orthographic and perspective side-camera fits.

This is diagnostic only: body correspondences are approximate and no rig data is
modified. One annotated frame is held out to expose overfitting.
"""
import json, math
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
CAL = json.loads((ROOT / "data/generated/single_camera_camera_calibration_annotations.json").read_text())
PTS = json.loads((ROOT / "data/generated/body_landmark_3d_selected.json").read_text())
NAMES = ["body_center", "head_snout", "tail_base", "body_length_reference"]
ALL = [1, 61, 121, 181, 240]
FIT = [1, 61, 121, 240]
P = np.asarray([PTS["points"][n] for n in NAMES], float)
Y = {f: np.asarray([CAL["frames"][str(f)][n]["uv"] for n in NAMES], float) for f in ALL}
CX, CY = 320.0, 360.0


def ortho():
    def pred(x, frame):
        r = Rotation.from_rotvec(x[:3]).as_matrix()
        q = (r @ P.T).T
        s = math.exp(x[3]); t = x[4 + 2 * FIT.index(frame):6 + 2 * FIT.index(frame)]
        return q[:, :2] * s + t
    def fun(x):
        return np.concatenate([(pred(x, f) - Y[f]).ravel() for f in FIT])
    x0 = np.zeros(4 + 2 * len(FIT)); x0[3] = math.log(2.0)
    for i in range(len(FIT)): x0[4 + 2*i:6 + 2*i] = [CX, CY]
    r = least_squares(fun, x0, loss="soft_l1", f_scale=5, max_nfev=20000)
    return evaluate("orthographic", r.cost, {f: pred(r.x, f) if f in FIT else None for f in ALL}, r.x)


def perspective():
    # Shared rotation/focal length; each frame gets an independent translation.
    # This is intentionally constrained and is not a metric calibration.
    def pred(x, frame):
        r = Rotation.from_rotvec(x[:3]).as_matrix()
        f = math.exp(x[3]); j = ALL.index(frame)
        t = np.array([x[4 + 3*j], x[5 + 3*j], math.exp(x[6 + 3*j])])
        q = (r @ P.T).T + t
        z = np.maximum(q[:, 2:3], 1e-4)
        return np.column_stack([CX + f*q[:, 0]/z[:, 0], CY + f*q[:, 1]/z[:, 0]])
    def fun(x):
        return np.concatenate([(pred(x, f) - Y[f]).ravel() for f in FIT])
    x0 = np.zeros(4 + 3 * len(ALL)); x0[3] = math.log(900.0)
    for i in range(len(ALL)):
        x0[4 + 3*i:7 + 3*i] = [0.0, 0.0, math.log(10.0)]
    r = least_squares(fun, x0, loss="soft_l1", f_scale=5, max_nfev=40000)
    return evaluate("perspective", r.cost, {f: pred(r.x, f) for f in ALL}, r.x)


def evaluate(model, cost, predictions, x):
    result = {"model": model, "robust_cost": float(cost), "frames": {}, "holdout_frames": [181]}
    all_res = []
    for f in ALL:
        if predictions[f] is None:
            result["frames"][str(f)] = {"status": "UNAVAILABLE"}
            continue
        e = np.linalg.norm(predictions[f] - Y[f], axis=1)
        all_res.extend(e.tolist())
        result["frames"][str(f)] = {"mean_px": float(e.mean()), "max_px": float(e.max()), "per_landmark_px": e.tolist(), "holdout": f == 181}
    result["overall_rms_px"] = float(np.sqrt(np.mean(np.square(all_res)))) if all_res else None
    result["fit_frames"] = FIT
    result["assumptions"] = ["approximate rig landmark correspondences", "per-frame translation", "metric depth remains ambiguous"]
    return result


if __name__ == "__main__":
    out = {"status": "DIAGNOSTIC", "orthographic": ortho(), "perspective": perspective()}
    path = ROOT / "data/generated/side_camera_calibration_comparison.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
