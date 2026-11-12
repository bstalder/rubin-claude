---
name: consdb
description: Use when querying the Rubin Consolidated Database (ConsDB) — per-exposure/visit metadata for LSSTCam, LSSTComCam, LATISS (cdb_lsstcam.exposure, visit1, visit1_quicklook, ccdvisit1_quicklook, exposure_quicklook) — from SDF or the RSP, or when a ConsDB column looks wrong (nulls, NaN-as-value, stale wind, TAI times, Zernikes, DIMM seeing, aos_fwhm). Includes access methods, schema traps and a portable query script.
---

# ConsDB (Consolidated Database)

## Access: pick by environment

| Method | Works on | How |
|---|---|---|
| `rubin_nights` FastAPI | RSP **and** SDF (needs an RSP token) | `from rubin_nights.connections import get_clients; c = get_clients(); df = c["consdb"].query(sql)` |
| `rubin_nights` TAP | RSP and SDF | `c["consdb_tap"].query(sql)` (ADQL subset; same tables) |
| `lsst.summit.utils.ConsDbClient` | in-cluster (RSP) | `ConsDbClient("http://consdb-pq.consdb:8080/consdb")` |
| Direct Postgres | SDF only | host `usdf-summitdb-logical-replica-svc.sdf.slac.stanford.edu`, db `exposurelog`, user `usdf`, password via `PGPASSFILE` |

- **Default to `get_clients()`** for code others will run: it works in both places. On 2026-11-11 the FastAPI, TAP, narrative-log, night-report and EFD clients all worked from an SDF node with a token in `~/.lsst/usdf_rsp`. Older notes claiming "the REST API gives 401 from SSH" were missing a token.
- Use direct Postgres on SDF for big pulls (no HTTP row limits, faster). Other hostnames (`usdf-summitdb.slac.stanford.edu`, `usdf-summitdb-replica*`) time out or don't resolve.
- The same replica also serves the `narrativelog` and `nightreport` databases with the **same `usdf` password**. A pgpass line is matched on the database name, so either use `*` in the database field (`host:5432:*:usdf:<pw>`) or add one line per database.
- Don't make code depend on a `CONSDB_HOST` environment variable without a default: nothing sets it, so you get a `KeyError`. Use `os.environ.get("CONSDB_HOST", "<replica host>")`.
- Legacy LATISS-only database (2023-11 to 2024-06): host `usdf-butler.slac.stanford.edu`, db `lsstdb1`, user `rubin`.
- Script: [`scripts/consdb_query.py`](scripts/consdb_query.py) `"SELECT ..." [-o out.parquet] [--pg]`.

## Schemas and tables

Schemas: `cdb_lsstcam`, `cdb_lsstcomcam`, `cdb_latiss`, `cdb_lsstcomcamsim`, `cdb_startrackerfast|narrow|wide`.

`cdb_lsstcam` tables:
- `exposure`: one row per exposure (`exposure_id`, `day_obs`, `seq_num`, `img_type`, `science_program`, `observation_reason`, `band`, `obs_start`/`obs_end`, `obs_start_mjd`, `exp_time`, `exp_midpt`, `s_ra`, `s_dec`, `altitude`, `azimuth`, `airmass`, `sky_rotation`, `zenith_distance_start/end`, `air_temp`, `pressure`, `humidity`, `wind_speed`, `wind_dir`, `dimm_seeing`, `focus_z`, `vignette`, `can_see_sky`, `scheduler_note`).
- `visit1`: one row per visit.
- `visit1_quicklook` (join `visit_id = exposure_id`): `psf_sigma_median`, `zero_point_median`, `eff_time`, `seeing_zenith_500nm_median`, Zernikes `z4`–`z28`, guider metrics, `aos_fwhm`, `donut_blur_fwhm`.
- `exposure_quicklook`: `mount_jitter_rms`, `mount_motion_image_degradation`.
- `ccdexposure`, `ccdexposure_camera`, `ccdexposure_quicklook`, `ccdvisit1` and `ccdvisit1_quicklook` (join `USING (ccdvisit_id)`): per-detector rows.
- `exposure_flexdata`, `ccdexposure_flexdata`: flexible key/value metadata.

