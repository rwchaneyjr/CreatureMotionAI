"""Native Blender landmark review controls for the two-camera reference."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
import blf

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from .pose_library import load as load_pose_library, save as save_pose_library, add_observation
from .reference_leg_identity import (build_approved_track, prepare_review,
                                     sha256_file)


CAMERAS = (("camera_A", "Camera A / side", "LEFT"), ("camera_B", "Camera B / front", "RIGHT"))
LEG_COLORS = ((0.9,0.2,0.2,1),(0.2,0.8,0.2,1),(0.2,0.5,1,1),(1,0.6,0.1,1),(0.8,0.2,0.8,1),(0.1,0.8,0.8,1),(1,0.9,0.1,1),(0.7,0.7,0.7,1))


def _project_root(scene=None):
    """Find the repository root from the selected source .blend when installed as a ZIP."""
    if scene is not None:
        model = Path(bpy.path.abspath(getattr(scene, 'cmai_model', '') or '')).resolve()
        if model.is_file():
            for candidate in model.parents:
                if (candidate / 'creature_motion_ai').is_dir() and (candidate / 'data').is_dir():
                    return candidate
    return Path(__file__).resolve().parents[1]


def _project_path(value, scene=None):
    """Resolve project-relative paths independently of the .blend location.

    Blender's // prefix normally means the directory containing the blend file.
    CreatureMotionAI properties use //data/... as project-relative paths, so a
    blend saved below data/generated would otherwise produce data/generated/data/.
    """
    raw = str(value or "")
    if raw.startswith("//"):
        return str((_project_root(scene) / raw[2:]).resolve())
    relative = Path(raw)
    if not relative.is_absolute() and relative.parts and relative.parts[0].lower() == 'data':
        return str((_project_root(scene) / relative).resolve())
    return bpy.path.abspath(raw)


def _load_data(scene):
    path = _project_path(scene.cmai_landmark_review_data, scene)
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


def _review_image_height(scene, area=None):
    """Height of the displayed still, used to convert Blender bottom-up Y to OpenCV top-down Y."""
    if area and area.type == 'IMAGE_EDITOR':
        image = area.spaces.active.image
        if image:
            return int(image.size[1])
    try:
        _, data = _load_data(scene)
        return int(data.get('review_image_size', [0, 0])[1])
    except Exception:
        return 0


def _view_to_image_xy(region, mouse_x, mouse_y, image_height):
    """Convert Image Editor view coordinates to the review JSON's OpenCV coordinates."""
    view_x, view_y = region.view2d.region_to_view(mouse_x, mouse_y)
    return float(view_x), float(image_height - view_y)


def _image_to_view_xy(x, y, image_height):
    """Convert OpenCV top-left-origin pixels to Blender Image Editor coordinates."""
    return float(x), float(image_height - y)

def _review_point_names(leg):
    """Use the single selected rig leg, or generic names for an unassigned track."""
    generic = tuple(f"Leg_Reference_{part}" for part in ("hip", "knee", "ankle", "foot"))
    if leg == 'UNVERIFIED':
        return generic
    return tuple(f"Leg_{leg}_{part}" for part in ("hip", "knee", "ankle", "foot"))


def _selected_review_points(row, camera, scene):
    all_points = _all_points(row, camera)
    selected = _review_point_names(scene.cmai_reference_leg_identity)
    if any(name in all_points for name in selected):
        return {name: all_points[name] for name in selected if name in all_points}
    # The current DLC source file represents one track, so its four points use
    # neutral Leg_Reference_* names until the user explicitly assigns identity.
    generic = tuple(f"Leg_Reference_{part}" for part in ("hip", "knee", "ankle", "foot"))
    return {name: all_points[name] for name in generic if name in all_points}

