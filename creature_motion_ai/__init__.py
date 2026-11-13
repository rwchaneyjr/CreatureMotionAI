"""Creature Motion AI: existing video tools plus the Reference Walk Builder."""

bl_info = {
    "name": "Creature Motion AI",
    "author": "Creature Motion AI",
    "version": (0, 2, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Creature Motion AI",
    "description": "Review creature motion, fit standing poses, and build validated waypoint walks",
    "category": "Animation",
}

try:
    import bpy
except ModuleNotFoundError:  # Allow portable analysis/solver modules outside Blender.
    bpy = None

if bpy is not None:
    from . import operators, panel, skeleton_operator, animation_operator, landmark_review, collision_proxies, reference_walk_ui


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


def unregister():
    if bpy is None:
        return
    reference_walk_ui.unregister()
    panel.unregister()
    landmark_review.unregister()
    collision_proxies.unregister()
    skeleton_operator.unregister()
    animation_operator.unregister()
    operators.unregister()


if __name__ == "__main__":
    register()

