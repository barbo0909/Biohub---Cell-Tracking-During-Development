# Biohub EDA Findings

Date: 2026-07-09

This file records the current, cleaned project understanding after resolving the Drive extraction issues. Earlier `181/182/183` counts came from an incomplete Drive copy and should not be used as final dataset facts.

## Project Goal

The competition asks us to reconstruct cell tracking graphs from 3D+time microscopy volumes.

Submission rows:

- `node`: detected cell centroid with integer voxel coordinates `t,z,y,x`
- `edge`: temporal link from `source_id` to `target_id`

Metric-relevant scale:

- `z = 1.625 um/voxel`
- `y = 0.40625 um/voxel`
- `x = 0.40625 um/voxel`
- centroid matching cap: `7.0 um`

Ground truth is sparse. Unlabeled cells are not background, so sparse-GT node precision is not a reliable standalone quality signal.

## Current Data Source

Primary development path in Colab/Drive:

```text
/content/drive/MyDrive/Biohub - Cell Tracking During Development/data
```

Kaggle source of truth also checked clean:

```text
/kaggle/input/competitions/biohub-cell-tracking-during-development
```

Expected layout:

```text
data/
  train/
    <sample>.zarr
    <sample>.geff
  test/
    <sample>.zarr
  sample_submission.csv
```

## Final Dataset Status

After a clean Drive re-extract and verification:

- train `.zarr`: `199`
- train `.geff`: `199`
- paired train samples: `199`
- test `.zarr`: `4`
- GEFF without Zarr: `[]`
- Zarr without GEFF: `[]`

Embryo split:

| split | embryo_id | count |
|---|---|---:|
| train | `44b6` | 71 |
| train | `6bba` | 128 |
| test public | `44b6` | 2 |
| test public | `6bba` | 2 |

Kaggle input check also confirmed:

- train `.zarr`: `199`
- train `.geff`: `199`
- paired train samples: `199`
- test `.zarr`: `4`
- `sample_submission.csv`: present, shape `(20, 10)`
- bad Zarr structure count: `0`

Conclusion: the real full train set has `199` image+GEFF pairs. Previous `181/182/183` results were caused by an incomplete Drive extraction/upload state.

Quick integrity check after clean re-extract:

- checked train Zarr samples: `5/5`, all OK
- checked test Zarr samples: `4/4`, all OK
- checked train GEFF samples: `5/5`, all OK
- quick integrity result: passed

## Zarr Metadata

Final Zarr metadata scan:

- train scanned: `199/199`
- test scanned: `4/4`
- metadata/read errors: `0`
- valid train Zarrs: `199`
- invalid train Zarr IDs: `[]`
- valid image+GEFF pairs: `199`

Uniform image metadata:

- shape: `(100, 64, 256, 256)`
- dtype: `uint16`
- chunks: `(1, 64, 256, 256)`
- raw uint16 size per sample: `0.78125 GiB`

Conclusion: images are structurally consistent. Processing should stay chunk/timepoint based; do not load full samples into RAM.

## GEFF / GT Notes

Quick first-sample checks confirmed GEFF reading and coordinate alignment:

- `44b6_0113de3b`: `52` GT nodes, `50` GT edges
- first quick overlay selected a GT-containing view and the point landed on a plausible bright cell
- GEFF coordinates are interpreted correctly as voxel `t,z,y,x`

Sparse GT remains an important modeling fact:

- GT labels only a subset of real cells.
- `estimated_number_of_nodes` can be far larger than labeled node count.
- Local validation should emphasize sparse-GT recall and edge correctness, not raw precision against sparse labels.

Full GEFF summary on the final `199` paired samples:

- runtime in Colab/Drive: about `22m26s`
- samples summarized: `199`
- mean GT nodes per sample: `669.94`
- median GT nodes per sample: `659`
- min/max GT nodes per sample: `50 / 1950`
- mean GT edges per sample: `647.65`
- median GT edges per sample: `639`
- min/max GT edges per sample: `49 / 1879`
- mean `gt_nodes_per_t_median`: `6.87`
- median `gt_nodes_per_t_median`: `7.0`
- max `gt_nodes_per_t_max`: `33`
- total division nodes: `151`
- median division nodes per sample: `0`
- 75th percentile division nodes per sample: `1`
- max division nodes per sample: `5`
- `max_out_degree`: at most `2`
- median `estimated_number_of_nodes`: `17909`
- min/max `estimated_number_of_nodes`: `3783 / 78644`

