"""Read-only audit of the rejected contact-lock blend against stored anchors."""
import bpy, json
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
out = root / "data/generated/balisk_camera_fullbody_walk_02/contact_lock_v1"
obs = json.loads((out / "contact_observations.json").read_text(encoding="utf-8"))
arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.context.scene.objects if o.type == "MESH" and any(
    m.type == "ARMATURE" and m.object == arm for m in o.modifiers))
scene = bpy.context.scene
result = {}
for leg, patch in obs["patches"].items():
    ids = np.asarray(patch["indices"], dtype=np.int64)
    rows = []
    for frame, source in enumerate(obs["frames"][leg], 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        me = ev.to_mesh()
        xyz = np.empty(len(me.vertices) * 3, dtype=np.float64)
        me.vertices.foreach_get("co", xyz)
        xyz = xyz.reshape(-1, 3)
        mat = np.asarray(ev.matrix_world, dtype=np.float64)
        points = xyz[ids] @ mat[:3, :3].T + mat[:3, 3]
        centroid = points.mean(axis=0)
        clearance = float(points[:, 2].min() - scene.objects["CMAI_Ground_Contact"].location.z)
        ev.to_mesh_clear()
        anchor = source.get("anchor")
        residual = float(np.linalg.norm(centroid[:2] - np.asarray(anchor[:2]))) if source.get("lock") and anchor else None
        rows.append({"frame": frame, "state": source["state"], "lock": source["lock"],
                     "clearance": clearance, "centroid": centroid.tolist(),
                     "anchor_residual_xy": residual})
    vals = [r["anchor_residual_xy"] for r in rows if r["anchor_residual_xy"] is not None]
    result[leg] = {"mean_anchor_residual_xy": float(np.mean(vals)) if vals else None,
                   "max_anchor_residual_xy": float(max(vals)) if vals else None,
                   "rows": rows}
(out / "candidate_anchor_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print("ANCHOR_AUDIT " + json.dumps({k: {a: v[a] for a in ("mean_anchor_residual_xy", "max_anchor_residual_xy")}
                                    for k, v in result.items()}), flush=True)
