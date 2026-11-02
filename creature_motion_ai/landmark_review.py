"""Native Blender landmark review controls for the two-camera reference."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import bpy
from bpy.props import EnumProperty, IntProperty, StringProperty


CAMERAS = (("camera_A", "Camera A / side", "LEFT"), ("camera_B", "Camera B / front", "RIGHT"))


def _load_data(scene):
    path = bpy.path.abspath(scene.cmai_landmark_review_data)
    if not path or not Path(path).is_file():
        raise RuntimeError("Choose a landmark JSON file first")
    return Path(path), json.loads(Path(path).read_text(encoding="utf-8"))


def _frame(data, number):
    for row in data.get("frames", []):
        if int(row.get("frame", -1)) == number:
            return row
    raise RuntimeError(f"Frame {number} is not present in the landmark file")


def _set_image(area, path):
    if area and area.type == "IMAGE_EDITOR" and Path(path).is_file():
        image = bpy.data.images.load(str(path), check_existing=True)
        area.spaces.active.image = image


class CMAI_OT_review_load_image(bpy.types.Operator):
    bl_idname = "cmai.review_load_image"
    bl_label = "Load Reference Image"

    def execute(self, context):
        scene = context.scene
        try:
            _, data = _load_data(scene)
            root = Path(bpy.path.abspath(scene.cmai_landmark_review_samples))
            name = f"frame_{scene.cmai_landmark_review_frame:06d}_{scene.cmai_landmark_review_camera}.png"
            path = root / name
            if not path.is_file():
                raise RuntimeError(f"Reference image not found: {path}")
            _set_image(context.area, path)
            self.report({'INFO'}, f"Loaded {path.name}. Use an Image Editor area for correction.")
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


class CMAI_OT_review_correct(bpy.types.Operator):
    bl_idname = "cmai.review_correct_landmark"
    bl_label = "Correct Landmark (Click Image)"
    bl_options = {'BLOCKING'}

    _moving = False

    def invoke(self, context, event):
        if context.area.type != "IMAGE_EDITOR":
            self.report({'ERROR'}, "Run this operator from an Image Editor area")
            return {'CANCELLED'}
        self._moving = False
        context.window_manager.modal_handler_add(self)
        self.report({'INFO'}, "Click the corrected landmark position; Esc cancels")
        return {'RUNNING_MODAL'}


class CMAI_OT_review_track(bpy.types.Operator):
    bl_idname = "cmai.review_track"
    bl_label = "Track Landmarks"
    direction: EnumProperty(items=(("FORWARD", "Forward", "Track forward"), ("BACKWARD", "Backward", "Track backward")), default="FORWARD")

    def execute(self, context):
        scene = context.scene
        script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools", "track_leg_landmarks.py"))
        output = bpy.path.abspath(scene.cmai_landmark_review_output)
        video = bpy.path.abspath(scene.cmai_video)
        seeds = bpy.path.abspath(scene.cmai_landmark_review_data)
        if not all(os.path.isfile(x) for x in (script, video, seeds)):
            self.report({'ERROR'}, "Set MP4 Video and Landmark JSON first")
            return {'CANCELLED'}
        command = [sys.executable, script, video, seeds, "--output", output, "--max-frames", str(scene.cmai_landmark_review_max_frames)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode:
            self.report({'ERROR'}, result.stderr[-500:] or "Tracking failed")
            return {'CANCELLED'}
        self.report({'INFO'}, f"{self.direction.title()} tracking written to {output}; review remains provisional")
        return {'FINISHED'}


class CMAI_OT_review_validate(bpy.types.Operator):
    bl_idname = "cmai.review_validate"
    bl_label = "Validate Tracking"

    def execute(self, context):
        scene = context.scene
        try:
            path, data = _load_data(scene)
            rows = data.get("frames", [])[:scene.cmai_landmark_review_max_frames]
            leg_names = sorted({p.get("leg") for row in rows for p in row.get("points", []) if p.get("leg")})
            report = {"status": "native_review_validation", "frames": len(rows), "legs": {}, "animation_enabled": False}
            for leg in leg_names:
                complete = 0
                for row in rows:
                    names = [p for p in row.get("points", []) if p.get("leg") == leg]
                    visible = {p.get("name") for p in names if p.get("state") in ("manual_reviewed", "proposal", "optical_flow")}
                    if len(visible) >= 3:
                        complete += 1
                report["legs"][leg] = {"complete_visible_frames": complete, "tracked_fraction": complete / max(len(rows), 1)}
            report["complete_all_leg_frames"] = sum(x["complete_visible_frames"] == len(rows) for x in report["legs"].values()) == len(report["legs"]) and bool(report["legs"])
            out = Path(bpy.path.abspath(scene.cmai_landmark_review_report))
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, indent=2), encoding="utf-8")
            self.report({'INFO'}, f"Validation saved: {out.name}; animation remains disabled")
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            return {'CANCELLED'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            region = context.region
            view = region.view2d.region_to_view(event.mouse_region_x, event.mouse_region_y)
            scene = context.scene
            try:
                path, data = _load_data(scene)
                row = _frame(data, scene.cmai_landmark_review_frame)
                camera = scene.cmai_landmark_review_camera
                item = row.setdefault(camera, {}).setdefault("landmarks", {}).setdefault(scene.cmai_landmark_review_landmark, {})
                item.update({"x": float(view[0]), "y": float(view[1]), "visible": True, "state": "manual_reviewed", "source": "blender_image_editor"})
                path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                self.report({'INFO'}, f"Saved {scene.cmai_landmark_review_landmark} at ({view[0]:.1f}, {view[1]:.1f})")
                return {'FINISHED'}
            except Exception as exc:
                self.report({'ERROR'}, str(exc))
                return {'CANCELLED'}
        return {'RUNNING_MODAL'}


class CMAI_PT_landmark_review(bpy.types.Panel):
    bl_label = "Landmark Review"
    bl_idname = "CMAI_PT_landmark_review"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Creature Motion AI"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene, "cmai_landmark_review_data")
        layout.prop(scene, "cmai_landmark_review_samples")
        layout.prop(scene, "cmai_landmark_review_frame")
        layout.prop(scene, "cmai_landmark_review_camera")
        layout.prop(scene, "cmai_landmark_review_landmark")
        layout.operator("cmai.review_load_image", icon='IMAGE_DATA')
        layout.operator("cmai.review_correct_landmark", icon='PIVOT_CURSOR')
        layout.prop(scene, "cmai_landmark_review_output")
        row = layout.row(align=True)
        op = row.operator("cmai.review_track", text="Track Forward", icon='FORWARD')
        op.direction = "FORWARD"
        op = row.operator("cmai.review_track", text="Track Backward", icon='BACK')
        op.direction = "BACKWARD"
        layout.prop(scene, "cmai_landmark_review_report")
        layout.prop(scene, "cmai_landmark_review_max_frames")
        layout.operator("cmai.review_validate", icon='CHECKMARK')
        layout.label(text="Only manually reviewed points are written.", icon='INFO')
        layout.label(text="Hidden points remain uncertain; no guess is added.")


CLASSES = (CMAI_OT_review_load_image, CMAI_OT_review_correct, CMAI_OT_review_track, CMAI_OT_review_validate, CMAI_PT_landmark_review)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cmai_landmark_review_data = StringProperty(name="Landmark JSON", subtype='FILE_PATH', default="//data/generated/landmark_reviewed.json")
    bpy.types.Scene.cmai_landmark_review_samples = StringProperty(name="Reference Frames", subtype='DIR_PATH', default="//data/generated/goodsplitbalisk_pipeline_v2/samples")
    bpy.types.Scene.cmai_landmark_review_frame = IntProperty(name="Reference Frame", default=1, min=1, max=241)
    bpy.types.Scene.cmai_landmark_review_camera = EnumProperty(name="Camera", items=CAMERAS, default="camera_A")
    bpy.types.Scene.cmai_landmark_review_landmark = StringProperty(name="Landmark", default="Leg_Front.L_01_head")
    bpy.types.Scene.cmai_landmark_review_output = StringProperty(name="Tracked Output", subtype='FILE_PATH', default="//data/generated/native_tracked_landmarks_24.json")
    bpy.types.Scene.cmai_landmark_review_report = StringProperty(name="Validation Report", subtype='FILE_PATH', default="//data/generated/native_tracking_report.json")
    bpy.types.Scene.cmai_landmark_review_max_frames = IntProperty(name="Max Frames", default=24, min=1, max=241)


def unregister():
    for name in ("cmai_landmark_review_data", "cmai_landmark_review_samples", "cmai_landmark_review_frame", "cmai_landmark_review_camera", "cmai_landmark_review_landmark", "cmai_landmark_review_output", "cmai_landmark_review_report", "cmai_landmark_review_max_frames"):
        delattr(bpy.types.Scene, name)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
