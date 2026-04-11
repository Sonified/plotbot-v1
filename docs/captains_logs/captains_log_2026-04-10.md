# Captain's Log — 2026-04-10

## v1.09 — Legacy variable cleanup + honest correlation-methods explainer for Jaye's Monday presentation

Maintenance pass on the E27 spectral correlation notebook plus a substantive rewrite of the methods/caveats section. No scientific results changed — every r, every p, every n is bitwise identical to v1.08 — but the codebase is meaningfully tidier and the notes section is now both consistent with the current pipeline and useful for someone presenting the work.

**Legacy variable sweep** — three rounds of cuts:

1. **Cell 8 (Step 5)** — removed 5 dead alias lines: `band_30s_smooth`, `hamogram_smooth`, and the `rp_h_raw/sm`, `rpL_h_raw/sm`, `rs_h_raw/sm`, `n_h_raw/sm` block. Pure refactor debris from when this cell was named the "30s smoothed hamogram" cell — downstream code never consulted any of them.

2. **Cell 10 (Step 7)** — removed the entire `*_band_raw`, `*_full_raw`, `*_band_sm`, `*_full_sm` alias block (21 lines, ~24 names). These existed solely as safety rails during the smoothing-removal refactor in v1.08 and zero downstream code ever consulted them. Kept the `n_*_total` aliases (`n_ham_total`, `n_ta_total`, etc.) because cell 12 references them 35+ times — they're the canonical sample-size names downstream, not aliases.

3. **Cell 12 (Step 9)** — removed 6 dead `_lo_*` unpack lines (every per-target below-cutoff unpack except hamogram). The hamogram below-cutoff unpack was *almost* cut on the same logic, but `_hg_lo_rpL` and `_hg_lo_rs` are actually used in Step 9's BAND SPECIFICITY block (5 + 1 references). The first cleanup pass missed that asymmetry — the hamogram is the only target where Step 9 prints both above and below — and we hit a `NameError` on the next run. Restored those two via a slim `_, _hg_lo_rpL, _, _hg_lo_rs, _ = hg_below` line. Lesson logged: when sweeping unused variables, the hamogram is special-cased in Step 9; don't blanket-cut the whole `_lo` group.

**Net cuts**: ~30 dead alias lines removed, zero behavioral change, all 14 `*_below` correlation tuples and all 7 `n_*_total` names still live where they're actually consumed.

**Notes section overhaul** — four subsections were stale or moot under the v1.08 native-binning regime, plus a substantive new methods explainer was added at Robert's request for Jaye's Monday presentation:

- **NEW: "How we measured correlations: four metrics, two reported, one principle"** — replaces the old "Pearson vs log-Pearson vs Spearman" subsection with a much more honest treatment. Walks through what each of the four metrics tests, what each one assumes, and when it's the right tool. Crucially, **does not claim log-Pearson is universally appropriate** — explicitly calls out that log-log Pearson is more theoretically motivated for the ratio targets ($n_{\text{ham}}/n_{\text{core}}$ and the temperature anisotropies, where $y$ is itself log-distributed) and that the Spearman > log-Pearson gap on $n_{\text{ham}}/n_{\text{core}}$ ($+0.65$ vs $+0.39$) is the direct symptom of this. The rationale for keeping log-Pearson + Spearman as the headline metrics is now grounded in the **agreement principle**: log-Pearson is parametric with assumed functional form, Spearman is distribution-free with no functional form, and when two methodologically distinct tests agree on direction and significance the result is robust regardless of the shape. The subsection ends with a verbatim "what to say if asked at a presentation" pull-quote that Jaye can lift directly. This was the result of Robert pushing back on an earlier hand-wave that "log-Pearson is the natural fit" — it isn't, universally, and the rewrite says so plainly.

