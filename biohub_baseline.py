"""
Notebook-style baseline for the Biohub Cell Tracking During Development competition.

This file is safe to import before the dataset has finished downloading: all
parameters and functions are defined, and the full pipeline only runs when the
dataset is available and one of the explicit run flags is enabled.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

zarr = None
plt = None
gaussian_filter = None
linear_sum_assignment = None
cdist = None
peak_local_max = None
tqdm = None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

KAGGLE_BASE_DIR = Path("/kaggle/input/biohub-cell-tracking-during-development")
COLAB_BASE_DIR = Path("/content/biohub-cell-tracking-during-development")
DRIVE_PROJECT_DIR = Path("/content/drive/MyDrive/Biohub - Cell Tracking During Development")
DRIVE_PROJECT_DATA_DIR = DRIVE_PROJECT_DIR / "data"
DRIVE_DATA_DIR = Path("/content/drive/MyDrive/data")
DRIVE_BASE_DIR = DRIVE_PROJECT_DATA_DIR / "biohub-cell-tracking-during-development"

# Default for Colab with Google Drive mounted at /content/drive. This matches
# a Drive copy of this project folder with the dataset extracted under data/.
BASE_DIR = DRIVE_BASE_DIR

TRAIN_DIR = BASE_DIR / "train"
TEST_DIR = BASE_DIR / "test"
SAMPLE_SUBMISSION_PATH = BASE_DIR / "sample_submission.csv"

# Defaults are intentionally off so a missing or partial dataset cannot start
# a long run by accident.
DEBUG_MODE = False
RUN_TEST_SUBMISSION = False

DETECTION_PARAMS = {
    "percentile_low": 1,
    "percentile_high": 99.8,
    "gaussian_sigma": 1.0,
    "min_distance": 3,
    "threshold_abs": 0.2,
    "max_detections_per_frame": None,
}

LINKING_PARAMS = {
    "z_scale": 1.625,
    "y_scale": 0.40625,
    "x_scale": 0.40625,
    "max_distance_um": 7.0,
}


def dependency_error(name: str) -> ImportError:
    return ImportError(
        f"Missing dependency '{name}'. Install it first, e.g. in Colab: "
        f"!pip install {name}"
    )


def get_zarr():
    global zarr
    if zarr is None:
        try:
            import zarr as zarr_module
        except ImportError as exc:
            raise dependency_error("zarr") from exc
        zarr = zarr_module
    return zarr


def get_pyplot():
    global plt
    if plt is None:
        try:
            import matplotlib.pyplot as pyplot_module
        except ImportError as exc:
            raise dependency_error("matplotlib") from exc
        plt = pyplot_module
    return plt


def get_detection_dependencies():
    global gaussian_filter, peak_local_max
    if gaussian_filter is None:
        try:
            from scipy.ndimage import gaussian_filter as gaussian_filter_func
        except ImportError as exc:
            raise dependency_error("scipy") from exc
        gaussian_filter = gaussian_filter_func
    if peak_local_max is None:
        try:
            from skimage.feature import peak_local_max as peak_local_max_func
        except ImportError as exc:
            raise dependency_error("scikit-image") from exc
        peak_local_max = peak_local_max_func
    return gaussian_filter, peak_local_max


def get_linking_dependencies():
    global cdist, linear_sum_assignment
    if cdist is None:
        try:
            from scipy.spatial.distance import cdist as cdist_func
        except ImportError as exc:
            raise dependency_error("scipy") from exc
        cdist = cdist_func
    if linear_sum_assignment is None:
        try:
            from scipy.optimize import linear_sum_assignment as linear_sum_assignment_func
        except ImportError as exc:
            raise dependency_error("scipy") from exc
        linear_sum_assignment = linear_sum_assignment_func
    return cdist, linear_sum_assignment


def get_tqdm():
    global tqdm
    if tqdm is None:
        try:
            from tqdm.auto import tqdm as tqdm_func
        except ImportError:
            return None
        tqdm = tqdm_func
    return tqdm


def configure_base_dir(base_dir: str | Path) -> Path:
    """Update global dataset paths after choosing a dataset location."""
    global BASE_DIR, TRAIN_DIR, TEST_DIR, SAMPLE_SUBMISSION_PATH

    BASE_DIR = Path(base_dir)
    TRAIN_DIR = BASE_DIR / "train"
    TEST_DIR = BASE_DIR / "test"
    SAMPLE_SUBMISSION_PATH = BASE_DIR / "sample_submission.csv"
    return BASE_DIR


def find_dataset_base_dir(data_dir: str | Path = DRIVE_PROJECT_DATA_DIR) -> Path:
    """Find the dataset whether it was extracted into data/ or a subfolder."""
    data_dir = Path(data_dir)
    candidates = [
        data_dir / "biohub-cell-tracking-during-development",
        data_dir,
        DRIVE_PROJECT_DATA_DIR / "biohub-cell-tracking-during-development",
        DRIVE_PROJECT_DATA_DIR,
        DRIVE_DATA_DIR / "biohub-cell-tracking-during-development",
        DRIVE_DATA_DIR,
        KAGGLE_BASE_DIR,
        COLAB_BASE_DIR,
    ]

    seen = set()
    for candidate in candidates:
        candidate_key = str(candidate)
        if candidate_key in seen:
            continue
        seen.add(candidate_key)
        if (
            (candidate / "train").exists()
            and (candidate / "test").exists()
            and (candidate / "sample_submission.csv").exists()
        ):
            return configure_base_dir(candidate)

    return configure_base_dir(candidates[0])


def print_missing_dataset_message(base_dir: str | Path = BASE_DIR) -> None:
    print(
        "\nDataset directory is not available yet.\n"
        f"Expected BASE_DIR: {Path(base_dir)}\n"
        "Supported Drive layouts:\n"
        "  /content/drive/MyDrive/Biohub - Cell Tracking During Development/data/train\n"
        "  /content/drive/MyDrive/Biohub - Cell Tracking During Development/data/test\n"
        "  /content/drive/MyDrive/Biohub - Cell Tracking During Development/data/sample_submission.csv\n"
        "or:\n"
        "  /content/drive/MyDrive/Biohub - Cell Tracking During Development/data/biohub-cell-tracking-during-development/train\n"
        "  /content/drive/MyDrive/Biohub - Cell Tracking During Development/data/biohub-cell-tracking-during-development/test\n"
        "  /content/drive/MyDrive/Biohub - Cell Tracking During Development/data/biohub-cell-tracking-during-development/sample_submission.csv\n"
        "The dataset may still be downloading or extracting. Let that finish, "
        "then set BASE_DIR to the extracted competition folder and rerun the "
        "inspection or pipeline cells.\n"
        "All functions and parameter dictionaries are still defined."
    )


def dataset_available(base_dir: str | Path = BASE_DIR, verbose: bool = True) -> bool:
    """Return True only when the expected competition files are present."""
    base_dir = Path(base_dir)
    if not base_dir.exists():
        if verbose:
            print_missing_dataset_message(base_dir)
        return False

    required_paths = {
        "train directory": base_dir / "train",
        "test directory": base_dir / "test",
        "sample_submission.csv": base_dir / "sample_submission.csv",
    }
    missing = [label for label, path in required_paths.items() if not path.exists()]
    if missing:
        if verbose:
            print(f"BASE_DIR exists, but these required paths are missing: {missing}")
            print("The download/extraction may still be incomplete.")
        return False

    return True


# ---------------------------------------------------------------------------
# Optional Colab/Kaggle setup helpers
# ---------------------------------------------------------------------------

def print_colab_download_notes() -> None:
    print(
        "Colab setup notes:\n"
        "1. Mount Google Drive first: from google.colab import drive; drive.mount('/content/drive')\n"
        "2. Downloading plus extracting this dataset can exceed available disk.\n"
        "3. Put the extracted dataset under this project's data folder in Drive.\n"
        "4. After extraction, call find_dataset_base_dir() and "
        "inspect_dataset()."
    )


# ---------------------------------------------------------------------------
# Dataset inspection and loading
# ---------------------------------------------------------------------------

def inspect_dataset(base_dir: str | Path = BASE_DIR) -> Optional[Dict[str, object]]:
    if not dataset_available(base_dir):
        return None

    base_dir = Path(base_dir)
    train_dir = base_dir / "train"
    test_dir = base_dir / "test"

    train_zarr = sorted(train_dir.glob("*.zarr"))
    train_geff = sorted(train_dir.glob("*.geff"))
    test_zarr = sorted(test_dir.glob("*.zarr"))

    zarr_ids = {p.stem for p in train_zarr}
    geff_ids = {p.stem for p in train_geff}
    missing_geff = sorted(zarr_ids - geff_ids)
    missing_zarr = sorted(geff_ids - zarr_ids)

    summary = {
        "base_dir": base_dir,
        "train_zarr_count": len(train_zarr),
        "train_geff_count": len(train_geff),
        "test_zarr_count": len(test_zarr),
        "train_examples": [p.name for p in train_zarr[:5]],
        "test_examples": [p.name for p in test_zarr[:5]],
        "missing_geff_for_train_zarr": missing_geff[:20],
        "missing_zarr_for_train_geff": missing_zarr[:20],
    }

    print(pd.Series(summary))
    return summary


def open_zarr_array(array_path: Path):
    zarr_module = get_zarr()
    if not array_path.exists():
        raise FileNotFoundError(f"Missing Zarr array path: {array_path}")
    return zarr_module.open(str(array_path), mode="r")


def open_image_zarr(sample_path: str | Path, print_info: bool = True):
    """Open the image array at '<sample>.zarr/0' without loading it."""
    sample_path = Path(sample_path)
    img = open_zarr_array(sample_path / "0")

    if print_info:
        print(f"Opened image Zarr: {sample_path}")
        print(f"shape={img.shape}, dtype={img.dtype}, chunks={getattr(img, 'chunks', None)}")

    return img


def load_geff_annotations(geff_path: str | Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load sparse GEFF nodes and edges into DataFrames."""
    geff_path = Path(geff_path)
    if not geff_path.exists():
        raise FileNotFoundError(f"Missing GEFF path: {geff_path}")

    node_ids = np.asarray(open_zarr_array(geff_path / "nodes" / "ids")[:])
    t = np.asarray(open_zarr_array(geff_path / "nodes" / "props" / "t" / "values")[:])
    z = np.asarray(open_zarr_array(geff_path / "nodes" / "props" / "z" / "values")[:])
    y = np.asarray(open_zarr_array(geff_path / "nodes" / "props" / "y" / "values")[:])
    x = np.asarray(open_zarr_array(geff_path / "nodes" / "props" / "x" / "values")[:])

    nodes_df = pd.DataFrame({"node_id": node_ids, "t": t, "z": z, "y": y, "x": x})

    edges_array = np.asarray(open_zarr_array(geff_path / "edges" / "ids")[:])
    edges_df = pd.DataFrame(edges_array, columns=["source_id", "target_id"])

    print(f"GEFF nodes={len(nodes_df)}, edges={len(edges_df)}")
    if len(nodes_df):
        print(nodes_df[["t", "z", "y", "x"]].agg(["min", "max"]))
    return nodes_df, edges_df


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def visualize_slice(img, t: int, z: int) -> None:
    pyplot = get_pyplot()
    slice_yx = np.asarray(img[t, z])
    pyplot.figure(figsize=(6, 6))
    pyplot.imshow(slice_yx, cmap="gray")
    pyplot.title(f"t={t}, z={z}")
    pyplot.axis("off")
    pyplot.show()


