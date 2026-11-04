import bpy, json, math, time, os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(r"C:\Users\rober\CreatureMotionAI")
BLEND = Path(os.environ.get("CMAI_VALIDATE_BLEND", str(ROOT / "data/generated/front_l_fk_8deg_03_3deg.blend")))
OUT = ROOT / "data/generated"
GROUND = -0.23375284671783447
LEG_NAMES = ["Front.L", "Front.R", "MidFront.L", "MidFront.R", "MidRear.L", "MidRear.R", "Rear.L", "Rear.R"]

def region_for_vertex(mesh, v):
    scores = {}
    for g in v.groups:
        name = mesh.vertex_groups[g.group].name
        if name.startswith("Leg_"):
            scores[name.rsplit("_", 1)[0].replace("Leg_", "")] = scores.get(name.rsplit("_", 1)[0].replace("Leg_", ""), 0.0) + g.weight
    return max(scores, key=scores.get) if scores else "Body"

def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    scene = bpy.context.scene
    mesh = next(o for o in scene.objects if o.type == "MESH")
    arm = next(o for o in scene.objects if o.type == "ARMATURE")
    deps = bpy.context.evaluated_depsgraph_get()
    source_regions = [region_for_vertex(mesh, v) for v in mesh.data.vertices]
    orientation = {"status": "UNVERIFIED_ANATOMICAL_LIMITS", "reference_frame": 1, "frames": []}
    scene.frame_set(1); bpy.context.view_layer.update()
    ref = arm.pose.bones["Leg_Front.L_03"].matrix.to_quaternion()
    for frame in [1, 11, 12, 13, 14, 24]:
        scene.frame_set(frame); bpy.context.view_layer.update()
        b = arm.pose.bones["Leg_Front.L_03"]
        q = b.matrix.to_quaternion()
        foot_dir = (arm.matrix_world.to_3x3() @ b.vector).normalized()
        angle = math.degrees(ref.rotation_difference(q).angle)
        orientation["frames"].append({"frame": frame, "foot_direction_world": list(foot_dir), "angle_from_rest_deg": angle, "bone_rotation_euler_deg": [math.degrees(x) for x in b.rotation_euler], "anatomical_limits": "NOT_DEFINED", "bend_measurement": "UNVERIFIED"})
    (OUT / "front_l_orientation_measurements.json").write_text(json.dumps(orientation, indent=2), encoding="utf-8")
    collision = {"status": "PASS_NO_NONADJACENT_COLLISIONS" , "frames": [], "region_mapping": {}, "timing": {}}
    frames = [int(x) for x in os.environ.get("CMAI_VALIDATE_FRAMES", "11,12,13,14").split(",")]
    for frame in frames:
        t0 = time.perf_counter(); scene.frame_set(frame); bpy.context.view_layer.update()
        ev = mesh.evaluated_get(deps); data = ev.to_mesh(); verts = [ev.matrix_world @ v.co for v in data.vertices]
        regions = {}
        for poly in data.polygons:
            rid = source_regions[poly.vertices[0]] if poly.vertices else "Body"
            if any(source_regions[i] != rid for i in poly.vertices): rid = "Mixed"
            regions.setdefault(rid, {"verts": [], "faces": [], "tri_ids": []})
            base = len(regions[rid]["verts"]); regions[rid]["verts"].extend([verts[i] for i in poly.vertices]); regions[rid]["faces"].append((base, base+1, base+2)); regions[rid]["tri_ids"].append(poly.index)
        bvhs = {r: BVHTree.FromPolygons(v["verts"], v["faces"], all_triangles=True) for r,v in regions.items() if len(v["faces"]) > 0}
        pairs=[]; keys=list(bvhs)
        for ai,a in enumerate(keys):
            for b in keys[ai+1:]:
                if a == b or a == "Mixed" or b == "Mixed": continue
                hits=bvhs[a].overlap(bvhs[b])
                for ia,ib in hits[:100]:
                    pa=regions[a]["verts"][regions[a]["faces"][ia][0]]; pb=regions[b]["verts"][regions[b]["faces"][ib][0]]
                    pairs.append({"frame":frame,"region_a":a,"region_b":b,"triangle_id_a":regions[a]["tri_ids"][ia],"triangle_id_b":regions[b]["tri_ids"][ib],"location":[(pa.x+pb.x)/2,(pa.y+pb.y)/2,(pa.z+pb.z)/2],"adjacent_or_expected_contact":False})
        if pairs: collision["status"]="FAIL_NONADJACENT_COLLISION_DETECTED"
        collision["frames"].append({"frame":frame,"pairs":pairs,"runtime_seconds":time.perf_counter()-t0})
        ev.to_mesh_clear()
    (OUT / "balisk_region_collision_report.json").write_text(json.dumps(collision, indent=2), encoding="utf-8")
    for frame in [12,13]:
        scene.frame_set(frame); scene.render.filepath=str(OUT / f"front_l_validation_frame{frame}.png"); bpy.ops.render.render(write_still=True)
    summary={"status":"FAIL_PHYSICAL_VALIDATION","collision_report":str(OUT/"balisk_region_collision_report.json"),"orientation_report":str(OUT/"front_l_orientation_measurements.json"),"ground_penetration":0.0006775408983230591,"anatomical_limits":"UNVERIFIED","next":"Review region pairs and orientation images before any correction."}
    (OUT / "front_l_final_validation.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
main()
