# Biohub Experiment Log

Date started: 2026-07-11

This file tracks the experiments, notebooks, artifacts, decisions, and observed scores for the Biohub Cell Tracking During Development Kaggle project. The goal is to keep a reproducible record of what was tried, why it was tried, what changed, and whether it helped.

## Current Baseline Understanding

Competition task:

- Detect cell centroids in 3D+time microscopy volumes.
- Link cells across consecutive timepoints.
- Recover divisions/lineage.
- Submit `submission.csv` with node rows and edge rows.

Metric:

```text
score = adjusted_edge_jaccard + 0.1 * division_jaccard
```

Important metric details:

- Node matching uses scaled centroid distance.
- Matching cap: `7.0 um`.
- Physical scale: `z=1.625`, `y=0.40625`, `x=0.40625 um/voxel`.
- Ground truth is sparse, so local sparse-GT precision is not reliable by itself.
- Edge false negatives matter a lot because most observed local errors are missed true GT edges, not matched false positives.

Data status:

- Train image Zarrs: `199`
- Train GEFFs: `199`
- Paired train samples: `199`
- Public test Zarrs: `4`
- Zarr shape: `(100, 64, 256, 256)`
- dtype: `uint16`
- chunks: `(1, 64, 256, 256)`
- Final Drive extraction is clean.

## Main Notebooks

| Notebook | Purpose | Status |
|---|---|---|
| `Biohub_Cell_Tracking_Baseline_Colab.ipynb` | Safe classical baseline, Drive paths, optional Kaggle download | Working |
| `Biohub_EDA_and_Local_Validation.ipynb` | Dataset integrity, GEFF/Zarr checks, visual checks | Working |
| `Biohub_Strategy_EDA_and_Validation.ipynb` | Full EDA summaries, validation sample selection, reports | Working |
| `Biohub_Local_Scorer_and_Sweep.ipynb` | Classical local scorer and threshold/radius sweeps | Working |
| `Biohub_First_Submission.ipynb` | First classical Kaggle submission | Working, public score `0.631` |
| `Biohub_Local_Method_Compare.ipynb` | Compare saved submissions against sparse train GT | Working |
| `Biohub_DeepCenter_Colab_Local_Validation.ipynb` | Run public DeepCenter pipeline in Colab/Drive | Working after checkpoint repairs |
| `Biohub_DeepCenter_Missing19_Recovery.ipynb` | Recover missing/corrupt DeepCenter prediction GEFFs | Used successfully |
| `Biohub_DeepCenter_Postprocess_Tuning.ipynb` | Full/checkpoint postprocess tuning | Used, one long run failed before repairs |
| `Biohub_Targeted_Postprocess_Tuning.ipynb` | Targeted postprocess tests on worst/guard samples | Active |
| `Biohub_Video_and_Overlay_Viewer.ipynb` | Visualize 3D/time videos and overlays | Created |

## External Artifacts

Downloaded/extracted public artifacts:

```text
external_archives/archive (1).zip
external_archives/archive.zip
external_archives/archive (2).zip
```

Extracted locations:

```text
artifacts/biohub-tracking-support-pack-50ep-v1
artifacts/biohub-deepcenter-unet3d-center-prior-v1
```

Main learned model pieces:

- UNet/DeepCenter detection prior.
- Node transformer edge predictor.
- ILP graph linking/postprocess.
- Full-frame center fusion checkpoint:

```text
artifacts/biohub-deepcenter-unet3d-center-prior-v1/weights/full_frame_center/checkpoint_last.pt
```

Note:

- Full-frame checkpoint reports `epoch=500`, `best_score=-0.045...`.
- The negative value is an internal training/loss-style score from the checkpoint, not the Kaggle score.

## Experiment 1: Classical Baseline

Notebook:

```text
Biohub_First_Submission.ipynb
```

Method:

- Per-frame classical peak/blob detection.
- Simple nearest-neighbor physical-distance linking.
- Tuned with local sparse-GT sweeps.

Kaggle result:

```text
Public score: 0.631
```

Conclusion:

- Format and submission pipeline are correct.
- Classical approach is far below leaderboard and public DeepCenter-style methods.
- Useful as sanity baseline only.

## Experiment 2: Classical Parameter Sweep

Notebook:

```text
Biohub_Local_Scorer_and_Sweep.ipynb
```

Early 6-sample selected-config result:

| Config | Local adjusted approx | Edge matched | Node recall |
|---|---:|---:|---:|
| `det4_radius9_balanced` | `0.676015` | `0.704389` | `0.876390` |
| `det4_radius8_balanced` | `0.673518` | `0.701715` | `0.876390` |
| `det0_radius9_high_recall` | `0.575721` | `0.698287` | `0.925486` |
| `det0_radius8_high_recall` | `0.572417` | `0.694434` | `0.925486` |

Full-sequence mini validation, 6 samples:

```text
mean edge_jaccard_adjusted_approx: 0.675821
mean edge_jaccard_matched:         0.700331
mean node_recall_sparse_gt:        0.894652
```

Conclusion:

- Classical detector/linker is not competitive.
- High recall alone overpredicts nodes and hurts adjusted score.
- We moved to the learned public DeepCenter pipeline.

