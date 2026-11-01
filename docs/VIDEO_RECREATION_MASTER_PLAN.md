# CreatureMotionAI: Two-Camera Synthetic-Training Video-to-Rig Plan

Status: Phase 1 audit and planning only. No Blender assets, original FBX files, or source videos are modified by this plan.

## Objective

Build a reusable pipeline for unusual creatures that:

1. preserves an existing rig and rest pose;
2. renders synthetic, anatomically valid training data with known joint positions;
3. trains a creature-specific keypoint detector;
4. validates the detector on known synthetic motion;
5. optionally accepts a dual-view generated/reference video;
6. reconstructs 3D joint motion with calibrated cameras;
7. creates a new Blender Action on the original deform rig; and
8. validates ground contact, joint limits, deformation, and export.

The first target is the eight-legged Balisk. Later profiles should support different leg, head, wing, and tail counts without hardcoded bone names.

## Existing system inventory

### Add-on and Python modules

- `creature_motion_ai/__init__.py`, `panel.py`, and `operators.py`: Blender registration, sidebar, and operators.
- `creature_motion_ai/skeleton.py`: armature inspection, hierarchy extraction, chain candidates, and profile writing.
- `creature_motion_ai/video_analysis.py`: OpenCV silhouette/motion observations. It does not identify anatomical joints.
- `creature_motion_ai/solver.py`: segment-angle pose targets. It currently uses simple 2D angles and is not a validated 3D solver.
- `creature_motion_ai/animation_operator.py`: writes pose-target rotations into a new Blender Action. It needs rest-pose-relative rotations and stronger validation before production use.
- `creature_motion_ai/motion_data.py`: motion-data validation helpers.

### Tools

Reusable or relevant tools include:

- `inspect_creature_mesh.py`, `generate_skeleton_from_profile.py`, and `bind_and_test_generated_rig.py` for anatomy/rig prototypes.
- `extract_frames.py`, `analyze_video_opencv.py`, and `compare_render_to_video.py` for video processing and comparisons.
- `make_static_original_pose.py`, `diagnose_asset_difference.py`, and `verify_clean_rig.py` for asset preservation checks.
- `calibrate_single_frame.py`, `fit_single_frame_pose.py`, and `fit_multibone_single_frame.py` for experimental camera/pose fitting.
- `validate_ik_rest_pose.py` and grounded-leg tests for failure diagnostics.
- `propose_dlc_annotations.py` and `run_auto_annotation.ps1` for optional reviewable landmark proposals.
- `make_side_by_side_video.py`, `side_by_side_videos.py`, and render helpers for visual validation.

These are prototypes and experiments, not yet a single reproducible pipeline. Several contain hardcoded Windows paths or Blender executable paths.

### Assets and known canonical inputs

- Clean source rig: `data/generated/original_static_standing.blend`.
- Reference video: `C:\Users\rober\Downloads\8leggedBalisk.mp4`.
- Original FBX supplied by the user: `CrimsonSpineBehemoth_Animated.fbx`.
- Existing eight leg chains:

  - `Leg_Front.L_01 → _02 → _03`
  - `Leg_Front.R_01 → _02 → _03`
  - `Leg_MidFront.L_01 → _02 → _03`
  - `Leg_MidFront.R_01 → _02 → _03`
  - `Leg_MidRear.L_01 → _02 → _03`
  - `Leg_MidRear.R_01 → _02 → _03`
  - `Leg_Rear.L_01 → _02 → _03`
  - `Leg_Rear.R_01 → _02 → _03`

- Axial/head/tail bones: `Root`, `Body_01`–`Body_03`, `Head_01`–`Head_02`, and `Tail_01`–`Tail_08`.

The clean source has 38 bones, no IK constraints, and a static standing Action. It remains the authoritative baseline.

## Comparison with the demonstrated workflow

