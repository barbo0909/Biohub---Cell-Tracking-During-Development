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

## Main Files

- `biohub_baseline.py`: modular baseline code for data inspection, Zarr/GEFF loading, visualization, detection, linking, and submission generation.
- `Biohub_Cell_Tracking_Baseline_Colab.ipynb`: Colab notebook that imports `biohub_baseline.py`, mounts Drive, finds the dataset under the project `data/` folder, and exposes safe debug/submission cells.
