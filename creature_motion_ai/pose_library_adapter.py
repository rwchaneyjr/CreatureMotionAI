"""Read-only conversion from approved pose-library observations to FK input."""
from .pose_library import load, side_view_fk_input

def load_approved_side_observations(path, source_video=None):
    return side_view_fk_input(load(path), source_video=source_video)
