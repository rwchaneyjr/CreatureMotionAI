import json
import os
import subprocess
import sys
from pathlib import Path

import bpy
from bpy.props import StringProperty, IntProperty, EnumProperty

def _project_root_for_scene(scene):
    """Find the workspace when this add-on is installed under Blender AppData."""
    video = Path(bpy.path.abspath(getattr(scene, 'cmai_video', '') or '')).resolve()
    candidates = [p for p in (video, *video.parents)]
    here = Path(__file__).resolve()
    candidates.extend(here.parents)
    candidates.append(Path(r'C:\Users\rober\CreatureMotionAI'))
    return next((p for p in candidates if (p/'tools').is_dir()), None)


class CMAI_OT_extract_frames(bpy.types.Operator):
    bl_idname = "cmai.extract_frames"
    bl_label = "Extract Frames"
    bl_description = "Extract a numbered PNG frame range using the external Python environment"

    def execute(self, context):
        scene = context.scene
        video = bpy.path.abspath(scene.cmai_video)
        output = bpy.path.abspath(scene.cmai_output)
        if not video or not os.path.isfile(video):
            self.report({'ERROR'}, "Select an existing MP4 video")
            return {'CANCELLED'}
        os.makedirs(output, exist_ok=True)
        script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools", "extract_frames.py"))
        python_executable = bpy.path.abspath(scene.cmai_python) or sys.executable
        if not os.path.isfile(python_executable):
            self.report({'ERROR'}, "External Python executable was not found")
            return {'CANCELLED'}
        command = [python_executable, script, "--video", video, "--output", output,
                   "--start", str(scene.cmai_start), "--end", str(scene.cmai_end)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
        except OSError as exc:
            self.report({'ERROR'}, f"Could not start extractor: {exc}")
            return {'CANCELLED'}
        if result.returncode:
            self.report({'ERROR'}, result.stderr[-500:] or "Frame extraction failed")
            return {'CANCELLED'}
        self.report({'INFO'}, result.stdout.strip()[-500:] or "Frames extracted")
        return {'FINISHED'}

class CMAI_OT_set_project_paths(bpy.types.Operator):
    bl_idname = "cmai.set_project_paths"
    bl_label = "Use CreatureMotionAI Project Files"
    def execute(self, context):
        root = Path(r'C:\Users\rober\CreatureMotionAI')
        scene = context.scene
        candidates = [root/'data'/'generated'/'dlc_balisk_side_view.mp4', root/'data'/'reference'/'goodspilitbalisk.mp4']
        video = next((p for p in candidates if p.is_file()), candidates[0])
        model_candidates = [root/'data'/'generated'/'original_static_standing.blend', root/'data'/'generated'/'original_static_standing.blend']
        model = next((p for p in model_candidates if p.is_file()), model_candidates[0])
        scene.cmai_video = str(video)
        scene.cmai_model = str(model)
        scene.cmai_output = str(root/'data'/'frames')
        scene.cmai_python = r'C:\Users\rober\AppData\Local\Programs\Python\Python311\python.exe'
        scene.cmai_dlc_output = str(root/'data'/'generated'/'dlc_balisk_project')
        self.report({'INFO'}, "CreatureMotionAI project paths filled")
        return {'FINISHED'}


class CMAI_OT_not_ready(bpy.types.Operator):
    bl_idname = "cmai.not_ready"
    bl_label = "Not Available in Milestone 1"
    message: StringProperty(default="This feature is planned for a later milestone.")

    def execute(self, context):
        self.report({'INFO'}, self.message)
        return {'CANCELLED'}


class CMAI_OT_run_camera_diagnostic(bpy.types.Operator):
    bl_idname = "cmai.run_camera_diagnostic"
    bl_label = "Run 4-Point Camera Diagnostic"
    bl_description = "Fit the restricted orthographic camera and write diagnostic reprojection errors"

    def execute(self, context):
        script = Path(__file__).resolve().parent.parent / "tools" / "fit_four_point_ortho_camera.py"
        python_executable = bpy.path.abspath(context.scene.cmai_python) or sys.executable
        if not script.is_file():
            self.report({'ERROR'}, "Camera diagnostic script is missing")
            return {'CANCELLED'}
        try:
            result = subprocess.run([python_executable, str(script)], capture_output=True, text=True, check=False)
        except OSError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        if result.returncode:
            self.report({'ERROR'}, result.stderr[-500:] or "Camera diagnostic failed")
            return {'CANCELLED'}
        self.report({'INFO'}, "Camera diagnostic saved; inspect reprojection errors before fitting bones")
        return {'FINISHED'}


class CMAI_OT_export_confirmed_markers(bpy.types.Operator):
    bl_idname = "cmai.export_confirmed_markers"
    bl_label = "Export Confirmed 3D Markers"
    bl_description = "Export only markers explicitly marked confirmed or adjusted"

    def execute(self, context):
        markers = [o for o in context.scene.objects if o.name.startswith("CMAI_Marker_")]
        if not markers:
            self.report({'ERROR'}, "No CMAI marker objects are present in this scene")
            return {'CANCELLED'}
        unconfirmed = [o.name for o in markers if o.get("status") not in {"confirmed", "adjusted"}]
        if unconfirmed:
            self.report({'ERROR'}, f"Unconfirmed markers remain: {', '.join(unconfirmed)}")
            return {'CANCELLED'}
        output = bpy.path.abspath("//data/generated/confirmed_3d_body_landmarks.json")
        data = {"status": "USER_CONFIRMED_EXPORT", "points": {o.get("landmark_name", o.name): {"world_xyz": list(o.matrix_world.translation), "status": o.get("status"), "source_bone": o.get("source_bone")} for o in markers}}
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.report({'INFO'}, f"Exported {len(markers)} confirmed markers")
        return {'FINISHED'}


class CMAI_OT_launch_single_camera_annotation(bpy.types.Operator):
    bl_idname = "cmai.launch_single_camera_annotation"
    bl_label = "Open Single-Camera Annotation"
    mode: EnumProperty(items=(("leg", "Leg landmarks", "Annotate leg joints"), ("calibration", "Camera landmarks", "Annotate body references"), ("suggestions", "Review DLC suggestions", "Approve or correct provisional labels")), default="leg")
    def execute(self, context):
        # Installed add-ons live under Blender's AppData folder. Resolve the
        # actual workspace from the configured video before launching tools.
        candidates=[]
        video=Path(bpy.path.abspath(getattr(context.scene, 'cmai_video', '') or '')).resolve()
        for parent in (video, *video.parents):
            if (parent/'tools'/'single_camera_side_annotation.py').is_file(): candidates.append(parent)
        here=Path(__file__).resolve()
        for parent in (here, *here.parents):
            if (parent/'tools'/'single_camera_side_annotation.py').is_file(): candidates.append(parent)
        explicit=Path(r'C:\Users\rober\CreatureMotionAI')
        if explicit.exists(): candidates.append(explicit)
        root=next((p for p in candidates if (p/'tools'/'single_camera_side_annotation.py').is_file()), None)
        if root is None:
            self.report({'ERROR'}, "CreatureMotionAI project root not found"); return {'CANCELLED'}
        script=root/'tools'/'single_camera_side_annotation.py'
        fallback=root/'.venv-dlc'/'Scripts'/'python.exe'
        configured=bpy.path.abspath(context.scene.cmai_python)
        # Prefer the project DLC environment: the older global environment may
        # contain opencv-python-headless and cannot open the review window.
        gui_python=Path(r'C:\Users\rober\AppData\Local\Programs\Python\Python311\python.exe')
        # The DLC environment may contain opencv-python-headless. Use the
        # verified GUI-capable Python for this OpenCV window when available.
        py=str(gui_python) if gui_python.is_file() else (str(fallback) if fallback.is_file() else (configured if configured and Path(configured).is_file() else sys.executable))
        if not script.is_file(): self.report({'ERROR'}, "Single-camera annotation tool is missing"); return {'CANCELLED'}
        log_path=root/'data/generated/single_camera_annotation_launch.log'; log=log_path.open('a',encoding='utf-8')
        log.write(f'LAUNCH mode={self.mode} python={py} script={script} cwd={root}\n'); log.flush()
        subprocess.Popen([py,str(script),'--mode',self.mode],cwd=str(root),stdout=log,stderr=subprocess.STDOUT)
        self.report({'INFO'}, f"Started {self.mode} annotation with {Path(py).name}; log: {log_path.name}"); return {'FINISHED'}


class CMAI_OT_create_dlc_project(bpy.types.Operator):
    bl_idname = "cmai.create_dlc_project"
    bl_label = "Create DeepLabCut Project"
    bl_description = "Create a DeepLabCut project and basilisk landmark list"

    def execute(self, context):
        scene = context.scene
        video = bpy.path.abspath(scene.cmai_video)
        output = bpy.path.abspath(scene.cmai_dlc_output)
        root = _project_root_for_scene(scene)
        script = str(root/'tools'/'setup_dlc_balisk_project.py') if root else ''
        python_executable = bpy.path.abspath(scene.cmai_python)
        if not os.path.isfile(video):
            self.report({'ERROR'}, "Select the MP4 file first")
            return {'CANCELLED'}
        try:
            result = subprocess.run([python_executable, script], capture_output=True, text=True, check=False)
        except OSError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        if result.returncode:
            self.report({'ERROR'}, result.stderr[-500:] or "DeepLabCut project creation failed")
            return {'CANCELLED'}
        self.report({'INFO'}, "DeepLabCut project created. Open its config.yaml to label frames.")
        return {'FINISHED'}


class CMAI_OT_dlc_train_check(bpy.types.Operator):
    bl_idname='cmai.dlc_train_check'; bl_label='Train Balisk Tracker'
    def execute(self, context):
        report=Path(bpy.path.abspath('//data/generated/dlc_setup_report.json'))
        self.report({'ERROR'} if not report.is_file() else {'WARNING'}, 'Training blocked: five anchor frames are imported, but more diverse corrected labels are required before training')
        return {'CANCELLED'}

class CMAI_OT_prepare_dlc_training(bpy.types.Operator):
    bl_idname='cmai.prepare_dlc_training'; bl_label='Prepare DLC Training Data'
    def execute(self, context):
        path=Path(r'C:\Users\rober\CreatureMotionAI\data\generated\dlc_training_suggestions.json')
        data=json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
        frames=data.get('frames',{})
        verified=[k for k,v in frames.items() if all(v.get(n,{}).get('state')=='manual_verified' for n in ('hip','knee','ankle','foot'))]
        provisional=sum(1 for v in frames.values() for p in v.values() if p.get('state')=='provisional_prediction')
        report={'status':'READY_FOR_REVIEW' if len(verified)>=10 else 'BLOCKED_REVIEW_REQUIRED','manual_verified_frames':len(verified),'provisional_landmarks':provisional,'training_started':False,'verified_frame_numbers':[int(x) for x in verified]}
        path.parent.joinpath('dlc_training_data_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        self.report({'INFO'} if len(verified)>=10 else {'WARNING'}, f"DLC data: {len(verified)} verified frames; {provisional} provisional landmarks")
        return {'FINISHED'}

class CMAI_OT_validate_dlc_tracker(bpy.types.Operator):
    bl_idname='cmai.validate_dlc_tracker'; bl_label='Validate Tracker'
    def execute(self, context):
        self.report({'WARNING'}, 'Tracker validation blocked until a trained model exists; no training started')
        return {'CANCELLED'}


class CMAI_OT_dlc_track_check(bpy.types.Operator):
    bl_idname='cmai.dlc_track_check'; bl_label='Track Video with DeepLabCut'
    def execute(self, context):
        self.report({'ERROR'}, 'Tracking blocked until a validated Balisk DLC model is trained')
        return {'CANCELLED'}


class CMAI_OT_analyze_video_opencv(bpy.types.Operator):
    bl_idname = "cmai.analyze_video_opencv"
    bl_label = "Analyze Video (OpenCV)"
    bl_description = "Extract conservative normalized motion landmarks without DeepLabCut"

    def execute(self, context):
        scene = context.scene
        video = bpy.path.abspath(scene.cmai_video)
        output = bpy.path.abspath(scene.cmai_motion_output)
        script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools", "analyze_video_opencv.py"))
        python_executable = bpy.path.abspath(scene.cmai_python) or sys.executable
        if not os.path.isfile(video):
            self.report({'ERROR'}, "Select an existing MP4 video")
            return {'CANCELLED'}
        command = [python_executable, script, "--video", video, "--output", output,
                   "--start", str(scene.cmai_start), "--end", str(scene.cmai_end)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
        except OSError as exc:
            self.report({'ERROR'}, f"Could not start OpenCV analysis: {exc}")
            return {'CANCELLED'}
        if result.returncode:
            self.report({'ERROR'}, result.stderr[-500:] or "OpenCV analysis failed")
            return {'CANCELLED'}
        self.report({'INFO'}, result.stdout.strip()[-500:] or "Motion analysis complete")
        return {'FINISHED'}


class CMAI_OT_solve_video_opencv(bpy.types.Operator):
    bl_idname = "cmai.solve_video_opencv"
    bl_label = "Solve Animation Automatically (OpenCV)"
    bl_description = "Generate a new eight-legged Action without DeepLabCut"

    def execute(self, context):
        self.report({'ERROR'}, "Full automatic eight-leg video solve is not implemented; use verified landmark review and the provisional single-leg fitting path")
        return {'CANCELLED'}


def register():
    for cls in (CMAI_OT_extract_frames, CMAI_OT_set_project_paths, CMAI_OT_prepare_dlc_training, CMAI_OT_validate_dlc_tracker, CMAI_OT_not_ready, CMAI_OT_run_camera_diagnostic, CMAI_OT_export_confirmed_markers, CMAI_OT_launch_single_camera_annotation, CMAI_OT_dlc_train_check, CMAI_OT_dlc_track_check, CMAI_OT_create_dlc_project, CMAI_OT_analyze_video_opencv, CMAI_OT_solve_video_opencv):
        bpy.utils.register_class(cls)
    bpy.types.Scene.cmai_video = StringProperty(name="MP4 Video", subtype='FILE_PATH')
    bpy.types.Scene.cmai_model = StringProperty(name="Source Model", subtype='FILE_PATH')
    bpy.types.Scene.cmai_output = StringProperty(name="Output Folder", subtype='DIR_PATH', default="//data/frames")
    bpy.types.Scene.cmai_python = StringProperty(name="External Python", subtype='FILE_PATH', default="C:\\Users\\rober\\.venv\\deeplabcut\\Scripts\\python.exe")
    bpy.types.Scene.cmai_dlc_output = StringProperty(name="DLC Project Folder", subtype='DIR_PATH', default="//data/deeplabcut")
    bpy.types.Scene.cmai_motion_output = StringProperty(name="Motion Data", subtype='FILE_PATH', default="//data/motion/motion.json")
    bpy.types.Scene.cmai_start = IntProperty(name="Start Frame", default=0, min=0)
    bpy.types.Scene.cmai_end = IntProperty(name="End Frame", default=30, min=1)
    bpy.types.Scene.cmai_solver_output = StringProperty(name="Solved Blend", subtype='FILE_PATH', default="//data/generated/cmai_solved.blend")
    bpy.types.Scene.cmai_solver_report = StringProperty(name="Solver Report", subtype='FILE_PATH', default="//data/generated/cmai_solver_report.json")
    bpy.types.Scene.cmai_camera_report = StringProperty(name="Camera Diagnostic", subtype='FILE_PATH', default="//data/generated/four_point_camera_fit_report.json")
    bpy.types.Scene.cmai_annotation_mode = EnumProperty(name="Annotation Mode", items=(("leg", "Leg landmarks", ""),("calibration", "Camera landmarks", ""),("suggestions", "Review DLC suggestions", "")), default="leg")


def unregister():
    for name in ("cmai_video", "cmai_model", "cmai_output", "cmai_python", "cmai_dlc_output", "cmai_motion_output", "cmai_start", "cmai_end", "cmai_solver_output", "cmai_solver_report", "cmai_camera_report", "cmai_annotation_mode"):
        delattr(bpy.types.Scene, name)
    for cls in reversed((CMAI_OT_extract_frames, CMAI_OT_set_project_paths, CMAI_OT_prepare_dlc_training, CMAI_OT_validate_dlc_tracker, CMAI_OT_not_ready, CMAI_OT_run_camera_diagnostic, CMAI_OT_export_confirmed_markers, CMAI_OT_launch_single_camera_annotation, CMAI_OT_dlc_train_check, CMAI_OT_dlc_track_check, CMAI_OT_create_dlc_project, CMAI_OT_analyze_video_opencv, CMAI_OT_solve_video_opencv)):
        bpy.utils.unregister_class(cls)

