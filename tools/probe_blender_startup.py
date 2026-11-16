"""Read-only delayed GUI startup probe; never open/save files inside startup."""
import json
import sys
import time
from pathlib import Path
import bpy

destination = Path(sys.argv[-1]).resolve()
started = time.monotonic()

def probe():
    windows = list(bpy.context.window_manager.windows)
    ready = bool(windows) and all(w.screen is not None for w in windows)
    if not ready and time.monotonic()-started < 30:
        return .5
    import creature_motion_ai
    operators = {}
    for name in ('measure_side_video', 'improve_reference_pose', 'refit_standing_cameras'):
        try:
            getattr(bpy.ops.cmai, name).get_rna_type()
            operators[name] = True
        except Exception:
            operators[name] = False
    destination.write_text(json.dumps({
        'status': 'PASS' if ready and all(operators.values()) else 'FAIL',
        'file': bpy.data.filepath, 'window_count':len(windows),
        'screens_ready': ready, 'operators':operators,
        'module':creature_motion_ai.__file__,
        'scene_modified':False, 'seconds_after_script':time.monotonic()-started,
        'method':'Normal .blend launch; deferred read-only probe after UI initialization'
    },indent=2))
    return None

bpy.app.timers.register(probe, first_interval=2)