Embryo-level full GEFF totals:

| embryo_id | n_gt_nodes | n_gt_edges | division_nodes |
|---|---:|---:|---:|
| `44b6` | 20197 | 19826 | 26 |
| `6bba` | 113121 | 109057 | 125 |

Interpretation:

- `6bba` dominates the labeled training signal and division signal.
- Most samples still have no labeled divisions, but `151` total division nodes are enough to justify explicit division handling.
- Since `max_out_degree <= 2`, division logic can focus on binary splits.
- Validation must be stratified; early sorted `44b6` examples are not representative of the full training set.

Division-focused summary from the strategy notebook:

- samples with at least one labeled division: `87`
- total labeled division nodes: `151`
- strongest division sample: `6bba_48816121` with `5` division nodes
- all high-division examples still have `max_out_degree = 2`, confirming binary split handling is enough

Top division-heavy samples:

| sample_id | embryo_id | n_gt_nodes | n_gt_edges | division_nodes | gt_nodes_per_t_median | gt_nodes_per_t_max | estimated_number_of_nodes |
|---|---|---:|---:|---:|---:|---:|---:|
| `6bba_48816121` | `6bba` | 935 | 918 | 5 | 10.0 | 13 | 23965 |
| `6bba_09961292` | `6bba` | 1950 | 1871 | 4 | 18.0 | 33 | 31117 |
| `6bba_cdcfe533` | `6bba` | 1419 | 1348 | 4 | 18.5 | 28 | 29785 |
| `6bba_debd7bfa` | `6bba` | 766 | 729 | 4 | 7.5 | 15 | 11807 |
| `6bba_df673a83` | `6bba` | 668 | 654 | 4 | 7.0 | 10 | 19239 |
| `6bba_afb141ff` | `6bba` | 654 | 626 | 4 | 6.0 | 12 | 6054 |

Density extremes:

- lowest labeled-density examples are mostly `44b6` with about `50-90` GT nodes and `1` median GT node per labeled timepoint
- highest labeled-density examples are `6bba`, up to `1950` GT nodes and `33` max GT nodes per timepoint
- `estimated_number_of_nodes` can be high even when sparse labeled node count is low, so validation should use both sparse GT density and estimated total count

## Edge Distance Notes

Full GT edge-distance analysis on the final `199` paired samples:

- total GT edges measured: `128883`
- `dt`: always `1`
- mean distance: `2.130 um`
- median distance: `1.817 um`
- 90th percentile: `4.143 um`
- 95th percentile: `5.343 um`
- 99th percentile: `8.385 um`
- max observed: `60.758 um`

Interpretation:

- Most true links are short, but the distribution has a long tail.
- The metric's `7.0 um` centroid matching cap should not be treated as the maximum plausible temporal movement.
- Candidate linking radius should be swept and validated because larger gates can recover tail motion but may add false edges in dense regions.

Planned linking sweep:

```text
max_distance_um = 5, 6, 7, 8, 9, 10
```

Important nuance: the competition's `7.0 um` is the centroid matching cap, not a guarantee that all true temporal links move less than `7.0 um`.

## Intensity Notes

Quick intensity sampling showed strong sample/time variation. A raw global threshold is likely fragile.

Current quick intensity scan used the first 5 sorted train samples, all `44b6`.

Median per-sample intensity summary from that quick scan:

| sample_id | p1 | p50 | p99 | p99_8 | max | mean |
|---|---:|---:|---:|---:|---:|---:|
| `44b6_0113de3b` | 35 | 189 | 1369 | 1774 | 2950 | 257 |
| `44b6_0b24845f` | 86 | 1504 | 2670 | 2888 | 3356 | 1285 |
| `44b6_0c582fdc` | 88 | 475 | 1848 | 2125 | 3244 | 547 |
| `44b6_0db75fae` | 0 | 113 | 1619 | 1885 | 2635 | 313 |
| `44b6_12dfb391` | 101 | 592 | 1956 | 2304 | 4021 | 645 |

Detection strategy should keep:

- per-timepoint percentile normalization
- parameter sweeps for `percentile_high`, `threshold_abs`, `gaussian_sigma`, and `min_distance`

The intensity scan should be improved to use representative samples from both embryos instead of only the first few sorted `44b6` examples.

Representative intensity on the 24 selected validation samples was saved to:

```text
reports/representative_intensity.csv
```

Key median intensity examples:

| embryo_id | sample_id | p1 | p50 | p99 | p99_8 | max | mean |
|---|---|---:|---:|---:|---:|---:|---:|
| `44b6` | `44b6_d754aa59` | 20 | 52 | 429 | 665 | 1297 | 75.7 |
| `44b6` | `44b6_aaf8b0ea` | 47 | 237 | 1470 | 1798 | 2990 | 409.0 |
| `44b6` | `44b6_0c582fdc` | 88 | 475 | 1848 | 2125 | 3244 | 546.6 |
| `44b6` | `44b6_18ced818` | 92 | 1121 | 2291 | 2609 | 3740 | 1096.4 |
| `6bba` | `6bba_afb141ff` | 10 | 30 | 419 | 694 | 1397 | 48.7 |
| `6bba` | `6bba_6321a359` | 29 | 55 | 388 | 554 | 1003 | 72.6 |
| `6bba` | `6bba_48816121` | 37 | 204 | 932 | 1155 | 1900 | 255.9 |
| `6bba` | `6bba_57b7cc1e` | 611 | 1040 | 1499 | 1658 | 2227 | 1041.4 |

Interpretation:

- Brightness varies strongly both within and across embryos.
- Some dense/division `6bba` samples are very dim (`p50` around `30-70`), while others are bright (`p50` around `1040`).
- `44b6` also ranges widely (`p50` around `52-1121` in the validation set).
- Detection must use per-timepoint or per-sample normalization. A raw fixed intensity threshold will fail.
- Parameter sweeps should compare normalized thresholds rather than raw thresholds.

## Validation Set

The strategy notebook selected `24` validation samples and saved them to:

```text
reports/validation_samples.csv
```

Validation embryo split:

| embryo_id | count |
|---|---:|
| `44b6` | 10 |
| `6bba` | 14 |

Selection reasons:

- embryo-specific low/medium/high density quantiles
- high `estimated_number_of_nodes`
- top division samples

Selected validation samples:

| sample_id | embryo_id | n_gt_nodes | n_gt_edges | division_nodes | estimated_number_of_nodes | selection_reason |
|---|---|---:|---:|---:|---:|---|
| `44b6_0c582fdc` | `44b6` | 71 | 70 | 0 | 27958 | `44b6_density_quantile` |
| `44b6_d754aa59` | `44b6` | 72 | 70 | 1 | 5171 | `44b6_density_quantile` |
| `44b6_aaf8b0ea` | `44b6` | 209 | 206 | 1 | 22099 | `44b6_density_quantile` |
| `44b6_2a2eff9f` | `44b6` | 214 | 210 | 1 | 56367 | `44b6_density_quantile` |
| `44b6_7e557709` | `44b6` | 570 | 560 | 0 | 56060 | `44b6_density_quantile` |
| `44b6_8f5ab931` | `44b6` | 616 | 604 | 0 | 27571 | `44b6_density_quantile` |
| `44b6_18ced818` | `44b6` | 100 | 99 | 0 | 78644 | `high_estimated_count` |
| `44b6_e31261b4` | `44b6` | 116 | 113 | 0 | 72856 | `high_estimated_count` |
| `44b6_e28840c6` | `44b6` | 311 | 309 | 2 | 74686 | `high_estimated_count` |
| `44b6_8f9ecab4` | `44b6` | 374 | 370 | 0 | 74833 | `high_estimated_count` |
| `6bba_3db54e20` | `6bba` | 502 | 474 | 1 | 23236 | `6bba_density_quantile` |
| `6bba_c328f2fd` | `6bba` | 511 | 500 | 2 | 31228 | `6bba_density_quantile` |
| `6bba_b204cac7` | `6bba` | 826 | 811 | 2 | 5092 | `6bba_density_quantile` |
| `6bba_6321a359` | `6bba` | 827 | 798 | 1 | 4821 | `6bba_density_quantile` |
| `6bba_283bf9f1` | `6bba` | 1342 | 1288 | 0 | 20861 | `6bba_density_quantile` |
| `6bba_af149c94` | `6bba` | 1350 | 1317 | 0 | 8933 | `6bba_density_quantile` |
| `6bba_afb141ff` | `6bba` | 654 | 626 | 4 | 6054 | `top_division` |
| `6bba_df673a83` | `6bba` | 668 | 654 | 4 | 19239 | `top_division` |
| `6bba_debd7bfa` | `6bba` | 766 | 729 | 4 | 11807 | `top_division` |
| `6bba_48816121` | `6bba` | 935 | 918 | 5 | 23965 | `top_division` |
| `6bba_cdcfe533` | `6bba` | 1419 | 1348 | 4 | 29785 | `top_division` |
| `6bba_57b7cc1e` | `6bba` | 1659 | 1592 | 3 | 65511 | `top_division` |
| `6bba_bb9f20c3` | `6bba` | 1925 | 1879 | 3 | 23071 | `top_division` |
| `6bba_09961292` | `6bba` | 1950 | 1871 | 4 | 31117 | `top_division` |