class CMAI_OT_verify_reference_leg(bpy.types.Operator):
    bl_idname = 'cmai.verify_reference_leg'
    bl_label = 'Prepare Reference Leg Review'
    def execute(self, context):
        scene=context.scene; root=_project_root(scene)
        video=Path(bpy.path.abspath(scene.cmai_video)).resolve()
        track=Path(_project_path(scene.cmai_landmark_review_track, scene)).resolve()
        if not video.is_file(): self.report({'ERROR'},'Select the current side-view MP4 in the main Creature Motion AI panel first'); return {'CANCELLED'}
        if not track.is_file(): self.report({'ERROR'},f'Prediction track not found: {track}'); return {'CANCELLED'}
        video_hash=sha256_file(video); track_hash=sha256_file(track)
        # Mapping-profile suffix isolates corrected crop coordinates from the
        # earlier horizontally-compressed review and leaves its evidence intact.
        out=root/'data/generated/reference_leg_identity_review'/f'{video_hash[:10]}_{track_hash[:10]}_leftpanel_v2'
        target=out/'landmark_review.json'
        # Preserve corrections if this exact video/track pair was already prepared.
        reusable=False
        if target.is_file():
            try:
                old=json.loads(target.read_text(encoding='utf-8'))
                reusable=(old.get('source_video_sha256')==video_hash and old.get('source_track_sha256')==track_hash)
            except (OSError,ValueError):
                reusable=False
        if not reusable:
            # Keep the review workflow self-contained when installed from the
            # add-on ZIP; do not assume the repository's tools/ folder exists.
            script=Path(__file__).with_name('prepare_review_cli.py')
            python=bpy.path.abspath(getattr(scene,'cmai_python','')) or sys.executable
            result=subprocess.run([python,str(script),str(video),str(track),str(out)],capture_output=True,text=True)
            if result.returncode:
                self.report({'ERROR'},(result.stderr or result.stdout)[-700:] or 'Could not prepare native review'); return {'CANCELLED'}
        data=json.loads(target.read_text(encoding='utf-8'))
        scene.cmai_landmark_review_data=str(target); scene.cmai_landmark_review_samples=str(out)
        scene.cmai_landmark_review_frame=int(data['frames'][0]['frame'])
        scene.cmai_landmark_review_camera='camera_A'; scene.cmai_landmark_review_landmark='Leg_Reference_hip'
        scene.cmai_reference_leg_identity='UNVERIFIED'
        try: _set_image(context.area,out/f"frame_{scene.cmai_landmark_review_frame:06d}_camera_A.png")
        except Exception: pass
        self.report({'INFO'},f"Loaded {len(data['frames'])} suggested frames. Every point is still a prediction; no identity is approved.")
        return {'FINISHED'}

class CMAI_OT_reference_leg_approve_save(bpy.types.Operator):
    bl_idname='cmai.reference_leg_approve_save'; bl_label='Confirm Identity & Save Evidence'
    def execute(self,context):
        scene=context.scene
        try:
            path,data=_load_data(scene); leg=scene.cmai_reference_leg_identity
            if leg=='UNVERIFIED' or scene.cmai_identity_confirmed_leg != leg:
                raise RuntimeError('Select and highlight the physical rig chain, then click Confirm Physical Leg Identity before approval.')
            video=Path(bpy.path.abspath(scene.cmai_video)).resolve()
            source_track=Path(_project_path(scene.cmai_landmark_review_track, scene)).resolve()
            if not video.is_file() or not source_track.is_file(): raise RuntimeError('Current source video or prediction track is missing.')
            if sha256_file(video)!=data.get('source_video_sha256') or str(video)!=data.get('source_video'):
                raise RuntimeError('The selected video differs from the video used to prepare this review; prepare again.')
            if sha256_file(source_track)!=data.get('source_track_sha256') or str(source_track)!=data.get('source_track'):
                raise RuntimeError('The selected prediction track has changed since review preparation; prepare again.')
            armature,bones=_find_leg_chain(leg)
            approved=build_approved_track(data,leg)
            complete_frames = [row for row in approved['frames'] if all(
                row.get('landmark_status', {}).get(part) == 'manually_reviewed'
                for part in ('hip', 'knee', 'ankle', 'foot'))]
            if len(complete_frames)<2:
                raise RuntimeError('Manually place and mark H/K/A/F VISIBLE in at least two frames before approval.')
            stamp=datetime.now().strftime('%Y%m%dT%H%M%S')
            token=hashlib.sha256(json.dumps({'review':data,'leg':leg,'bones':bones},sort_keys=True).encode()).hexdigest()[:10]
            out=path.parent; evidence_path=out/f'approved_landmarks_track_{stamp}_{token}.json'
            evidence_path.write_text(json.dumps(approved,indent=2),encoding='utf-8')
            manifest={'schema_version':1,'status':'approved','identity_verified':True,'leg':approved['leg'],
                      'source_video':str(video),'source_video_sha256':sha256_file(video),
                      'source_prediction_track':str(source_track),'source_prediction_track_sha256':sha256_file(source_track),
                      'review_json':str(path),'review_json_sha256':sha256_file(path),
                      'approved_track':str(evidence_path),'track_sha256':sha256_file(evidence_path),
                      'rig_armature':armature.name,'rig_chain_bones':bones,
                      'approved_frames':[row['frame'] for row in approved['frames']],
                      'complete_visible_chain_frames':[row['frame'] for row in complete_frames],
                      'identity_confirmation':'USER_CONFIRMED_IN_BLENDER',
                      'approval_method':'explicit user confirmation after manually confirming H/K/A/F image points and highlighting the rig chain',
                      'animation_candidate_allowed':False,
                      'next_gates':['independent 3D fit','bone reachability','anatomical/joint-limit validation','physical deformation/contact validation']}
            manifest_path=out/f'identity_approval_{stamp}_{token}.json'; manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
            report_path=out/f'step_event_report_{stamp}_{token}.json'
            python=bpy.path.abspath(getattr(scene,'cmai_python','')) or sys.executable
            script=Path(__file__).with_name('analyze_step_events_cli.py')
            result=subprocess.run([python,str(script),str(evidence_path),str(report_path),'--approval',str(manifest_path)],capture_output=True,text=True)
            if result.returncode: raise RuntimeError('Identity evidence saved, but step-event analysis failed: '+(result.stderr or result.stdout)[-500:])
            scene.cmai_landmark_review_report=str(report_path)
            scene.cmai_identity_approval_file=str(manifest_path)
            self.report({'INFO'},f"Identity evidence saved for {leg}; {len(approved['frames'])} manually reviewed frames. 3D/anatomy gates remain required.")
            return {'FINISHED'}
        except Exception as exc: self.report({'ERROR'},str(exc)); return {'CANCELLED'}


