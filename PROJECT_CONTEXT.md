# Project Context

This project is for the Kaggle competition "Biohub Cell Tracking During Development".

## Working Setup

The project is developed locally in:

```text
Biohub - Cell Tracking During Development/
```

The same project folder will also be uploaded to Google Drive for Colab use:

```text
/content/drive/MyDrive/Biohub - Cell Tracking During Development/
```

## Expected Drive Structure

The project files and dataset should live together like this:

```text
Biohub - Cell Tracking During Development/
  Biohub_Cell_Tracking_Baseline_Colab.ipynb
  biohub_baseline.py
  data/
```

The dataset may be extracted either directly under `data/`:

```text
data/
  train/
  test/
  sample_submission.csv
```

or inside the competition folder under `data/`:

```text
data/
  biohub-cell-tracking-during-development/
    train/
    test/
    sample_submission.csv
```

Both layouts are supported by `find_dataset_base_dir()`.

## Execution Defaults

- Colab is the primary runtime.
- Google Drive is mounted at `/content/drive`.
- `DEBUG_MODE` defaults to `False`.
- `RUN_TEST_SUBMISSION` defaults to `False`.
- If the dataset is missing or still downloading, the code should print a clear message and avoid running the full pipeline.

## Competition Format And Metric Notes

- Image arrays are Zarr v3 at `<sample>.zarr/0` with shape `(T, Z, Y, X)`.
- Voxel scale is `z=1.625`, `y=0.40625`, `x=0.40625` micrometers per voxel.
- Edge matching uses optimal assignment on scaled centroid distance with max distance `7.0 um`.
- Ground-truth GEFF annotations are sparse; unlabeled regions must not be treated as background.
- Submission CSV columns are exactly:

```text
id,dataset,row_type,node_id,t,z,y,x,source_id,target_id
```

- Node rows use `row_type=node`, integer `node_id,t,z,y,x`, and `source_id=target_id=-1`.
- Edge rows use `row_type=edge`, integer `source_id,target_id`, and `node_id=t=z=y=x=-1`.
- `dataset` must match the test folder/sample name without `.zarr`.
- Every test dataset should appear in the submission.

## Dataset Description

Each sample is a short 3D+time fluorescence microscopy video of labeled zebrafish embryo cells. The task is to detect cell centroids at each timepoint and link them through time to produce a tracking graph.

### Image Zarr Format

- Image volumes are `.zarr` directories.
- Each image sample contains a single array at path `0/`.
- Array shape is `(T, Z, Y, X)`.
- Typical shape is `(100, 64, 256, 256)`.
- Dtype is `uint16`.
- Chunks are one timepoint each: `(1, 64, 256, 256)`.
- Chunk for timepoint `t` is located at `0/c/{t}/0/0/0`.
- Array metadata is stored in `0/zarr.json`.
- Compression is blosc/zstd.
- Physical scale is `z=1.625`, `y=0.40625`, `x=0.40625` micrometers per voxel.
- Linking and matching distances should be computed in physical units, not raw voxel units.

### Training GEFF Ground Truth

Training samples have paired `.geff` directories. GEFF is also built on Zarr v3 and stores a sparse tracking graph:

```text
nodes/ids
nodes/props/t/values
nodes/props/z/values
nodes/props/y/values
nodes/props/x/values
edges/ids
```

`edges/ids` has shape `(N, 2)` with columns:

```text
source_id,target_id
```

Coordinates are integer centroid coordinates in voxels.

Important: annotations are sparse. Not every real cell is labeled in every frame, and unlabeled regions must not be treated as background. The `estimated_number_of_nodes` field in GEFF `zarr.json` estimates the true total cell count per sample.

### Embryo Identity

Folder names follow:

```text
{embryo_id}_{field_of_view}
```

Example:

```text
44b6_0049_0438_1330_1273
```

The first segment is the embryo identity. Multiple samples can share an embryo. Train and test are embryo-disjoint.

### Files

```text
train/                 paired .zarr image volumes and .geff ground-truth graphs
test/                  .zarr image volumes only
sample_submission.csv  valid submission example and required CSV schema
```

The public test samples are examples/copies from train. In Kaggle rerun, a hidden test set is swapped in and is approximately training-set sized.

## Main Files

- `biohub_baseline.py`: modular baseline code for data inspection, Zarr/GEFF loading, visualization, detection, linking, and submission generation.
- `Biohub_Cell_Tracking_Baseline_Colab.ipynb`: Colab notebook that imports `biohub_baseline.py`, mounts Drive, finds the dataset under the project `data/` folder, and exposes safe debug/submission cells.
- `Biohub_EDA_and_Local_Validation.ipynb`: deeper analysis notebook for dataset integrity checks, Zarr/GEFF metadata summaries, GT density, edge-distance and division analysis, intensity sampling, visual sanity checks, and baseline-vs-GT local validation.
- `Biohub_Strategy_EDA_and_Validation.ipynb`: strategy notebook for the cleaned 199-pair dataset; builds GEFF summary cache, division/density lists, stratified validation samples, representative intensity summaries, selected boundary checks, and runtime profiling hooks. It writes generated tables under `reports/`.
- `Biohub_Local_Scorer_and_Sweep.ipynb`: local scoring and parameter sweep notebook. It runs baseline detection/linking on selected validation samples, matches predictions to sparse GT in physical units, reports sparse node recall and edge Jaccard-like metrics, and writes sweep tables under `reports/`.
- `Biohub_First_Submission.ipynb`: clean first-submission notebook. It uses the selected classical config from local validation, runs the test `.zarr` samples only, writes `submission.csv`, and performs basic format checks.
- `Biohub_Drive_Unzip_and_Verify.ipynb`: utility notebook for clean Drive unzip and dataset verification.
- `EDA_FINDINGS.md`: running notes from actual Colab outputs, including count discrepancies, orphan GEFF checks, Zarr/GEFF summaries, intensity findings, and baseline validation observations.