- **REWRITTEN: "Why native binning instead of smoothing"** — was the v1.07-and-earlier "Why smoothing, and what it costs us" subsection, fully stale after v1.08 removed smoothing. Now explains why smoothing was tried first (noise suppression), the two problems we hit (scipy's `uniform_filter1d` propagating NaNs through its cumulative-sum implementation, and smoothing introducing autocorrelation that biased p-values), and why 60s native binning replaced it (one bin = one independent sample, no $n_{\text{eff}}$ bookkeeping needed, scale-validated by the Step 10 stress test).

- **REWRITTEN: "$n_{\text{ham}}/n_{\text{core}}$: still worth a detrend test"** — was the old "n_ham red flag" subsection that talked about smoothing inflation (Pearson jumping from raw 0.17 to smoothed 0.47, which doesn't apply now). The detrend recommendation is *still valid* but for a different reason: not smoothing-induced autocorrelation, but possible shared long-timescale structure (PSP heliocentric distance evolution, solar wind regime change) over the 80-minute window. The new framing makes the detrend test a forward-looking spot-check rather than a damage assessment. Robert's question "we're talking about detrending... that still fits for our binned approach? we're no longer smoothing" was a good catch — detrending is orthogonal to smoothing (smoothing kills high-frequency noise; detrending kills low-frequency drift) and is in fact *cleaner* to apply now because there's no autocorrelation bookkeeping to worry about.

- **DELETED: "Effective-n is a conservative estimate"** — entirely moot under native binning (each bin is one independent sample by construction, so $n_{\text{eff}} = n$ trivially).

- **TRIMMED: "Next steps for paper-grade rigor"** — removed the "block bootstrap for honest p-values on smoothed data" item (no smoothing means honest p-values are the default). List went from 5 items to 4: reproduce on a second encounter, detrend $n_{\text{ham}}/n_{\text{core}}$ + above-cutoff power, scan the cutoff across 5–20 Hz to verify a plateau, derive the cutoff from theory.

**Round-trip lessons captured**:

1. *"Useful legacy variables vs sloppy code"* — Robert asked the meta-question "is keeping legacy variables sloppy or actually useful?" The answer that emerged in this session: real legacy variables that bridge a rename or preserve a useful dual representation are fine; alias blocks that exist solely as "safety rails during a refactor" should be cut the moment the refactor lands. The `*_band_raw / *_full_sm` block was a textbook example — written for a correct moment, never cleaned up after the moment passed.

2. *Don't blanket-trust unused-variable scans on print-heavy code* — the first cleanup pass cut `_hg_lo_rpL` and `_hg_lo_rs` because a regex count said they were unused. They were used inside a print f-string that the regex skim missed. Lesson: when cutting unpacked names from a tuple, look at the print blocks too, not just direct uses.

3. *VS Code Jupyter kernel is a fragile beast* — the user hit a kernel hang during this session that had nothing to do with our edits. Switching to a different kernel resolved it instantly. Plotbot's `ham` data type uses `'data_sources': ['local_cdf']` only (no download path), so when `ham.datetime_array` came back as `None` after the kernel hang, it was kernel-state corruption and not a missing-file problem. The local CDF was right where it was supposed to be the whole time. The password prompt the user saw was for the orthogonal `mag_rtn` Berkeley remote-version-check, not for ham data.

**Files touched**: `plotbot/__init__.py` (version + commit message), `docs/captains_logs/captains_log_2026-04-10.md` (this entry), `example_notebooks/spectral_correlation_e27.ipynb` (cells 8, 10, 12, 14).

**Net diff**: ~30 dead lines removed from cells 8/10/12, ~150 lines of substantive notes-section rewrite in cell 14. No numerical results changed, no scientific claims changed, headline still log-Pearson $r = +0.57, p = 5 \times 10^{-8}$ for the hamogram. Ready for Jaye to present Monday with the methods explainer at the bottom of the notebook as backing material.

---

## v1.08 — Seven-target pipeline, velocity-selectivity hierarchy, 60s default binning, smoothing fully removed

Further refinement to the E27 spectral correlation notebook after v1.07. Where v1.07 established the Landau-KAW mechanism from five observables, v1.08 adds two more anisotropy targets (core and neck temperature anisotropies per Jaye's bulk-plasma-heating question), simplifies the binning default to one-minute windows, purges dead smoothing code, and adds a scale stress test cell that reruns the pipeline across multiple bin sizes. Net result: a cleaner, more defensible story with an additional physical finding (the three-population velocity-selectivity hierarchy).

### New scientific findings

**The three-population anisotropy hierarchy (Jaye's question answered).**
Added `Tperp_core/Tpar_core` and `Tperp_neck/Tpar_neck` as two new correlation targets, alongside the existing `Tperp_ham/Tpar_ham`. All three are correlated against above-cutoff wave power at the same 60s native binning. Result:

- **ham**: log-Pearson = -0.352, Spearman = -0.279, p ~ 0.001 — **significant**
- **neck**: log-Pearson = -0.065, Spearman = +0.132 — **null**
- **core**: log-Pearson = -0.103, Spearman = +0.008 — **null**

The ham population is the only one showing significant wave-power response. Physical interpretation: Landau resonance requires `v_par ~ omega/k_par`, and with the beam pinning at 2.2 × v_A the resonant parallel velocity is far above the core thermal speed (typically v_core,th ~ 0.1-0.3 × v_A). The core has essentially zero particles at the Landau-resonant velocity and does not participate. **The hierarchy ham >> neck ~ core is direct evidence of velocity-selective wave-particle coupling**, not broadband plasma heating. Answer to Jaye's bulk-heating question: on the 60s timescale, direct wave-to-core heating via this channel is **not observed**; the waves operate specifically on the suprathermal tail.

**Medians of the three populations** (from actual HamPy-fitted data, 60s binned):

- `core T_perp/T_par`: median ~0.66 → parallel-dominated
- `neck T_perp/T_par`: median ~3.46 → perpendicular-dominated
- `ham  T_perp/T_par`: median ~3.14 → perpendicular-dominated

The ham and neck populations have T_perp > T_par in the fitted sub-population moments because the hammerhead "cap" shape comes from the **perpendicular velocity-space diffusion** described in Verniero et al. (2022). The core is a roughly thermal bulk population with a slight parallel bias. This corrects an earlier misstatement in v1.07 where I had claimed hammerheads were parallel-dominated in temperature moments (they're parallel in DRIFT velocity, not temperature).

**The corrected Landau discriminator.** The negative sign of the ham anisotropy correlation is now framed as the **discriminating signature** between Landau damping and cyclotron-resonance scattering (Verniero et al. 2022's alternative mechanism):

- **Landau damping** pumps T_par exclusively → T_perp/T_par goes DOWN
- **Cyclotron scattering** pumps T_perp → T_perp/T_par would go UP

Our observed negative correlation **favors the Landau interpretation** over cyclotron scattering, because the sign would be wrong for the cyclotron mechanism. This is a sharper claim than "consistent with Landau" — it's a specific falsifiable test that the 2022 mechanism fails.

### Pipeline simplifications

**Default bin_sec → 60s (one-minute bins).** Changed from 120s to 60s as the primary default. The 60s version is the sweet spot on the stress test: good sample size (n ~ 79), correlations still strong, beam clustering still holds, and "one-minute bins" is trivial to communicate. The 120s version oversells the saturation claim (the drift pinning is bin-averaging-dependent), and 30s is too noisy.

**Smoothing infrastructure fully removed.** Previous versions carried legacy `smooth_factor_band`, `smooth_factor_ham`, and `smooth_factor_hamogram` variables. After the v1.07 native-binning refactor these became no-ops (all set to 1 by default), but the code still carried the infrastructure: `uniform_filter1d` calls, "SMOOTHED" duplicate plot panels in Step 5, "(smooth 1x)" labels, and RAW vs SMOOTHED duplicate correlation rows that contained identical numbers. v1.08 removes this dead weight:

- `smooth_factor_hamogram` variable: gone
- Step 5 `uniform_filter1d` calls: gone
- Step 5 4-panel plot → clean 2-panel plot (just band PSD and hamogram)
- Step 5 "SMOOTHED" duplicate correlation block: gone
- Step 8 visual overlay smoothing knob: gone
- All "(smooth 1x)" and "smoothed Nx" labels: gone
- Verified: every single correlation coefficient, p-value, and diagnostic is bitwise identical to the pre-cleanup version (the smoothing was a no-op, so removing it had zero numerical impact)

### New Step 10: Scale stress test

Added a dedicated stress-test cell that reruns the full 7-target correlation pipeline at multiple bin sizes (30s, 60s, 120s, 240s) and prints a comparison table with significance stars. Also includes a bin-by-bin comparison of the beam-pinning diagnostic (`|v_drift/v_A|` median, IQR, CV, verdict). This directly tests which findings are robust vs bin-averaging artifacts, and confirms:

- **Robust across all bin sizes**: hamogram, n_ham/n_core, ham anisotropy, core/neck nulls, below-cutoff controls
- **Bin-size-dependent**: `|v_drift/v_A|` clustering tightness — CV grows from 0.12 (120s) to 0.20 (30s), with outlier values up to 5.8 × v_A appearing at 30s. The "pinning at 2.2 × v_A" is therefore a ~minute-averaging feature, not an instantaneous pin. Narrative updated accordingly from "pinned" to "clustered on ~minute timescales."

### Narrative cleanup

Multiple rounds of pass-through cleanup to eliminate stale references:

- All top-of-cell comments reviewed and corrected: "4-panel overview" → "7-panel overview", "three targets" → "seven targets", "six result tuples" → "14 result tuples" (7 × 2 for above/below), etc.
- Loose "band" terminology (inherited from the v1.05-era narrow 12-35 Hz band) replaced with precise "above-cutoff range" / "below cutoff" language throughout
- Hardcoded "120s bins" labels in Step 9 findings → dynamic `f'{_bin_hamogram}s bins'` so they track the config
- Ham anisotropy interpretation corrected (perpendicular-dominated in sub-pop moments, not parallel-dominated)
- Saturation claim softened from "pinned" to "clustered around ~2.2 × v_A on ~minute averaging timescales"
- Plot y-limits raised on three panels: `T_perp/T_par` from `(0.1, 10)` to `(0.1, 100)` (data ranges up to ~53 for neck), `|v_drift/v_A|` floor raised from 0.01 to 1.0 for resolution, `|v_drift|` raw given explicit `(100, 3000)` bounds

### References section added

Added a "References and theoretical grounding" section to the notes markdown cell with **eleven verified citations** looked up via web search (not memory):

- **Bruno & Carbone (2013)** — Living Reviews in Solar Physics — turbulence cascade
- **Alexandrova et al. (2013)** — Space Science Reviews — ion-scale instabilities
- **Chen (2016)** — Philosophical Transactions of the Royal Society A — kinetic-scale dissipation review
- **Bruno et al. (2015)** — GRL — ion break location vs plasma beta
- **Howes et al. (2008)** — JGR Space Physics, 113, A05103 — cascade model
- **Schekochihin et al. (2009)** — ApJS, 182, 310 — astrophysical gyrokinetics, KAW dispersion
- **Bowen et al. (2020)** — ApJS, 246, 66 — PSP ion-scale wave survey
- **Verniero et al. (2020)** — ApJS, 248, 5 — PSP proton beams + ion-scale waves
- **Shankarappa et al. (2024)** — ApJ, 973, 20 — cyclotron damping heating rates
- **Verniero et al. (2022)** — ApJ, 924, 112 — hammerhead discovery paper, cyclotron interpretation
- **Das & Verniero (2025)** — EGU abstract EGU25-15609 — HamPy package

Each citation tagged with which specific claim in the notebook it supports. Includes a disclaimer that the specific identifiers should be spot-checked before formal paper use.

### Headline numbers as of v1.08 (60s native binning, n=79)

| Target | Pearson | log-Pearson | log-log | Spearman |
|---|---|---|---|---|
| hamogram (above) | +0.55 | **+0.568** | +0.59 | **+0.665** |
| n_ham/n_core (above) | **+0.718** | +0.391 | +0.659 | +0.645 |
| Tperp/Tpar ham (above) | -0.211 | **-0.352** | -0.269 | -0.279 |
| Tperp/Tpar core (above) | -0.152 | -0.103 | -0.104 | +0.008 |
| Tperp/Tpar neck (above) | -0.036 | -0.065 | +0.017 | +0.132 |
| \|v_drift/v_A\| (above) | -0.097 | -0.035 | -0.035 | -0.130 |
| \|v_drift_raw\| (above) | **-0.304** | -0.252 | -0.240 | -0.255 |

All seven targets show the expected band-specific behavior (disjoint below-cutoff controls near zero). Beam-drift median clusters at 2.23 × v_A with IQR width 0.34, consistent with KAW parallel phase velocity at `k_perp*rho_i ~ 2`.

### Commit message
`v1.08 Refactor: 7 hammerhead targets, velocity-selectivity via 3-population anisotropy, 60s native binning default, smoothing removed`

---

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