## Experiment 3: Public DeepCenter Notebook Inspection

External notebook:

```text
biohub-cell-tracking-blend-preprocessings.ipynb
```

Public idea:

- Learned center detection.
- Transformer edge prediction.
- ILP linking.
- Postprocess with motion relink, gap close, safe divisions, short-track filtering.

Observed public leaderboard:

```text
DeepCenter-style public score around 0.889 / 0.897 depending variant.
Top leaderboard around 0.910.
```

Decision:

- Use public DeepCenter pipeline as the new base.
- Improve by targeted postprocess tuning instead of building a new model from scratch immediately.

## Experiment 4: DeepCenter 6-Sample Local Validation

Notebook:

```text
Biohub_DeepCenter_Colab_Local_Validation.ipynb
Biohub_Local_Method_Compare.ipynb
```

Samples:

```text
44b6_0c582fdc
44b6_d754aa59
44b6_aaf8b0ea
44b6_2a2eff9f
44b6_7e557709
44b6_8f5ab931
```

Result versus classical baseline:

| Method | Local edge adjusted approx | Edge matched | Node recall |
|---|---:|---:|---:|
| baseline classical | `0.735336` | `0.735336` | `0.893118` |
| deepcenter | `0.966079` | `0.966079` | `0.996332` |

Conclusion:

- DeepCenter is dramatically better than classical baseline.
- Local sparse-GT edge score can be much higher than Kaggle public because official metric and hidden set are stricter.

## Experiment 5: First DeepCenter Kaggle Submission

Notebook:

```text
Biohub First Submission / public DeepCenter variant
```

Kaggle public result:

```text
Public score: 0.889
```

Interpretation:

- Strong base; close to public cluster around `0.897`.
- Need incremental improvements, not a wholesale rewrite yet.

## Experiment 6: Full199 DeepCenter Local Validation

Notebook:

```text
Biohub_DeepCenter_Colab_Local_Validation.ipynb
Biohub_Local_Method_Compare.ipynb
```

Purpose:

- Run DeepCenter on all 199 train samples as pseudo-test.
- Build local sparse-GT scores and run stats.
- Identify weak samples and postprocess levers.

Runtime:

```text
prediction minutes total: ~694.7 min
```

Generated:

```text
reports/deepcenter_full199_local_validation_scores.csv
reports/deepcenter_full199_local_validation_run_stats.csv
reports/deepcenter_full199_local_validation_score_summary.csv
reports/deepcenter_full199_local_validation_worst_samples.csv
```

Full199 output size:

```text
rows:  7,899,544
nodes: 4,024,988
edges: 3,874,556
bad node coords before clip: 7603
bad node coords after clip:  0
```

Local sparse-GT summary:

```text
local_weighted_edge_jaccard_approx: 0.950808
mean_edge_jaccard_matched:          0.947716
median_edge_jaccard_matched:        0.958478
p10_edge_jaccard_matched:           0.880274
min_edge_jaccard_matched:           0.744966
mean_node_recall_sparse_gt:         0.989475
total_edge_tp:                      122678
total_edge_fp_matched:              142
total_edge_fn:                      6205
total_gt_divisions_direct:          151
total_pred_divisions_direct:        12961
direct_division_jaccard_diagnostic: ~0.000229
```

Important run-stat totals:

```text
motion_relink_edges:         3,897,785
motion_relink_tight_edges:   3,758,858
motion_relink_relaxed_edges:   138,927
gap_added_nodes:                77,829
gap_added_edges:               155,658
safe_division_candidates:       17,374
safe_divisions_added:           12,971
short_track_nodes_removed:     268,989
short_track_edges_removed:     191,858
```

Conclusion:

- Main DeepCenter weakness locally is not matched FP; `edge_fp_matched` is tiny.
- The main edge loss is false negatives and distance drift.
- Division-like predicted branches are far more numerous than sparse direct GT divisions.
- Official division metric is more complex than direct out-degree, so direct division diagnostic is useful but not definitive.

## Experiment 7: Checkpoint GEFF Recovery

Problem:

- Full prediction GEFF checkpoint initially incomplete/corrupt.
- Missing 19 prediction graphs.
- Then 9 GEFFs were structurally corrupt.

Checkpoint folder:

```text
reports/deepcenter_full199_prediction_geff_checkpoint
```

Recovered missing 19 samples:

```text
6bba_df673a83
6bba_e16ffc58
6bba_e5e44988
6bba_ebdf3b34
6bba_ebff6e76
6bba_ed9377fd
6bba_edf14583
6bba_eebc57a5
6bba_ef7b4f7e
6bba_f17befbc
6bba_f1fde7e0
6bba_f20478e9
6bba_f4ae811c
6bba_f8ffd5e7
6bba_fbc898dc
6bba_fc516dc6
6bba_fc5f39dc
6bba_fc83837d
6bba_fe670320
```

Repaired/recovered bad 9 GEFFs:

```text
6bba_cff5865f
6bba_d0fc38b5
6bba_d1acb6ff
6bba_d2b9fc0c
6bba_d3da753b
6bba_d5eae175
6bba_d6ecebbb
6bba_d82a4fc6
6bba_debd7bfa
```

Final checkpoint status:

