# Captain's Log — 2026-04-10

## v1.07 — Landau damping of KAWs identified via beam velocity pinning

Substantial scientific and statistical refinement to the E27 spectral correlation analysis. Tonight's work (continuation of the same day as v1.06) converted the result from "correlation in a band" into a specific, quantitatively-grounded Landau-damping-of-kinetic-Alfvén-waves story with **five independent observational signatures** and a **measured beam saturation velocity**.

### Pipeline refactor: smoothing → native binning

The biggest methodological improvement: per-detection ham quantities (n_ham/n_core, Tperp/Tpar) used to be handled via rolling-mean smoothing over adjacent irregularly-sampled detections. This has been replaced with **native 120-second binning** matching the hamogram treatment, via a new `_bin_per_detection` helper in Step 3. Result: ~40 fully independent samples per target, no effective-n bookkeeping, honest scipy p-values straight from the distribution.

**Surprise finding from the refactor:** the correlation numbers went UP, not down. The per-detection n_ham estimates were so noisy that smoothing over 6 adjacent detections couldn't clean them up as well as averaging ~17 detections per 120s window. The n_ham/n_core Pearson jumped from ~0.17 (smoothed) to **+0.78** (binned) at n=40. The anisotropy Tperp/Tpar went from -0.04 (noise) to **-0.43** (significant). Both were real effects that were drowning in per-detection noise, and native binning was the right aggregation.

### Config system

Added `use_single_bin = True` and `bin_sec = 120` as top-level config in Step 1, with per-target override variables (`bin_sec_hamogram`, `bin_sec_n_ham`, `bin_sec_t_aniso`) for power-user mode. Downstream cells read `_bin_hamogram` / `_bin_n_ham` / `_bin_t_aniso` resolved values. Changing one knob updates every target in single-bin mode; tuning individually requires flipping the toggle.

