"""Profile-driven multi-creature setup and workflow selector.

This module is intentionally additive: the established Balisk panels and
operators remain available and unchanged.
"""
from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path

import bpy
from mathutils import Vector
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty,
                       IntProperty, PointerProperty, StringProperty)

from .rig_profiles import propose_anatomy_profile


class CMAI_AnatomyLeg(bpy.types.PropertyGroup):
    name: StringProperty(name="Limb")
    bones_csv: StringProperty(name="Bone chain", description="Ordered parent-to-foot bone names, comma separated")
    contact_bone: StringProperty(name="Distal/contact bone")
    side: EnumProperty(name="Side", items=[("left", "Left", ""), ("right", "Right", ""),
                                               ("center", "Center/unknown", "")], default="center")
    identity_confirmed: BoolProperty(name="Identity confirmed", default=False)


class CMAI_AnatomySettings(bpy.types.PropertyGroup):
    armature: PointerProperty(name="Creature Armature", type=bpy.types.Object,
                              poll=lambda self, obj: obj.type == 'ARMATURE')
    workflow: EnumProperty(name="Workflow", items=[
        ("EXISTING", "Improve Existing Animation", "Analyze or improve an existing Action; no video is required"),
        ("VIDEO", "Create Animation From Reference Video", "Video-based tracking workflow; a video is required")], default="EXISTING")
    reference_video: StringProperty(name="Reference Video", subtype="FILE_PATH")
    action_name: StringProperty(name="Starting Action", default="Move_Scissor_Offset")
    profile_name: StringProperty(name="Profile Name")
    legs: CollectionProperty(type=CMAI_AnatomyLeg)
    active_leg: IntProperty(default=0)
    body_bones_csv: StringProperty(name="Body bones", description="Comma-separated optional bone names")
    head_bones_csv: StringProperty(name="Head/neck bones")
    wing_bones_csv: StringProperty(name="Wing bones")
    tail_bones_csv: StringProperty(name="Tail bones")
    profile_path: StringProperty(name="Saved profile", subtype="FILE_PATH")
    profile_confirmed: BoolProperty(name="Anatomy mapping confirmed", default=False)
    report_path: StringProperty(name="Latest report", subtype="FILE_PATH")


def _csv(value):
    return [part.strip() for part in value.split(",") if part.strip()]


class CMAI_OT_profile_detect(bpy.types.Operator):
    bl_idname = "cmai.anatomy_profile_detect"
    bl_label = "Detect Anatomy Profile"
    bl_description = "Propose limb chains and body/wing/tail roles from armature names and hierarchy"

    def execute(self, context):
        p = context.scene.cmai_anatomy
        arm = p.armature or (context.active_object if context.active_object and context.active_object.type == 'ARMATURE' else None)
        if not arm:
            self.report({'ERROR'}, "Select an armature or choose Creature Armature first")
            return {'CANCELLED'}
        proposal = propose_anatomy_profile(arm)
        p.armature = arm
        p.profile_name = proposal["profile_name"]
        p.legs.clear()
        for leg in proposal["legs"]:
            row = p.legs.add()
            row.name = leg["name"]
            row.bones_csv = ", ".join(leg["bones"])
            row.contact_bone = leg["contact_bone"]
            row.side = leg["side"] if leg["side"] in {"left", "right"} else "center"
            row.identity_confirmed = False
        p.body_bones_csv = ", ".join(proposal["body_bones"])
        p.head_bones_csv = ", ".join(proposal["head_bones"])
        p.wing_bones_csv = ", ".join(proposal["wing_bones"])
        p.tail_bones_csv = ", ".join(proposal["tail_bones"])
        p.profile_confirmed = False
        self.report({'INFO'}, f"Proposed {len(proposal['legs'])} parent-validated leg chains; confirm/correct before use")
        return {'FINISHED'}


