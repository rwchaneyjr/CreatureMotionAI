"""Creature Motion AI: existing video tools plus the Reference Walk Builder."""

bl_info = {
    "name": "Creature Motion AI",
    "author": "Creature Motion AI",
    "version": (0, 4, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Creature Motion AI",
    "description": "Analyze reference video and rig anatomy before building validated waypoint walks",
    "category": "Animation",
}

try:
    import bpy
except ModuleNotFoundError:  # Allow portable analysis/solver modules outside Blender.
    bpy = None

if bpy is not None:
    from . import operators, panel, skeleton_operator, animation_operator, landmark_review, collision_proxies, reference_walk_ui, anatomy_profile_ui, action_extrema, video_pose_waypoints


def register():
    if bpy is None:
        raise RuntimeError("Blender is required to register the add-on")
    operators.register()
    skeleton_operator.register()
    animation_operator.register()
    landmark_review.register()
    collision_proxies.register()
    panel.register()
    reference_walk_ui.register()
    anatomy_profile_ui.register()
    action_extrema.register()
    video_pose_waypoints.register()


def unregister():
    if bpy is None:
        return
    anatomy_profile_ui.unregister()
    action_extrema.unregister()
    video_pose_waypoints.unregister()
    reference_walk_ui.unregister()
    panel.unregister()
    landmark_review.unregister()
    collision_proxies.unregister()
    skeleton_operator.unregister()
    animation_operator.unregister()
    operators.unregister()


if __name__ == "__main__":
    register()

