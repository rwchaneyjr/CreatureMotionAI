# Eight-leg reference refinement — review candidate

Both videos contain 120 newly rendered frames at 24 FPS (5 seconds). Decoded frames show motion throughout the clip. This is an experimental refinement, not a verified reference reconstruction.

The higher standing result in ../standing_attempt2_refit_01/standing.blend is preserved. Walking uses a body height 0.03 BU lower, allowing the full 0.13 BU stride on every leg. All original 38 bones, mesh vertices, weights and bone rest matrices passed the unchanged-data fingerprint check.

Implemented changes: retained the existing corrected solver; adjusted rear foot placement to remove measured rear/middle proxy intersections; added forward root motion at 0.005 BU/frame and a following camera; kept a 40-frame cycle repeated three times. No old Blender animation or preview was overwritten.

| Leg | Foot clearance BU | Forward/back travel BU | Max penetration BU | Max planted bone-tip slip/frame BU |
|---|---:|---:|---:|---:|
| Front.L | 0.05681 | 0.13000 | 0.000495 | 0.000003 |
| Front.R | 0.05841 | 0.13018 | 0.000451 | 0.000003 |
| MidFront.L | 0.05454 | 0.13000 | 0.000471 | 0.000007 |
| MidFront.R | 0.05662 | 0.13264 | 0.000375 | 0.000898 |
| MidRear.L | 0.06764 | 0.13097 | 0.000395 | 0.000110 |
| MidRear.R | 0.06780 | 0.13000 | 0.000262 | 0.000238 |
| Rear.L | 0.08038 | 0.13000 | 0.000359 | 0.000096 |
| Rear.R | 0.08041 | 0.13000 | 0.000312 | 0.000065 |

Contacts: maximum penetration 0.000495 BU; maximum planted floating 0.000953 BU. Maximum motion of any measured sole-region vertex is 0.001572 BU/frame, with per-leg medians no larger than 0.000166 BU/frame. Four to seven feet are in support.

Collision proxies: no inter-leg/body proxy intersections across the sampled 40-frame cycle. Exact surface self-intersections remain UNVERIFIED.

Loop: evaluated in-place pose error is zero. Root travels continuously; camera-relative projected joint error at frames 1/121 is 0.000166 pixels. The loop is not a teleport back to the same world position.

Mesh: original topology and weights unchanged. At sampled moving poses, the 99th percentile edge ratio relative to walk frame 1 is at most 1.197. Up to 43 small edges exceed 3x their frame-1 lengths, so localized deformation remains REVIEW_REQUIRED. Comparison to the older, already distorted attempt2 mesh is reported separately and must not be confused with neutral-rest deformation.

Reference evidence: provisional optical-flow patches show approximately148–180 pixel body-relative horizontal travel. The front patch has image-ground lift peaks at frames36 and75 (39-frame interval, consistent with the approximate38-frame observation). Generated Front.R peaks are36,76,116. Middle/rear second-cycle peaks occur about6 frames earlier than the reference.

After approximate shoulder-height/ground display alignment, Blender foot travel is about81–83 pixels versus provisional reference89–109 pixels. Centered trajectory RMSE is about17–29 pixels. These compare image patches against bone tips and are NOT calibrated anatomical reprojection errors.

Remaining visible differences: the preserved model has a longer tail and larger body relative to its legs; rear lift remains more exaggerated; some legs overlap in this side view; reference identities are unresolved. Far-side timing is modeled. No full dynamics or verified3D camera calibration is claimed.

Files: eight_leg_walk.blend; balisk_eight_leg_review_5sec.mp4; balisk_reference_comparison_5sec.mp4; standing.blend; standing_comparison.png; refinement_summary.json; saved_action_validation.json; walk_validation.json; media_validation.json; walk_configuration.json.

The source_snapshot folder captures the four implementation files used for this deliverable. Earlier versions remain available in reference_walk_refinement_02 and _03.
