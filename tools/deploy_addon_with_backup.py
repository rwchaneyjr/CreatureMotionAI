"""Back up the installed add-on, then deploy a vetted project ZIP without deletion."""
import hashlib
import json
import sys
import uuid
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
archive = Path(sys.argv[1]).resolve()
installed = Path.home() / 'AppData/Roaming/Blender Foundation/Blender/5.2/scripts/addons/creature_motion_ai'
run = root / 'data/generated/addon_deployments' / uuid.uuid4().hex[:12]
run.mkdir(parents=True)
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = {p.relative_to(installed).as_posix(): digest(p) for p in installed.rglob('*') if p.is_file()}
backup = run / 'installed_addon_backup.zip'
with ZipFile(backup, 'x', ZIP_DEFLATED) as z:
    for name in before:
        z.write(installed / name, 'creature_motion_ai/' + name)
with ZipFile(backup) as z:
    assert z.testzip() is None
    for name, sha in before.items():
        assert hashlib.sha256(z.read('creature_motion_ai/' + name)).hexdigest() == sha
# Validate every member before changing installed files.
with ZipFile(archive) as z:
    files = []
    for item in z.infolist():
        if item.is_dir(): continue
        relative = Path(item.filename)
        if relative.is_absolute() or '..' in relative.parts or relative.parts[0] != 'creature_motion_ai':
            raise ValueError('Unexpected archive member: ' + item.filename)
        target = installed.joinpath(*relative.parts[1:]).resolve()
        if not target.is_relative_to(installed.resolve()): raise ValueError('Unsafe install target')
        files.append((item.filename, target))
    for name, target in files:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(z.read(name))
    verified = all(hashlib.sha256(z.read(name)).hexdigest() == digest(target) for name, target in files)
receipt = dict(archive=str(archive), archive_sha256=digest(archive), installed=str(installed),
               backup=str(backup), backup_verified=True, files_before=before,
               installed_files=len(files), installed_hashes_match=verified)
(run/'deployment.json').write_text(json.dumps(receipt, indent=2))
assert verified
print(json.dumps({k:v for k,v in receipt.items() if k != 'files_before'}, indent=2))
print('Receipt:', run/'deployment.json')