def visualize_gt_overlay(img, nodes_df: pd.DataFrame, t: int, z: int, z_tolerance: int = 2) -> None:
    pyplot = get_pyplot()
    slice_yx = np.asarray(img[t, z])
    overlay = nodes_df[(nodes_df["t"] == t) & ((nodes_df["z"] - z).abs() <= z_tolerance)]

    pyplot.figure(figsize=(6, 6))
    pyplot.imshow(slice_yx, cmap="gray")
    pyplot.scatter(overlay["x"], overlay["y"], s=20, facecolors="none", edgecolors="red")
    pyplot.title(f"GT overlay: t={t}, z={z}, nodes={len(overlay)}")
    pyplot.axis("off")
    pyplot.show()


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def normalize_volume_percentile(volume_zyx: np.ndarray, params: Dict[str, object]) -> np.ndarray:
    volume = np.asarray(volume_zyx, dtype=np.float32)
    p_low = np.percentile(volume, params["percentile_low"])
    p_high = np.percentile(volume, params["percentile_high"])
    if p_high <= p_low:
        return np.zeros_like(volume, dtype=np.float32)
    volume = np.clip(volume, p_low, p_high)
    return (volume - p_low) / (p_high - p_low)


def detect_cells_in_timepoint(volume_zyx: np.ndarray, t: int, params: Dict[str, object]) -> pd.DataFrame:
    gaussian_filter_func, peak_local_max_func = get_detection_dependencies()

    volume_norm = normalize_volume_percentile(volume_zyx, params)
    sigma = params.get("gaussian_sigma")
    if sigma and sigma > 0:
        volume_norm = gaussian_filter_func(volume_norm, sigma=sigma)

    coords = peak_local_max_func(
        volume_norm,
        min_distance=int(params["min_distance"]),
        threshold_abs=float(params["threshold_abs"]),
        exclude_border=False,
    )

    if len(coords) == 0:
        return pd.DataFrame(columns=["t", "z", "y", "x", "score"])

    scores = volume_norm[coords[:, 0], coords[:, 1], coords[:, 2]]
    detections = pd.DataFrame(
        {
            "t": int(t),
            "z": coords[:, 0].astype(float),
            "y": coords[:, 1].astype(float),
            "x": coords[:, 2].astype(float),
            "score": scores.astype(float),
        }
    ).sort_values("score", ascending=False)

    max_detections = params.get("max_detections_per_frame")
    if max_detections is not None:
        detections = detections.head(int(max_detections))

    return detections.reset_index(drop=True)