def _find_leg_chain(leg):
    armatures=[obj for obj in bpy.data.objects if obj.type=='ARMATURE']
    exact=[obj for obj in armatures if obj.name=='CrimsonSpineBehemoth_Rig']
    candidates=exact or armatures
    if len(candidates)!=1: raise RuntimeError('Select/open the original Balisk rig; expected one identifiable armature.')
    armature=candidates[0]
    names=[f'Leg_{leg}_{index:02d}' for index in (1,2,3)]
    missing=[name for name in names if name not in armature.data.bones]
    if missing: raise RuntimeError('Rig chain is incomplete: '+', '.join(missing))
    actual = tuple(armature.data.bones[name].parent.name if armature.data.bones[name].parent else None for name in names)
    if actual[1:] != (names[0], names[1]):
        raise RuntimeError(f'Rig hierarchy for {leg} is not a continuous three-bone chain: {actual}.')
    return armature,names


class CMAI_OT_confirm_reference_leg_identity(bpy.types.Operator):
    bl_idname='cmai.confirm_reference_leg_identity'; bl_label='Confirm Physical Leg Identity'
    bl_description='Explicitly confirm that the selected video chain is the highlighted Blender rig leg'
    def execute(self, context):
        scene=context.scene; leg=scene.cmai_reference_leg_identity
        try:
            if leg=='UNVERIFIED': raise RuntimeError('Choose the physical rig leg that you verified in the video first.')
            armature,names=_find_leg_chain(leg)
            scene.cmai_identity_confirmed_leg=leg
            scene.cmai_identity_confirmed_rig=armature.name
            scene.cmai_identity_confirmed_bones=','.join(names)
            context.area.tag_redraw()
            self.report({'INFO'},f'Confirmed video leg as {leg}: {names[0]} head → {names[0]} tail/{names[1]} head → {names[1]} tail/{names[2]} head → {names[2]} tail.')
            return {'FINISHED'}
        except Exception as exc:
            scene.cmai_identity_confirmed_leg=''
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class CMAI_OT_highlight_reference_leg_chain(bpy.types.Operator):
    bl_idname='cmai.highlight_reference_leg_chain'; bl_label='Highlight Selected Rig Chain'
    bl_description='Select the original three-bone chain in Pose Mode without changing its pose'
    def execute(self,context):
        try:
            leg=context.scene.cmai_reference_leg_identity
            if leg=='UNVERIFIED': raise RuntimeError('Choose the candidate rig leg first.')
            armature,names=_find_leg_chain(leg)
            if context.object and context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT'); armature.select_set(True); context.view_layer.objects.active=armature
            bpy.ops.object.mode_set(mode='POSE')
            for bone in armature.data.bones: bone.select=False
            for name in names:
                bone=armature.data.bones[name]; bone.select=True; bone.select_head=True; bone.select_tail=True
            armature.data.bones.active=armature.data.bones[names[0]]
            self.report({'INFO'},f'Highlighted {leg}: '+', '.join(names)+'; no transforms changed.')
            return {'FINISHED'}
        except Exception as exc: self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class CMAI_OT_review_confirm_landmark(bpy.types.Operator):
    bl_idname='cmai.review_confirm_landmark'; bl_label='Confirm Landmark Here'
    def execute(self,context):
        try:
            path,data=_load_data(context.scene); row=_frame(data,context.scene.cmai_landmark_review_frame)
            item=_all_points(row,context.scene.cmai_landmark_review_camera).get(context.scene.cmai_landmark_review_landmark)
            if (not item or not item.get('visible') or not all(k in item for k in ('x','y'))
                    or item.get('source') not in {'native_review_click','native_review_drag'}):
                raise RuntimeError('Place this point manually on a clearly visible anatomical location first. A DLC prediction cannot be confirmed in place.')
            item.update({'state':'manual_reviewed','confidence':1.0,
                         'visibility_status':'MANUALLY_CONFIRMED_VISIBLE',
                         'source':'native_review_user_confirmed'})
            path.write_text(json.dumps(data,indent=2),encoding='utf-8')
            context.area.tag_redraw(); self.report({'INFO'},f"Confirmed {context.scene.cmai_landmark_review_landmark} in source frame {context.scene.cmai_landmark_review_frame}.")
            return {'FINISHED'}
        except Exception as exc: self.report({'ERROR'},str(exc)); return {'CANCELLED'}

