"""Read-only probe of terminal weighted foot surfaces for an anatomy profile.

Run with Blender on an isolated copy. It reports candidate surface sizes and
vertical ranges but does not write to the .blend or create Actions.
"""
import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output", required=True)
    args, _ = parser.parse_known_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    scene = bpy.context.scene
    arm = bpy.data.objects[profile["armature"]]
    mesh = next(o for o in scene.objects if o.type == 'MESH' and any(
        m.type == 'ARMATURE' and m.object == arm for m in o.modifiers))
    action = bpy.data.actions.get("Move_Scissor_Offset")
    if action is None:
        raise RuntimeError("Requested Move_Scissor_Offset action not found")
    start, end = (int(round(x)) for x in action.frame_range)
    groups = {leg["name"]: mesh.vertex_groups.get(leg["contact_bone"]) for leg in profile["legs"]}
    group_weights = {}
    for leg, group in groups.items():
        if group is None:
            group_weights[leg] = None
            continue
        values = np.zeros(len(mesh.data.vertices), dtype=np.float32)
        for vertex in mesh.data.vertices:
            for membership in vertex.groups:
                if membership.group == group.index:
                    values[vertex.index] = membership.weight
        group_weights[leg] = values
    rows = {leg["name"]: [] for leg in profile["legs"]}
    frame_samples = sorted(set([start, end] + list(range(start, end + 1, max(1, (end-start)//8)))))
    for frame in frame_samples:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        ev = mesh.evaluated_get(deps)
        me = ev.to_mesh()
        co = np.empty(len(me.vertices)*3, np.float32); me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        mat = np.asarray(ev.matrix_world, dtype=float)
        world = co @ mat[:3,:3].T + mat[:3,3]
        no = np.empty(len(me.vertices)*3, np.float32); me.vertices.foreach_get("normal", no)
        normal = no.reshape(-1,3) @ np.linalg.inv(mat[:3,:3])
        normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-12)
        for leg in profile["legs"]:
            name = leg["name"]
            weights = group_weights[name]
            if weights is None:
                rows[name].append({"frame":frame,"status":"NO_CONTACT_VERTEX_GROUP"}); continue
            ids = np.flatnonzero((weights >= .35) & (normal[:,2] < -.25))
            if len(ids):
                z = world[ids,2]
                rows[name].append({"frame":frame,"candidate_vertices":int(len(ids)),
                                   "min_z":float(z.min()),"p05_z":float(np.percentile(z,5)),
                                   "median_z":float(np.median(z)),"max_z":float(z.max()),
                                   "low_patch_vertices":int(np.sum(z <= z.min()+.003))})
            else:
                rows[name].append({"frame":frame,"candidate_vertices":0,"status":"NO_DOWNWARD_WEIGHTED_VERTICES"})
        ev.to_mesh_clear()
    report = {"status":"READ_ONLY_SURFACE_PROBE","source_action":action.name,
              "frame_range":[start,end],"sampled_frames":frame_samples,
              "per_leg":rows,"ground_object_candidates":[o.name for o in scene.objects if o.type=='MESH' and 'ground' in o.name.lower()],
              "note":"This is only a weighted underside probe, not a verified sole or ground calibration."}
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("CONTACT_SURFACE_PROBE " + json.dumps({"output":str(out),"per_leg_counts":{k:sum(x.get('candidate_vertices',0)>0 for x in v) for k,v in rows.items()}}),flush=True)


if __name__ == "__main__":
    main()
