# Biohub Model Development Roadmap

## Leaderboard Signal

The 12 July 2026 screenshot shows a tight public cluster from roughly `0.900` to `0.910`, plus a major `0.968` outlier. A score alone does not reveal that entry's method, but the size of the gap strongly suggests that incremental threshold tuning is not the entire answer. We need to identify whether our remaining loss is dominated by detection, association, node-count adjustment, or divisions.

Current public anchors:

- simple handcrafted baseline: `0.631`
- old learned DeepCenter-style pipeline: `0.889`
- d3ac1a 400-epoch + 8-view TTA + adaptive short-track rescue: `0.900`
- d3ac1a with global min-track length 5: public result pending

## What Full199 Must Answer

The exact unchanged d3ac1a `0.900` Full199 diagnostic is the new reference. For every sample it must measure:

- sparse-GT node recall and centroid matching distance
- edge TP, matched FP, and FN
- old `0.889` to new `0.900` deltas
- density, intensity, motion, gap, and short-track statistics
- predicted and GT direct division counts as a diagnostic
- performance by embryo and by failure phenotype

The resulting worst samples must be grouped by failure cause, not merely sorted by score.

## Development Axes

### 1. Exact metric reproduction

Before small gains are trusted, reproduce the official node over-prediction adjustment and connected-component division scoring as closely as the released metric permits. Our sparse local edge score is useful for ranking changes but can be overly optimistic and does not reproduce the official division term.

### 2. Detection calibration

Use TTA disagreement and center heatmap confidence to identify uncertain detections. Test sample-adaptive thresholds based on intensity, density, and estimated foreground occupancy instead of one global `0.97` threshold. Preserve a node-count calibration guard because over-detection is explicitly penalized.

### 3. Confidence-gated association ranker

Integrate the separate 22-feature association ranker only for ambiguous links. Do not globally replace high-confidence edges. Candidate rewiring should require:

- at least two plausible targets
- low confidence or small margin in the current linker
- a sufficiently large ranker top-1 versus top-2 margin
- valid next-frame timing and physical-distance constraints
- no damage to protected high-confidence division structures

Evaluate it first on the new d3ac1a worst set plus balanced high-score guards.

### 4. Temporal motion model

Current motion relinking is mostly geometric. For samples whose errors are dominated by edge FN despite high node recall, test learned velocity/acceleration residual scoring over 3-5 frames. This should be a local candidate-edge feature, not unrestricted graph rewriting.

### 5. Division-specific model

The competition awards a separate `0.1 * division_jaccard` term. Train or calibrate a parent/daughter event scorer using temporal image crops, parent-to-child geometry, sister separation, intensity change, and association confidence. Evaluate with embryo-disjoint folds and the connected-component interpretation of the official metric.

### 6. Model diversity and ensembling

If detection remains the bottleneck, train embryo-disjoint 3D center models with different preprocessing or receptive fields. Fuse detections by calibrated consensus and uncertainty rather than blindly unioning nodes. If association remains the bottleneck, ensemble edge logits or rankers while keeping one constrained graph optimizer.

## Experiment Protocol

Every promoted change must pass three stages:

1. Fast targeted set: the worst failure group plus balanced guards from both embryos.
2. Broad validation set: all new d3ac1a bad samples plus density/division/motion guards.
3. Full199 diagnostic: only after a clear targeted gain with no guard collapse.

Promotion conditions:

- weighted matched edge Jaccard improves
- TP rises or FN falls in the intended failure group
- matched FP does not spike
- node over-prediction risk does not worsen materially
- guard samples remain stable
- division diagnostics do not regress unless the edge gain clearly compensates

## Immediate Next Steps

