"""Native Blender landmark review controls for the two-camera reference."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.props import EnumProperty, IntProperty, StringProperty


CAMERAS = (("camera_A", "Camera A / side", "LEFT"), ("camera_B", "Camera B / front", "RIGHT"))
LEG_COLORS = ((0.9,0.2,0.2,1),(0.2,0.8,0.2,1),(0.2,0.5,1,1),(1,0.6,0.1,1),(0.8,0.2,0.8,1),(0.1,0.8,0.8,1),(1,0.9,0.1,1),(0.7,0.7,0.7,1))


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


def _all_points(row, camera):
    return row.get(camera, {}).get("landmarks", {})


def _leg_index(name):
    for i, leg in enumerate(("Front.L", "Front.R", "MidFront.L", "MidFront.R", "MidRear.L", "MidRear.R", "Rear.L", "Rear.R")):
        if name.startswith("Leg_" + leg): return i
    return 0


class CMAI_OT_review_all_landmarks(bpy.types.Operator):
    bl_idname = "cmai.review_all_landmarks"
    bl_label = "Review All Landmarks"
    _handle = None
    _active = None
    _dragging = False

    def _draw(self, context):
        try: _, data = _load_data(context.scene); row = _frame(data, context.scene.cmai_landmark_review_frame); pts = _all_points(row, context.scene.cmai_landmark_review_camera)
        except Exception: return
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        region = context.region
        def xy(item): return region.view2d.view_to_region(float(item.get('x',0)), float(item.get('y',0)), clip=False)
        for leg in ("Front.L", "Front.R", "MidFront.L", "MidFront.R", "MidRear.L", "MidRear.R", "Rear.L", "Rear.R"):
            names=[f"Leg_{leg}_{part}" for part in ("hip","knee","ankle","foot")]
            coords=[xy(pts[n]) for n in names if n in pts and pts[n].get('visible')]
            if len(coords)>1:
                batch=batch_for_shader(shader,'LINE_STRIP',{'pos':coords}); shader.bind(); shader.uniform_float('color',LEG_COLORS[_leg_index(names[0])]); batch.draw(shader)
        for name,item in pts.items():
            if not item.get('visible'): continue
            x,y=xy(item); color=(1,1,1,1) if item.get('state')=='manual_reviewed' else (1,0.5,0.1,1) if item.get('state')=='model_prediction' else LEG_COLORS[_leg_index(name)]
            batch=batch_for_shader(shader,'POINTS',{'pos':[(x,y)]}); shader.bind(); shader.uniform_float('color',color); gpu.state.point_size_set(9); batch.draw(shader)

    def invoke(self, context, event):
        if context.area.type != 'IMAGE_EDITOR': self.report({'ERROR'}, 'Run from an Image Editor area'); return {'CANCELLED'}
        if self._handle is None: self._handle=bpy.types.SpaceImageEditor.draw_handler_add(self._draw,(context,), 'WINDOW','POST_PIXEL')
        context.area.tag_redraw(); context.window_manager.modal_handler_add(self); self.report({'INFO'}, 'Review All active: drag points; click Hide/Uncertain in the panel'); return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC','RIGHTMOUSE'}:
            if self._handle: bpy.types.SpaceImageEditor.draw_handler_remove(self._handle,'WINDOW'); self._handle=None
            context.area.tag_redraw(); return {'CANCELLED'}
        try: _, data=_load_data(context.scene); row=_frame(data,context.scene.cmai_landmark_review_frame); pts=_all_points(row,context.scene.cmai_landmark_review_camera); view=context.region.view2d.region_to_view(event.mouse_region_x,event.mouse_region_y)
        except Exception: return {'RUNNING_MODAL'}
        if event.type=='LEFTMOUSE' and event.value=='PRESS':
            candidates=[(name,item) for name,item in pts.items() if item.get('visible') and ((float(item.get('x',0))-view[0])**2+(float(item.get('y',0))-view[1])**2)<18**2]
            if candidates: self._active=min(candidates,key=lambda z:(float(z[1].get('x',0))-view[0])**2+(float(z[1].get('y',0))-view[1])**2)[0]; self._dragging=True
        elif event.type=='MOUSEMOVE' and self._dragging and self._active:
            pts[self._active].update({'x':float(view[0]),'y':float(view[1]),'visible':True,'state':'manual_reviewed','confidence':1.0,'source':'native_review_drag'}); Path(bpy.path.abspath(context.scene.cmai_landmark_review_data)).write_text(json.dumps(data,indent=2)); context.area.tag_redraw()
        elif event.type=='LEFTMOUSE' and event.value=='RELEASE':
            if self._active:
                base=pts[self._active]
                for delta in (-2,-1,1,2):
                    try:
                        near=_frame(data,context.scene.cmai_landmark_review_frame+delta); target=_all_points(near,context.scene.cmai_landmark_review_camera).setdefault(self._active,{})
                        if target.get('state') not in ('manual_reviewed',): target.update({'x':base.get('x'),'y':base.get('y'),'visible':base.get('visible',True),'confidence':0.55,'state':'provisional_prediction','source':'native_review_propagation'})
                    except Exception: pass
                Path(bpy.path.abspath(context.scene.cmai_landmark_review_data)).write_text(json.dumps(data,indent=2))
            self._dragging=False; self._active=None
        return {'RUNNING_MODAL'}


class CMAI_OT_review_frame_step(bpy.types.Operator):
    bl_idname='cmai.review_frame_step'; bl_label='Step Review Frame'; direction:IntProperty(default=1)
    def execute(self,context): context.scene.cmai_landmark_review_frame=max(1,min(context.scene.cmai_landmark_review_max_frames,context.scene.cmai_landmark_review_frame+self.direction)); context.area.tag_redraw(); return {'FINISHED'}


class CMAI_OT_review_hide_uncertain(bpy.types.Operator):
    bl_idname='cmai.review_hide_uncertain'; bl_label='Hide / Uncertain'
    def execute(self,context):
        try: path,data=_load_data(context.scene); row=_frame(data,context.scene.cmai_landmark_review_frame); item=_all_points(row,context.scene.cmai_landmark_review_camera).get(context.scene.cmai_landmark_review_landmark,{}); item.update({'visible':False,'confidence':0.0,'state':'uncertain_occluded'}); path.write_text(json.dumps(data,indent=2)); context.area.tag_redraw(); return {'FINISHED'}
        except Exception as exc: self.report({'ERROR'},str(exc)); return {'CANCELLED'}


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
        layout.operator("cmai.review_all_landmarks", icon='TRACKING')
        row = layout.row(align=True); op=row.operator("cmai.review_frame_step", text="Previous", icon='TRIA_LEFT'); op.direction=-1; op=row.operator("cmai.review_frame_step", text="Next", icon='TRIA_RIGHT'); op.direction=1
        layout.operator("cmai.review_hide_uncertain", icon='HIDE_OFF')
        try:
            _, data = _load_data(scene); row = _frame(data, scene.cmai_landmark_review_frame); pts = _all_points(row, scene.cmai_landmark_review_camera); reviewed=sum(1 for x in pts.values() if x.get('state')=='manual_reviewed'); uncertain=sum(1 for x in pts.values() if not x.get('visible') or x.get('state','').startswith('uncertain')); layout.label(text=f"Reviewed: {reviewed}  Uncertain: {uncertain}")
        except Exception: layout.label(text="Reviewed: —  Uncertain: —")
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


CLASSES = (CMAI_OT_review_load_image, CMAI_OT_review_correct, CMAI_OT_review_all_landmarks, CMAI_OT_review_frame_step, CMAI_OT_review_hide_uncertain, CMAI_OT_review_track, CMAI_OT_review_validate, CMAI_PT_landmark_review)


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