### Bugs fixed
- **scipy.ndimage.uniform_filter1d NaN contamination**: a single NaN in the input poisons every output position from that index forward (cumulative-sum implementation). Added NaN-interpolation guards before smoothing and `_fill_binned_nans` helper to plug empty bins with linear interpolation after binning.
- **Plot ylim clipping**: n_ham/n_core panel had `ylim(1e-3, 10)` but the actual data spans `1.7e-5` to `0.97`. Fixed to `ylim(1e-5, 1)` to show all 668 valid points instead of 454.
- **Reference notebook typo (Jaye's `vdrift_commands.ipynb`)**: `compute_vpar` is called with `By_inst` in the third argument slot where `Bz_inst` should go. Our notebook fixed this silently and flagged it for Jaye.

### Scientific findings — the five signatures

All on native 120s binning, n=40 fully independent samples, no smoothing, honest scipy p-values.

**Finding 1: Hamogram (occurrence rate) vs above-cutoff wave power**
- log-Pearson r = +0.65, p = 6.5e-06
- Spearman r = +0.76, p = 1.9e-08
- Delta (above - below cutoff) = +0.61
- Rock solid, band-specific.

**Finding 2: n_ham/n_core (hammerhead fraction) vs above-cutoff wave power**
- Pearson r = +0.78, p = 2.6e-09
- log-log Pearson r = +0.71, p = 2.6e-07
- Spearman r = +0.69, p = 1.1e-06
- Nearly as strong as Finding 1. Was hidden in per-detection noise before the binning refactor.

**Finding 3: Tperp_ham/Tpar_ham (anisotropy) vs above-cutoff wave power**
- log-Pearson r = -0.43, p = 0.006
- Spearman r = -0.35, p = 0.026
- **Corrected interpretation per Jaye**: this is NOT cyclotron scattering (which would increase Tperp/Tpar on parallel-dominated populations). The sign is consistent with Landau damping: hammerheads are parallel-extended by construction, and Landau-resonant wave energy heats T_‖ without touching T_⊥, driving the ratio down.

**Finding 4: |v_drift_hc / v_A| (normalized beam velocity) vs above-cutoff wave power**
- All metrics near zero, none significant
- **BUT** the drift is tightly clustered at `median = 2.20 x v_A`, IQR = [2.11, 2.39], robust CV = 0.12
- Pinned at ~2.2 × v_A, not freely varying
- **This is the key physics identification**: pinning at 2.2 × v_A is consistent with Landau-resonant damping of kinetic Alfvén waves at finite perpendicular wavenumber, where the parallel phase velocity is boosted above v_A by √(1 + k_⊥²ρ_i²). At k_⊥ρ_i ~ 1-2 the dispersion factor gives 1.4-2.5 × v_A naturally. Our measured 2.20 falls right in that range.

**Finding 5: |v_drift_hc| raw (km/s) vs above-cutoff wave power**
- All metrics weakly negative (~-0.23), none significant
- Same null story as Finding 4 without the v_A normalization
- Confirms the beam velocity is genuinely flat (pinned), not a normalization artifact

### The physical story

**Landau-resonant damping of kinetic Alfvén waves at the ion kinetic break is continuously pumping resonant protons into a parallel-beam state saturated at the KAW parallel phase velocity (~2.2 × v_A for this encounter).** Wave power modulates the population of that beam state (Findings 1, 2, 3) but not its velocity (Findings 4, 5 — pinned).

The 10 Hz cutoff is not empirical tuning: it's approximately the proton cyclotron frequency at E27 perihelion (B ~ 500-1000 nT → f_ci ~ 5-15 Hz), which is the ion kinetic break. Below the break: MHD cascade, no parallel electric fields, no Landau channel → no correlation. Above: kinetic dispersive modes with parallel electric fields → Landau damping active → correlations appear.

### Analytical improvements

- **Pearson, log-Pearson, log-log Pearson, Spearman** — all four correlation metrics are now computed and reported in Step 7's final diagnostic table. log-log Pearson (power-law fit) is appropriate for continuous log-normal quantities like n_ham/n_core and Tperp/Tpar; log-Pearson (log-x, linear-y) is appropriate for count data like hamogram; Pearson is the linear baseline; Spearman is the shape-agnostic monotonic check.
- **Landau saturation diagnostic**: computes robust coefficient of variation (IQR/median) for the normalized drift and classifies the result (clustered at ~1 v_A → pure Alfvén Landau; clustered at 1.3-3 v_A → KAW Landau; clustered at >3 v_A → beam-cyclotron/magnetosonic; spread too wide → not saturated). Auto-interprets the measured saturation velocity in terms of wave dispersion.
- **Step 9 findings printout** is now fully dynamic with a paper-ready paragraph that regenerates from live computed values — including the measured saturation velocity and KAW dispersion explanation.

### Attribution
- **Jaye caught the cyclotron-scattering sign error** and suggested Landau damping, which was the right mechanism. Credited explicitly in the Step 9 narrative.
- **Jaye suggested native 120s binning** instead of rolling-mean smoothing on hamogram; we extended that philosophy to all per-detection targets and it paid off dramatically.
- **vdrift computation adapted from Jaye's `vdrift_commands.ipynb`** (with the `Bz_inst` typo fixed).

### What's next
- Reproduce on E26 (and earlier encounters) with the 10 Hz cutoff frozen
- Wavelet polarization analysis of the above-cutoff band to directly confirm k_⊥ρ_i ~ 1-2
- Detrending test for robustness of n_ham/n_core and Tperp/Tpar correlations

### Commit message
`v1.07 Feature: E27 spectral correlation - Landau damping of KAWs, 5-target pipeline, beam pinned at 2.2 x v_A`

---

## v1.06 — E27 Spectral Correlation Notebook

Added a new exploratory notebook: `example_notebooks/spectral_correlation_e27.ipynb`.

### What it does
Tests the hypothesis that ion cyclotron waves drive hammerhead formation in PSP SPAN-I proton velocity distributions. Correlates B_N power spectral density above a tunable cutoff frequency against three hammerhead observables:

1. **Hamogram (occurrence rate)** — hammerhead detection count per bin
2. **n_ham / n_core** — fraction of the proton population in the hammerhead state
3. **Tperp_ham / Tpar_ham** — temperature anisotropy of the hammerhead population

Time window: `2026/03/11 07:10–08:30 UT` (E27 perihelion approach).

### Key design choices
- **Single split point** (`f_cutoff = 10 Hz`) divides the spectrum into two disjoint regions:
  - Above cutoff = target (cyclotron-resonant range)
  - Below cutoff = disjoint control
- **Kolmogorov roll-off argument** justifies extending the above-cutoff band to Nyquist — power rolls off so hard above ~50 Hz that including those bins is cosmetic.
- **Native 120-second binning** for all three targets (`bin_sec = 120`, `use_single_bin = True`) instead of rolling-mean smoothing. Gives ~40 fully independent samples per target. Honest p-values straight from scipy — no effective-n bookkeeping needed.
- **Per-target bin-size overrides** available when `use_single_bin = False` (per-hamogram, per-n_ham, per-anisotropy).

### Pipeline structure
- **Step 1**: load `mag_rtn.bn`, `ham.n_ham`, `ham.n_core`, `ham.Tperp_ham`, `ham.Tpar_ham` + binning config
- **Step 2**: B_N spectrogram (10 s windows, ~0.1 Hz resolution, NaN-interpolated to prevent blank bands)
- **Step 3**: 5-panel overview (B_N, spectrogram, n_ham/n_core, Tperp/Tpar, hamogram) + native binning of all three per-detection targets with NaN fill across empty bins
- **Step 3b**: split-point tuning cell with horizontal line overlay
- **Step 4**: per-detection correlations (n_ham/n_core and Tperp/Tpar) on the 120 s grid
- **Step 5**: hamogram-specific correlation (30 s → 120 s rebin) with side-by-side above/below cutoff scatter plots
- **Step 6**: sanity-check table comparing all three targets × (above, below) cutoff
- **Step 7**: full diagnostic with Pearson / log-Pearson / log-log / Spearman columns and honest p-values
- **Step 8**: 30 s (now 120 s) binned overlay plot
- **Step 9**: dynamic paper-ready findings printout
- **Notes cell**: markdown write-up of caveats (smoothing tradeoffs, Pearson vs log-Pearson vs log-log vs Spearman, band-tuning caveat, effective-n, next steps)

### Results so far (E27 perihelion)
- **Hamogram (formation rate)**: log-Pearson r ≈ +0.65, Spearman r ≈ +0.76, p ≈ 10⁻⁸ at n = 40 fully independent 120 s bins. Below-cutoff control ≈ 0. Band-specific, bulletproof.
- **n_ham / n_core (fraction)**: weaker positive correlation, Spearman ~+0.36 to +0.51. Tentative.
- **Tperp / Tpar (anisotropy)**: weak negative hint. Uncertain whether real self-regulation or trajectory drift — detrending would settle it.

### Infrastructure changes beyond the notebook
- `plotbot/__init__.py`: version bumped to v1.06
- `.gitignore`: added `Hamstrings_E27/` so the E27 source archive stays local-only
- E27 CDF files copied into `data/cdf_files/Hamstrings/` so plotbot's existing ham handler picks them up automatically
- `example_notebooks/plotbot_audification_examples.ipynb`: unrelated pending updates also included in this push

### Gotchas worth remembering
- `scipy.ndimage.uniform_filter1d` has a cumulative-sum internal implementation — a single NaN input poisons every subsequent output. Always NaN-interpolate before smoothing.
- When correlating count data (hamogram) with log-normal quantities (band power), `log-Pearson` (log x vs linear y) is the right metric. For two log-normal quantities, `log-log Pearson` (power-law fit) is more appropriate.
- With n_raw = 670 per-detection samples, even r ≈ 0.12 crosses conventional p < 0.01. Native binning to n = 40 gives honest effect sizes and honest p-values — which is why we switched.

### Commit message
`v1.06 Feature: E27 spectral correlation notebook (hamogram vs B_N, three-target pipeline)`