class CMAI_OT_pose_library_load(bpy.types.Operator):
    bl_idname='cmai.pose_library_load'; bl_label='Load Approved Pose Observations'
    def execute(self, context):
        scene=context.scene; path=Path(bpy.path.abspath(scene.cmai_pose_library_data))
        if not path.is_file(): self.report({'ERROR'},'Pose library file not found'); return {'CANCELLED'}
        data=load_pose_library(path); target=Path(bpy.path.abspath(scene.cmai_landmark_review_data)); current=json.loads(target.read_text(encoding='utf-8'))
        row=_frame(current,scene.cmai_landmark_review_frame); view='side' if scene.cmai_landmark_review_camera=='camera_A' else 'front'
        copied=0
        for obs in data.get('observations',[]):
            if int(obs.get('frame',-1))!=scene.cmai_landmark_review_frame or obs.get('view')!=view or obs.get('approval_status') not in ('manual_verified','approved'): continue
            pts=_all_points(row,scene.cmai_landmark_review_camera)
            for name,item in obs.get('landmarks',{}).items():
                if item.get('visible') is False: continue
                pts.setdefault(name,{}).update(item); pts[name]['state']='manual_reviewed'; pts[name]['confidence']=obs.get('confidence',{}).get(name,pts[name].get('confidence',1.0)); copied+=1
        target.write_text(json.dumps(current,indent=2),encoding='utf-8'); context.area.tag_redraw(); self.report({'INFO'},f'Loaded {copied} approved visible observations'); return {'FINISHED'}

class CMAI_OT_pose_library_export_current(bpy.types.Operator):
    bl_idname='cmai.pose_library_export_current'; bl_label='Save Current Review to Pose Library'
    def execute(self, context):
        scene=context.scene; _,data=_load_data(scene); row=_frame(data,scene.cmai_landmark_review_frame); pts=_all_points(row,scene.cmai_landmark_review_camera); view='side' if scene.cmai_landmark_review_camera=='camera_A' else 'front'; lib=load_pose_library(Path(bpy.path.abspath(scene.cmai_pose_library_data)))
        landmarks={n:{k:v for k,v in item.items() if k in ('x','y','visible','state')} for n,item in pts.items() if item.get('visible')}
        add_observation(lib,source_video=bpy.path.abspath(scene.cmai_video),frame=scene.cmai_landmark_review_frame,view=view,landmarks=landmarks,confidence={n:float(v.get('confidence',1.0)) for n,v in pts.items() if v.get('visible')},approval_status='manual_verified')
        save_pose_library(Path(bpy.path.abspath(scene.cmai_pose_library_data)),lib); self.report({'INFO'},'Current visible review saved to pose library'); return {'FINISHED'}


class CMAI_OT_review_load_image(bpy.types.Operator):
    bl_idname = "cmai.review_load_image"
    bl_label = "Load Reference Image"

    def execute(self, context):
        scene = context.scene
        try:
            _, data = _load_data(scene)
            root = Path(_project_path(scene.cmai_landmark_review_samples, scene))
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


