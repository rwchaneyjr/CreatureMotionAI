import json
import os
import subprocess
import sys

import bpy
from bpy.props import StringProperty, IntProperty


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


class CMAI_OT_not_ready(bpy.types.Operator):
    bl_idname = "cmai.not_ready"
    bl_label = "Not Available in Milestone 1"
    message: StringProperty(default="This feature is planned for a later milestone.")

    def execute(self, context):
        self.report({'INFO'}, self.message)
        return {'CANCELLED'}


class CMAI_OT_create_dlc_project(bpy.types.Operator):
    bl_idname = "cmai.create_dlc_project"
    bl_label = "Create DeepLabCut Project"
    bl_description = "Create a DeepLabCut project and basilisk landmark list"

    def execute(self, context):
        scene = context.scene
        video = bpy.path.abspath(scene.cmai_video)
        output = bpy.path.abspath(scene.cmai_dlc_output)
        script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools", "create_dlc_project.py"))
        python_executable = bpy.path.abspath(scene.cmai_python)
        if not os.path.isfile(video):
            self.report({'ERROR'}, "Select the MP4 file first")
            return {'CANCELLED'}
        try:
            result = subprocess.run([python_executable, script, "--video", video, "--output", output], capture_output=True, text=True, check=False)
        except OSError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        if result.returncode:
            self.report({'ERROR'}, result.stderr[-500:] or "DeepLabCut project creation failed")
            return {'CANCELLED'}
        self.report({'INFO'}, "DeepLabCut project created. Open its config.yaml to label frames.")
        return {'FINISHED'}


def register():
    for cls in (CMAI_OT_extract_frames, CMAI_OT_not_ready, CMAI_OT_create_dlc_project):
        bpy.utils.register_class(cls)
    bpy.types.Scene.cmai_video = StringProperty(name="MP4 Video", subtype='FILE_PATH')
    bpy.types.Scene.cmai_output = StringProperty(name="Output Folder", subtype='DIR_PATH', default="//data/frames")
    bpy.types.Scene.cmai_python = StringProperty(name="External Python", subtype='FILE_PATH', default="C:\\Users\\rober\\.venv\\deeplabcut\\Scripts\\python.exe")
    bpy.types.Scene.cmai_dlc_output = StringProperty(name="DLC Project Folder", subtype='DIR_PATH', default="//data/deeplabcut")
    bpy.types.Scene.cmai_start = IntProperty(name="Start Frame", default=0, min=0)
    bpy.types.Scene.cmai_end = IntProperty(name="End Frame", default=30, min=1)


def unregister():
    for name in ("cmai_video", "cmai_output", "cmai_python", "cmai_dlc_output", "cmai_start", "cmai_end"):
        delattr(bpy.types.Scene, name)
    for cls in reversed((CMAI_OT_extract_frames, CMAI_OT_not_ready, CMAI_OT_create_dlc_project)):
        bpy.utils.unregister_class(cls)

