---
name: analysis-methods
description: Use before quoting any correlation, trend, spec-compliance verdict or headline number from Rubin per-exposure/per-night data (image quality vs wind/temperature/airmass, mount jitter, dome seeing, downtime fractions), and when checking numbers against Rubin requirement documents (LPM-17 SRD, LSE-29 LSR, LSE-30 OSS, LSE-61 DMSR). Gives the within-night fixed-effects + placebo recipe, the spec-verdict taxonomy, detection-statistic null tests, requirement-document traps, and prior early-operations results to compare against.
---

# Analysis methods for Rubin operations data

## 1. Per-exposure correlations: effective N is nights, not exposures

Exposures in a night share atmosphere, thermal state, wind regime and dome configuration. With ~36k exposures over ~73 nights, the effective N is about 73. Pooled per-exposure correlations are confounded by between-night (often seasonal) trends.

Required on every headline number:
1. **Night-demean** both sides (subtract the per-night median). Report the within-night estimate as primary, pooled only as a diagnostic.
2. **Placebo:** permute the driver *within each night* and rerun. A real effect disappears; an artefact reproduces most of the "signal".
3. **Cluster standard errors on night.** iid SEs understated uncertainty by ~8× in practice.
4. **Positive control:** show that a known driver (airmass → PSF, DIMM → PSF) is recovered by the same design, so a null isn't just low power.

Example (2026): wind → PSF was +0.24 between nights but +0.02 within nights, while airmass recovered at t ≈ +7.8. Wind is seasonally trended (ρ(day-of-year, wind) = +0.37), and dome seeing acts on minute timescales, so a between-night-only signal isn't causal.

Estimator traps:
- **Suppressor variables:** DIMM *anti*-correlates with wind (ρ = −0.37), so partialling DIMM out *inflated* the PSF–wind partial r (+0.30 → +0.39). "Survives controlling for X" means nothing until you check sign(r_xz).
- **One-sided clipping:** `sqrt(PSF² − atm²)` went negative ~54 % of the time (the DIMM over-predicts), and clipping at 0 manufactured a positive wind-correlated residual (the placebo reproduced +0.37 of +0.46). Never quadrature-subtract a noisy proxy per exposure; fit the variance budget jointly.
- Clip `dimm_seeing` to (0.2, 3.0)″ first, and check that the source is still publishing (see the consdb skill).
- Use the EFD wind, not ConsDB `wind_speed`, in the high-wind tail.

## 2. Spec verification: non-contradiction is not compliance

Define **U = (95 % bound of the projected metric at the spec point) / budget** and classify:

| Verdict | Condition |
|---|---|
| CONSISTENT | U ≤ 1 |
| UNDERPOWERED | U > 1 and \|t\| < 2 (bound is loose, slope not detected) |
| NO-BUDGET | U > 1, \|t\| ≥ 2, but only a relative/screening budget exists |
| CONTRADICTED | U > 1, \|t\| ≥ 2, and an absolute budget |

- If the data never reach the spec point (e.g. max sustained wind 18.9 m/s against a 20 m/s spec), say so: you're extrapolating, and a loose bound means *limited power*, not degradation. Load ∝ V², so evaluating a 25 m/s gust from data to 19 m/s inflates the uncertainty ~1.75×.
- **Decode the spec numerically before testing it.** Quoted values often over-determine the intended form. Example: the system-IQ contribution "15 % … 0.52″ at X = 2, 0.42″ at X = 1.4" gives 0.52/0.42 = 1.238 = (2/1.4)^0.6, so the budget scales as X^0.6. "15 %" is quadrature (`sys = atm·√(1.15² − 1)`), and both points imply 0.604″ zenith seeing (the outer-scale-*corrected* median; the raw DIMM median is 0.69″). A budget that grows with airmass makes **zenith** the binding case.
- Test the airmass/elevation dependence within nights, separately from the level.

## 3. Detection statistics that take a maximum have no natural null

A matched filter or Radon/line search that takes the *max* over many offsets and angles returns large "SNR" on blank sky (SNR 140–740 by latching onto field stars, or a null max ≈ 11 for unit-variance cells).
- Build the null empirically: rerun on **column-shuffled** real data, or with a **rotated-90° control** path, and use the ratio to the control.
- Require **repeatability** across independent exposures or passes. A single exposure over threshold isn't a detection.
- Look at the cutouts. Real satellite trails were horizontal bands in rectified strips; artefacts were vertical stripes.
- For satellites, never screen with current TLEs propagated months back (positions 30–300° off). Use the historical TLE for each night (Space-Track), and expect ~1′ cross-track TLE errors even for fresh TLEs.

