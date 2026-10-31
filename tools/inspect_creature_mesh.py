"""Inspect a creature mesh and propose anatomy without reading its armature."""
import argparse
import json
from pathlib import Path

import bpy
from mathutils import Vector


def _mesh_bounds(mesh_objects):
    points = [obj.matrix_world @ Vector(corner) for obj in mesh_objects for corner in obj.bound_box]
    if not points:
        raise RuntimeError("No mesh geometry found")
    minimum = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maximum = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return minimum, maximum


def inspect(filepath, output):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if filepath.lower().endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=filepath)
    elif filepath.lower().endswith(".glb") or filepath.lower().endswith(".gltf"):
        bpy.ops.import_scene.gltf(filepath=filepath)
    else:
        bpy.ops.wm.open_mainfile(filepath=filepath)
    meshes = []
    mesh_objects = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        mesh_objects.append(obj)
        meshes.append({
            "name": obj.name,
            "vertices": len(obj.data.vertices),
            "polygons": len(obj.data.polygons),
            "dimensions": list(obj.dimensions),
            "location": list(obj.location),
            "materials": [material.name for material in obj.data.materials if material],
        })
    minimum, maximum = _mesh_bounds(mesh_objects)
    center = (minimum + maximum) / 2
    length = max(maximum.y - minimum.y, 1e-6)
    height = max(maximum.z - minimum.z, 1e-6)
    width = max(maximum.x - minimum.x, 1e-6)
    # The default template is deliberately editable and does not claim that
    # every creature has this topology. Longitudinal stations and side anchors
    # are proposed from the mesh bounds only.
    stations = [0.22, 0.50, 0.78]
    limbs = []
    for index, station in enumerate(stations, 1):
        y = minimum.y + length * station
        for side, x in (("L", maximum.x * 0.72 + minimum.x * 0.28),
                        ("R", minimum.x * 0.72 + maximum.x * 0.28)):
            limbs.append({"name": f"Leg_{index:02d}.{side}", "side": side,
                          "station": station, "hip": [x, y, center.z],
                          "knee": [x * 1.06, y, minimum.z + height * 0.32],
                          "foot": [x * 1.12, y + length * 0.025, minimum.z + height * 0.06]})
    candidate_parts = {
        "body": [{"name": "Torso", "center": list(center), "bounds_min": list(minimum), "bounds_max": list(maximum)}],
        "head_neck": [{"name": "Head", "anchor": [center.x, maximum.y - length * 0.07, center.z + height * 0.05]}],
        "limbs": limbs,
        "tail": [{"name": "Tail", "start": [center.x, minimum.y + length * 0.15, center.z],
                   "end": [center.x, minimum.y, center.z - height * 0.03]}],
        "wings": [], "other": []
    }
    profile = {
        "format": "creature_motion_ai.anatomy_profile.v1",
        "source": str(filepath),
        "mesh_objects": meshes,
        "template": {"legs_per_side": 3, "heads": 1, "tails": 1, "wings": 0,
                     "longitudinal_axis": "Y", "vertical_axis": "Z"},
        "bounds": {"min": list(minimum), "max": list(maximum)},
        "candidate_parts": candidate_parts,
        "review_required": True,
        "notes": "Mesh-only proposal. Verify stations and anchors before production use; no source armature data was used.",
    }
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    print(json.dumps({"meshes": len(meshes), "output": str(path), "armature_data_used": False}))


parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
inspect(args.input, args.output)
