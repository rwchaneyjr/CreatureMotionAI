"""Exercise the registered pose sidebar operator against an existing camera run."""
import json
import sys
from pathlib import Path
import bpy
from types import SimpleNamespace

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
import creature_motion_ai

creature_motion_ai.register()
drawn_operators = []
drawn_properties = []


class RecordingLayout:
    """Exercise the panel draw callback and validate its property references."""
    def box(self): return self
    def row(self, **kwargs): return self
    def label(self, **kwargs): pass
    def prop(self, owner, name, **kwargs):
        assert hasattr(owner, name), name
        drawn_properties.append(name)
    def operator(self, identifier, **kwargs):
        drawn_operators.append(identifier)
        return SimpleNamespace()


creature_motion_ai.reference_walk_ui.CMAI_PT_reference_walk.draw(
    SimpleNamespace(layout=RecordingLayout()), bpy.context)
assert {'cmai.refit_standing_cameras', 'cmai.test_camera_pose'} <= set(drawn_operators)
assert {'side_video', 'front_video', 'standing_model', 'project_folder'} <= set(drawn_properties)
settings = bpy.context.scene.cmai_walk
settings.project_folder = str(root)
settings.external_python = str(root / '.venv-dlc/Scripts/python.exe')
settings.shared_manifest = sys.argv[-1]
before = [(obj.name, obj.type) for obj in bpy.context.scene.objects]
actions = [action.name for action in bpy.data.actions]
result = bpy.ops.cmai.test_camera_pose()
assert result == {'FINISHED'}, result
assert before == [(obj.name, obj.type) for obj in bpy.context.scene.objects]
assert actions == [action.name for action in bpy.data.actions]
report = {
    'operator': str(result), 'scene_preserved': True, 'actions_preserved': True,
    'pose_report': settings.compare_report,
    'panel_draw': 'PASS',
    'test_mode': 'Registered sidebar operator in background Blender; interactive click not tested',
}
Path(settings.shared_manifest).with_name('pose_sidebar_test.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report))
