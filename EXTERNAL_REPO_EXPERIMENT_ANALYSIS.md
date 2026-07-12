# External Biohub Experiment Log Analysis

## Source Scope

The public source repository is `Beiciccc/biohub-cell-tracking-development`, audited locally at commit `3d7ec3c03794b6ecba7cc6eb75d19d01503e7ee2` (2026-07-11). Its `kaggle/` tree contains 44 experiment directories: 34 notebook entries and 10 Python-script entries. Every directory has valid `kernel-metadata.json`, every referenced code file exists, and every notebook parses successfully.

The repository intentionally excludes model artifacts, competition data, generated submissions, and downloaded reference notebooks. It is therefore a complete record of the submitted entry code and metadata, but not a self-contained training repository.

The experiment log contains 43 rows (41 numeric public scores and 2 runtime failures), while `kaggle/` contains 44 entries. The extra entry is `exp009_ftweights_prefix_gap`: its code and metadata exist, but it has no status or score in the experiment log. Treat it as an unverified/unsubmitted candidate, not leaderboard evidence.

## Source Verification

- Our local `biohub-cell-tracking-blend-preprocessings-d3ac1a.ipynb` is code-equivalent to repository experiment `exp053_pilkwang_v21_rescue`. The only differences are two run-summary label strings changed from `RUN SUMMARY` to `COPY THIS TO GPT`.
- Therefore the running Full199 d3ac1a diagnostic uses the correct public-`0.900` pipeline, not an approximation reconstructed from the experiment log.
- `exp052` is the first public-`0.900` D4 anchor. `exp053` adds conditional short-track rescue and also scores `0.900`; its log says rescue fired on one public sample and restored 41 components / 180 nodes.
- `exp054` changes only the detection threshold to `0.9725` and falls to `0.899`.
- `exp056` changes the ILP division prior to `0.9` and ties `0.900`. Its Kaggle metadata lists an association-ranker dataset, but the notebook source contains no ranker/association use. That input is unused and the score cannot be attributed to the ranker.
- The latest repository commit only records results through `exp056`; it does not contain the later leaderboard-leading `0.968` solution.

## Experiment Lineage

### Classical and early learned anchors

- Classical local maxima + Hungarian: `0.750`.
- Initial public UNet + transformer + ILP at threshold `0.99`: `0.810`.
- Edge/division-weight and geometry pruning variations: approximately `0.812-0.818`.
- Conservative rule-based division recovery: `0.839`.

This confirms that detection/linking structure matters much more than small early ILP-weight tuning.

### Strong rule-based phase

- Two-pass velocity linking, gap closing, and short-track filtering: `0.842`.
- Tightening one-frame gap distance from `6.0` to `5.5`, then `5.25`: `0.843`, then `0.844`.
- Multi-scale DoG, line smoothing, two-frame recovery, and divisions: `0.858`.
- Detection threshold and gap tuning reached `0.860`.

The useful transferable signal is that conservative one-frame gap geometry can produce repeatable micro-gains. Broader/slower gap recovery timed out or did not improve the learned branches.

### Learned graph phase

- Learned-edge tracker + conservative pruning: `0.884-0.885`.
- Lower threshold/recall-clean branch: `0.888`.
- Gap and tightened division branch: `0.893`.
- Motion relink and division-seed variants remained `0.893`.
- Increasing minimum track length to 7 reached `0.897`.
- Increasing it further to 8 reduced score to `0.896`.
- DeepCenter full-frame prior with min6 tied `0.897`.

The public evidence points to a node-count/short-fragment sweet spot. Removing some short components was highly beneficial, but stronger pruning crossed the optimum. DeepCenter additions were too sparse to beat the best short-track setting.

### 400-epoch D4 phase

- 400-epoch graph model + full D4 spatial detection TTA + threshold `0.97` + min6: `0.900`.
- Conditional high-confidence short-track rescue: `0.900` at public three-decimal resolution.
- Raising threshold to `0.9725`: `0.899`.
- Lowering ILP division prior from `1.0` to `0.9`: `0.900`.

This is the exact family currently being diagnosed in our Full199 run. D4 TTA and recall-oriented detection were the clear late-stage improvement. Adaptive rescue and division-prior `0.9` were unresolved ties, while slightly increasing the threshold was harmful.

## Strong Conclusions

1. Recall mattered: `0.985/0.99`-style learned branches generally beat stricter `0.992-0.995` precision branches, and the best anchor used `0.97` with D4 TTA.
2. Node pruning mattered: min7 gave a meaningful gain under the older anchor, while min8 over-pruned.
3. More gap recovery was not automatically better. Conservative one-frame geometry helped rule systems, while broader learned-branch gap additions often regressed.
4. DeepCenter fusion was not the winning axis in the final family.
5. Small division-geometry or ILP-prior changes were mostly public ties; three-decimal public scores are too coarse to declare them equivalent.
6. The visible public-test node count near the best learned submissions was roughly 126k-129k. This is not a hidden-test target, but it supports the existence of a precision/recall count sweet spot.
7. Full D4 TTA increased visible inference from roughly 6-7 minutes to about 10.5 minutes, so future additions must respect the hidden 12-hour limit.

## What the Log Did Not Test Well

- calibrated use of TTA disagreement
- confidence-gated use of the separate 22-feature association ranker
- dedicated temporal 3D detection
- image-conditioned division classification
- longer learned association context over 3-5 frames
- embryo-disjoint model training and checkpoint selection
- close reproduction of the official connected-component division metric
- sample-adaptive detection thresholds based on intensity/density
- distillation of 8-view TTA into a faster student

These are more promising than repeating already-negative global gap, min8, or aggressive precision-pruning variants.

## Recommended Experiments for Our Pipeline

### Low-cost micro-gain queue

1. Global d3ac1a min5 scored `0.899` versus min6 at `0.900`; keep min6 as the global policy and investigate only confidence-gated short-track rescue.
2. On exact d3ac1a, test only `GAP_CLOSE_UM: 6.0 -> 5.5 -> 5.25` with every other setting fixed. The external log found this useful in rule branches, but it was not cleanly isolated on the final D4 anchor.
3. Compare ILP division prior `1.0` versus `0.9` using Full199 local division diagnostics; public scores tied and cannot resolve the direction.
4. Test adaptive rescue on/off using the exact same D4 predictions. Public `0.900` ties hide sub-0.001 effects.
5. Test confidence-gated ranker rewiring only on association-ambiguous failures and balanced guards.

### Avoid repeating without new evidence

- global min8 pruning
- higher detection threshold near `0.9725+`
- broad two-frame gap recovery
- aggressive edge-consensus pruning
- global dataset-specific short-track restoration
- DeepCenter fusion as a default global addition

## Interpretation Warning

The experiment log uses public leaderboard scores and visible-test output counts. Public score differences can contain sampling noise and hidden-test distribution effects. A tie at three decimals does not mean two methods are identical. Full199 local diagnostics should determine mechanism; Kaggle submissions should confirm only the strongest guarded candidates.
