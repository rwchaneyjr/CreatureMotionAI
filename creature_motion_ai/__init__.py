"""Creature Motion AI Blender add-on - Milestone 1."""

bl_info = {
    "name": "Creature Motion AI",
    "author": "Creature Motion AI",
    "version": (0, 1, 1),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Creature Motion AI",
    "description": "Prepare creature video motion workflows and extract MP4 frames",
    "category": "Animation",
}

try:
    import bpy
except ModuleNotFoundError:  # Allow portable analysis/solver modules outside Blender.
    bpy = None

if bpy is not None:
    from . import operators, panel, skeleton_operator, animation_operator, landmark_review, collision_proxies


def register():
    if bpy is None:
        raise RuntimeError("Blender is required to register the add-on")
    operators.register()
    skeleton_operator.register()
    animation_operator.register()
    landmark_review.register()
    collision_proxies.register()
    panel.register()


def unregister():
    if bpy is None:
        return
    panel.unregister()
    landmark_review.unregister()
    collision_proxies.unregister()
    skeleton_operator.unregister()
    animation_operator.unregister()
    operators.unregister()


if __name__ == "__main__":
    register()