Interpretation: this is a good first validation set because it covers both embryos, sparse and dense labels, high estimated counts, and division-heavy cases. It is intentionally harder than random sampling.

## Baseline Snapshot

Quick local validation on `44b6_0113de3b`, first 5 timepoints:

- predicted nodes: `1165`
- sparse GT nodes in those frames: `3`
- matched sparse GT nodes: `3`
- sparse-GT node recall: `1.0`
- predicted edges: `757`
- sparse GT edges: `2`
- edge TP/FP/FN: `2/0/0`

This was only a tiny sanity check. It shows the baseline is not random, but it is not enough for parameter selection.

## Visual Spot Checks

Manual visual spot checks were run on selected validation samples including sparse, dense, and division-heavy cases:

```text
44b6_0c582fdc
6bba_afb141ff
6bba_09961292
6bba_48816121
6bba_df673a83
6bba_cdcfe533
44b6_d754aa59
6bba_3db54e20
6bba_c328f2fd
```

Observations:

- GT overlays generally land on plausible bright cell-like structures, so coordinate interpretation remains correct.
- Dense `6bba` samples can be crowded and anisotropic; single z-slice views often show only a few labeled nodes even when the sample has many GT nodes.
- Some selected views had `overlay_nodes=0`; this is a visualization-selection issue, not necessarily a data issue. Choosing median z for a GT-rich timepoint can miss labels when GT nodes are spread across z.
- Better visualization should choose the densest `(t,z)` neighborhood rather than median `z` at the densest `t`.
- Several samples show strong FOV/boundary effects and partial cell fields, so edge/boundary cases should be part of validation.

Action: use an improved visual spot-check helper that selects the densest `t,z` slab within a configurable z tolerance.

Follow-up visual spot check with the improved densest-slab helper:

- reviewed samples included `6bba_afb141ff`, `6bba_09961292`, `6bba_48816121`, `6bba_df673a83`, `6bba_cdcfe533`, `44b6_d754aa59`, `6bba_3db54e20`, `6bba_c328f2fd`, and `6bba_debd7bfa`
- `slab_nodes=0` no longer appeared in the reviewed outputs
- selected GT points again landed on plausible bright cell-like structures
- dense `6bba` samples remain crowded and boundary-heavy, making them useful stress cases
- dim samples such as `6bba_afb141ff` and `44b6_d754aa59` remain important threshold stress cases

Conclusion: data/coordinate sanity checks are complete enough to move from EDA to local scoring and parameter sweeps.

## Runtime Notes

Baseline detection runtime on three validation samples, first `5` timepoints:

| sample_id | detections | seconds_per_timepoint | estimated_seconds_100t |
|---|---:|---:|---:|
| `44b6_0c582fdc` | 1879 | 1.30 | 130.1 |
| `6bba_afb141ff` | 510 | 1.30 | 130.1 |
| `6bba_09961292` | 1783 | 1.35 | 135.4 |

Interpretation:

- Current detection baseline is about `1.3-1.35 s/timepoint`.
- A full 100-timepoint sample is about `2.2 minutes` for detection.
- If hidden test size is close to train size, detection-only runtime is roughly `7-8 hours`, leaving some but not unlimited room under Kaggle's `12h` notebook limit.
- Final submission notebook should avoid EDA work and only run the selected pipeline.