def _build_profile(context):
    p = context.scene.cmai_anatomy
    arm = p.armature
    if arm is None:
        raise ValueError("Choose a creature armature")
    names = set(arm.data.bones.keys())
    if not p.legs:
        raise ValueError("Detect or add at least one leg chain")
    legs = []
    used = set()
    for row in p.legs:
        chain = _csv(row.bones_csv)
        if len(chain) < 2:
            raise ValueError(f"{row.name}: enter at least two bones in parent-to-foot order")
        missing = [name for name in chain if name not in names]
        if missing:
            raise ValueError(f"{row.name}: unknown bone(s): {', '.join(missing)}")
        if row.contact_bone not in chain:
            raise ValueError(f"{row.name}: distal/contact bone must belong to its chain")
        for index in range(1, len(chain)):
            if arm.data.bones[chain[index]].parent != arm.data.bones[chain[index - 1]]:
                raise ValueError(f"{row.name}: {chain[index]} is not parented to {chain[index - 1]}")
        overlap = used.intersection(chain)
        if overlap:
            raise ValueError(f"Bone(s) assigned to more than one limb: {', '.join(sorted(overlap))}")
        used.update(chain)
        legs.append({"name": row.name.strip() or chain[0], "bones": chain,
                     "contact_bone": row.contact_bone, "side": row.side,
                     "identity_confirmed": bool(row.identity_confirmed)})
    def checked_role(value, label):
        result = _csv(value)
        missing = [name for name in result if name not in names]
        if missing:
            raise ValueError(f"Unknown {label} bone(s): {', '.join(missing)}")
        return result
    if not all(row["identity_confirmed"] for row in legs):
        raise ValueError("Confirm the physical identity of every proposed limb")
    return {"schema_version": 2, "profile_name": p.profile_name or arm.name + "_anatomy",
            "armature": arm.name, "bone_count": len(names), "legs": legs,
            "body_bones": checked_role(p.body_bones_csv, "body"),
            "head_bones": checked_role(p.head_bones_csv, "head/neck"),
            "wing_bones": checked_role(p.wing_bones_csv, "wing"),
            "tail_bones": checked_role(p.tail_bones_csv, "tail"),
            "confirmed": True, "mapping_status": "USER_CONFIRMED",
            "coordinate_space": "armature local rest pose"}


class CMAI_OT_profile_confirm_save(bpy.types.Operator):
    bl_idname = "cmai.anatomy_profile_confirm_save"
    bl_label = "Confirm Mapping and Save New Profile"

    def execute(self, context):
        p = context.scene.cmai_anatomy
        try:
            profile = _build_profile(context)
            folder = Path(bpy.path.abspath("//cmai_anatomy_profiles"))
            folder.mkdir(parents=True, exist_ok=True)
            safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", profile["profile_name"])
            target = folder / f"{safe}_{time.strftime('%Y%m%d_%H%M%S')}.json"
            target.write_text(json.dumps(profile, indent=2), encoding="utf-8")
            p.profile_path = str(target)
            p.profile_confirmed = True
            self.report({'INFO'}, f"Confirmed profile saved separately: {target.name}")
            return {'FINISHED'}
        except Exception as exc:
            p.profile_confirmed = False
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


class CMAI_OT_workflow_check(bpy.types.Operator):
    bl_idname = "cmai.multi_creature_workflow_check"
    bl_label = "Check Workflow Inputs"
    bl_description = "Check the selected mode without changing actions or requiring video in existing-animation mode"

    def execute(self, context):
        p = context.scene.cmai_anatomy
        try:
            if not p.profile_confirmed or not p.profile_path:
                raise ValueError("Detect, correct, and save a confirmed anatomy profile first")
            profile = json.loads(Path(bpy.path.abspath(p.profile_path)).read_text(encoding="utf-8"))
            if profile.get("armature") != p.armature.name:
                raise ValueError("Saved anatomy profile belongs to a different armature")
            if p.workflow == "EXISTING":
                action = bpy.data.actions.get(p.action_name)
                if action is None:
                    raise ValueError(f"Starting Action not found: {p.action_name}")
                status = "PASS_INPUTS_EXISTING_ACTION"
                details = {"workflow": "Improve Existing Animation", "action": action.name,
                           "frame_range": list(action.frame_range), "video_required": False}
            else:
                video = Path(bpy.path.abspath(p.reference_video)) if p.reference_video else None
                if not video or not video.is_file():
                    raise ValueError("Choose an existing reference video for this workflow")
                status = "PASS_INPUTS_REFERENCE_VIDEO"
                details = {"workflow": "Create Animation From Reference Video", "video": str(video),
                           "video_required": True,
                           "note": "Input validation only; this does not claim video-to-animation generation is complete."}
            report = {"status": status, "armature": p.armature.name,
                      "profile": str(Path(bpy.path.abspath(p.profile_path))),
                      "leg_count": len(profile.get("legs", [])), **details}
            outdir = Path(bpy.path.abspath("//cmai_anatomy_reports")); outdir.mkdir(parents=True, exist_ok=True)
            target = outdir / f"workflow_check_{time.strftime('%Y%m%d_%H%M%S')}.json"
            target.write_text(json.dumps(report, indent=2), encoding="utf-8")
            p.report_path = str(target)
            self.report({'INFO'}, f"{status}: {target.name}")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