class CMAI_OT_review_one_click_setup(bpy.types.Operator):
    bl_idname = "cmai.review_one_click_setup"
    bl_label = "Load Balisk Review Frame"
    bl_description = "Fill the standard 24-frame review paths and display the first side frame"

    def execute(self, context):
        scene = context.scene
        project = Path(__file__).resolve().parents[1]
        data = project / "data/generated/goodsplitbalisk_pipeline_v2/leg_identity_review_24_visible_v3/initial_landmarks.json"
        samples = project / "data/generated/goodsplitbalisk_pipeline_v2/samples"
        if not data.is_file() or not samples.is_dir():
            self.report({'ERROR'}, "Standard 24-frame review data is missing")
            return {'CANCELLED'}
        scene.cmai_landmark_review_data = str(data)
        scene.cmai_landmark_review_samples = str(samples)
        scene.cmai_landmark_review_frame = 1
        scene.cmai_landmark_review_camera = 'camera_A'
        scene.cmai_landmark_review_landmark = 'Leg_Front.L_01_head'
        path = samples / "frame_000001_camera_A.png"
        _set_image(context.area, path)
        self.report({'INFO'}, "Loaded side reference frame 1. Select a landmark and click Correct Landmark.")
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

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            return {'CANCELLED'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            try:
                scene = context.scene
                path, data = _load_data(scene)
                row = _frame(data, scene.cmai_landmark_review_frame)
                camera = scene.cmai_landmark_review_camera
                landmarks = row.setdefault(camera, {}).setdefault('landmarks', {})
                name = scene.cmai_landmark_review_landmark
                height = _review_image_height(scene, context.area)
                if height <= 0:
                    raise RuntimeError('Load the review image before placing a landmark.')
                image_x, image_y = _view_to_image_xy(context.region, event.mouse_region_x,
                                                     event.mouse_region_y, height)
                item = landmarks.setdefault(name, {})
                item.update({'x': image_x, 'y': image_y, 'visible': True,
                             'state': 'manual_reviewed', 'confidence': 1.0,
                             'visibility_status': 'MANUALLY_CONFIRMED_VISIBLE',
                             'source': 'native_review_click'})
                path.write_text(json.dumps(data, indent=2), encoding='utf-8')
                context.area.tag_redraw()
                self.report({'INFO'}, f'Placed {name} at image pixel ({image_x:.1f}, {image_y:.1f})')
                return {'FINISHED'}
            except Exception as exc:
                self.report({'ERROR'}, str(exc))
                return {'CANCELLED'}
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
        scene=context.scene
        selected_name=scene.cmai_landmark_review_landmark
        pts={selected_name:pts[selected_name]} if selected_name in pts else {}
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        region = context.region
        image_height = _review_image_height(context.scene, context.area)
        def xy(item):
            vx, vy = _image_to_view_xy(float(item.get('x', 0)), float(item.get('y', 0)), image_height)
            return region.view2d.view_to_region(vx, vy, clip=False)
        # Do not draw a connected chain from detector predictions. That can
        # falsely imply both visibility and physical identity.
        # The display is intentionally one marker at a time. Predictions are
        # hidden by default; the user may reveal the selected point only.
        role_colors={'hip':(0.1,0.85,1.0,1),'knee':(1.0,0.78,0.05,1),'ankle':(0.75,0.35,1.0,1),'foot':(0.2,1.0,0.35,1)}
        for name,item in pts.items():
            manual=item.get('source') in {'native_review_click','native_review_drag','native_review_user_confirmed'}
            if not item.get('visible') or (item.get('state')=='prediction_only' and not scene.cmai_show_landmark_predictions): continue
            if not manual and not scene.cmai_show_landmark_predictions: continue
            x,y=xy(item); role=name.rsplit('_',1)[-1]; color=role_colors.get(role,(1,1,1,1))
            batch=batch_for_shader(shader,'POINTS',{'pos':[(x,y)]}); shader.bind(); shader.uniform_float('color',color); gpu.state.point_size_set(20); batch.draw(shader)
            segments=[(x-8,y,x+8,y),(x,y-8,x,y+8)]
            linepos=[(ax,ay) for x1,y1,x2,y2 in segments for ax,ay in ((x1,y1),(x2,y2))]
            batch=batch_for_shader(shader,'LINES',{'pos':linepos}); shader.bind(); shader.uniform_float('color',color); batch.draw(shader)
            status='VISIBLE' if item.get('state')=='manual_reviewed' else 'PREDICTION'
            label=f"{role.upper()} · {status}"
            blf.position(0,x+9,y+3,0); blf.size(0,12); blf.color(0,*color); blf.draw(0,label)

    def invoke(self, context, event):
        if context.area.type != 'IMAGE_EDITOR': self.report({'ERROR'}, 'Run from an Image Editor area'); return {'CANCELLED'}
        if self._handle is None: self._handle=bpy.types.SpaceImageEditor.draw_handler_add(self._draw,(context,), 'WINDOW','POST_PIXEL')
        context.area.tag_redraw(); context.window_manager.modal_handler_add(self); self.report({'INFO'}, 'Drag only the selected HIP/KNEE/ANKLE/FOOT point. ESC exits.'); return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC','RIGHTMOUSE'}:
            if self._handle: bpy.types.SpaceImageEditor.draw_handler_remove(self._handle,'WINDOW'); self._handle=None
            context.area.tag_redraw(); return {'CANCELLED'}
        try:
            _, data = _load_data(context.scene)
            row = _frame(data, context.scene.cmai_landmark_review_frame)
            pts = _all_points(row, context.scene.cmai_landmark_review_camera)
            height = _review_image_height(context.scene, context.area)
            view = _view_to_image_xy(context.region, event.mouse_region_x, event.mouse_region_y, height)
        except Exception: return {'RUNNING_MODAL'}
        if event.type=='LEFTMOUSE' and event.value=='PRESS':
            selected=context.scene.cmai_landmark_review_landmark
            item=pts.get(selected)
            candidates=[(selected,item)] if item and item.get('visible') and (item.get('state')!='prediction_only' or context.scene.cmai_show_landmark_predictions) and ((float(item.get('x',0))-view[0])**2+(float(item.get('y',0))-view[1])**2)<24**2 else []
            if candidates: self._active=min(candidates,key=lambda z:(float(z[1].get('x',0))-view[0])**2+(float(z[1].get('y',0))-view[1])**2)[0]; self._dragging=True
        elif event.type=='MOUSEMOVE' and self._dragging and self._active:
                pts[self._active].update({'x':float(view[0]),'y':float(view[1]),'visible':True,'state':'manual_reviewed','confidence':1.0,'visibility_status':'VISIBLE','source':'native_review_drag'}); Path(_project_path(context.scene.cmai_landmark_review_data, context.scene)).write_text(json.dumps(data,indent=2)); context.area.tag_redraw()
        elif event.type=='LEFTMOUSE' and event.value=='RELEASE':
            if self._active:
                base=pts[self._active]
                for delta in (-2,-1,1,2):
                    try:
                        near=_frame(data,context.scene.cmai_landmark_review_frame+delta); target=_all_points(near,context.scene.cmai_landmark_review_camera).setdefault(self._active,{})
                        # Do not propagate a point by copying its coordinates to
                        # other frames; that fabricates stationary observations.
                    except Exception: pass
                Path(_project_path(context.scene.cmai_landmark_review_data, context.scene)).write_text(json.dumps(data,indent=2))
            self._dragging=False; self._active=None
        return {'RUNNING_MODAL'}


class CMAI_OT_review_frame_step(bpy.types.Operator):
    bl_idname='cmai.review_frame_step'; bl_label='Step Review Frame'; direction:IntProperty(default=1)
    def execute(self,context):
        try:
            _,data=_load_data(context.scene); values=sorted(int(row['frame']) for row in data.get('frames',[]))
            if not values: raise RuntimeError('Prepare the current video/track review first.')
            current=context.scene.cmai_landmark_review_frame
            if current not in values: target=values[0] if self.direction>0 else values[-1]
            else: target=values[max(0,min(len(values)-1,values.index(current)+self.direction))]
            context.scene.cmai_landmark_review_frame=target
            samples = Path(_project_path(context.scene.cmai_landmark_review_samples, context.scene))
            image = samples / f"frame_{target:06d}_{context.scene.cmai_landmark_review_camera}.png"
            if image.is_file():
                _set_image(context.area, image)
            else:
                raise RuntimeError(f'Reference image for frame {target} is missing: {image}')
            context.area.tag_redraw(); return {'FINISHED'}
        except Exception as exc: self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class CMAI_OT_review_set_visibility(bpy.types.Operator):
    bl_idname='cmai.review_set_visibility'; bl_label='Set Landmark Visibility'
    status: EnumProperty(items=(("VISIBLE","Visible","Point is directly visible in the selected image"),("OCCLUDED","Occluded","Anatomical point is hidden by the creature or another object"),("UNVERIFIED","Unverified","Cannot identify this point reliably")), default="UNVERIFIED")
    def execute(self,context):
        try:
            scene=context.scene; path,data=_load_data(scene); row=_frame(data,scene.cmai_landmark_review_frame)
            item=_all_points(row,scene.cmai_landmark_review_camera).setdefault(scene.cmai_landmark_review_landmark,{})
            if self.status=='VISIBLE':
                if item.get('source') not in {'native_review_click','native_review_drag','native_review_user_confirmed'} or not all(k in item for k in ('x','y')):
                    raise RuntimeError('VISIBLE requires manually placing the selected point on a clearly visible feature first.')
                item.update({'visible':True,'state':'manual_reviewed','confidence':1.0,'visibility_status':'VISIBLE'})
            else:
                item.update({'visible':False,'confidence':0.0,'state':self.status.lower(),'visibility_status':self.status})
            path.write_text(json.dumps(data,indent=2)); context.area.tag_redraw(); return {'FINISHED'}
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

class CMAI_PT_landmark_review(bpy.types.Panel):
    bl_label = "Landmark Review"
    bl_idname = "CMAI_PT_landmark_review"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Creature Motion AI"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        box=layout.box(); box.label(text='Verify One Physical Leg',icon='TRACKER')
        box.label(text='One physical leg at a time • predictions hidden by default',icon='INFO')
        box.label(text='1. Prepare current side video + prediction track')
        box.operator('cmai.verify_reference_leg',text='Prepare Current Review',icon='IMPORT')
        box.prop(scene,'cmai_landmark_review_track',text='Prediction Track')
        box.label(text='2. Inspect the visible chain; predictions are not truth')
        box.prop(scene,'cmai_reference_leg_identity',text='Candidate Rig Leg')
        box.operator('cmai.highlight_reference_leg_chain',icon='BONE_DATA')
        if scene.cmai_reference_leg_identity != 'UNVERIFIED':
            leg=scene.cmai_reference_leg_identity
            box.label(text=f'Leg_{leg}_01 head = HIP')
            box.label(text=f'Leg_{leg}_01 tail / _02 head = KNEE')
            box.label(text=f'Leg_{leg}_02 tail / _03 head = ANKLE')
            box.label(text=f'Leg_{leg}_03 tail = FOOT endpoint')
            if scene.cmai_identity_confirmed_leg == leg:
                box.label(text=f'Identity explicitly confirmed: {leg}',icon='CHECKMARK')
            else:
                box.operator('cmai.confirm_reference_leg_identity',text='Confirm Physical Leg Identity',icon='DECORATE_OVERRIDE')
        box.label(text='3. Select one point and place/drag it on the image')
        layout.prop(scene, "cmai_landmark_review_data")
        row=box.row(align=True); row.operator('cmai.review_frame_step',text='Previous',icon='TRIA_LEFT').direction=-1
        row.operator('cmai.review_frame_step',text='Next',icon='TRIA_RIGHT').direction=1
        box.prop(scene, "cmai_landmark_review_frame",text='Source Video Frame')
        box.prop(scene, "cmai_landmark_review_landmark",text='Point')
        box.prop(scene,'cmai_show_landmark_predictions',text='Show Unverified Predictions')
        box.operator("cmai.review_load_image", text='Reload This Frame', icon='IMAGE_DATA')
        row=box.row(align=True); row.operator("cmai.review_correct_landmark",text='Click to Place',icon='PIVOT_CURSOR')
        box.operator("cmai.review_all_landmarks",text='Drag Selected Point',icon='TRACKING')
        row=box.row(align=True)
        for status,label in (('VISIBLE','VISIBLE'),('OCCLUDED','OCCLUDED'),('UNVERIFIED','UNVERIFIED')):
            op=row.operator('cmai.review_set_visibility',text=label); op.status=status
        box.operator('cmai.review_confirm_landmark',text='Confirm Manually Placed Point',icon='CHECKMARK')
        box.label(text='H cyan • K yellow • A purple • F green',icon='INFO')
        box.label(text='Image coordinates are converted to Blender display coordinates.',icon='INFO')
        box.label(text='No connecting lines are shown until identity approval.',icon='INFO')
        approve=box.row(); approve.enabled=(scene.cmai_reference_leg_identity!='UNVERIFIED' and scene.cmai_identity_confirmed_leg==scene.cmai_reference_leg_identity)
        approve.operator('cmai.reference_leg_approve_save',text='Save New Versioned Evidence',icon='FILE_TICK')
        box.operator('cmai.analyze_approved_leg_events',text='Re-run Step Event Analysis',icon='TIME')
        box.label(text='Animation stays locked pending 3D fit + reachability + anatomy.',icon='LOCKED')
        layout.separator()
        layout.label(text='Advanced / fallback review tools',icon='TOOL_SETTINGS')
        layout.prop(scene, "cmai_landmark_review_samples")
        layout.prop(scene, "cmai_landmark_review_camera")
        layout.prop(scene, "cmai_landmark_review_landmark")
        layout.operator("cmai.review_load_image", icon='IMAGE_DATA')
        layout.operator("cmai.review_correct_landmark", icon='PIVOT_CURSOR')
        layout.operator("cmai.review_all_landmarks", icon='TRACKING')
        row = layout.row(align=True); op=row.operator("cmai.review_frame_step", text="Previous", icon='TRIA_LEFT'); op.direction=-1; op=row.operator("cmai.review_frame_step", text="Next", icon='TRIA_RIGHT'); op.direction=1
        layout.prop(scene,'cmai_show_landmark_predictions',text='Show Unverified Predictions')
        layout.prop(scene, "cmai_pose_library_data")
        row = layout.row(align=True); row.operator('cmai.pose_library_load', icon='IMPORT'); row.operator('cmai.pose_library_export_current', icon='EXPORT')
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
        layout.label(text="Prediction JSON is kept separate from approved evidence.", icon='INFO')
        layout.label(text="Hidden points remain OCCLUDED/UNVERIFIED; no guess is added.")


class CMAI_OT_analyze_approved_leg_events(bpy.types.Operator):
    bl_idname='cmai.analyze_approved_leg_events'; bl_label='Re-run Approved Step Events'
    def execute(self,context):
        try:
            scene=context.scene; _,review=_load_data(scene); out=Path(_project_path(scene.cmai_landmark_review_samples, scene))
            manifest=Path(_project_path(scene.cmai_identity_approval_file,scene)) if scene.cmai_identity_approval_file else None
            if not manifest or not manifest.is_file(): raise RuntimeError('No versioned identity approval exists. Save a reviewed chain first.')
            approval=json.loads(manifest.read_text(encoding='utf-8')); track=Path(approval.get('approved_track',''))
            if not track.is_file(): raise RuntimeError('The approved landmark track referenced by the manifest is missing.')
            report=out/f"step_event_report_rerun_{datetime.now().strftime('%Y%m%dT%H%M%S')}.json"; python=bpy.path.abspath(getattr(scene,'cmai_python','')) or sys.executable
            script=Path(__file__).with_name('analyze_step_events_cli.py')
            result=subprocess.run([python,str(script),str(track),str(report),'--approval',str(manifest)],capture_output=True,text=True)
            if result.returncode: raise RuntimeError((result.stderr or result.stdout)[-700:] or 'Step-event analysis failed')
            scene.cmai_landmark_review_report=str(report); self.report({'INFO'},'Step-event evidence report refreshed; animation remains blocked pending 3D validation.')
            return {'FINISHED'}
        except Exception as exc: self.report({'ERROR'},str(exc)); return {'CANCELLED'}


CLASSES = (CMAI_OT_verify_reference_leg, CMAI_OT_reference_leg_approve_save,
           CMAI_OT_highlight_reference_leg_chain, CMAI_OT_confirm_reference_leg_identity,
           CMAI_OT_review_confirm_landmark,
           CMAI_OT_analyze_approved_leg_events, CMAI_OT_review_load_image,
           CMAI_OT_review_one_click_setup, CMAI_OT_review_correct,
           CMAI_OT_review_all_landmarks, CMAI_OT_review_frame_step,
           CMAI_OT_review_set_visibility, CMAI_OT_review_track,
           CMAI_OT_review_validate, CMAI_OT_pose_library_load,
           CMAI_OT_pose_library_export_current, CMAI_PT_landmark_review)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cmai_landmark_review_data = StringProperty(name="Landmark JSON", subtype='FILE_PATH', default="//data/generated/landmark_reviewed.json")
    bpy.types.Scene.cmai_landmark_review_samples = StringProperty(name="Reference Frames", subtype='DIR_PATH', default="//data/generated/goodsplitbalisk_pipeline_v2/samples")
    bpy.types.Scene.cmai_landmark_review_frame = IntProperty(name="Reference Frame", default=1, min=1, max=241)
    bpy.types.Scene.cmai_landmark_review_camera = EnumProperty(name="Camera", items=CAMERAS, default="camera_A")
    bpy.types.Scene.cmai_landmark_review_landmark = EnumProperty(name="Point", items=(
        ("Leg_Reference_hip","Hip (H)","Hip point"),
        ("Leg_Reference_knee","Knee (K)","Knee point"),
        ("Leg_Reference_ankle","Ankle (A)","Ankle point"),
        ("Leg_Reference_foot","Foot (F)","Foot point")), default="Leg_Reference_hip")
    bpy.types.Scene.cmai_landmark_review_output = StringProperty(name="Tracked Output", subtype='FILE_PATH', default="//data/generated/native_tracked_landmarks_24.json")
    bpy.types.Scene.cmai_landmark_review_report = StringProperty(name="Validation Report", subtype='FILE_PATH', default="//data/generated/native_tracking_report.json")
    bpy.types.Scene.cmai_landmark_review_max_frames = IntProperty(name="Max Frames", default=24, min=1, max=241)
    bpy.types.Scene.cmai_landmark_review_track = StringProperty(name='Prediction Track', subtype='FILE_PATH', default='data/generated/dlc_tracking_best30/leg_rear_left_tracking.json')
    bpy.types.Scene.cmai_reference_leg_identity = EnumProperty(name='Reference Leg Identity', items=(("UNVERIFIED","Unverified","Do not assign a rig leg"),("Front.L","Front.L",""),("Front.R","Front.R",""),("MidFront.L","MidFront.L",""),("MidFront.R","MidFront.R",""),("MidRear.L","MidRear.L",""),("MidRear.R","MidRear.R",""),("Rear.L","Rear.L",""),("Rear.R","Rear.R","")), default='UNVERIFIED')
    bpy.types.Scene.cmai_show_landmark_predictions = BoolProperty(name='Show Unverified Predictions', default=False)
    bpy.types.Scene.cmai_identity_confirmed_leg = StringProperty(name='Confirmed Physical Leg', default='')
    bpy.types.Scene.cmai_identity_confirmed_rig = StringProperty(name='Confirmed Armature', default='')
    bpy.types.Scene.cmai_identity_confirmed_bones = StringProperty(name='Confirmed Bone Chain', default='')
    bpy.types.Scene.cmai_identity_approval_file = StringProperty(name='Versioned Identity Approval', subtype='FILE_PATH', default='')
    bpy.types.Scene.cmai_pose_library_data = StringProperty(name="Pose Library", subtype='FILE_PATH', default="C:\\Users\\rober\\CreatureMotionAI\\data\\generated\\cmai_pose_library.json")


def unregister():
    for name in ("cmai_landmark_review_data", "cmai_landmark_review_samples", "cmai_landmark_review_frame", "cmai_landmark_review_camera", "cmai_landmark_review_landmark", "cmai_landmark_review_output", "cmai_landmark_review_report", "cmai_landmark_review_max_frames", "cmai_landmark_review_track", "cmai_pose_library_data", "cmai_reference_leg_identity", "cmai_show_landmark_predictions", "cmai_identity_confirmed_leg", "cmai_identity_confirmed_rig", "cmai_identity_confirmed_bones", "cmai_identity_approval_file"):
        delattr(bpy.types.Scene, name)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