```text
checkpoint GEFF count: 199
still_bad: 0
CHECKPOINT STRUCTURE OK: 199/199
```

Conclusion:

- We can now do postprocess-only tuning without rerunning the expensive model inference.
- This checkpoint is critical; do not delete it.

## Experiment 8: Worst-Sample Analysis

Reports:

```text
reports/targeted_worst_samples_for_tuning.csv
reports/targeted_worst_variant_sets.csv
reports/targeted_validation_sets.csv
```

Worst observed samples include:

| sample_id | edge_jaccard | node_recall | edge_fn | match_p95_um | motion_relaxed | gap_frac | safe_div |
|---|---:|---:|---:|---:|---:|---:|---:|
| `44b6_87bba6c4` | `0.744966` | `0.934641` | `38` | `4.942` | `2363` | `0.0253` | `119` |
| `44b6_f28707c6` | `0.786885` | `0.873016` | `13` | `4.040` | `1078` | `0.0169` | `45` |
| `6bba_207c6aaf` | `0.801325` | `0.955789` | `87` | `5.230` | `1678` | `0.0253` | `83` |
| `6bba_c73a1d11` | `0.826573` | `0.983718` | `119` | `5.463` | `2308` | `0.0235` | `110` |
| `44b6_e57ff5c6` | `0.833333` | `0.968912` | `31` | `4.531` | `2208` | `0.0331` | `63` |
| `44b6_2f31fc2f` | `0.835294` | `1.000000` | `14` | `4.503` | `1655` | `0.0340` | `80` |

Correlation with edge score:

| Feature | Correlation vs edge_jaccard |
|---|---:|
| `match_distance_p95_um` | `-0.6798` |
| `motion_relink_relaxed_edges` | `-0.6484` |
| `edge_fn` | `-0.6171` |
| `pruned_isolated_nodes` | `-0.6069` |
| `gap_added_nodes_frac` | `-0.4638` |
| `short_track_nodes_removed` | `-0.4099` |
| `safe_divisions_added` | `-0.3773` |
| `node_recall_sparse_gt` | `+0.6588` |
| `edge_to_node_ratio` | `+0.4614` |

Interpretation:

- The bad samples are mostly edge-FN / distance-drift / aggressive postprocess problems.
- Matched FP is not the main issue.
- `no_safe_divisions` alone is too blunt because safe division sometimes helps preserve true edges.
- The next tuning should focus on:
  - conservative safe division, not disabling it
  - motion/gap controls
  - linefit/smoothing distance drift
  - short-track filtering

## Experiment 9: Targeted Set Construction

Target set flags:

| Set | Count | Purpose |
|---|---:|---|
| `bottom24_edge_rescue` | `24` | Worst edge-score samples |
| `low_recall_rescue` | `11` | Low node-recall samples |
| `motion_gap_conservative` | `16` | High motion/gap-risk samples |
| `branch_div_conservative` | `16` | High branch/division-risk samples |
| `guard_high_score` | `12` | High-score samples to protect |
| `balanced_target_guard` | `51` | Larger mixed target set |

Current active targeted set:

```text
bottom24_edge_rescue + guard_high_score = 36 samples
```

Note:

- A 39-sample set was mentioned in discussion, but local CSV currently shows 36 for `bottom24 + guard` and 51 for the full balanced set.

Decision:

- Use 36-sample target set for quick tests.
- Expand to 51-sample target set before full199 if a variant looks promising.

## Experiment 10: Targeted No-Safe-Divisions Diagnostic

Notebook:

```text
Biohub_Targeted_Postprocess_Tuning.ipynb
```

Configuration:

```text
TARGET_SET_NAME = bottom24_plus_guard
SELECTED_VARIANT = no_safe_divisions_diagnostic
BIOHUB_OUTPUT_SAFE_DIVISIONS = 0
```

Purpose:

- Test whether the large number of predicted division-like branches was damaging the edge score.
- This was diagnostic, not expected to be final.

Output:

```text
Found 36 prediction graphs
Wrote submission.csv with 1,692,394 rows
Node rows: 865,208
Edge rows: 827,186
bad node coords before clip: 1603
bad node coords after clip: 0
```

Saved files:

```text
reports/deepcenter_target_bottom24_plus_guard_no_safe_divisions_diagnostic_local_validation_submission.csv
reports/deepcenter_target_bottom24_plus_guard_no_safe_divisions_diagnostic_local_validation_run_stats.csv
reports/deepcenter_target_bottom24_plus_guard_no_safe_divisions_diagnostic_local_validation_scores.csv
reports/deepcenter_target_bottom24_plus_guard_no_safe_divisions_diagnostic_local_validation_score_summary.csv
reports/deepcenter_target_bottom24_plus_guard_no_safe_divisions_diagnostic_local_validation_worst_samples.csv
```

Same 36-sample comparison:

| Metric | Baseline rebuild/full199 settings | No safe divisions |
|---|---:|---:|
| weighted edge | `0.889908` | `0.887888` |
| mean edge | `0.899633` | `0.897914` |
| median edge | `0.874521` | `0.870637` |
| p10 edge | `0.829953` | `0.824577` |
| min edge | `0.744966` | `0.744966` |
| mean node recall | `0.978926` | `0.978192` |
| edge TP | `16304` | `16267` |
| edge FP matched | `34` | `34` |
| edge FN | `1983` | `2020` |
| predicted direct divisions | `3064` | `0` |
| safe_divisions_added | `3066` | `0` |

