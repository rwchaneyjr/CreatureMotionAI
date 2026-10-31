# CreatureMotionAI project specification

## Objective

Build a reusable Blender add-on that can accept an unrigged or rigged creature model plus an MP4 reference and, as far as technically feasible, analyze the creature, generate or reuse a skeleton, rig the mesh, fit motion, create a Blender Action, and export an animated FBX for Unity.

Initial test assets:

- Video: `C:\Users\rober\Downloads\balisk.mp4`
- Existing motion output: `data/motion/balisk_opencv_motion.json`
- Reference model: Crimson Spine Behemoth / Balisk assets supplied by the user

## Non-negotiable architecture

- Preserve the existing add-on and OpenCV backend.
- Keep model inspection, anatomy analysis, skeleton generation, skinning, video analysis, camera alignment, pose optimization, animation baking, export, and diagnostics independent.
- Do not hardcode one creature, leg count, bone naming convention, or humanoid/deer skeleton.
- Use editable anatomy profiles and skeleton templates.
- DeepLabCut remains optional; OpenCV silhouette/motion data is not assumed to identify anatomical joints.
- Never overwrite original models, videos, animations, or project files. Use working copies and new Actions.

## Required staged workflow

1. Audit and protect the project.
2. Inspect mesh geometry and identify candidate body parts.
3. Save an editable anatomy profile.
4. Generate an armature from a configurable template, with hierarchy and constraints.
5. Bind and validate weights; flag deformation failures.
6. Analyze video, preserving timing and confidence/missing observations.
7. Fit poses using model-guided render/compare optimization with limits, temporal consistency, and optional foot contact.
8. Bake, smooth, preview, report low-confidence frames, save a new `.blend`, export and reimport-test FBX.
9. Generalize through tested profiles, not unverified claims.

## Creature roadmap

Potential profiles: biped, quadruped, hexapod, octopod, scorpion, winged dragon, hydra, serpent, and octopus. A profile is not considered supported until a representative model passes rigging and animation tests.

## Testing gates

Before moving from skeleton work to video fitting, verify that bones are inside the mesh, intended limbs move independently, deformation is acceptable, the original asset remains unchanged, and a visual artifact is saved. Begin animation fitting with one frame, then approximately one second, before expanding.

## Current status

- Add-on installation and sidebar: implemented.
- MP4 selection and safe frame extraction: implemented.
- OpenCV normalized motion backend: implemented, but only silhouette/motion cues.
- Armature inspection and editable chain profile: implemented and tested on the Behemoth FBX.
- Portable pose-target solver and Blender Action writer: implemented and tested with a synthetic two-frame target.
- Automatic anatomy recognition: not implemented.
- Automatic skeleton generation: not implemented.
- Automatic skin weighting: not implemented or validated.
- Render-and-compare optimization: not implemented.
- Complete video-to-bones animation: not implemented.

## Immediate next phase

Complete mesh/anatomy inspection for the Balisk/Behemoth, produce an editable anatomy profile, then generate and visually validate a skeleton and initial skin weights. Do not begin the full animation solver until those artifacts pass validation.
