# Biohub d3ac1a Pipeline Analysis

## Purpose

This document explains how the public Biohub pipeline reached `0.889`, what changed in the `d3ac1a` notebook that scored `0.900`, how the notebook cells connect, and why the changes can improve the competition metric.

The central finding is that the learned model checkpoint did not change. Both notebooks use the same primary UNet + node-transformer weight:

```text
12f6881ee3620a831697ca098ff8f48e687a24225f4e048b538deec3562fe771
```

The public gain came from inference and postprocess changes.

## End-to-End Pipeline

```text
3D+time Zarr image
    -> UNet cell-center heatmaps and detections
    -> node-transformer edge probabilities
    -> ILP candidate tracking graph
    -> motion, gap, division, and short-track postprocess
    -> submission.csv
```

The competition score is dominated by adjusted edge Jaccard, with an additional division term:

```text
score = adjusted_edge_jaccard + 0.1 * division_jaccard
```

Improvement therefore requires recovering true links and divisions without causing excessive node or edge false positives.

## How the 0.889 Pipeline Worked

The old experiment tag was:

```text
selected_30_deepcenter_500_last_sparse_gate_min7
```

### Cell Detection

The UNet predicted cell-center heatmaps at each timepoint.

- Detection threshold: `0.99`
- Detection TTA: four views
  - identity
  - X flip
  - Y flip
  - X+Y flip

Predictions from transformed images were mapped back to the original coordinate system and averaged. The high threshold produced conservative detections but could miss weak cells.

### Learned Association and ILP

The node transformer assigned learned probabilities to candidate links between adjacent frames. ILP then selected a graph while considering:

- edge probability
- appearance and disappearance costs
- parent and child constraints
- division cost

This produced the first tracking graph before notebook-level repair.

### DeepCenter Fusion

The old pipeline also loaded the epoch-500 full-frame DeepCenter checkpoint. It proposed additional center candidates intended to rescue cells missed by the primary graph model.

This could improve recall, but sparse GT made aggressive full-frame additions risky because some added nodes were not useful to the scored graph.

### Graph Postprocess

The old notebook then applied:

- next-frame edge enforcement
- single-parent repair
- motion relinking
- single-frame gap closing
- safe-division addition
- isolated-node pruning
- short-track filtering
- line-fit coordinate smoothing

The important short-track setting was:

```python
OUTPUT_MIN_TRACK_LEN = 7
```

Non-division components shorter than seven nodes were removed. This reduced noise but also deleted some real short trajectories. The combined pipeline scored `0.889` publicly.

## What Changed in the 0.900 d3ac1a Pipeline

The new experiment tag is:

```text
selected_44_400ep_adaptive_short_track_recovery
```

The primary learned weight is unchanged, so the `+0.011` public improvement is a pipeline gain.

### Detection Threshold: 0.99 to 0.97

The preset cell sets:

```python
os.environ["BIOHUB_DET_THRESHOLD"] = "0.97"
```

A lower threshold allows weaker center candidates to enter the graph pipeline.

Expected effects:

- higher node recall
- fewer missed true cells
- more candidate edges for the transformer and ILP
- possible extra false detections that downstream graph filtering must control

### Detection TTA: Four Views to Eight Views

Before running inference, the prediction cell patches `predict_unet_transformer.py`.

The old four views were identity plus three flips. The new spatial D4-style set adds:

- 90-degree rotation
- 270-degree rotation
- transpose
- anti-transpose

Each transformed image is passed through the same model. Heatmaps are transformed back and averaged over eight views.

Expected effects:

- less orientation sensitivity
- lower random heatmap noise
- more stable weak-cell peaks
- better detections in dense, tilted, or irregular structures

This change alters the raw prediction GEFF checkpoint. It is not merely a submission postprocess change.

### Base Minimum Track Length: 7 to 6

The preset cell sets:

```python
os.environ["BIOHUB_OUTPUT_MIN_TRACK_LEN"] = "6"
```

Length-six components are retained instead of removed. This relaxes the excessive pruning observed in the old pipeline.

### Adaptive Short-Track Recovery

The new pipeline adds conditional recovery after the normal short-track filter.

Recovery activates only when initial pruning removes at least 10% of the video's nodes. A removed component is eligible when:

- its length is 4 or 5
- mean learned edge probability is at least `0.82`
- mean edge distance is at most `3.25 um`

Recovery is limited by both:

- at most 1.8% of the video's nodes
- at most 180 nodes

The method does not globally keep every short component. It restores only high-confidence short components when pruning appears unusually severe.

In the public four-example diagnostic run, recovery triggered for one dataset and restored:

- 41 components
- 180 nodes

### Slightly More Conservative Safe Divisions

Safe-division geometry and caps were reduced slightly:

```text
parent distance:          4.70 -> 4.66 um
sister distance:          7.20 -> 7.05 um
existing-child distance:  7.80 -> 7.65 um
frame cap:                0.008 -> 0.0076
global cap:               0.004 -> 0.00375
```