Sample-level result:

```text
improved samples: 0
worse samples:    15
same samples:     21
```

Largest losses:

| sample_id | edge base | edge new | delta | TP delta | FN delta |
|---|---:|---:|---:|---:|---:|
| `44b6_e57ff5c6` | `0.83333` | `0.82258` | `-0.01075` | `-2` | `+2` |
| `44b6_71a4179f` | `0.84874` | `0.84034` | `-0.00840` | `-1` | `+1` |
| `6bba_1f58c2f6` | `0.87291` | `0.86622` | `-0.00669` | `-2` | `+2` |
| `6bba_23af9eeb` | `0.99599` | `0.98998` | `-0.00601` | `-3` | `+3` |

Conclusion:

- Disabling safe divisions is not good.
- Safe division creates many branch-like sources, but it also preserves some true edges.
- Future variants should make safe division stricter, not disable it.

## Current Best Known Strategy

Do not rerun full 199 blindly for every idea. Use checkpoint GEFFs and postprocess-only variants on targeted samples.

Recommended next ablation notebook:

```text
Biohub_Targeted_Postprocess_Ablation_51.ipynb
```

Status:

- Created locally.
- Uses saved checkpoint GEFF predictions from `reports/deepcenter_full199_prediction_geff_checkpoint`.
- Does not rerun the expensive model inference.
- Default target set is `all_bad_plus_guard`, which is currently 51 samples from `reports/targeted_validation_sets.csv`.
- The problem/bad subset has 39 samples: union of `bottom24_edge_rescue`, `low_recall_rescue`, `motion_gap_conservative`, and `branch_div_conservative`.
- The guard subset has 12 high-score samples from `guard_high_score`.
- There is no bad/guard overlap in the current CSV, so the default target is `39 bad + 12 guard = 51`.
- Writes one submission, run-stats, score table, and score summary per variant.
- Writes combined ablation summary:

```text
reports/deepcenter_ablation_all_bad_plus_guard_summary.csv
```

Important comparison rule:

- Do **not** rebuild a baseline variant inside this ablation loop.
- The comparison baseline is the saved full199 DeepCenter result from `reports/deepcenter_full199_local_validation_scores.csv`, i.e. the Kaggle-strong method that produced the `0.889` public score.
- Every variant reports `delta_*_vs_reference` against that saved full199 DeepCenter reference.

Recommended variants:

| Variant | Main idea | Expected risk |
|---|---|---|
| `safe_div_conservative_v2` | Keep safe divisions, reduce distance/caps | May reduce true recovered edges if too strict |
| `safe_div_conservative_v3` | Even stricter safe division | Higher FN risk |
| `motion_gap_conservative_v1` | Reduce relaxed motion and gap close | May reduce spurious long relinks; may also lose recovered FNs |
| `motion_gap_conservative_v2` | Stronger motion/gap restriction | Higher FN risk |
| `short_track_len5_v1` | Reduce min track length from 7 to 5 | May keep more true short GT tracks; may increase noise |
| `linefit_low_weight_v1` | Reduce smoothing/linefit impact | May improve centroid matching p95 |
| `edge_max_12_5_v1` | Reduce max output edge distance | May remove bad long edges; may lose true long movement |
| `combo_safe_motion_v1` | Combine best safe + motion settings | Candidate if individual variants help |
| `combo_safe_motion_short_v1` | Add short-track relaxation | Candidate if FN drops without FP spike |

Decision rule:

A variant is promising only if:

- weighted edge improves on the target set
- bottom24 improves
- guard_high_score does not drop materially
- TP increases or FN decreases
- matched FP does not spike
- node recall does not drop meaningfully
- predicted divisions are reduced but not collapsed to zero unless official score proves it helps

## Open Questions

- Does a stricter safe-division variant improve official Kaggle score even if local direct-division diagnostic is weak?
- Does linefit smoothing increase `match_distance_p95_um` on the worst samples?
- Is the 36-sample target set enough, or should all promising variants be checked on the 51-sample balanced target set before full199?
- Can we approximate official division metric better than direct out-degree diagnostics?
- Should we train or fine-tune a model later? Current priority is postprocess because it is cheaper and already near public `0.889`.

## Do Not Forget

- The public Kaggle rerun hidden test is approximately 199 samples, so runtime matters.
- Full inference can take many hours; checkpoint GEFF reuse is our friend.
- Do not delete:

```text
reports/deepcenter_full199_prediction_geff_checkpoint
```

- Before any full submission:
  - clip/check coordinates
  - verify every test dataset appears
  - verify edge endpoints exist
  - ensure notebook internet is disabled for Kaggle submission
  - keep output file named exactly `submission.csv`

## Fast 12-Sample Screening

Notebook: `Biohub_Targeted_Postprocess_Ablation_12.ipynb`

