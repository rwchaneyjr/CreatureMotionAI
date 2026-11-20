"""Mesh-BVH rear-leg collision diagnostic for an existing Blender walk copy.

The check is baseline-relative: it excludes triangle pairs sharing source
vertices and reports intersections between separately weighted anatomy regions.
It does not edit or save the input .blend.
"""
import argparse
import json
import sys
from pathlib import Path


LEGS = (
    "Front.L", "Front.R", "MidFront.L", "MidFront.R",
    "MidRear.L", "MidRear.R", "Rear.L", "Rear.R",
)
BODY_BONES = ("Body_01", "Body_02", "Body_03")


def chain_names(leg):
    return [f"Leg_{leg}_{i:02d}" for i in (1, 2, 3)]


def run(blend_path, output_path, frame_start=1, frame_end=40):
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    bpy.ops.wm.open_mainfile(filepath=str(Path(blend_path).resolve()))
    scene = bpy.context.scene
    mesh = next(o for o in scene.objects if o.type == "MESH")
    arm = next(o for o in scene.objects if o.type == "ARMATURE")
    mesh.data.calc_loop_triangles()
    source_tris = [tuple(t.vertices) for t in mesh.data.loop_triangles]
    source_vertex_count = len(mesh.data.vertices)

    # Match the project's validated weighted-chain segmentation rule.
    def regions_at_rest():
        scene.frame_set(frame_start)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        ev = mesh.evaluated_get(deps)
        data = ev.to_mesh()
        verts = [ev.matrix_world @ v.co for v in data.vertices]
        ev.to_mesh_clear()

        def segment_distance(point, a, b):
            delta = b - a
            t = max(0.0, min(1.0, (point - a).dot(delta) / (delta.dot(delta) or 1.0)))
            return (point - (a + delta * t)).length

        regions = {}
        for region in (*LEGS, "BODY"):
            names = chain_names(region) if region != "BODY" else list(BODY_BONES)
            group_ids = {mesh.vertex_groups[n].index for n in names if mesh.vertex_groups.get(n)}
            if not group_ids:
                regions[region] = set()
                continue
            segments = []
            for name in names:
                pb = arm.pose.bones.get(name)
                if pb:
                    segments.append((arm.matrix_world @ pb.head, arm.matrix_world @ pb.tail))
            selected = set()
            for v in mesh.data.vertices:
                chain_weight = sum(g.weight for g in v.groups if g.group in group_ids)
                max_weight = max((g.weight for g in v.groups), default=0.0)
                p = mesh.matrix_world @ v.co
                near = min((segment_distance(p, a, b) for a, b in segments), default=0.0)
                if chain_weight >= 0.35 and chain_weight >= max_weight * 0.75 and near <= 0.12:
                    selected.add(v.index)
            regions[region] = selected
        return regions

    regions = regions_at_rest()
    region_tris = {
        # Keep only triangles fully assigned to a region.  Including boundary
        # triangles with two vertices caused adjacent skin-weight regions to
        # create thousands of false overlaps along their shared seams.
        name: [tri for tri in source_tris if all(index in ids for index in tri)]
        for name, ids in regions.items()
    }
    # The model is a single skinned surface; connected seam triangles are not
    # independent penetrations, so they are filtered by shared source vertex.
    pair_list = []
    for leg in LEGS:
        if leg.startswith("Rear"):
            pair_list.extend((leg, other) for other in (*LEGS, "BODY") if other != leg)
    checks = list(dict.fromkeys(pair_list))
    rows = []
    for frame in range(frame_start, frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        ev = mesh.evaluated_get(deps)
        data = ev.to_mesh()
        verts = [ev.matrix_world @ v.co for v in data.vertices]
        frame_hits = []
        for a, b in checks:
            ta, tb = region_tris[a], region_tris[b]
            if not ta or not tb:
                continue
            ba = BVHTree.FromPolygons(verts, ta, all_triangles=True)
            bb = BVHTree.FromPolygons(verts, tb, all_triangles=True)
            overlaps = ba.overlap(bb)
            filtered = []
            for ia, ib in overlaps:
                if set(ta[ia]).intersection(tb[ib]):
                    continue
                filtered.append((ia, ib))
            if filtered:
                frame_hits.append({"region_a": a, "region_b": b,
                                   "filtered_overlap_count": len(filtered),
                                   "examples": [[list(ta[x]), list(tb[y])] for x, y in filtered[:8]]})
        rows.append({"frame": frame, "intersection_pairs": frame_hits,
                     "intersection_count": sum(x["filtered_overlap_count"] for x in frame_hits)})
        ev.to_mesh_clear()

    result = {
        "status": "NO_REAR_MESH_INTERSECTIONS_IN_CYCLE" if not any(r["intersection_count"] for r in rows)
                 else "REAR_MESH_INTERSECTIONS_FOUND",
        "input_blend": str(Path(blend_path).resolve()),
        "action": arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None,
        "frames_checked": [frame_start, frame_end],
        "mesh": mesh.name,
        "source_vertex_count": source_vertex_count,
        "region_vertex_counts": {name: len(ids) for name, ids in regions.items()},
        "region_triangle_counts": {name: len(tris) for name, tris in region_tris.items()},
        "test": "Evaluated mesh BVH overlaps between Rear.L/Rear.R weighted surface regions and each other leg/body region; pairs sharing source vertices excluded.",
        "maximum_intersections_in_frame": max((r["intersection_count"] for r in rows), default=0),
        "frames_with_intersections": [r["frame"] for r in rows if r["intersection_count"]],
        "frames": rows,
        "caveat": "Weighted-region BVH detects surface crossings, not all near-contact gaps. Rest-pose/pre-existing mesh penetrations should be compared separately.",
    }
    out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "frames_checked", "maximum_intersections_in_frame", "frames_with_intersections")}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=40)
    args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
    run(args.blend, args.report, args.start, args.end)


if __name__ == "__main__":
    main()