def detect_cells_for_sample(
    img,
    sample_id: str,
    params: Dict[str, object],
    max_timepoints: Optional[int] = None,
) -> pd.DataFrame:
    n_timepoints = int(img.shape[0])
    if max_timepoints is not None:
        n_timepoints = min(n_timepoints, int(max_timepoints))

    iterator = range(n_timepoints)
    tqdm_func = get_tqdm()
    if tqdm_func is not None:
        iterator = tqdm_func(iterator, desc=f"Detecting {sample_id}")

    per_frame = []
    counts = []
    for t in iterator:
        volume_t = np.asarray(img[t])
        frame_df = detect_cells_in_timepoint(volume_t, t=t, params=params)
        counts.append(len(frame_df))
        per_frame.append(frame_df)

    if per_frame:
        detections = pd.concat(per_frame, ignore_index=True)
    else:
        detections = pd.DataFrame(columns=["t", "z", "y", "x", "score"])

    detections.insert(0, "sample_id", sample_id)
    detections.insert(1, "node_id", np.arange(1, len(detections) + 1, dtype=int))

    if counts:
        print(
            f"{sample_id}: detections total={len(detections)}, "
            f"per-frame min/median/max={np.min(counts)}/{np.median(counts):.1f}/{np.max(counts)}"
        )
    return detections