- Purpose: shorten the postprocess experiment loop before 51- and 199-sample validation.
- Bad set: the true lowest-scoring 8 samples from `deepcenter_full199_local_validation_scores.csv`.
- Guard set: the highest-scoring 2 `44b6` and 2 `6bba` samples among the preselected `guard_high_score` pool.
- Total: 12 samples, with an explicit no-overlap and exact-count check.
- Reference: saved full199 DeepCenter scores from the Kaggle-strong `0.889` method.
- Promotion rule: only variants that improve the bad set without materially reducing guard performance advance to the 51-sample check; only the winner advances to 199 samples.

### `safe_div_conservative_v2`

- Target: true worst 8 + embryo-balanced 4 guards.
- Reference weighted edge: `0.873180`.
- Variant weighted edge: `0.872006` (`-0.001174`).
- Worst-8 weighted edge: `0.827619 -> 0.826017` (`-0.001602`).
- Guard weighted edge: unchanged at `0.998241`.
- Edge changes: TP `-5`, matched FP `0`, FN `+5`.
- Per sample: 0 improved, 10 unchanged, 2 worsened (`44b6_e57ff5c6`, `6bba_32db13fc`).
- Direct predicted divisions: `864 -> 323`; direct sparse-GT division TP remained `0/2` for both reference and variant.
- Decision: reject as an edge winner, retain only as a division-conservative candidate because the official connected-component division metric is not reproduced locally.

### Fast-screen interim results: variants 2-4

| Variant | Weighted edge | Delta vs reference | TP delta | FP delta | FN delta | Decision |
|---|---:|---:|---:|---:|---:|---|
| `safe_div_conservative_v3` | 0.871771 | -0.001409 | -6 | 0 | +6 | Worse than v2; reject for edge |
| `motion_gap_conservative_v1` | 0.851374 | -0.021806 | -92 | +1 | +92 | Strong regression; reject |
| `motion_gap_conservative_v2` | 0.818844 | -0.054336 | -233 | -2 | +233 | Severe regression; reject |

Interpretation:

- The earlier association between poor samples and high motion/gap postprocess counts was correlational, not evidence that those operations caused the low scores.
- Tightening motion relinking and gap closing removed many true links, converting TP into FN almost one-for-one.
- The two conservative motion/gap variants must not be promoted or included in combination variants without a different, sample-aware gate.

### Fast 12-sample screen: final ranking

Reference weighted edge: `0.873180`.

| Variant | Weighted edge | Delta | TP delta | FP delta | FN delta | Decision |
|---|---:|---:|---:|---:|---:|---|
| `short_track_len5_v1` | 0.882104 | +0.008924 | +38 | 0 | -38 | Clear winner; promote after guard audit |
| `edge_max_12_5_v1` | 0.873180 | 0.000000 | 0 | 0 | 0 | No effect |
| `safe_div_conservative_v2` | 0.872006 | -0.001174 | -5 | 0 | +5 | Edge loss; division-only candidate |
| `safe_div_conservative_v3` | 0.871771 | -0.001409 | -6 | 0 | +6 | Reject |
| `combo_safe_motion_short_v1` | 0.868749 | -0.004431 | -18 | +1 | +18 | Reject |
| `linefit_low_weight_v1` | 0.867043 | -0.006137 | -27 | -1 | +27 | Reject; current linefit is useful |
| `motion_gap_conservative_v1` | 0.851374 | -0.021806 | -92 | +1 | +92 | Reject |
| `combo_safe_motion_v1` | 0.850200 | -0.022980 | -97 | +1 | +97 | Reject |
| `motion_gap_conservative_v2` | 0.818844 | -0.054336 | -233 | -2 | +233 | Reject |

`short_track_len5_v1` changed only minimum retained track length from 7 to 5. It reduced removed short-track nodes from about 21.9k to 11.7k on the 12-sample set, increased mean sparse node recall from `0.968813` to `0.979871`, recovered 38 true edges, and introduced no matched edge FP. Direct predicted divisions stayed unchanged at 864. This indicates the original length-7 filter was deleting useful short fragments.

Next gate: inspect per-sample guard deltas, then run only `short_track_len5_v1` on the 51-sample bad+guard set. Do not run all nine variants again.

## Public notebook update: `d3ac1a` (`0.900` public)

Compared files:

- old `biohub-cell-tracking-blend-preprocessings.ipynb` (`0.889` public)
- new `biohub-cell-tracking-blend-preprocessings-d3ac1a.ipynb` (`0.900` public)

The model weight is unchanged:

- artifact: `biohub-tracking-support-pack-400ep-snapshot-v1`
- weight SHA256: `12f6881ee3620a831697ca098ff8f48e687a24225f4e048b538deec3562fe771`

Therefore, the `+0.011` public gain comes from inference/postprocess changes rather than a new learned checkpoint.

Main changes:

1. Detection threshold: `0.99 -> 0.97`.
2. Detection TTA: old 4-view setup (identity + three flips) expanded to 8 spatial views by adding 90/270-degree rotations, transpose, and anti-transpose.
3. Base short-track minimum: `7 -> 6`.
4. Adaptive short-track rescue added. It activates when pruning removes at least 10% of nodes and selectively restores components of length 4-5 when mean edge probability is at least 0.82 and mean edge distance is at most 3.25 um, capped by 1.8% of nodes and 180 nodes per dataset.
5. Safe-division limits received a small conservative trim (`4.7/7.2/7.8 -> 4.66/7.05/7.65 um`, with slightly lower caps).
6. The old full-frame DeepCenter fusion path is removed. The new code contains optional DeepCenter repair veto logic, but the winning preset explicitly disables all DeepCenter vetoes.
7. `GAP_CLOSE_MAX_GAP=2` is set, but implementation still uses `min(max_gap, 1)`, so effective gap closing remains one frame. Gap2 recovery remains disabled.

