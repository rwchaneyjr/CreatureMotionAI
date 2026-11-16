# Camera workflow integration — 2026-11-15

The existing Reference Walk Builder panel now includes **Match Cameras to Standing
Model** and **Test Camera-Constrained Pose**, under Independent Reference Cameras.
Set the project folder, original standing Blender file, preserved best animation,
side video, optional front video, OpenCV Python, and output folder. No manual
Python command is required. Workers run in background Blender; the current scene
and Actions are not edited. These synchronous operators can temporarily block
the Blender interface while rendering.

## Executed checks

- Both new registered sidebar operators executed in Blender 5.2.2 using the
  workspace add-on. The open scene and Action list were unchanged.
- Camera fitting also passed with the front video left empty.
- The pose operator also passed without a front video; the panel draw callback
  exposed both new buttons and valid input fields. No interactive click was tested.
- This was an operator-level test in background Blender, not an interactive
  mouse-click test or proof that the installed GUI copy is updated.
- Fixed relative render paths being interpreted as `C:/data/...` by resolving
  workflow paths before opening a Blender file.
- Blender workers now use `--python-exit-code 1`; exceptions cannot silently
  return a successful process code. Error messages point to worker logs.
- Installed add-on code locates workers through the displayed project-folder
  setting, not its installation directory.

## Camera results

Actual rendered standing model; reference frame 26 optimized; frames 61 and 121
held out independently in each video. All measurement images are 640 by 360.
The blue rectangle is an upper-body image region, not a semantic torso mask.

| View | Upper-region IoU before → after | Centroid error before → after | Full silhouette IoU after |
| --- | --- | --- | --- |
| Side | 0.217 → 0.848 | 43.06 → 5.13 px | 0.632 |
| Front | 0.252 → 0.903 | 28.10 → 0.87 px | 0.561 |

Held-out upper-region IoU: side 0.843/0.839; front 0.896/0.893.
The side render faces right, like its reference. Bone pose channels were unchanged.
The before values are the unrefined candidate camera, not the historical 0.602
calibration; those historical scores are not directly comparable.

Calibration remains approximate/LOW confidence. Projection and depth are
ambiguous, and landmark reprojection error is unavailable without reliable
correspondences for these exact videos. The saturation-based mask currently
assumes a colored creature against a relatively neutral background. It is not
validated for arbitrary reference backgrounds or grayscale creatures. The
search is bounded, not a guarantee of the global optimum or metric calibration.
Visual inspection also found the side tail touches the left image boundary and
the front feet extend beyond the lower boundary. These are diagnostic body fits,
not approved full-body preview cameras. The standing legs do not match the
reference walking posture. A higher upper-body score does not resolve this.

## Pose result

The sidebar trial selects a detected camera-near chain geometrically rather than
hardcoding Balisk bone names. On this rig it selected MidRear.R with LOW anatomy
confidence. Three bounded existing-IK hypotheses rendered from both cameras.
All solver checks passed, with maximum joint error 8.56e-8 BU. The best silhouette
candidate changed side IoU from 0.631628 to 0.636784 and front IoU from 0.560677 to
0.562553. This is NOT an accepted reconstruction: joint identity, compatible front
pose, ground contact, and mesh collisions are not validated. No Action was created
or modified and no replacement walking video was produced.

## Shared state and remaining integration

Each camera run creates one `workflow_manifest.json` referenced by the sidebar
and existing workflow state. It stores input videos, camera profiles, calibration
report, calibrated copy, preserved best-animation path, and pose report.
`measured_positions` and `gait_timing` deliberately remain null, not invented.
Automatic improvement remains NOT TESTED. The legacy builder still has its own
state; full reconciliation of legacy measurements/gait timing with this manifest
is incomplete.

| Feature | Sidebar connection | This run |
| --- | --- | --- |
| Side/front video selection | Existing | Used, independent views |
| Standing-model camera search/overlays | New | Operator PASS |
| Bounded pose hypotheses | New | Operator PASS; reconstruction NOT ACCEPTED |
| Anatomy / Analyze Video and Rig | Existing | Not rerun here |
| Standing fit / waypoints / walk / validation / preview / loop | Existing | Not rerun; preserved baseline |
| Compare & Improve | Existing | Still uses earlier Blender comparison workflow; not a validated automatic reference optimizer |
| Verified pose reconstruction and automatic acceptance | Incomplete | No candidate accepted |

Output root: `data/generated/sidebar_camera_refit_tests/camera_refit_fd7b8bfdaf`.
Original standing and corrected walking files are preserved.
