# Supplementary Note: Identification and Handling of Susceptibility-Related Artifacts in Seed-Free Resting-State Co-Activation Pattern (CAP) Analysis

## 1. Overview

During the seed-free co-activation pattern (CAP) analysis of resting-state functional MRI data, a consistent deactivation pattern was observed in inferior brain regions — notably the uncus, cerebellar tonsils, and inferior temporal poles — across all extracted CAPs. This supplementary note documents the systematic evaluation of this pattern, provides evidence supporting its classification as a magnetic susceptibility artifact rather than a neurobiologically meaningful deactivation, and outlines the methodological approach adopted to address it.

## 2. Observation

Across all CAP solutions, a stereotyped pattern of negative values (deactivation) was present in the inferior aspects of the brain. The affected regions consistently included:

- **Uncus** (anterior medial temporal lobe)
- **Cerebellar tonsils** (inferior cerebellum)
- **Inferior temporal poles**
- **Orbitofrontal cortex** (ventral surface)

This pattern appeared as a spatially contiguous band of deactivation at the base of the brain, present in virtually every CAP centroid regardless of the number of clusters or analytical parameters employed.

## 3. Robustness Testing Across Analytical Configurations

To determine whether this deactivation pattern reflected a genuine neural signal or a methodological artifact, the CAP analysis was repeated under multiple analytical configurations. The pattern persisted identically across all scenarios tested:

| Configuration | Number of clusters (K) | Clustering iterations | Gray matter mask threshold | Deactivation pattern present |
|---|---|---|---|---|
| Scenario 1 | K = 4 | 50 | Default | Yes |
| Scenario 2 | K = 4 | 50 | GM probability > 0.4 | Yes |
| Scenario 3 | K = 10 | 30 | Default | Yes |

**Table 1.** Analytical configurations tested. The inferior brain deactivation pattern was invariant across all parameter combinations, including different numbers of clusters, clustering iterations, and gray matter mask stringency levels.

The persistence of this pattern across varying K values, iteration counts, and gray matter mask thresholds indicates that it is driven by a constant signal property of the data rather than by the clustering algorithm or mask definition.

## 4. Evidence Supporting Artifact Classification

Several converging lines of evidence support the interpretation that the observed inferior brain deactivation reflects magnetic susceptibility artifact rather than a true neurobiological signal:

### 4.1. Anatomical localization to known susceptibility zones

The affected regions — uncus, cerebellar tonsils, inferior temporal poles, and orbitofrontal cortex — are situated at air–tissue and bone–tissue interfaces (sphenoid sinus, petrous bone, foramen magnum). These boundaries are well-established sources of static magnetic field (B₀) inhomogeneities in echo-planar imaging (EPI) acquisitions, leading to signal dropout, geometric distortion, and reduced temporal signal-to-noise ratio (tSNR) (Ojemann et al., 1997; Deichmann et al., 2003; Weiskopf et al., 2006).

### 4.2. Resting-state design precludes task-driven deactivation

In task-based fMRI, consistent deactivation in specific brain regions may be attributed to task-negative network engagement (e.g., default mode network suppression during attentional demands). In the present resting-state design, there is no external task that could systematically drive the same voxels to deactivate across every temporal frame. The absence of a task-related explanatory mechanism makes a neural interpretation of this uniform, ubiquitous deactivation untenable.

### 4.3. Seed-free analysis amplifies susceptibility artifact influence

In seed-based CAP analysis, only frames exceeding an activation threshold in a predefined region of interest enter the clustering procedure, providing some degree of neurobiological constraint on frame selection. In the present seed-free approach, all frames (or a global-criterion-selected subset) are submitted to whole-brain k-means clustering. This means:

1. **Every voxel contributes to the distance metric** that determines cluster assignment.
2. Susceptibility-affected voxels, which exhibit **consistently low signal and low temporal variance**, are effectively constant across frames.
3. After z-score normalization, these low-signal voxels consistently fall **below the whole-brain mean**, receiving negative values in virtually every cluster centroid.
4. The k-means algorithm treats this stable, low-variance pattern as a **reliable spatial feature**, incorporating it into every CAP as an apparent "deactivation."

Thus, in seed-free CAP analysis, the susceptibility artifact does not merely appear as a cosmetic issue in visualization — it actively participates in the clustering distance calculations and can influence the overall partitioning of frames into clusters.

### 4.4. Invariance across analytical parameters

A genuine neural deactivation pattern (e.g., DMN suppression during a transient attention-related brain state) would be expected to vary in its expression across different cluster solutions: it might appear in some CAPs but not others, or its spatial extent might change with K. The observed pattern, by contrast, is **identically present in every CAP across K = 4 and K = 10**, and is unaffected by the number of clustering iterations (30 vs. 50) or gray matter mask threshold (default vs. > 0.4). This invariance is the signature of a data-constant artifact, not of dynamic neural activity.

## 5. Methodological Approach