Public 4-example diagnostics from the new notebook:

- prediction time: 9.73 minutes
- nodes: 128,715
- edges: 124,127
- safe divisions added: 392
- short-track nodes removed: 6,025
- adaptive rescue triggered on 1/4 datasets
- rescued components/nodes: 41 / 180

Interaction with our result:

- Our old-pipeline `min_track_len=5` winner and the new adaptive rescue both target excessive short-track pruning, so their gains likely overlap.
- Directly changing the new method from 6 to 5 may recover useful length-5 components but may also keep low-confidence noise that the adaptive gate intentionally rejects.
- The correct next experiment must run the new 0.900 inference once on the 12-sample set, cache those new prediction GEFFs, then compare exact 0.900 baseline vs global min-5 and adaptive-rescue variants from the same checkpoint.

### New-pipeline Drive-persistent validation notebook

Notebook: `Biohub_d3ac1a_Worst12_Drive_ShortTrack_Ablation.ipynb`

- Exact reference source: `biohub-cell-tracking-blend-preprocessings-d3ac1a.ipynb` (public `0.900`).
- Selection: old-pipeline true worst 8 plus embryo-balanced 4 guards.
- Data source: Drive `data/train`; no duplicated pseudo-test volume cache.
- Inference repo and generated d3ac1a prediction GEFFs are written directly to `reports/d3ac1a_worst12_drive_work` on Drive.
- Rerunning dependency setup preserves an existing valid Drive repo and prediction directory instead of deleting it.
- Inference preflight validates all required GEFF arrays and skips inference when all 12 Drive predictions are complete.
- Every completed postprocess variant immediately writes submission, raw backup, run stats, per-sample scores, summary, and progress CSV to Drive `reports/`.

Cross-pipeline audit outputs:

- `reports/d3ac1a_exact_vs_old0899_worst8_guard4_per_sample.csv`
- `reports/d3ac1a_exact_vs_old0899_worst8_guard4_summary.csv`

These explicitly answer whether the old pipeline's worst samples improved, stayed equal, or worsened under exact d3ac1a. They do not assume that the old worst ranking remains the new pipeline's worst ranking.

Short-track variants, all using the same new d3ac1a prediction checkpoint:

1. exact d3ac1a: min-6 + adaptive rescue
2. global min-5 + adaptive rescue
3. global min-5 with adaptive rescue disabled
4. min-6 + expanded adaptive rescue budget/trigger

Promotion compares variants against exact d3ac1a, while the separate cross-pipeline report compares exact d3ac1a against the old `0.889` pipeline.

### d3ac1a external artifact audit

Inspected downloads:

- `archive (3).zip`, 349,480,810 bytes
- `archive (4).zip`, 18,994 bytes

`archive (3).zip` is byte-for-byte identical to the already used `archive (1).zip`:

- whole-archive SHA256: `2EA8F16D8E2DF6781F3D48713004B18075AE3E462266773670DE05A56F908C8A`
- artifact: `biohub-tracking-support-pack-400ep-snapshot-v1`
- model weight SHA256: `12f6881ee3620a831697ca098ff8f48e687a24225f4e048b538deec3562fe771`
- prediction script SHA256: `c44e771ba5980b820f93091e03a303c25dfe8f3232e501f54dc9565731c234b9`

Therefore, `archive (3)` does not need to replace or be re-uploaded over the existing Drive support artifact.

`archive (4).zip` contains a separate local association ranker:

- artifact type: `biohub_local_association_ranker`
- checkpoint: `model/local_association_ranker.pt`
- checkpoint SHA256: `b49a9ab4228daba63d31056ae5beef9fd3e8bcd3ba26d9f57a45ef828d4fb4b8`
- 22 graph/motion/density features
- training data: 385,648 candidate rows, 126,705 groups, all 199 training datasets processed
- validation split is dataset-based; best epoch 7, validation top-1 0.9609, MRR 0.97774
- declared runtime intent: constrained local association tie-breaker, not a global edge veto

The d3ac1a notebook contains no association-ranker path, loader, feature builder, or inference call. Thus `archive (4)` is not used by the public `0.900` run even if attached as a Kaggle input. It should not be added to the current exact-reproduction notebook. It may be evaluated later as a separate, controlled relinking/tie-break experiment.

### Kaggle d3ac1a global min-5 submission candidate

Notebook: `biohub-cell-tracking-blend-preprocessings-d3ac1a-min5.ipynb`

- Source: exact public `0.900` `biohub-cell-tracking-blend-preprocessings-d3ac1a.ipynb`.
- Only functional source change: `BIOHUB_OUTPUT_MIN_TRACK_LEN = "6"` to `"5"`.
- Model weight, 8-view TTA, detection threshold 0.97, adaptive rescue, safe-division settings, ILP, gap handling, and all other inference/postprocess code remain unchanged.
- All stale notebook outputs/execution counters were cleared before upload.
- Static syntax check: 19 cells, no errors.
- Notebook SHA256: `d492f1aef3be529135ba18161a2916aa51eb3a43b43ad25c252d21639b96a254`.

