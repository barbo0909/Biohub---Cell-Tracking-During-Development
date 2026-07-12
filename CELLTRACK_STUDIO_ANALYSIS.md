# CellTrack Studio Analysis

## Repository

- Source: `https://github.com/tom99763/celltrack-studio`
- Audited commit: `6daa1a50e1ae8addba5b6d35cb7d4fff323bcbc6`
- License: MIT (the vendored competition metric retains its upstream license).

CellTrack Studio is not a detector or tracker model. It is a 3D+time napari viewer, hot-reloadable graph post-processing workbench, and local evaluator for Biohub prediction/GT GEFF graphs.

## Critical Verification

The repository vendors metric code from `royerlab/kaggle-cell-tracking-competition`. The following files were compared against the current upstream repository and are byte-for-byte identical:

- `celltrack_studio/_vendor/tracking_cellmot/metrics.py`
- `celltrack_studio/_vendor/tracking_cellmot/division_metrics.py`

Pinned SHA256 values:

- `metrics.py`: `F7305D3D0A571479741DA1FB38A85A3CB357B07D5B46B8E06FF6F6B37AC784F7`
- `division_metrics.py`: `60FAA6BF682AF282C546E0AA203847EB7E0843297ED112FFDE04B1AAE7C3C71F`

This resolves a major weakness in our earlier local scorer: CellTrack Studio applies the official sparse-GT edge-validity rules, sample-size-weighted node-count adjustment, and connected-component division matching rather than our direct-division approximation.

## Integration With Exact d3ac1a 0.900

Notebook: `Biohub_CellTrack_Studio_Official_Metric_Colab.ipynb`

The notebook:

1. pins CellTrack Studio to the audited commit and verifies metric source hashes;
2. discovers final exact-d3ac1a postprocess batch CSVs under `reports/d3ac1a_0900_full199/`;
3. rebuilds each final graph in memory using the competition repository's CSV-to-graph remapping logic;
4. reads GT GEFF, physical scale, and `estimated_number_of_nodes`;
5. computes exact per-sample edge/division counts and final metric components;
6. checkpoints after every sample and resumes completed work;
7. writes summaries, embryo breakdowns, errors, and the worst 40 samples to Drive.

It intentionally scores final postprocessed batch CSVs. Raw inference GEFF checkpoints do not represent the full public-0.900 pipeline because motion relinking, gap insertion, safe divisions, short-track filtering/rescue, line fitting, and coordinate clipping happen later.

## Output Directory

`reports/d3ac1a_0900_full199/celltrack_studio_official_metric/`

Primary files:

- `d3ac1a_official_metric_per_sample.csv`
- `d3ac1a_official_metric_summary.csv`
- `d3ac1a_official_metric_by_embryo.csv`
- `d3ac1a_official_metric_worst40.csv`
- `d3ac1a_official_metric_errors.csv` (only when errors occur)

## Interpretation

This gives the exact metric mechanics on sparse training GT, but it remains an in-sample diagnostic because the learned artifact was trained using competition training data. It is suitable for controlled A/B comparisons on identical sample sets and for selecting failure cases. It is not an unbiased estimate of Kaggle public/private score.

The napari desktop GUI requires a Qt display and is not launched in Colab. The headless official metric is the useful Colab component; desktop/WSLg can later be used for interactive 3D inspection of selected worst samples.