## 4. Data-window and provenance hygiene

- Query the data window (`max(day_obs)`, last EFD sample) every time; don't trust a remembered date.
- Treat telemetry state gaps longer than about a day as uncovered.
- Record the SHA-256 of simulation databases and the versions of upstream code that produced a metric. Shared sim files have been regenerated in place.
- Never key a coverage mask on one band (it silently drops objects covered only in another band). Use unions over sub-pixels for footprint coverage.

## 5. Requirement documents (LPM-17, LSE-29, LSE-30, LSE-61)

- **The LSR commits the SRD *minimum*, not design, for delivered IQ and encircled energy** (LSR-REQ-0007): S1 = 0.59/0.72/0.89″, not 0.56/0.69/0.87″. LSR-REQ-0090 per-band depths are 0.1–0.4 mag shallower than SRD design in u/g/r/i. Report against LSR (committed) with SRD design as a labelled aspiration.
- Most SRD specs are **triplets** (median, outlier threshold, allowed outlier fraction): PA1/PA2/PF1, AM1/AD1/AF1, SE1/SE2/EF1, TE1/TE3/TEF, D1/Z1/DF1, S1/SX/SF1. Median-only dashboards don't measure the requirement.
- **SR1/SR2/SR3 encircled-energy values conflict four ways** across the LPM-17 body, LPM-17 glossary, LSE-29 and LSE-30 (percentages, radius vs diameter, values). Don't quote them externally until an LCR reconciles them.
- LSE-29 table unit errors: LSR-REQ-0083 TFMax = 120 *seconds* (the table says minute); LSR-REQ-0098 `fastRevisitMin` = 40 *seconds* (the table says degree²). LSR-REQ-0097 is descoped (LCR-1554); cite LSR-REQ-0123/0124/0125.
- Image-loss specs differ by scope (OSS-REQ-0111 ≤ 1 % end-to-end vs DMS-REQ-0309 ≤ 1e-5 within DM). Always label the scope.
- No top-level open-shutter-fraction, observing-efficiency, MTBF/MTTR or satellite-constellation requirement exists in these four documents.

## 6. Prior early-operations results to compare against

These are working results from B. Stalder's 2026 analyses, not project-official numbers. The public notebooks show the method; rerun them before quoting.

| Topic | Result (as of) | Notebook |
|---|---|---|
| Dome seeing | driver is mirror–air ΔT, FWHM ≈ 0.115·\|ΔT\|^0.5″; wind null within nights; thermal t 6.3 (Jan–Apr) → 3.4 (full 121 nights), weak May–Jul (2026-11) | `bstalder/rubin_notebooks` `earlyoperations/dome_and_wind/Dome_Seeing_Model_Construction.ipynb` |
| Inside vs outside wind | inside ≈ 0.36 + 0.109·outside m/s (floor + coupling); into-wind p95 can exceed 0.5× outside at V > 8 (2026-09) | `.../dome_and_wind/Wind_Loading_and_Ingression_Operational_Limits.ipynb` |
| Wind spec 20/25 m/s | no contradiction except mount jitter at the 25 m/s gust (U = 1.05, marginal); max sustained 18.9 m/s observed (2026-09) | same |
| System IQ contribution | aos_fwhm-based U ≈ 1.3 at the budget, worst at zenith, improving (recent U ≈ 1.17); camera term 0.207″ (2026-08) | `.../optical_psf/System_IQ_Contribution_Spec_Verification.ipynb` |
| Focus wander | genuine ~5-min uncontrolled focus disturbance seen open-loop (T614), distributed thermal origin | `.../optical_psf/MTAOS_Z4_Focus_Trends.ipynb` |
| Weather downtime | allskycam cloud index > 0.3 ≈ 0.14 of dark time (> 0.5 ≈ 0.12), year-to-year σ ≈ 0.04; the CTIO 0.25 default is wrong in seasonal shape (2026-10) | `.../system_performance/weather_downtime_climatology.ipynb`; `lsst/sp_notebooks` `tracking_hub/ops/rosp-11_time_loss_accounting/` |
| Engineering | louver drive health, hexapod slips, TMA az encoder-head impulses | `.../engineering/*.ipynb` |
