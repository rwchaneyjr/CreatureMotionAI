# Creature Motion AI

Milestone 1 provides a Blender sidebar and a safe MP4 frame extractor. Machine-learning packages stay outside Blender's Python.

## Install the add-on

1. In Blender, open **Edit > Preferences > Add-ons > Install...**.
2. Select the `creature_motion_ai` folder (or a zip made from it).
3. Enable **Creature Motion AI**.
4. In the 3D View sidebar (`N`), open the **Creature Motion AI** tab.
5. Set Output Folder to an existing or new folder such as `C:\Users\rober\CreatureMotionAI\data\frames`.

## Extract a short test range

Use the external environment from PowerShell:

```powershell
& "C:\Users\rober\.venv\deeplabcut\Scripts\python.exe" `
  "C:\Users\rober\CreatureMotionAI\tools\extract_frames.py" `
  --video "C:\Users\rober\Pose2SimBehemoth\videos\balisk.mp4" `
  --output "C:\Users\rober\CreatureMotionAI\data\balisk_test" `
  --start 0 --end 30
```

The extractor writes numbered PNGs, `metadata.json`, and never modifies the source MP4. `--end` is exclusive.

## Milestone status

- Complete: add-on registration, sidebar, input validation, frame extraction, metadata.
- Not implemented yet: DeepLabCut project/training, landmark preview, rig mapping, 3D reconstruction, animation baking, cleanup, export.