This is a direct public-leaderboard probe. The old-pipeline targeted gain is not assumed to transfer because d3ac1a already uses min-6 plus adaptive length-4/5 rescue.

Public result: `0.899` versus the exact d3ac1a min-6 anchor at `0.900`.

Decision: reject global min-5. Restoring every length-5 component does not generalize on the public set; its recall gain is outweighed by additional false-positive/node-count cost. The earlier targeted local improvement (`+0.008924` weighted edge on worst8+guard4 under the old checkpoint family) was real for that diagnostic set but did not transfer to the exact D4 public pipeline. Future short-track work must be confidence-gated or sample-adaptive while retaining global min-6.

### Exact d3ac1a full199 diagnostic map

Detailed pipeline and cell-level explanation: `D3AC1A_PIPELINE_ANALYSIS.md`.

Notebook: `Biohub_d3ac1a_Full199_Drive_Batched_Diagnostics.ipynb`

Purpose: determine where the unchanged exact public-0.900 pipeline improves or regresses relative to the old 0.889 pipeline, and rebuild the real worst-sample ranking under d3ac1a. The Kaggle min-5 submission is a separate experiment and is not run here.

- Exact d3ac1a preset: threshold 0.97, 8-view TTA, min track length 6, adaptive short-track rescue enabled.
- All 199 paired train Zarr/GEFF samples are required and verified.
- Inference runs in resumable batches of 10.
- Postprocess and sparse-GT scoring run in resumable batches of 10 for exact d3ac1a min-6 only.
- All new outputs are isolated under Drive `reports/d3ac1a_0900_full199/`; old 0.889 reports remain untouched.
- Prediction GEFFs, manifests, batch submissions, run stats, score CSVs, and progress files are written directly under Drive `reports/`.
- Existing complete GEFFs and completed score batches are reused after runtime interruption.
- No single 7.9-million-row full199 submission CSV is required for this diagnostic; scoring is aggregated from batch outputs.

Primary outputs:

- `d3ac1a_full199_prediction_checkpoint_manifest.csv`
- `d3ac1a_full199_exact_local_validation_scores.csv`
- `d3ac1a_full199_exact_local_validation_run_stats.csv`
- `d3ac1a_full199_exact_local_validation_score_summary.csv`
- `d3ac1a_full199_exact_vs_old0899_per_sample.csv`
- `d3ac1a_full199_exact_vs_old0899_summary.csv`
- `d3ac1a_0900_full199_vs_old0899_per_sample.csv`
- `d3ac1a_0900_full199_vs_old0899_summary.csv`
- `d3ac1a_0900_full199_worst40.csv`
- `d3ac1a_0900_full199_analysis_table.csv`
- `d3ac1a_0900_full199_spearman_correlations.csv`

Interpretation warning: the model was learned from competition train data and GT is sparse; these full199 local scores are an error-analysis map, not an unbiased public/private leaderboard estimate. Official division scoring is still not reproduced exactly.

### d3ac1a Full199 first inference failure and recovery hardening

The first exact-d3ac1a Full199 inference attempt failed in batch 1 after roughly four minutes. No prediction GEFF passed the completeness check (`0/199`). The original cell used `subprocess.run(..., check=True)` without capturing the child process output, so the visible `CalledProcessError` did not preserve the actual root-cause log.

`Biohub_d3ac1a_Full199_Drive_Batched_Diagnostics.ipynb` was hardened as follows:

- combined child stdout/stderr is saved under `reports/d3ac1a_0900_full199/inference_logs/`
- the final log tail is printed in Colab on both success and failure
- CUDA allocation failures automatically retry model batch size `4 -> 2 -> 1`
- a failed ten-sample group is recursively bisected to isolate a sample-specific failure
- completed, structurally valid GEFF outputs remain resumable from the Drive checkpoint

No algorithm, threshold, TTA transform, or postprocess parameter was changed by this recovery patch.

The captured log identified the root cause as a Google Drive filesystem limitation, not a model or sample failure. Zarr v3 attempted an atomic metadata hard-link (`os.link`) while creating `nodes/zarr.json`; mounted Drive returned `PermissionError: Operation not permitted`.

The notebook now uses a two-tier checkpoint design:

- Zarr/GEFF creation occurs on Colab local storage under `/content/biohub_d3ac1a_0900_full199_runtime/`.
- After each successful inference group, complete GEFF directories are staged and copied to Drive under `reports/d3ac1a_0900_full199/prediction_geff_checkpoint/`.
- On a fresh runtime, complete Drive GEFFs are symlinked back into the local inference repo for resume and postprocess reads.
- Plain-text logs, manifests, score tables, and analysis outputs continue to write directly to Drive.

This storage fix changes no prediction or postprocess logic. It avoids unsupported Zarr writes on the Drive FUSE mount while preserving batch-level persistence.

### Leaderboard gap and model-development strategy