class CMAI_OT_analyze_existing_action(bpy.types.Operator):
    bl_idname = "cmai.analyze_existing_action"
    bl_label = "Analyze Existing Action"
    bl_description = "Measure profiled limb motion and rest lengths without modifying the Action"

    def execute(self, context):
        p = context.scene.cmai_anatomy
        arm = p.armature
        created_anim_data = False
        previous_action = previous_slot = None
        previous_frame = context.scene.frame_current
        try:
            if p.workflow != "EXISTING":
                raise ValueError("Select Improve Existing Animation mode")
            if not arm or not p.profile_confirmed or not p.profile_path:
                raise ValueError("Choose an armature and save its confirmed anatomy profile first")
            profile_path = Path(bpy.path.abspath(p.profile_path))
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            if profile.get("armature") != arm.name or not profile.get("confirmed"):
                raise ValueError("Confirmed profile does not match the selected armature")
            action = bpy.data.actions.get(p.action_name)
            if action is None:
                raise ValueError(f"Starting Action not found: {p.action_name}")

            if arm.animation_data is None:
                arm.animation_data_create()
                created_anim_data = True
            else:
                previous_action = arm.animation_data.action
                previous_slot = getattr(arm.animation_data, "action_slot", None)
            arm.animation_data.action = action
            # Blender 4.4+ layered Actions may have slots. Bind a compatible slot
            # when available, while preserving the armature's previous slot.
            slots = getattr(action, "slots", None)
            if slots and len(slots):
                slot = next((s for s in slots if s.target_id_type == 'OBJECT'), slots[0])
                try:
                    arm.animation_data.action_slot = slot
                except (AttributeError, TypeError):
                    pass

            start, end = map(float, action.frame_range)
            first, last = int(math.floor(start)), int(math.ceil(end))
            if last < first:
                raise ValueError("Action has an invalid frame range")
            scene = context.scene
            original_fps = scene.render.fps / scene.render.fps_base
            reports = []
            for leg in profile.get("legs", []):
                chain = leg.get("bones", [])
                missing = [name for name in chain if name not in arm.data.bones]
                if len(chain) < 2 or missing:
                    raise ValueError(f"{leg.get('name', 'limb')}: invalid profile chain; missing {missing}")
                if any(arm.data.bones[chain[i]].parent != arm.data.bones[chain[i - 1]]
                       for i in range(1, len(chain))):
                    raise ValueError(f"{leg.get('name', 'limb')}: chain is not contiguous in the armature hierarchy")
                rest_lengths = [float(arm.data.bones[name].length) for name in chain]
                paths = {name: 0.0 for name in chain}
                previous_heads = {}
                endpoint_samples = []
                for frame in range(first, last + 1):
                    scene.frame_set(frame)
                    context.view_layer.update()
                    for name in chain:
                        pb = arm.pose.bones[name]
                        head = arm.matrix_world @ pb.head
                        if name in previous_heads:
                            paths[name] += (head - previous_heads[name]).length
                        previous_heads[name] = head.copy()
                    foot = arm.matrix_world @ arm.pose.bones[chain[-1]].tail
                    endpoint_samples.append(tuple(float(v) for v in foot))
                reports.append({
                    "name": leg.get("name", chain[0]), "side": leg.get("side", "unknown"),
                    "bones": chain, "contact_bone": leg.get("contact_bone"),
                    "rest_bone_lengths": rest_lengths,
                    "bone_head_path_length_world_units": paths,
                    "terminal_tail_world_bounds": {
                        "min": [min(point[i] for point in endpoint_samples) for i in range(3)],
                        "max": [max(point[i] for point in endpoint_samples) for i in range(3)]},
                    "evaluated_frames": len(endpoint_samples)})

            report = {
                "schema_version": 1, "status": "READ_ONLY_ACTION_ANALYSIS",
                "armature": arm.name, "profile": str(profile_path), "action": action.name,
                "frame_range": [first, last], "fps": original_fps,
                "video_required": False, "action_modified": False,
                "animation_data_restored": True,
                "appendage_bone_counts": {role: len(profile.get(key, [])) for role, key in
                                           (("body", "body_bones"), ("head", "head_bones"),
                                            ("wings", "wing_bones"), ("tail", "tail_bones"))},
                "legs": reports,
                "limitations": ["Motion paths describe bone-head translation; this is not a contact or collision validation.",
                                "No bone rotations, keys, mesh, or source Action were changed."]}
            outdir = Path(bpy.path.abspath("//cmai_anatomy_reports"))
            outdir.mkdir(parents=True, exist_ok=True)
            target = outdir / f"action_analysis_{time.strftime('%Y%m%d_%H%M%S')}.json"
            target.write_text(json.dumps(report, indent=2), encoding="utf-8")
            p.report_path = str(target)
            self.report({'INFO'}, f"Read-only analysis saved: {target.name}")
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        finally:
            if arm and arm.animation_data:
                if created_anim_data:
                    arm.animation_data_clear()
                else:
                    arm.animation_data.action = previous_action
                    if previous_slot is not None:
                        try:
                            arm.animation_data.action_slot = previous_slot
                        except (AttributeError, TypeError):
                            pass
            context.scene.frame_set(previous_frame)


