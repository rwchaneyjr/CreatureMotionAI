# MoCapAnything V2 Balisk leg-motion diagnosis

## Result

The 24-frame official custom-rig prediction contains some leg motion, but the
resulting animation does **not** pass the original Balisk walking test. The
experimental Action is saved only in a copy of the Blender file. No five-second
loop was produced.

## Where leg motion was lost

The official Balisk species metadata lists 20 of its 24 leg bones in
`static_rot_joints`. The V2 pose-to-rotation stage applies that mask before BVH
export, replacing predicted leg rotations with reference rotations. This mask
comes from the example Balisk Move clip used to build species metadata; it is
not a limitation of BVH channels or our retargeter.

The saved `pose_pred.npy` has moving Rear.L joints, but its inferred distances
change substantially: the Rear.L hip-to-knee segment varies by up to 52% and
the knee-to-ankle segment by up to 23%. Those positions cannot be applied as
rigid bone endpoints without a constrained reconstruction step.

An isolated run of the official pose-to-rotation stage with only the 20 leg
mask entries disabled produced a new BVH with motion on all 24 leg bones. This
is an experiment, not a change to the official repository or the add-on.

## Retarget test on the original rig

The unmasked BVH was imported and retargeted to a copy of the original
38-bone armature. The original 601,909-vertex mesh deforms, the original bone
rest matrices remain unchanged, and existing Actions remain present. Rear.L
has visible knee/foot motion, no measured knee reversal, 10 contact frames,
and a maximum 5.37-degree foot-orientation change. Its frame-1 to frame-24
foot-tip seam is 0.0734 Blender units, so this test does not loop cleanly.

The full 24-frame test fails: 11 frames have more than 0.01 units of new mesh
ground penetration (maximum 0.0671 units); MidRear.L and Rear.R have no
detected contacts. In the synchronized comparison, the rendered creature is
too low and its legs drag while the reference walks upright. The original rig
and mesh are correctly transferred but the video match is poor. A Blender
visibility issue initially made the validator call the source bones static;
validation now unhides the source armature while measuring frame motion.

## Outputs (local, ignored by Git)

- `data/generated/mocapanything_poc/prediction_stage_diagnostic.json`
- `data/generated/mocapanything_poc/unmasked_rotation_test.json`
- `data/generated/mocapanything_poc/unmasked_bvh_channels.json`
- `data/generated/mocapanything_poc/balisk_unmasked_retarget_24f.blend`
- `data/generated/mocapanything_poc/unmasked_final_validation.json`
- `data/generated/mocapanything_poc/unmasked_24f_comparison_FAILED.mp4`
- `data/generated/mocapanything_poc/unmasked_24f_contact_sheet_FAILED.png`

## Next implementation step

Keep reliable MoCapAnything body motion as a candidate, then solve leg targets
from the reference video using CreatureMotionAI's visibility, contact, and
rest-pose constraints. Test Rear.L in a copied file first. The video-supported
leg motion must pass ground and visual checks before extending to all eight
legs. Do not present the current unmasked Action as a valid walk.