## Local Sweep 1

First GT-aligned local sweep:

- samples: first `6` validation samples
- window: `20` timepoints per sample, aligned to each sample's first GT timepoint
- runs: `150`
- runtime in Colab/Drive: about `26m`
- metric used for ranking: `edge_jaccard_matched`

Top matched-edge result:

| det_config_id | percentile_high | threshold_abs | gaussian_sigma | min_distance | linking_radius_um | edge_jaccard_matched | node_recall_sparse_gt | pred_nodes | pred_edges |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 99.7 | 0.18 | 1.0 | 3 | 8.0 | 0.816 | 0.958 | 7577 | 6076 |
| 0 | 99.7 | 0.18 | 1.0 | 3 | 9.0 | 0.816 | 0.958 | 7577 | 6205 |
| 4 | 99.8 | 0.20 | 1.2 | 4 | 9.0 | 0.810 | 0.937 | 5712 | 4654 |
| 4 | 99.8 | 0.20 | 1.2 | 4 | 8.0 | 0.807 | 0.937 | 5712 | 4558 |
| 0 | 99.7 | 0.18 | 1.0 | 3 | 7.0 | 0.806 | 0.958 | 7577 | 5949 |

Interpretation:

- Lower threshold config `0` gives the best matched-edge score and very high sparse-GT node recall.
- Config `4` is slightly lower on matched-edge score but produces substantially fewer nodes and edges, which may matter once the official node overprediction adjustment is approximated.
- Linking radius improves from `5` to `8`, then mostly plateaus at `8-9`; next validation should focus on `8.0` and maybe `9.0`.
- Naive edge Jaccard remains very low because sparse GT labels do not cover all real cells; it should not be used as the primary selection metric.

Next sweep:

- run top configs `0` and `4` over all `24` validation samples
- compare radius `8.0` and `9.0`
- add an approximate node-count adjustment using `estimated_number_of_nodes`

## Selected Config Validation 1

Selected config validation:

- samples: all `24` validation samples
- window: `20` GT-aligned timepoints per sample
- runs: `96`
- runtime in Colab/Drive: about `30m`

Summary:

| selected_config_name | percentile_high | threshold_abs | gaussian_sigma | min_distance | linking_radius_um | edge_jaccard_matched | edge_jaccard_naive | node_recall_sparse_gt | pred_nodes | pred_edges |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `det4_radius9_balanced` | 99.8 | 0.20 | 1.2 | 4 | 9.0 | 0.704 | 0.0396 | 0.876 | 5900 | 4770 |
| `det4_radius8_balanced` | 99.8 | 0.20 | 1.2 | 4 | 8.0 | 0.702 | 0.0400 | 0.876 | 5900 | 4649 |
| `det0_radius9_high_recall` | 99.7 | 0.18 | 1.0 | 3 | 9.0 | 0.698 | 0.0308 | 0.925 | 7471 | 6034 |
| `det0_radius8_high_recall` | 99.7 | 0.18 | 1.0 | 3 | 8.0 | 0.694 | 0.0312 | 0.925 | 7471 | 5879 |

Interpretation:

- On the full validation set, the balanced config `det4` beats high-recall config `det0` on matched edge score.
- `det4` also produces about `21%` fewer nodes and edges than `det0`, which should be safer under the official overprediction penalty.
- Radius `9.0` slightly improves matched-edge score over `8.0`, but also adds edges; the gap is small.
- Current best candidate before node-adjustment approximation: `det4_radius9_balanced`.
- Conservative candidate if edge count penalty looks costly: `det4_radius8_balanced`.

Next action: add an approximate node overprediction adjustment and rerank these configs before deciding the first submission config.

Approximate adjusted summary after applying the estimated-node overprediction factor:

| selected_config_name | edge_jaccard_adjusted_approx | edge_jaccard_matched | node_overprediction_factor | node_recall_sparse_gt | pred_nodes | expected_nodes_window | pred_edges |
|---|---:|---:|---:|---:|---:|---:|---:|
| `det4_radius9_balanced` | 0.676 | 0.704 | 0.958 | 0.876 | 5900 | 6675 | 4770 |
| `det4_radius8_balanced` | 0.674 | 0.702 | 0.958 | 0.876 | 5900 | 6675 | 4649 |
| `det0_radius9_high_recall` | 0.576 | 0.698 | 0.832 | 0.925 | 7471 | 6675 | 6034 |
| `det0_radius8_high_recall` | 0.572 | 0.694 | 0.832 | 0.925 | 7471 | 6675 | 5879 |