class CMAI_PT_multi_creature(bpy.types.Panel):
    bl_label = "Multi-Creature Setup"
    bl_idname = "CMAI_PT_multi_creature_setup"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Creature Motion AI"

    def draw(self, context):
        layout = self.layout
        p = context.scene.cmai_anatomy
        layout.label(text="Reusable anatomy profile", icon='ARMATURE_DATA')
        layout.prop(p, "armature")
        layout.operator("cmai.anatomy_profile_detect", icon='VIEWZOOM')
        if p.legs:
            layout.prop(p, "profile_name")
            for index, row in enumerate(p.legs):
                box = layout.box()
                box.label(text=f"Limb {index + 1}: {row.name}", icon='BONE_DATA')
                box.prop(row, "bones_csv", text="Chain")
                box.prop(row, "contact_bone")
                rowline = box.row(align=True)
                rowline.prop(row, "side", text="Side")
                rowline.prop(row, "identity_confirmed", text="Identity confirmed")
            for prop in ("body_bones_csv", "head_bones_csv", "wing_bones_csv", "tail_bones_csv"):
                layout.prop(p, prop)
            layout.operator("cmai.anatomy_profile_confirm_save", icon='FILE_TICK')
            layout.label(text="Confirmed" if p.profile_confirmed else "Proposal needs review",
                         icon='CHECKMARK' if p.profile_confirmed else 'INFO')
            if p.profile_path:
                layout.label(text=Path(bpy.path.abspath(p.profile_path)).name)
        layout.separator()
        layout.label(text="Choose workflow")
        layout.prop(p, "workflow", expand=True)
        if p.workflow == 'EXISTING':
            layout.prop(p, "action_name")
            layout.label(text="No video required; analysis leaves the source Action untouched.")
            layout.operator("cmai.analyze_existing_action", icon='ANIM_DATA')
        else:
            layout.prop(p, "reference_video")
            layout.label(text="Video solving remains a separate validation stage.", icon='INFO')
        layout.operator("cmai.multi_creature_workflow_check", icon='CHECKMARK')
        if p.report_path:
            layout.label(text=Path(bpy.path.abspath(p.report_path)).name, icon='TEXT')


CLASSES = (CMAI_AnatomyLeg, CMAI_AnatomySettings, CMAI_OT_profile_detect,
           CMAI_OT_profile_confirm_save, CMAI_OT_workflow_check,
           CMAI_OT_analyze_existing_action, CMAI_PT_multi_creature)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cmai_anatomy = PointerProperty(type=CMAI_AnatomySettings)


def unregister():
    if hasattr(bpy.types.Scene, "cmai_anatomy"):
        del bpy.types.Scene.cmai_anatomy
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