### 5.1. Adopted strategy: reporting co-activation patterns only

Given the evidence presented above, the deactivation component of CAP maps in inferior brain regions was classified as artifactual. To avoid misinterpretation of these artifacts as neurobiologically meaningful deactivation, CAP results are reported and displayed showing **co-activation patterns only** (i.e., positive values / z > 0).

This approach has established precedent in the seed-free resting-state CAP literature, where deactivation patterns are frequently not interpreted in detail due to susceptibility-related confounds (Liu & Duyn, 2013; Chen et al., 2015).

### 5.2. Alternative and complementary approaches considered

Several additional strategies were evaluated to address this artifact. These approaches, while not adopted in the primary analysis, represent valid alternatives for future investigations:

| Approach | Description | Advantages | Limitations |
|---|---|---|---|
| **tSNR-based voxel exclusion (pre-clustering)** | Compute a group-mean temporal signal-to-noise ratio (tSNR) map and exclude voxels below a threshold (e.g., tSNR < 20–30) before k-means clustering | Directly addresses the root cause by removing low-quality voxels from the feature space; preserves legitimate deactivation in well-signaled regions | Requires computation of tSNR maps; results in some loss of ventral brain coverage |
| **tSNR-based voxel exclusion (post-clustering)** | Apply a tSNR mask to CAP maps after clustering for visualization and interpretation only | Simpler to implement; does not require re-running the analysis | Artifact voxels still influence clustering; the partitioning solution may be subtly biased |
| **Stricter gray matter mask** | Increase the gray matter probability threshold (e.g., > 0.5 or > 0.6) | Easy to implement | Gray matter masks do not directly index signal quality; already tested at > 0.4 with no effect on the artifact |
| **Transparency overlay for low-tSNR regions** | Display full CAP maps with a visual indicator (e.g., hatching or transparency) for regions with low tSNR | Provides full spatial information with transparent flagging of unreliable regions | Visually complex; may be difficult to interpret in publication figures |

**Table 2.** Alternative methodological approaches for handling susceptibility-related artifacts in CAP analysis.

### 5.3. Recommendation for future analyses

For subsequent analyses or replication studies, we recommend applying a tSNR-based voxel exclusion mask **prior to clustering** (pre-clustering approach). This strategy removes susceptibility-affected voxels from the k-means feature space entirely, ensuring that they do not influence cluster assignment. The tSNR threshold should be determined empirically from the group-mean tSNR map (a threshold of 20–30 is generally appropriate for 3T resting-state EPI data). This approach can be combined with the co-activation-only reporting strategy to provide the most rigorous treatment of susceptibility artifacts in seed-free CAP analysis.

To verify that artifact voxels did not meaningfully distort the clustering solution in the current analysis, we recommend computing spatial correlations between CAP centroids obtained with and without the tSNR mask. High spatial correlations (r > 0.90) would confirm that the artifact, while visually prominent, did not substantially alter the co-activation patterns identified.

## 6. Limitations

The adopted approach of reporting co-activation patterns only entails a trade-off: while it eliminates the risk of misinterpreting susceptibility artifacts as neural deactivation, it also precludes the identification of potentially genuine anti-correlated dynamics in well-signaled brain regions (e.g., reciprocal suppression between default mode and dorsal attention networks). Future work applying pre-clustering tSNR masking would allow deactivation patterns to be reported in regions where signal quality is sufficient to support their interpretation.

Additionally, it should be noted that the susceptibility-affected voxels participated in the clustering procedure in the present analysis. While the co-activation patterns in well-signaled regions are expected to be robust, the possibility that low-signal voxels marginally influenced cluster membership cannot be entirely excluded without a comparative analysis using pre-clustering masking.

## 7. References

- Chen, J. E., Chang, C., Greicius, M. D., & Glover, G. H. (2015). Introducing co-activation pattern metrics to quantify spontaneous brain network dynamics. *NeuroImage*, 111, 476–488.
- Deichmann, R., Gottfried, J. A., Hutton, C., & Turner, R. (2003). Optimized EPI for fMRI studies of the orbitofrontal cortex. *NeuroImage*, 19(2), 430–441.
- Liu, X., & Duyn, J. H. (2013). Time-varying functional network information extracted from brief instances of spontaneous brain activity. *Proceedings of the National Academy of Sciences*, 110(11), 4392–4397.
- Ojemann, J. G., Akbudak, E., Snyder, A. Z., McKinstry, R. C., Raichle, M. E., & Conturo, T. E. (1997). Anatomic localization and quantitative analysis of gradient refocused echo-planar fMRI susceptibility artifacts. *NeuroImage*, 6(3), 156–167.
- Weiskopf, N., Hutton, C., Josephs, O., & Deichmann, R. (2006). Optimal EPI parameters for reduction of susceptibility-induced BOLD sensitivity losses: a whole-brain analysis at 3 T and 1.5 T. *NeuroImage*, 33(2), 493–504.