Safe divisions remain enabled, but proposals must pass slightly stricter geometry and count limits.

### DeepCenter Disabled in the Winning Preset

The d3ac1a source contains optional DeepCenter repair-veto support, but the winning preset sets:

```python
BIOHUB_USE_DEEPCENTER_VETO = "0"
BIOHUB_DEEPCENTER_GAP_VETO = "0"
BIOHUB_DEEPCENTER_SAFE_DIV_VETO = "0"
```

The old full-frame center-fusion path is not the score-up axis in the `0.900` run. The method relies on the primary 400-epoch graph model, eight-view TTA, and conditional short-track recovery.

### Gap Configuration Detail

The preset sets `GAP_CLOSE_MAX_GAP=2`, but the implementation still uses:

```python
effective_gap_max = min(GAP_CLOSE_MAX_GAP, 1)
```

Therefore effective gap closing remains one frame. Gap2 recovery is disabled. This setting is not a meaningful source of the public improvement.

## How the Notebook Cells Connect

Cell indices below refer to `biohub-cell-tracking-blend-preprocessings-d3ac1a.ipynb`.

### Cell 4: Winning Preset

This cell writes environment overrides before configuration is parsed. It controls:

- detection threshold
- minimum track length
- adaptive short-track recovery
- safe-division limits
- DeepCenter switches

An environment override takes priority over the default later in the configuration cell.

### Cell 5: Configuration

This cell reads the environment values into Python variables and prints the active configuration.

For example:

```python
OUTPUT_MIN_TRACK_LEN = int(os.environ.get("BIOHUB_OUTPUT_MIN_TRACK_LEN", "6"))
```

If Cell 4 set the environment variable, that value is used regardless of the fallback string in Cell 5.

### Cell 9: Artifact and Dependency Setup

This cell:

- locates the support artifact
- verifies the manifest and model weight
- installs offline dependencies
- materializes inference source and weights

The support artifact is `biohub-tracking-support-pack-400ep-snapshot-v1`, even though its Kaggle input slug may still contain `50ep-v1`.

### Cell 13: Predict Candidate Graphs

This cell:

- patches the inference script from four-view to eight-view TTA
- discovers test Zarr datasets
- creates the inference split
- runs UNet + node-transformer + ILP inference
- writes raw prediction GEFF graphs

Changes here affect detections and raw graph candidates. Postprocess cannot reproduce these effects from an older checkpoint.

### Cell 15: Build submission.csv

This cell reads prediction GEFF graphs and applies:

- edge validation
- parent/child constraints
- motion relinking
- gap closing
- safe divisions
- isolated-node pruning
- short-track filtering and adaptive recovery
- line-fit smoothing
- coordinate and submission formatting

The base min-track and adaptive-recovery changes act here.

### Cells 17-18: Diagnostics and Audit

These cells report:

- nodes and edges per dataset
- dropped and recovered structures
- safe divisions
- short-track removals and rescues
- output schema and integrity
- configuration and submission hash

They are necessary for attribution but do not alter the submission graph.

## Why the Public Score Likely Improved

The intended mechanism is:

```text
threshold 0.97 + eight-view TTA
    -> higher and more stable node recall
    -> better edge candidates for transformer and ILP
    -> min-6 removes fewer real tracks
    -> adaptive rescue restores only strong short components
    -> conservative safe-division trim controls extra false positives
    -> more edge TP and fewer FN without uncontrolled node/edge FP
```

The notebook describes its own score-up axis as:

```text
400ep graph with spatial TTA and conditional short-track recall recovery
```

The exact contribution of each change cannot be inferred from one public score. Controlled local ablations and the full199 exact-pipeline diagnostic are required.

## Relationship to Our Global Min-5 Experiment

On the old pipeline's selected worst8 plus guard4 set, changing minimum track length from 7 to 5 produced:

- weighted edge delta: `+0.008924`
- TP delta: `+38`
- FN delta: `-38`
- matched FP delta: `0`

This proved that old min-7 pruning deleted useful short fragments.

However, d3ac1a already uses min-6 plus conditional length-4/5 rescue. Therefore the old gain is not assumed to transfer additively. The Kaggle min-5 submission is a separate public probe.

## Full199 Diagnostic Plan

`Biohub_d3ac1a_Full199_Drive_Batched_Diagnostics.ipynb` runs the unchanged exact `0.900` pipeline on all 199 paired training samples.

It persists directly to:

```text
reports/d3ac1a_0900_full199/
```

The resulting reports will answer:

- which old 0.889 worst samples improved under d3ac1a
- which samples stayed difficult or regressed
- whether the gain came from node recall, edge TP, or FN reduction
- the new exact d3ac1a worst40
- how motion, gap, short-track, safe-division, density, and distance diagnostics correlate with score

Because the model was learned from competition training data and GT is sparse, these are diagnostic comparisons rather than unbiased leaderboard estimates. The official connected-component division metric is also not reproduced exactly.