# ---------------------------------------------------------------------------
# Linking
# ---------------------------------------------------------------------------

def voxel_to_physical_um(coords_zyx: np.ndarray, params: Dict[str, object]) -> np.ndarray:
    scales = np.array([params["z_scale"], params["y_scale"], params["x_scale"]], dtype=float)
    return coords_zyx.astype(float) * scales


def link_detections(detections_df: pd.DataFrame, params: Dict[str, object]) -> pd.DataFrame:
    cdist_func, linear_sum_assignment_func = get_linking_dependencies()

    if detections_df.empty:
        return pd.DataFrame(columns=["sample_id", "source_id", "target_id", "distance_um"])

    sample_id = detections_df["sample_id"].iloc[0]
    edges = []
    unmatched_total = 0
    max_distance_um = float(params["max_distance_um"])

    for t in sorted(detections_df["t"].unique()):
        current_df = detections_df[detections_df["t"] == t].reset_index(drop=True)
        next_df = detections_df[detections_df["t"] == t + 1].reset_index(drop=True)
        if current_df.empty or next_df.empty:
            unmatched_total += len(current_df) + len(next_df)
            continue

        current_um = voxel_to_physical_um(current_df[["z", "y", "x"]].to_numpy(), params)
        next_um = voxel_to_physical_um(next_df[["z", "y", "x"]].to_numpy(), params)
        distances = cdist_func(current_um, next_um)
        row_ind, col_ind = linear_sum_assignment_func(distances)

        accepted = 0
        for row, col in zip(row_ind, col_ind):
            distance_um = float(distances[row, col])
            if distance_um <= max_distance_um:
                edges.append(
                    {
                        "sample_id": sample_id,
                        "source_id": current_df.loc[row, "node_id"],
                        "target_id": next_df.loc[col, "node_id"],
                        "distance_um": distance_um,
                    }
                )
                accepted += 1
        unmatched_total += (len(current_df) - accepted) + (len(next_df) - accepted)

    edges_df = pd.DataFrame(edges, columns=["sample_id", "source_id", "target_id", "distance_um"])
    if not edges_df.empty:
        print(
            f"{sample_id}: edges={len(edges_df)}, "
            f"distance min/median/max="
            f"{edges_df.distance_um.min():.2f}/{edges_df.distance_um.median():.2f}/"
            f"{edges_df.distance_um.max():.2f} um, unmatched approx={unmatched_total}"
        )
    else:
        print(f"{sample_id}: no edges accepted, unmatched approx={unmatched_total}")
    return edges_df


