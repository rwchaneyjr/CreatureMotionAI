# Balisk good-walk baseline — 2026-11-12

This folder preserves the Balisk walking result associated with the CreatureMotionAI work from November 12, 2026. The source-code checkpoint is commit `ab93f5db` on this branch; these generated artifacts were originally under ignored `data/generated/` and therefore are archived here explicitly.

## Contents

- `eight_leg_walk.blend` — saved Blender scene for the 8-leg walk.
- `balisk_eight_leg_review_5sec.mp4` — five-second animation preview.
- `balisk_reference_comparison_5sec.mp4` — reference/result comparison preview.
- `walk_configuration.json` — gait and solver settings.
- `walk_validation.json`, `saved_action_validation.json`, `media_validation.json` — recorded validation outputs.
- `refinement_summary.json`, `review_summary.md` — run summary and review notes.
- `fit_eight_leg_standing_pose.py` — source snapshot used by the refinement workflow.

## What this baseline represents

The walk was generated procedurally with a 40-frame cycle, rest-relative IK targets, and per-leg phase offsets/stride/lift settings. Approximate side-view video motion cues informed the gait refinement. It is not frame-by-frame motion capture, and the comparison should not be treated as proof of an exact match to the reference. See the reports for their recorded measurements and limitations.

The latest project work is preserved separately on `codex/balisk-good-animation-checkpoint`; this branch is the dated baseline plus its formerly ignored deliverables.
