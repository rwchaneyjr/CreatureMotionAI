"""Creature Motion AI Blender add-on - Milestone 1."""

bl_info = {
    "name": "Creature Motion AI",
    "author": "Creature Motion AI",
    "version": (0, 1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Creature Motion AI",
    "description": "Prepare creature video motion workflows and extract MP4 frames",
    "category": "Animation",
}

import bpy
from . import operators, panel


def register():
    operators.register()
    panel.register()


def unregister():
    panel.unregister()
    operators.unregister()


if __name__ == "__main__":
    register()