def infer_divisions_placeholder(*args, **kwargs) -> pd.DataFrame:
    """Future hook for one-to-two division links.

    The first baseline uses one-to-one temporal linking. True cell division may
    require one source node to link to two target nodes in the next frame.
    """
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------

def inspect_sample_submission(sample_submission_path: str | Path = SAMPLE_SUBMISSION_PATH) -> Optional[pd.DataFrame]:
    sample_submission_path = Path(sample_submission_path)
    if not sample_submission_path.exists():
        print(f"sample_submission.csv is not available yet: {sample_submission_path}")
        return None

    sample_submission_df = pd.read_csv(sample_submission_path)
    print(f"sample_submission shape={sample_submission_df.shape}")
    print(f"columns={list(sample_submission_df.columns)}")
    print(sample_submission_df.head())
    print(sample_submission_df.dtypes)
    return sample_submission_df


def build_submission(
    detections_all_df: pd.DataFrame,
    edges_all_df: pd.DataFrame,
    sample_submission_df: pd.DataFrame,
    expected_datasets: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Build the required mixed node/edge submission CSV.

    Required columns:
    id,dataset,row_type,node_id,t,z,y,x,source_id,target_id
    """
    required_columns = [
        "id",
        "dataset",
        "row_type",
        "node_id",
        "t",
        "z",
        "y",
        "x",
        "source_id",
        "target_id",
    ]
    sample_columns = list(sample_submission_df.columns)
    if sample_columns != required_columns:
        raise ValueError(
            "Unexpected sample_submission.csv columns. Expected "
            f"{required_columns}, got {sample_columns}"
        )

    rows = []

    if not detections_all_df.empty:
        node_df = detections_all_df.copy()
        for coord_col in ["t", "z", "y", "x"]:
            node_df[coord_col] = node_df[coord_col].round().astype(int)
        node_df["node_id"] = node_df["node_id"].astype(int)

        for row in node_df.itertuples(index=False):
            rows.append(
                {
                    "dataset": row.sample_id,
                    "row_type": "node",
                    "node_id": int(row.node_id),
                    "t": int(row.t),
                    "z": int(row.z),
                    "y": int(row.y),
                    "x": int(row.x),
                    "source_id": -1,
                    "target_id": -1,
                }
            )

    if not edges_all_df.empty:
        edge_df = edges_all_df.copy()
        edge_df["source_id"] = edge_df["source_id"].astype(int)
        edge_df["target_id"] = edge_df["target_id"].astype(int)

        for row in edge_df.itertuples(index=False):
            rows.append(
                {
                    "dataset": row.sample_id,
                    "row_type": "edge",
                    "node_id": -1,
                    "t": -1,
                    "z": -1,
                    "y": -1,
                    "x": -1,
                    "source_id": int(row.source_id),
                    "target_id": int(row.target_id),
                }
            )

    submission_df = pd.DataFrame(rows, columns=required_columns[1:])
    submission_df.insert(0, "id", np.arange(len(submission_df), dtype=int))

    if expected_datasets is not None:
        submitted_datasets = set(submission_df["dataset"].unique())
        missing_datasets = sorted(set(expected_datasets) - submitted_datasets)
        if missing_datasets:
            print(
                "Warning: these test datasets have no submission rows. "
                "Consider lowering threshold_abs or adding a fallback detector: "
                f"{missing_datasets}"
            )

    print(
        f"Submission rows={len(submission_df)}, "
        f"nodes={(submission_df.row_type == 'node').sum()}, "
        f"edges={(submission_df.row_type == 'edge').sum()}"
    )
    return submission_df[required_columns]


def save_submission(submission_df: pd.DataFrame, output_path: str | Path = "submission.csv") -> Path:
    output_path = Path(output_path)
    submission_df.to_csv(output_path, index=False)
    print(f"Saved submission: {output_path.resolve()}")
    return output_path


# ---------------------------------------------------------------------------
# Main execution modes
# ---------------------------------------------------------------------------

def run_debug_mode(base_dir: str | Path = BASE_DIR) -> None:
    if not dataset_available(base_dir):
        return

    base_dir = Path(base_dir)
    train_samples = sorted((base_dir / "train").glob("*.zarr"))
    if not train_samples:
        print("No train .zarr samples found.")
        return

    sample_path = train_samples[0]
    sample_id = sample_path.stem
    img = open_image_zarr(sample_path)

    geff_path = base_dir / "train" / f"{sample_id}.geff"
    if geff_path.exists():
        nodes_df, _ = load_geff_annotations(geff_path)
        z_mid = int(img.shape[1] // 2)
        visualize_gt_overlay(img, nodes_df, t=0, z=z_mid)
    else:
        print(f"No GEFF found for debug sample: {geff_path}")

    detections = detect_cells_for_sample(img, sample_id, DETECTION_PARAMS, max_timepoints=3)
    link_detections(detections, LINKING_PARAMS)


def run_test_submission_mode(base_dir: str | Path = BASE_DIR) -> None:
    if not dataset_available(base_dir):
        return

    base_dir = Path(base_dir)
    sample_submission_df = inspect_sample_submission(base_dir / "sample_submission.csv")
    if sample_submission_df is None:
        return

    all_detections = []
    all_edges = []
    test_sample_paths = sorted((base_dir / "test").glob("*.zarr"))
    test_sample_ids = [p.stem for p in test_sample_paths]
    for sample_path in test_sample_paths:
        sample_id = sample_path.stem
        img = open_image_zarr(sample_path)
        detections = detect_cells_for_sample(img, sample_id, DETECTION_PARAMS)
        edges = link_detections(detections, LINKING_PARAMS)
        all_detections.append(detections)
        all_edges.append(edges)

    detections_all_df = pd.concat(all_detections, ignore_index=True) if all_detections else pd.DataFrame()
    edges_all_df = pd.concat(all_edges, ignore_index=True) if all_edges else pd.DataFrame()
    submission_df = build_submission(
        detections_all_df,
        edges_all_df,
        sample_submission_df,
        expected_datasets=test_sample_ids,
    )
    save_submission(submission_df)


def main() -> None:
    if not dataset_available(BASE_DIR):
        return

    if DEBUG_MODE:
        run_debug_mode(BASE_DIR)

    if RUN_TEST_SUBMISSION:
        run_test_submission_mode(BASE_DIR)

    if not DEBUG_MODE and not RUN_TEST_SUBMISSION:
        print(
            "Dataset is available, but DEBUG_MODE and RUN_TEST_SUBMISSION are both False. "
            "Set one flag to True to run a pipeline mode."
        )


if __name__ == "__main__":
    main()
