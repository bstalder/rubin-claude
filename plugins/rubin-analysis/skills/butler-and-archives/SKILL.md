---
name: butler-and-archives
description: Use when locating Rubin image/catalog data or raw archives at USDF — Butler repos (main, embargo, DP2 / dp2_prep), the Large File Annex (LFA) S3 bucket, the alert archive, the summit all-sky camera (allskycam) archive, DREAM cloud maps, rubin_sim / scheduler simulation databases, and external catalogs via NOIRLab Astro Data Lab — including the environment variables and credential setup each needs and their known traps.
---

# Butler repos and data archives at USDF

## Butler

- The repo index is `/sdf/group/rubin/shared/data-repos.yaml`. Aliases include `main`, `embargo`, `embargo_readonly`, `solarsystem`, `bts`, `tts` and others.
- On the RSP and in a set-up stack this is configured already. From a plain python, or when `Butler("main")` says "No repository index defined", set:

  ```bash
  export DAF_BUTLER_REPOSITORY_INDEX=/sdf/group/rubin/shared/data-repos.yaml
  export PGUSER=rubin
  export PGPASSFILE=~/.lsst/postgres-credentials.txt      # your pgpass file
  ```

  Symptoms when these are missing: `FATAL: no such user` (PGUSER defaulted to your login) or `fe_sendauth: no password supplied`.
- **Embargo repo:** also needs `AWS_SHARED_CREDENTIALS_FILE=~/.lsst/aws-credentials.ini` and `S3_ENDPOINT_URL=https://sdfembs3.sdf.slac.stanford.edu`. Use the alias `embargo`, not `embargo_readonly`, unless your pgpass has an entry for the read-only host. After April 2026 the embargo butler held only ISR runs under `LSSTCam/prompt/output-2026-04-08`.
- **DP2:**
  - Visit-level images (`preliminary_visit_image`) are in `/sdf/group/rubin/repo/dp2_prep`, collection `LSSTCam/runs/DRP/DP2`.
  - The production `/sdf/group/rubin/repo/dp2` is trimmed: coadds, catalogs and `visit_summary`, **no visit images**.
  - DP2 `deep_coadd` is on skymap `lsst_cells_v2` (197 105 patches, about 10× the Butler 20k default result limit). Constrain by tract or region, or you'll silently truncate.
- `butler.get("skyMap", …)` needs `lsst.skymap`. If you only need geometry, `butler.query_dimension_records("patch", …)` plus `rec.region.getCentroid()` needs only `lsst.sphgeom`.

## Large File Annex (LFA)

- The summit LFA bucket is `s3://rubinobs-lfa-cp/`, reachable from SDF via the endpoint `https://s3dfrgw.slac.stanford.edu/`. It needs a named profile (e.g. `lfa`) in your AWS credentials file. The `default` profile can't necessarily see this bucket, so check which profile your credentials grant.
- `rubin_nights.connections.usdf_lfa(uri)` converts an LFA URI recorded in the EFD into a USDF-accessible one. `get_clients()` also sets `S3_ENDPOINT_URL` and `LSST_DISABLE_BUCKET_VALIDATION=1` for USDF.
- Contents include `AllSkyCamera/YYYY/MM/DD/` (2024-02 →) and the DREAM cloud maps (NSIDE-32 HEALPix; `.gz` companions hold the same table as the FITS: `nobs, clouds, sigma, mask_visible, flags, *_cleaned`).

## Allskycam (summit all-sky camera)

- Call it **"allskycam"** in prose, labels and column names. Bare "camera" in a Rubin notebook reads as LSSTCam.
- Disk archive `/sdf/data/rubin/offline/allsky/storage/utYYMMDD/` covers 2021-07-10 → 2024-02-26; the LFA covers 2024-02 onward.
- Frames are 1 per minute; seq 0001 = 12:00 UTC of the day_obs; EXIF times are UTC.
- **Use the CR2 raws, not the JPEGs:** JPEG sky is quantized to ~5 DN, which is useless for photometry. Decode with `rawpy`.
- A reduction pipeline (astrometry, star-completeness cloud index, deep index) is maintained in the GitHub repo `bstalder/rubin_allskycam`. Use its products rather than re-reducing.
- DREAM `clouds` is extinction in **mag**: "cloudy" ≈ median extinction above 30° altitude > 0.5 mag. The 0.1 mag level is inside DREAM's zero-point floor. DREAM reads ~0.75× LSSTCam-measured extinction and saturates on broken cloud.

## Alert archive

- Path: `/sdf/group/rubin/shared/alert-archive/v2/alerts/<6-digit id prefix>/<diaSourceId>.avro.gz`. The format is Avro, Confluent wire format, with schemas in `v2/schemas/<id>.json`.
- Each prefix directory is about one night. Coverage is patchy: Feb 16 → Jul 13 2026, then Oct 29 2026 onward.
- `diaSourceId` bit layout: `detector = (id >> 19) & 0xFF`; `id >> 27 = 1267236864 + 32768 × (days since 2026-03-03) + seq_num`.
- Listing every directory takes ~10 min, so cache the listing.

## Simulations and site models

- `rubin_sim` data: `/sdf/data/rubin/shared/rubin_sim_data` (`RUBIN_SIM_DATA_DIR`).
- Scheduler sims: `/sdf/data/rubin/shared/fbs_sims/sims_featureScheduler_runs*/`. **Baseline databases can be regenerated in place under the same file name** (this happened to `baseline_v5.3.7_10yrs.db` on 2026-10-31). Record a SHA-256 of any sim db your results depend on, or copy it to a frozen location.

## External catalogs: NOIRLab Astro Data Lab (from USDF)

- TAP sync `https://datalab.noirlab.edu/tap/sync` and SIA `https://datalab.noirlab.edu/sia/<collection>` work without a token. The `dl` client isn't installed; use `requests`/`pyvo`.
- **Request `FORMAT=csv`, not VOTable.** pyvo's VOTable path silently truncated computed float columns to integers (an `AVG()` came back as `2`).
- `ls_dr10.bricks_s.psfdepth_*` sentinels differ by band: 0.0 in g/r/z but **+inf in i**. Test finite AND sane range AND `nexp_<band> > 0`.
- DELVE DR2 serves no images (catalog only). `ivoa_des_dr2.siav1` `fwhm`/`seeing` columns are all zeros. SIA band column is `obs_bandpass`. DES tile corners can wrap RA = 0.
- Mind the ~500 requests / 15 min API cap: batch server-side with `GROUP BY` HEALPix pixel.