The 12 July 2026 leaderboard screenshot showed a tight `0.900-0.910` cluster and a `0.968` outlier. We cannot infer the outlier's method from its score, but the gap is too large to treat postprocess threshold tuning as the only development path. The agreed strategy is to finish the exact d3ac1a Full199 error map, classify failures by cause, and then test targeted detection, association-ranker, temporal-motion, and division-model changes under guarded validation.

Detailed strategy and promotion gates: `MODEL_DEVELOPMENT_ROADMAP.md`.

### Project understanding reference

The complete Turkish conceptual and technical explanation of the biological task, 3D+time data, GEFF graph, detection/association/ILP pipeline, postprocess stages, metric, completed experiments, and Full199 decision tree is stored in `PROJECT_EXPLAINER_TR.md`. This document is the shared reference to consult before interpreting Full199 results or designing the next model experiment.

### Public model technical assessment

Strengths, likely architectural limitations, and a staged three-month custom-model direction were added to `MODEL_DEVELOPMENT_ROADMAP.md`. The current working hypothesis is that d3ac1a has a strong volumetric detector and graph backbone, but learned temporal context and image-conditioned division reasoning are weaker than its heuristic postprocess layer. The exact Full199 failure map will choose whether temporal detection or a division head is the first custom training project.

### Archive (5) inspection

`C:/Users/barba/Downloads/archive (5).zip` contains only PNG figures. It is byte-for-byte identical to the previously inspected `archive (2).zip`:

```text
SHA256 FA0E27A8AA3CC157E5308FDDAE00672D762416B11D81F071ED81F8D829FF2224
```

The only Biohub-specific files are `biohub_cover.png` and `biohub_lineage.png`. They are explanatory artwork showing fluorescent cells, a division motif, and lineage trajectories; they contain no model weights, code, configuration, metrics, training outputs, or machine-readable annotations. The remaining figures concern unrelated competition/project presentations. No upload, extraction, or pipeline integration is needed.

### External `beicicc` source repository audit

The public `Beiciccc/biohub-cell-tracking-development` repository was audited at commit `3d7ec3c03794b6ecba7cc6eb75d19d01503e7ee2`. Its `kaggle/` tree contains 44 valid code entries: 34 notebooks and 10 Python scripts, with no missing metadata/code targets or malformed notebooks. The experiment log has 43 rows: 41 numeric public scores, 2 runtime failures, and no row for the extra `exp009_ftweights_prefix_gap` candidate. It reconstructs the scored path from a `0.750` classical baseline through rule-based `0.860`, learned graph `0.897`, and the final 400-epoch D4 family at `0.900`.

Source comparison confirms that our local `biohub-cell-tracking-blend-preprocessings-d3ac1a.ipynb` is algorithmically identical to repository `exp053_pilkwang_v21_rescue`; only two human-readable run-summary labels differ. The Full199 diagnostic therefore uses the exact public-`0.900` entry. Repository `exp056` lists an association-ranker dataset in Kaggle metadata but never references ranker code, so its tied `0.900` score is attributable only to the ILP division-prior `1.0 -> 0.9` change. The repository contains submission notebooks and metadata, not model-training code or the later leaderboard-leading `0.968` method.

Its strongest evidence supports recall-oriented D4 detection and a short-track count sweet spot; it argues against min8, higher detection threshold `0.9725`, broad gap recovery, and aggressive pruning. The cleanest unexplored low-cost experiment on the final D4 anchor is isolated one-frame gap-distance tightening (`6.0 -> 5.5 -> 5.25`). Full analysis: `EXTERNAL_REPO_EXPERIMENT_ANALYSIS.md`.

### CellTrack Studio official-metric integration

Repository `tom99763/celltrack-studio` was audited at commit `6daa1a50e1ae8addba5b6d35cb7d4fff323bcbc6`. It is a viewer/postprocess/evaluation workbench, not a new tracking model. Its vendored `metrics.py` and `division_metrics.py` are byte-for-byte identical to the current `royerlab/kaggle-cell-tracking-competition` upstream files.

`Biohub_CellTrack_Studio_Official_Metric_Colab.ipynb` was added to score the final exact-d3ac1a Full199 batch CSVs with the official edge-validity, node-count adjustment, and connected-component division metric. It checkpoints per sample to `reports/d3ac1a_0900_full199/celltrack_studio_official_metric/` and can be rerun while more postprocess batches become available. Raw inference GEFFs are deliberately not scored as the final method because they precede d3ac1a postprocessing. Detailed audit: `CELLTRACK_STUDIO_ANALYSIS.md`.

### d3ac1a Full199 postprocess path recovery

After all prediction checkpoints were generated, the first exact postprocess batch reported `Found 0 prediction graphs`. The predictions were not lost. The embedded Kaggle configuration preferred `/kaggle/working` whenever that directory existed, overwriting the Colab inference repo path and making postprocess inspect an empty `/kaggle/working/tracking_repo` tree.

`Biohub_d3ac1a_Full199_Drive_Batched_Diagnostics.ipynb` now restores `WORKING_DIR`, `REPO_DIR`, `SUBMISSION_PATH`, and `RUN_STATS_PATH` to the Zarr-safe local runtime immediately after every embedded config execution. It also reattaches the requested batch from the persistent Drive prediction checkpoint and asserts `visible == batch size` before building a submission. No inference, model, TTA, or postprocess behavior changed.