Interpretation:

- Approximate adjustment makes the balanced config decisively better than the high-recall config.
- `det4_radius9_balanced` remains the best local candidate.
- `det4_radius8_balanced` is very close and slightly more conservative on edge count.

Current best classical baseline config:

```python
DETECTION_PARAMS = {
    "percentile_low": 1,
    "percentile_high": 99.8,
    "gaussian_sigma": 1.2,
    "min_distance": 4,
    "threshold_abs": 0.20,
    "max_detections_per_frame": None,
}

LINKING_PARAMS = {
    "z_scale": 1.625,
    "y_scale": 0.40625,
    "x_scale": 0.40625,
    "max_distance_um": 9.0,
}
```

## Full Sequence Mini Validation

Full `100T` mini validation with current best config `det4_radius9_balanced`:

- samples: `6`
- runtime: about `14m51s`
- mean detection time per sample: `147.5s`
- mean link time per sample: `0.70s`

Per-sample results:

| sample_id | edge_jaccard_adjusted_approx | edge_jaccard_matched | node_recall_sparse_gt | pred_nodes | estimated_number_of_nodes | pred_edges |
|---|---:|---:|---:|---:|---:|---:|
| `44b6_0c582fdc` | 0.429 | 0.429 | 0.676 | 24716 | 27958 | 20834 |
| `44b6_d754aa59` | 0.754 | 0.829 | 1.000 | 5684 | 5171 | 4621 |
| `6bba_afb141ff` | 0.787 | 0.787 | 0.933 | 5550 | 6054 | 4651 |
| `6bba_09961292` | 0.733 | 0.733 | 0.906 | 27898 | 31117 | 24382 |
| `6bba_48816121` | 0.697 | 0.697 | 0.916 | 22451 | 23965 | 18595 |
| `6bba_cdcfe533` | 0.655 | 0.728 | 0.938 | 33070 | 29785 | 27022 |

Mean full-sequence mini metrics:

- `edge_jaccard_adjusted_approx`: `0.676`
- `edge_jaccard_matched`: `0.700`
- `node_overprediction_factor`: `0.968`
- `node_recall_sparse_gt`: `0.895`
- mean predicted nodes: `19895`
- mean estimated nodes: `20675`
- mean predicted edges: `16684`

Interpretation:

- The config remains strong on full sequences.
- `44b6_0c582fdc` is the main weak case; full-sequence recall drops to `0.676`, while GT-aligned 20T looked much stronger. This sample needs error analysis by timepoint.
- For the other five samples, full-sequence matched edge score is roughly `0.70-0.83`, which is a credible first-submission classical baseline.
- Runtime is compatible with Kaggle's `12h` limit if the final notebook stays lean.

Next actions:

- inspect `44b6_0c582fdc` over time to understand late/early failure
- create a clean submission notebook using the current best config
- submit a first classical baseline before adding division logic
- then add division candidates and test whether the `0.1 * division_jaccard` term improves public LB

## Current Strategy

1. Use the cleaned `199`-pair dataset as the only final reference.
2. Use the selected `24`-sample validation set for baseline scoring and sweeps.
3. Improve representative visual/intensity checks on these validation samples.
4. Sweep detection and linking parameters before changing the algorithm deeply.
5. Add explicit binary division candidate logic.
6. Keep final Kaggle submission notebook independent of Drive/Colab state.

## Next Actions

- Review representative intensity and boundary outputs from the strategy notebook.
- Run visual spot checks on the selected validation samples.
- Add edge outlier and division visual analysis notebook.
- Add a parameter sweep table for detection and linking.
- Add division-focused validation examples.
- Keep `DEBUG_MODE=False` and `RUN_TEST_SUBMISSION=False` by default in reusable notebooks/scripts.
- Use `Biohub_Local_Scorer_and_Sweep.ipynb` as the next notebook for local scoring and parameter selection.