| Demonstrated concept | Current project | Planned implementation |
|---|---|---|
| Existing creature model | Mesh and original FBX available | Preserve as immutable source; use working copies |
| Automatic skeleton/rig validation | Prototype inspection and generation tools | Validate existing Balisk rig first; optional UniRig only for unrigged models |
| Synthetic labeled poses | Not implemented as a studio | Two calibrated Blender cameras, constrained random poses, labels and visibility |
| Creature-specific detector | Not implemented | DINO-family feature extractor plus keypoint head, using PyTorch |
| Automatic exam | Not implemented | Known-pose render → detection → reconstruction → error report |
| Dual-view motion | No reliable dual-view input yet | Blender-generated validation first; Google Vids output accepted only after consistency checks |
| 3D reconstruction | Experimental 2D/silhouette fitting only | Calibrated triangulation plus SciPy constrained fitting |
| Animation output | Experimental Actions; failures documented | New Action on original deform bones, then validation and FBX export |

The video’s behavior is a design reference. Its private implementation, training data, and exact detector are not assumed to be available.

## Reusable components

Retain and adapt:

- existing rig/profile inspection and verified bone map;
- original-pose preservation and asset-difference diagnostics;
- OpenCV frame extraction, video metadata, and render comparison;
- Blender Action creation concepts from `animation_operator.py` and the earlier Fab-Monsters retargeter;
- anatomy-profile approach for future creature types;
- side-by-side and quality-report tooling;
- optional DeepLabCut proposal/CSV workflow as a fallback review tool, not a required dependency.

Do not reuse as production motion logic:

- the old absolute-pixel-to-bone rotation calculations;
- generic gait outputs as a substitute for reference motion;
- the previous IK setup that curled or flipped legs;
- any generated `.blend` whose visual validation failed.

## Missing components

1. Reproducible dependency/environment manifest.
2. Canonical asset/report index so stale experiments cannot be selected accidentally.
3. Two-camera Blender studio with saved intrinsics/extrinsics and synchronized renders.
4. Constrained synthetic pose generator and 2D/3D/visibility label writer.
5. DINO-family detector training/evaluation pipeline.
6. Automatic synthetic-motion exam with numerical pass/fail thresholds.
7. Dual-view panel splitting and consistency validation for Google Vids output.
8. Calibrated triangulation and confidence-aware 3D reconstruction.
9. SciPy bounded pose fitting with fixed bone lengths, temporal smoothing, contacts, and rest-pose regularization.
10. Animation baking, invalid-frame repair, FBX export/reimport validation, and Unity smoke testing.
11. Non-blocking Blender job execution and progress/error reporting.

## Proposed architecture

```text
video_processing/   MP4 metadata, extraction, panel detection, frame quality
skeleton/           rig inspection, rest transforms, anatomy profiles, mapping
synthetic/          constrained poses, two-camera rendering, labels, visibility
detector/           DINO/PyTorch training, inference, confidence calibration
exam/               known-motion detector/reconstruction benchmark
reconstruction/     camera calibration, triangulation, uncertainty handling
solver/             SciPy least_squares, FK, limits, contacts, smoothing
animation/          local rotations, Actions, baking, preview rendering
validation/         joint limits, contacts, errors, deformation, comparisons
export/             FBX/GLB output and Unity reimport checks
blender_addon/      sidebar, background jobs, progress, artifact selection
``` 

The first implementation should remain inside the existing repository. A separate V2 copy is optional but must not replace the current project or source assets.

## Dependencies and hardware

Required baseline:

- Blender 5.2.x for asset inspection, rendering, Actions, and export.
- External Python environment for OpenCV, NumPy, SciPy, PyTorch, and data tools.
- DeepLabCut 3.0.2 is installed from the GitHub checkout but is optional.
- SLEAP is optional and is not required for the synthetic-detector plan.
- Git and a supported Python 3.12 environment are currently available.

Planned detector dependencies include PyTorch, DINO-family model code/weights, torchvision/timm as appropriate, OpenCV, SciPy, NumPy, and an image/data format library. Exact versions should be locked before training.

Hardware guidance:

- 100 synthetic images: CPU-capable, but GPU preferred.
- 3,000 images and detector training: dedicated GPU strongly recommended; VRAM requirement depends on image resolution, backbone, batch size, and augmentation.
- Keep model weights and large checkpoints outside Git and download them only after explicit approval.
- Generated images and renders may consume tens of GB; use an artifact directory and retention policy.

## Staged testing strategy

### Gate 1 — Asset and rig preservation

- Verify original mesh/materials, 38 bones, hierarchy, rest transforms, and weights.
- Confirm no source FBX or clean standing blend is modified.
- Render the original standing pose.

### Gate 2 — Two-camera studio

- Render one known pose from both cameras.
- Save camera JSON and projection matrices.
- Confirm both views show identical pose and synchronized frame numbering.

### Gate 3 — 100 synthetic poses

- Generate only anatomically valid poses.
- Validate labels against Blender projections and visibility flags.
- Inspect a contact sheet and held-out examples.

### Gate 4 — Detector exam

- Train/evaluate on held-out synthetic poses.
- Report per-joint pixel error, missing rate, identity swaps, and confidence calibration.
- Stop if overlapping-leg performance is unacceptable.

### Gate 5 — Known-motion reconstruction

- Render a known 24-frame Action from both cameras.
- Detect, triangulate, solve, and compare with ground truth.
- Require bone-length consistency, bounded rotation error, contact stability, and no invalid frames.

### Gate 6 — External dual-view video

- Validate panel boundaries, fixed cameras, timing, limb count, and cross-view consistency.
- Reject incompatible Google Vids output before triangulation.

### Gate 7 — One-second Balisk test

- Fit 24 frames only.
- Render a synchronized side-by-side comparison.
- Visually inspect all eight legs and ground contacts.
- Only then expand to 241 frames and export FBX.

## Estimated difficulty

| Phase | Difficulty | Main risk |
|---|---:|---|
| Asset/studio audit | Medium | stale artifacts and camera conventions |
| Two-camera Blender studio | Medium | projection/calibration consistency |
| Synthetic data generation | Medium | invalid random poses and storage |
| DINO detector | High | compute, data quality, overlapping legs |
| Automatic exam | High | detector and reconstruction errors interacting |
| Google Vids validation | High | generated views may not share 3D motion |
| Triangulation/pose fitting | Very high | single-view ambiguity and joint identity |
| Animation/FBX/Unity validation | Medium | coordinate systems and export settings |
| Generalization to other anatomies | Very high | profile and detector changes |

## Google Vids dual-camera risks

Google Vids/Veo may alter anatomy, limb count, camera geometry, timing, or the relationship between two panels. A prompt cannot guarantee physically consistent stereo views. Therefore:

- use Blender-generated dual-camera footage for the first reconstruction tests;
- treat external generated video as uncalibrated until measured;
- compare detections and triangulated geometry across both panels;
- reject the video if reprojection or cross-view consistency exceeds thresholds;
- never force triangulation from incompatible views.

### Split-screen reference workflow

The external-video workflow should use one split-screen reference image or video:

- left panel: Camera A side view;
- right panel: Camera B front view, approximately 90 degrees around the vertical axis;
- both panels: the same pose and frame time.

Two independently generated clips must not be treated as synchronized stereo. The
pipeline must split an imported split-screen MP4, validate panel boundaries and
timing, compare corresponding joint identities, and reject inconsistent views
before triangulation. Blender-generated dual-camera renders remain the ground-truth
calibration test because their geometry is known.

## Next exact implementation task

After approval of this plan, implement the next dual-camera stage:

1. Add a two-camera Blender studio builder around `original_static_standing.blend`.
2. Export camera intrinsics/extrinsics and projection matrices to JSON.
3. Render one identical standing pose from both cameras.
4. Produce a split-screen preview and a camera-validation report.
5. Generate the reusable Google Vids prompt at `prompts/balisk_google_vids.txt`.
6. Add split-screen MP4 import, panel splitting, and consistency checks.
7. Do not triangulate external video until the Blender known-motion exam passes.

No detector weights, Google Vids generation, new skeleton, IK setup, or full-video animation should be started before that gate passes.