1. Finish exact d3ac1a `0.900` Full199 inference and reports.
2. Compare its worst40 and per-sample deltas against the old `0.889` pipeline.
3. Determine the dominant failure category and build a targeted validation set from the new reference.
4. Run the first confidence-gated association-ranker ablation if association ambiguity is supported by the reports.
5. Build a closer local implementation of the official division and node-adjustment metric.
6. Global min-5 scored `0.899` against the min-6 anchor's `0.900`; reject it as a global policy. Use this as evidence that any short-track recall recovery must be confidence-gated or sample-adaptive.

The goal is not to imitate the `0.968` entry without knowing its method. The goal is to use reproducible error evidence to discover which capability our `0.900` pipeline is missing.

## Technical Assessment of the Public d3ac1a Model

### Strong design choices

- It decomposes the task into detection, learned association, constrained graph selection, and postprocess. This is easier to debug than a monolithic end-to-end tracker.
- The 3D UNet respects volumetric image structure instead of reducing the data to a single 2D projection.
- The node-transformer learns edge evidence rather than relying only on nearest-neighbour distance.
- ILP imposes useful global graph consistency and gives an explicit place for appearance, disappearance, and division costs.
- Spatial TTA materially improves robustness without changing the trained checkpoint.
- The output pipeline handles practical failure modes such as gaps, short fragments, motion relinking, and divisions.
- The inference implementation is compact enough to remain plausible under the 12-hour hidden-test constraint.

### Likely limitations

- Detection is primarily per-frame. Spatial TTA improves orientation robustness but does not provide learned temporal evidence for weak or overlapping cells.
- The association window is short and much of the longer-term motion reasoning is delegated to hand-designed postprocess rules.
- Motion relinking can replace many learned edges, so the final graph may depend more on geometric heuristics than on calibrated learned association probabilities.
- Division recovery is largely geometry- and cap-based rather than a dedicated image-conditioned mitosis model.
- One global detection threshold cannot be optimal across the very large intensity and density variation observed in the dataset.
- The pipeline does not explicitly expose calibrated uncertainty or TTA disagreement for deciding which nodes and edges are trustworthy.
- Short-track filtering, gap repair, line fitting, and safe-division insertion interact. Independent threshold changes can improve one phenotype while damaging another.
- Sparse annotation makes ordinary supervised losses and local validation optimistic unless unlabelled cells are masked rather than treated as negatives.
- If checkpoint selection or validation was not embryo-disjoint, the apparent local quality may overstate generalization to hidden embryos.
- Eight-view TTA is computationally expensive and leaves little 12-hour budget for richer temporal models or ensembles.

## Candidate Three-Month Model Direction

Do not discard the public model immediately. Use it as a teacher and baseline, then replace the weakest learned components in stages.

### Phase A: reliable validation and reproduction

- reproduce training and inference from the support artifact
- implement embryo-disjoint folds
- approximate the official node adjustment and connected-component division metric more closely
- establish runtime per video and memory budgets

### Phase B: temporal detection

Train an anisotropic 3D center model that receives a short temporal context such as `t-1, t, t+1`. Predict center heatmap, local offset, and uncertainty. Temporal evidence should recover dim cells while suppressing isolated noise better than lowering one global threshold.

### Phase C: multi-frame graph association

Use persistent image embeddings plus position, velocity, acceleration, density, and TTA uncertainty in a graph transformer over roughly 3-5 frames. Include explicit candidate heads for continuation, disappearance, gap recovery, and division.

### Phase D: division event model

Train a dedicated parent/daughter scorer on temporal 3D crops. Inputs should include pre-split and post-split appearance, parent-child displacement, sister geometry, intensity change, and association confidence. Feed its calibrated probability into the graph optimizer.

### Phase E: metric-aware constrained ensemble

Combine diverse detection or edge models only where they disagree. Calibrate node-count risk and division confidence, then use min-cost flow or ILP to create one legal graph. Keep inference below the hidden-test runtime budget.

The first custom model should therefore not be a complete rewrite. The highest-value initial experiment is either temporal detection or a dedicated division head, selected from the exact d3ac1a Full199 failure map.