**Column definitions** (units, time scales, descriptions) are in `sdm_schemas`: `python/lsst/sdm/schemas/cdb_lsstcam.yaml` in the stack (`$SDM_SCHEMAS_DIR` after `setup lsst_distrib`), or at https://sdm-schemas.lsst.io. Check there before guessing what a column means.

Column-name traps: in `cdb_lsstcam` it's `img_type = 'science'` (LATISS/old docs use `imgtype='OBJECT'`). Open-loop/wavefront blocks use `img_type = 'cwfs'`, so a `'science'` filter silently drops them. There is **no dome azimuth** column; get it from EFD `lsst.sal.MTDome.azimuth.positionActual`.

## Value traps (each one has produced a wrong result)

1. **`obs_start`/`obs_end` (and `*_mjd`) are TAI**, not UTC (sdm_schemas: "TAI, accurate to 10ms"). TAI − UTC = 37 s. Convert before joining to EFD (UTC) or quoting times. When someone gives "exposure started at hh:mm:ss" from ConsDB, assume TAI.
2. **Never trust a remembered data window.** Run `SELECT max(day_obs) FROM cdb_lsstcam.exposure WHERE img_type='science'` (or `visit1`). One stale note about "a survey pause" silently cut an analysis to 62 % of the available nights.
3. **`dimm_seeing` missing values are stored as `NaN`, not `NULL`**, so `count(dimm_seeing)` lies. Filter with `dimm_seeing <> 'NaN'::float8` and clip to (0.2, 3.0)″: raw values up to 40″ occur. Also check the DIMM is publishing at all; in late 2026 it had published nothing since 2026-07-14.
4. **`wind_speed` is a per-exposure summary that goes stale/held at high wind.** On 2026-05-26 it repeated one value (105 distinct values in 828 exposures) and reached 20.6 m/s, while a fresh 1-min EFD `ESS.airFlow` resample gave 18.9 m/s. The two agree overall (r ≈ 0.98) but diverge exactly in the tail that decides threshold or spec claims, so use the EFD for those.
5. **Zernikes `z4`–`z11` in `visit1_quicklook` were 100 % null for 2026-01-07 → 2026-07-01**, stored as the *string* `"None"` (dtype object). After `pd.to_numeric(errors="coerce")`, a pandas `.sum(axis=1)` over all-NaN rows returns **0.0**, which looks like real zero amplitude. Use `.sum(axis=1, min_count=1)` and gate on `.notna().sum()`.
6. `seeing_zenith_500nm_median` was 100 % null through 2026. `ccdvisit1_quicklook.pixel_scale` was NULL for every row in Nov 2026, so use the nominal 0.2″/pix.
7. **`aos_fwhm`** is the estimated *optical-system* contribution to FWHM from the measured Zernikes (z4–z28), in arcsec. It's model-derived and hasn't been validated in the FWHM domain. **`donut_blur_fwhm`** is the *atmospheric* term from donut forward modelling, **not** optics. The reference IQ decomposition is in `rubin_nights.rubin_scheduler_addons`: `idiq = sqrt(aos_fwhm² + 0.207²)` (camera term 0.207″), `atm = sqrt(fwhm_geom² − idiq²)`, wavelength ^0.2, airmass ^0.6.
8. The program label doesn't tell you what the hardware did. Some `BLOCK-T698/T703` AOS blocks actively dither hexapod focus by tens to hundreds of µm and others freeze M2. Check `lsst.sal.MTHexapod.application` demand ptp for the specific block before treating it as a passive stare.
9. Survey visits since survey start (2026-10-27) carry `science_program = 'BLOCK-407'`, `img_type = 'science'`. `observation_reason` separates `pairs_*`/`singles_*`/`triplet_*` (WFD-like) from `ddf_*` and `twilight_near_sun`.
10. Parsing times from the FastAPI: `pd.to_datetime(..., format="ISO8601")`.

## LSSTCam timeline (dated facts; re-check with a query)

- ConsDB LSSTCam science starts 2025-04-15.
- On-sky science ran through day_obs 2026-07-13 (2026-07-14 is calibrations only).
- The July 2026 storm and the scheduled downtime left no LSSTCam visits 2026-07-14 → 2026-10-26. Science resumed 2026-10-27.
