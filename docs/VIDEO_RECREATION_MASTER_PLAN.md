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

## Isolated foot-contact milestone — 2026-11-18

Implemented and measured a reusable, leg-count-independent contact-state layer
without changing the original Balisk loop or rig:

- `creature_motion_ai/contact_states.py`: confidence-weighted STANCE, SWING,
  and UNCERTAIN states, separate entry/exit thresholds, confirmation frames,
  and world-space anchor release when observations or constraints fail.
- `creature_motion_ai/contact_lock.py`: fixed weighted underside-mesh sole
  patches and generic per-limb contact helpers. The Blender experiment supplies
  anatomy-profile chains and reuses the existing rest-relative two-link IK;
  it does not apply whole-body root correction.
- `tools/run_contact_lock_experiment.py` and
  `tools/validate_contact_lock_readback.py`: isolated candidate generation and
  fresh saved-file before/after measurements. Original source remains intact.
- `tools/render_contact_lock_candidate.py` and
  `tools/make_contact_lock_comparison.py`: same-camera 5-second visual preview.

The candidate reduces mean stance sole drift on all eight legs (about 79% to
99.97% by fixed mesh-patch measurements). Rest-relative segment lengths and
knee-bend direction pass; all eight sole patches stay within the 3 mm ground
tolerance; loop endpoint error is zero. Capsule proxy checks report no hits.
Positive swing lift is **UNVERIFIED** because the baseline produces few confident
swing frames and sub-millimeter lift. Exact mesh self-collision and center-of-
mass support stability are also **UNVERIFIED**; proxy results do not establish
those properties. See `contact_lock_v1/contact_lock_comparison.json` for all
per-leg measurements and limitations. Candidate file and preview are in the
same `contact_lock_v1` output folder beside the preserved baseline.

Next: improve swing/contact observability and positive clearance, then add exact
evaluated-mesh collision validation and support-polygon stability before making
the contact layer a default add-on action. Do not treat the current candidate as
reference-video motion capture; it refines the existing procedural loop.

No detector weights, Google Vids generation, new skeleton, IK setup, or full-video animation should be started before that gate passes.

## Reference-guided stepping gate — 2026-11-18

Added a reusable 2D step-event evidence adapter:

- `creature_motion_ai/reference_step_events.py` measures hip-relative knee/foot
  paths and reports stance/swing *candidates* from explicitly reviewed points.
- `tools/analyze_reference_step_events.py` writes a per-frame diagnostic report.
- The adapter requires a hash-bound approval manifest containing the approved
  leg identity, `identity_verified: true`, and the exact tracking-file SHA-256
  before any observations become eligible for constrained fitting. Prediction
  rows, hidden/missing joints, and mismatched approval manifests remain
  provisional; approval only makes the 2D events eligible for 3D fitting and
  does not authorize Action creation. This code emits neither Blender keys nor
  3D contacts.
- `tools/test_reference_step_events.py` checks that prediction-only tracks and
  wrong-leg approvals are rejected, while reviewed relative foot lift is
  recognized as a candidate event.

The existing `data/generated/dlc_tracking_best30/leg_rear_left_tracking.json`
is still a DeepLabCut prediction track, not an approved Rear.L observation set.
Therefore the current track can quantify candidate 2D motion but cannot
truthfully drive a reference-guided Action. The previously saved planar Rear.L
test is not a substitute: its report identifies leg identity and camera-space
to-world motion as provisional. No new Action or preview was generated from
those unverified points. The next valid input is a manually reviewed, identity-
confirmed Rear.L track; after that, events can be fitted through calibrated 3D
sole points and the existing `FootContactTracker`/IK pipeline.

## Multi-creature quadruped compatibility test — 2026-11-19

Added one profile-driven Blender setup panel while leaving the existing Balisk
panels and solvers registered:

- `creature_motion_ai/rig_profiles.py` now proposes numbered limb chains only
  when their parent hierarchy is contiguous. It also proposes body, head, wing,
  and tail groups from names. These are editable proposals, not automatic truth.
- `creature_motion_ai/anatomy_profile_ui.py` adds the `Multi-Creature Setup`
  panel. Users can correct chains/roles, explicitly confirm each limb identity,
  and save a new versioned profile. It offers separate existing-Action and
  reference-video modes; only the video mode requires a video path.
- Existing-Action mode has a read-only analysis operator. It measures per-limb
  bone-head paths and distal endpoint bounds and restores the armature's assigned
  Action and frame afterward. It does not edit keys or claim contact, collision,
  or video validation.
- `tools/test_multicreature_anatomy_ui.py` smoke-tests the operators in Blender.
  The Balisk panels remain registered; no Balisk profile/action was used in the
  dragon contact test.
- `tools/test_balisk_profile_compat.py` confirmed the new proposer still finds
  all eight contiguous leg chains on `original_static_standing.blend` (38 bones).

Dragon test copy: `data/generated/dragon_quadruped_compatibility/`

- Read-only structure audit found a 47-bone armature, four contiguous
  three-bone leg chains, a weighted skinned mesh, and separate `FLAP`/`RUN`
  Actions. `Move_Scissor_Offset` is 73 frames at 30 fps. Wings have no motion in
  that Action. The original dragon file was not edited.
- A confirmed editable dragon profile and a no-video workflow report were
  written in `cmai_anatomy_profiles/` and `cmai_anatomy_reports/`.
- The Blender UI smoke test passed on the isolated copy: four legs were
  analyzed for frames 1–73, the source Action and current frame were restored,
  and `action_modified` was false. Report:
  `cmai_anatomy_reports/action_analysis_20261119_145257.json`.
- Contact-lock trial output is in `contact_trial/`. The source Action and a
  separate candidate Action/file are both retained. A same-camera source versus
  candidate preview was rendered at native timing:
  `contact_trial/dragon_move_scissor_before_after.mp4` (73 frames, 30 fps,
  2.43 seconds; not stretched or looped).

Contact result: **NOT PASSED**. The front terminal-weighted patches had small
reductions in total stance path (7.3% left, 6.4% right), but their worst
per-frame movement increased from about 0.0142 to 0.0439 world units. Both rear
chains remained UNCERTAIN for all 73 frames, and minimum support was zero. The
report marks ground penetration, rest bone lengths, proxy-collision checks, and
endpoint continuity as passing for this candidate, while support and overall
foot-slip criteria fail or remain unverified. Ground height was inferred from
low terminal-weighted surface samples because the scene has no ground object;
the detected regions are candidate underside patches, not artist-authored
soles. Segment proxies do not prove that the full mesh has no self-intersection.
The selected `Move_Scissor_Offset` is a flying/scissoring pose rather than a
grounded walking action, so it is a poor contact-lock benchmark. Keep the
candidate as a diagnostic artifact, not as an improved or validated
replacement.

This demonstrates that anatomy-profile setup and read-only Action analysis work
on a second, four-legged rig. It does **not** demonstrate quadruped contact
locking, reference-video animation on the dragon, or arbitrary-rig auto-detection.
The next useful quadruped test needs a grounded Action or explicitly defined
ground plane/contact regions; do not rerun contact locking on this airborne
Action as if it were a walking test.
