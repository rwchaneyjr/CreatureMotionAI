import bpy


class CMAI_PT_main(bpy.types.Panel):
    bl_label = "Creature Motion AI"
    bl_idname = "CMAI_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Creature Motion AI"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        box = layout.box()
        box.label(text="Milestone 1: Video Preparation")
        box.prop(scene, "cmai_video")
        box.prop(scene, "cmai_model")
        box.prop(scene, "cmai_output")
        box.prop(scene, "cmai_python")
        row = box.row(align=True)
        row.prop(scene, "cmai_start")
        row.prop(scene, "cmai_end")
        box.operator("cmai.extract_frames", icon='RENDER_ANIMATION')
        box.prop(scene, "cmai_motion_output")
        box.operator("cmai.analyze_video_opencv", icon='TRACKER')
        box.prop(scene, "cmai_solver_output")
        box.prop(scene, "cmai_solver_report")
        box.operator("cmai.solve_video_opencv", icon='POSE_HLT')
        box.label(text="Milestone 2: DeepLabCut Setup")
        box.prop(scene, "cmai_dlc_output")
        box.operator("cmai.create_dlc_project", icon='TRACKER')
        box.label(text="Creature-Independent Skeleton")
        box.prop(scene, "cmai_profile_output")
        box.operator("cmai.inspect_armature", icon='BONE_DATA')
        box.label(text="Animation Targets")
        box.prop(scene, "cmai_motion_targets")
        box.operator("cmai.apply_pose_targets", icon='KEY_HLT')
        layout.separator()
        wf = layout.box()
        wf.label(text="CreatureMotionAI Workflow", icon='SEQUENCE')
        wf.label(text="1  Import MP4      READY (path + frame extraction)")
        wf.operator("cmai.set_project_paths", text="Use CreatureMotionAI Project Files", icon='FILE_FOLDER')
        wf.label(text="2  Load Rig        READY (open/select armature)")
        wf.label(text="3  Track Landmarks PARTIAL (review required)")
        op=wf.operator("cmai.launch_single_camera_annotation", text="REVIEW SUGGESTED LABELS", icon='CHECKMARK'); op.mode='suggestions'
        wf.operator("cmai.prepare_dlc_training", text="Prepare DLC Training Data", icon='FILE_TICK')
        wf.prop(scene, "cmai_annotation_mode")
        op=wf.operator("cmai.launch_single_camera_annotation", text="Open Single-Camera Annotation", icon='TRACKER'); op.mode=scene.cmai_annotation_mode
        wf.operator("cmai.review_all_landmarks", text="Open Native Landmark Review", icon='IMAGE_DATA')
        wf.label(text="DeepLabCut tracker", icon='TRACKER')
        # Keep the approval entry point at the top of this section so it is
        # visible even when the sidebar is too short to show every control.
        op=wf.operator("cmai.launch_single_camera_annotation", text="Review Suggested Labels", icon='CHECKMARK'); op.mode='suggestions'
        wf.operator("cmai.create_dlc_project", text="Set Up / Import DLC Labels")
        wf.operator("cmai.dlc_train_check", text="Train Balisk Tracker")
        wf.operator("cmai.validate_dlc_tracker", text="Validate Tracker")
        wf.operator("cmai.dlc_track_check", text="Track Video with DeepLabCut")
        wf.label(text="DLC status: EXPERIMENTAL; 5 anchors only", icon='INFO')
        wf.label(text="4  Calibrate Camera DIAGNOSTIC ONLY")
        wf.prop(scene, "cmai_camera_report")
        wf.operator("cmai.run_camera_diagnostic", icon='CAMERA_DATA')
        wf.label(text="5  Fit Bones       BLOCKED (camera/3D data)")
        wf.label(text="6  Preview          ISOLATED TESTS ONLY")
        wf.label(text="7  Export FBX       BLOCKED (no validated video Action)")
        wf.label(text="Ground contact and 3D marker confirmation remain manual gates.", icon='INFO')
        layout.separator()
        layout.label(text="Experimental / not validated", icon='INFO')
        for label in ("Run AI Tracking", "Map Bones", "Generate Animation", "Export FBX", "Export GLB"):
            op = layout.operator("cmai.not_ready", text=label)
            op.message = f"{label} is planned for a later milestone."


def register():
    bpy.utils.register_class(CMAI_PT_main)


def unregister():
    bpy.utils.unregister_class(CMAI_PT_main)

