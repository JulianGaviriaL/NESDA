# Supplementary Note: Susceptibility-Related Artifacts in Seed-Free Resting-State Co-Activation Pattern Analysis

## 1. Observation and Rationale

During seed-free co-activation pattern (CAP) analysis of resting-state fMRI data, a consistent deactivation pattern was observed in inferior brain regions — notably the uncus, cerebellar tonsils, inferior temporal poles, and orbitofrontal cortex — across all extracted CAPs. This spatially contiguous band of negative values at the base of the brain was present in virtually every CAP centroid regardless of the number of clusters or analytical parameters employed.

To determine whether this pattern reflected genuine neural co-deactivation or a methodological artifact, the analysis was repeated under multiple configurations:

| Configuration | K | Iterations | GM mask threshold | Number of voxels | Deactivation present |
|---|---|---|---|---|---|
| Scenario 1 | 4 | 50 | Default | 166,520 | Yes |
| Scenario 2 | 4 | 50 | GM probability > 0.4 | 133,500 | Yes |
| Scenario 3 | 10 | 30 | Default | 166,520 | Yes |

**Table 1.** The inferior brain deactivation pattern was invariant across all parameter combinations, including different cluster numbers, iteration counts, mask stringency levels, and voxel counts.

## 2. Evidence Supporting Artifact Classification

Three converging lines of evidence support the classification of this pattern as magnetic susceptibility artifact:

### 2.1. Anatomical localization to known susceptibility zones

The affected regions are situated at air–tissue and bone–tissue interfaces (sphenoid sinus, petrous bone, foramen magnum) — well-established sources of B₀ inhomogeneities in EPI acquisitions, leading to signal dropout, geometric distortion, and reduced tSNR (Ojemann et al., 1997; Deichmann et al., 2003; Weiskopf et al., 2006).

### 2.2. Seed-free analysis amplifies susceptibility artifact influence

In seed-free CAP analysis, all frames are submitted to whole-brain k-means clustering, and every voxel contributes to the distance metric determining cluster assignment. Susceptibility-affected voxels exhibit consistently low signal and low temporal variance, making them effectively constant across frames. After z-score normalization, these voxels fall below the whole-brain mean in virtually every cluster centroid, and the algorithm treats this stable pattern as a reliable spatial feature — incorporating it as apparent "deactivation" in every CAP. Unlike seed-based approaches, where frame selection provides some neurobiological constraint, seed-free clustering is maximally sensitive to these data-constant artifacts.

### 2.3. Invariance across analytical parameters

While resting-state fMRI does exhibit genuine co-deactivation dynamics (e.g., DMN–DAN anti-correlations), such neural patterns are expected to vary across cluster solutions — appearing in some CAPs but not others, or changing in spatial extent with K. The observed inferior brain pattern, by contrast, is identically present in every CAP across K = 4 and K = 10, unaffected by iteration count (30 vs. 50) or gray matter mask threshold (default vs. > 0.4, reducing voxel count from 166,520 to 133,500). This invariance is characteristic of a data-constant artifact, not of dynamic neural activity.

## 3. Methodological Approach

### 3.1. Adopted strategy

CAP maps are reported showing co-activation patterns only (z > 0). This approach has precedent in the seed-free resting-state CAP literature (Liu & Duyn, 2013; Chen et al., 2015).

### 3.2. Alternative approaches considered

| Approach | Advantages | Limitations |
|---|---|---|
| **tSNR-based voxel exclusion (pre-clustering)** | Removes low-quality voxels from the k-means feature space; preserves legitimate deactivation elsewhere | Requires tSNR maps; loss of ventral brain coverage |
| **tSNR-based voxel exclusion (post-clustering)** | Simple; no re-analysis needed | Artifact voxels still influence cluster assignment |
| **Stricter gray matter mask** | Easy to implement | Does not index signal quality; tested at > 0.4 with no effect |
| **Transparency overlay for low-tSNR regions** | Full spatial information with flagged regions | Visually complex for publication |

**Table 2.** Alternative approaches for handling susceptibility artifacts in CAP analysis.

For future analyses, pre-clustering tSNR masking (threshold ≥ 20–30) is recommended to exclude artifact voxels from the feature space entirely. Spatial correlations between masked and unmasked CAP solutions can verify whether artifact voxels meaningfully distorted the clustering.

## 4. Limitations

Reporting co-activation only eliminates the risk of misinterpreting susceptibility artifacts but precludes identification of genuine anti-correlated dynamics in well-signaled regions. Additionally, susceptibility-affected voxels participated in the clustering procedure, and while co-activation patterns in well-signaled regions are expected to be robust, marginal influence on cluster membership cannot be excluded without comparative pre-clustering masking analysis.

## 5. References

- Chen, J. E., Chang, C., Greicius, M. D., & Glover, G. H. (2015). Introducing co-activation pattern metrics to quantify spontaneous brain network dynamics. *NeuroImage*, 111, 476–488.
- Deichmann, R., Gottfried, J. A., Hutton, C., & Turner, R. (2003). Optimized EPI for fMRI studies of the orbitofrontal cortex. *NeuroImage*, 19(2), 430–441.
- Liu, X., & Duyn, J. H. (2013). Time-varying functional network information extracted from brief instances of spontaneous brain activity. *Proceedings of the National Academy of Sciences*, 110(11), 4392–4397.
- Ojemann, J. G., Akbudak, E., Snyder, A. Z., McKinstry, R. C., Raichle, M. E., & Conturo, T. E. (1997). Anatomic localization and quantitative analysis of gradient refocused echo-planar fMRI susceptibility artifacts. *NeuroImage*, 6(3), 156–167.
- Weiskopf, N., Hutton, C., Josephs, O., & Deichmann, R. (2006). Optimal EPI parameters for reduction of susceptibility-induced BOLD sensitivity losses: a whole-brain analysis at 3 T and 1.5 T. *NeuroImage*, 33(2), 493–504.