"""Package existing add-on source, excluding bytecode and local outputs."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import uuid

root = Path(__file__).resolve().parents[1]
destination = root / 'data/generated' / ('creature_motion_ai_camera_sidebar_' + uuid.uuid4().hex[:8] + '.zip')
with ZipFile(destination, 'x', ZIP_DEFLATED) as archive:
    for path in sorted((root / 'creature_motion_ai').rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix in {'.py', '.json'}:
            archive.write(path, path.relative_to(root).as_posix())
with ZipFile(destination) as archive:
    assert archive.testzip() is None
    assert 'creature_motion_ai/camera_refit_service.py' in archive.namelist()
print(destination)
