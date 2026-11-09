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
        wf.label(text="Primary mode: side panel; front panel optional", icon='INFO')
        wf.operator("cmai.track_side_panel", text="Track Side Panel (Provisional)", icon='TRACKER')
        op=wf.operator("cmai.launch_single_camera_annotation", text="REVIEW SUGGESTED LABELS", icon='CHECKMARK'); op.mode='suggestions'
        wf.operator("cmai.prepare_dlc_training", text="Prepare DLC Training Data", icon='FILE_TICK')
        wf.prop(scene, "cmai_annotation_mode")
        op=wf.operator("cmai.launch_single_camera_annotation", text="Open Single-Camera Annotation", icon='TRACKER'); op.mode=scene.cmai_annotation_mode
        wf.operator("cmai.review_all_landmarks", text="Open Native Landmark Review", icon='IMAGE_DATA')
        pose_box = wf.box()
        pose_box.label(text="Pose Library", icon='POSE_HLT')
        pose_box.prop(scene, "cmai_pose_library_data")
        pose_row = pose_box.row(align=True)
        pose_row.operator("cmai.pose_library_load", text="Load Approved Observations", icon='IMPORT')
        pose_row.operator("cmai.pose_library_export_current", text="Save Current Review", icon='EXPORT')
        wf.label(text="DeepLabCut tracker", icon='TRACKER')
        wf.prop(scene, "cmai_annotation_leg", text="Review leg")
        wf.operator("cmai.show_video_leg_correspondence", text="Show Video Leg / Highlight Chain", icon='BONE_DATA')
        wf.operator("cmai.confirm_video_leg", text="Confirm Video Leg", icon='CHECKMARK')
        optional = wf.box()
        optional.label(text="Optional: independent front-view reference", icon='CAMERA_DATA')
        optional.operator("cmai.two_view_correspondence", text="Open Two-View Correspondence Editor", icon='CAMERA_DATA')
        optional.operator("cmai.validate_two_view_geometry", text="Validate Two-View Geometry", icon='CHECKMARK')
        optional.operator("cmai.diagnose_two_view_leg_events", text="Diagnose Two-View Leg Events", icon='TIME')
        # Keep the approval entry point at the top of this section so it is
        # visible even when the sidebar is too short to show every control.
        op=wf.operator("cmai.launch_single_camera_annotation", text="Review Suggested Labels", icon='CHECKMARK'); op.mode='suggestions'; op.leg=scene.cmai_annotation_leg
        wf.operator("cmai.create_dlc_project", text="Set Up / Import DLC Labels")
        wf.operator("cmai.dlc_train_check", text="Train Balisk Tracker")
        wf.operator("cmai.validate_dlc_tracker", text="Validate Tracker")
        wf.operator("cmai.dlc_track_check", text="Track Video with DeepLabCut")
        wf.label(text="DLC status: EXPERIMENTAL; 5 anchors only", icon='INFO')
        wf.label(text="Collision proxies (approximate)", icon='PHYSICS')
        wf.operator("cmai.build_collision_proxies", text="Build Collision Proxies", icon='MESH_CYLINDER')
        wf.operator("cmai.show_collision_proxies", text="Show Collision Proxies", icon='HIDE_OFF')
        wf.operator("cmai.check_animation_collisions", text="Check Animation Collisions", icon='PHYSICS')
        wf.operator("cmai.retarget_cmai_to_fbx", text="Retarget CMAI Action to FBX", icon='ARMATURE_DATA')
        walk = wf.box()
        walk.label(text="Calibrated gait (per-leg rest-relative)", icon='ANIM')
        walk.prop(scene, "cmai_stride")
        walk.prop(scene, "cmai_lift")
        walk.prop(scene, "cmai_joint_limits")
        walk.operator("cmai.generate_walk", text="Generate Calibrated Eight-Leg Walk", icon='POSE_HLT')
        walk.label(text="Output: balisk_calibrated_walk.blend", icon='INFO')
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

