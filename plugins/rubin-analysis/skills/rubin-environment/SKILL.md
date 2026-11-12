---
name: rubin-environment
description: Use at the start of any Rubin/LSST data task on USDF (SDF login/interactive nodes over SSH) or the Rubin Science Platform (RSP/Nublado), to work out where you are running, which LSST stack/kernel to use, how authentication works (RSP token, pgpass), where to write files, and which resource limits actually apply. Also covers getting `gh` from the stack and long-running/batch jobs on S3DF.
---

# Rubin analysis environment: SDF vs RSP

Rubin analysis happens in two places, and most failures come from assuming the wrong one.

## 1. Work out where you are

| Check | RSP / Nublado pod | SDF interactive node (SSH) |
|---|---|---|
| `echo $EXTERNAL_INSTANCE_URL` | set, e.g. `https://usdf-rsp.slac.stanford.edu` | empty |
| `/opt/lsst/software/jupyterlab` | exists | absent |
| `nproc`, `free -g` | ~4 cores / ~16 GB ("Large" pod) | 100+ cores / ~500 GB (`sdfiana*`) |
| LSST stack | already set up in the LSST kernel | must be set up with EUPS (below) |
| Direct Postgres (ConsDB, logs) | not reachable; use HTTP APIs | reachable with a pgpass file |

`rubin_nights.connections.get_clients()` uses the same rule: it picks the site from `EXTERNAL_INSTANCE_URL` and falls back to `usdf` outside the RSP.

## 2. LSST stack

- **RSP:** use the default LSST kernel. `lsst.*`, `lsst_efd_client`, `rubin_nights` and `lsst.summit.utils` are already importable.
- **SDF:** the stack lives in `/sdf/group/rubin/sw/`. A bare conda python such as `/sdf/group/rubin/sw/conda/envs/lsst-scipipe-*/bin/python3` has pandas, `lsst_efd_client` and `rubin_nights`. It does **not** have the EUPS products, so it fails with `No module named 'lsst.daf.butler'`, `lsst.sphgeom` or `lsst.summit.utils`. For those, run inside a setup:

  ```bash
  bash -c 'source /sdf/group/rubin/sw/loadLSST.bash; setup lsst_distrib; setup summit_utils; python3 script.py'
  ```

  Pin the env with `export LSST_CONDA_ENV_NAME=lsst-scipipe-<ver>` before sourcing. Don't trust a remembered version: list `/sdf/group/rubin/sw/conda/envs/` and check which `loadLSST.bash` defaults to. (In Nov 2026 it was `lsst-scipipe-14.0.0`, w_2026_45.)
- **Jupyter on SDF:** a kernel that only `exec`s the conda python has the same missing-module problem. Make a kernel whose launcher script sources `loadLSST.bash` and runs `setup lsst_distrib` before `exec python -m ipykernel_launcher "$@"`. Templates are in [`../rubin-notebooks/SKILL.md`](../rubin-notebooks/SKILL.md).
- **Building or testing Science Pipelines packages** (`pytest`, `scons`, `pipetask` against a weekly): use the `lsst-eups` skill from **https://github.com/lsst-dm/agent-skills** (Tim Jenness, DM). Install it with that repo's `install.sh --claude`. This plugin doesn't duplicate it.
- A stale `.env` in a repo (for example a full `env` dump from an older stack) can be injected by VS Code into kernels and break the PATH/PYTHONPATH of a newer stack. Keep `.env` files to the few variables you need.

## 3. Authentication. Never read, print or copy secret files.

- **RSP token.** This one token covers the HTTP services: ConsDB FastAPI/TAP, narrative log, exposure log, night report and the EFD through Sasquatch.
  - On the RSP it comes from `lsst.rsp.get_access_token()` automatically.
  - On SDF, create a token at the USDF RSP (see https://rsp.lsst.io/v/usdfprod/guides/auth/creating-user-tokens.html), save it as `~/.lsst/usdf_rsp`, and `chmod 600` it. `rubin_nights.get_clients()` finds it there, or through `ACCESS_TOKEN` / `ACCESS_TOKEN_FILE`.
  - Tokens are site-specific: a `usdf-rsp` token doesn't work on `usdf-rsp-dev`.
- **Postgres (SDF only).** Use a pgpass-format file, e.g. `~/.lsst/postgres-credentials.txt`, and point `PGPASSFILE` at it so libpq reads it. If the file has no entry for the database you're opening, you get `fe_sendauth: no password supplied`; `FATAL: no such user` means `PGUSER` is unset (it defaults to your login).
- **S3 / LFA.** Use an AWS-style credentials file, e.g. `~/.lsst/aws-credentials.ini`, via `AWS_SHARED_CREDENTIALS_FILE`, with a named profile. See the butler-and-archives skill.
- Let libraries read credential files. Don't `cat`, `grep` or echo them, and never paste their contents into code, notebooks, commits or chat.
- **GitHub CLI on SDF.** `gh` isn't on the default PATH, but it ships in the stack env (`.../envs/lsst-scipipe-*/bin/gh`). Run `source /sdf/group/rubin/sw/loadLSST.bash` in the **same** shell call, then `gh ...`. Don't pull tokens out of git credential stores.

## 4. Where to write files

| Location | Size / behaviour | Use for |
|---|---|---|
| `/sdf/home/<u>/<user>` | ~30 GB quota; fills fast | code, small configs |
| `/sdf/data/rubin/user/$USER` | large, shared, persistent | caches, products, scratch (`.../tmp/<task>/`) |
| `/sdf/scratch/users/<u>/$USER` | ~100 GB, **purged weekly** | regenerable caches only |
| `/tmp` | **node-local**, reaped | nothing you want to see from another node or Jupyter session |
| RSP home | 35 GB quota | same rules; RSP scratch is purged |

Never commit regenerable data, parquet caches or figures to git (see the rubin-notebooks skill).

## 5. Which limits actually bind

| Limit | RSP pod | SDF node |
|---|---|---|
| CPU/RAM (4 cores / 16 GB "Large") | **yes** | no |
| Portal query rows (10k default / 5M hard) | Portal only | no (direct SQL/TAP unaffected) |
| Butler query results (20k default warning) | yes | yes, so constrain by tract/region or page; don't silently truncate |
| API rate (≈500 requests / 15 min per user: TAP, Datalinker) | yes | **yes** (server-side) |
| EFD transfer / InfluxDB bucket limits | yes | yes, so chunk queries (see the efd skill) |

So on SDF, CPU isn't the constraint: don't shrink thread pools to 4. The API rate is: batch server-side with `GROUP BY` instead of making one request per object.

## 6. Long jobs on SDF

- For anything longer than a few minutes, detach with `setsid nohup python3 script.py > log 2>&1 &` and save the PID. Then an interrupted session doesn't kill it.
- Batch: Slurm on S3DF (e.g. `--partition milano` with your Rubin account, such as `rubin:commissioning` if you have it).
- `pkill -f <pattern>` / `pgrep -f` run from a shell tool also match **that shell's own command line** and kill it. Kill by saved PID instead.
- `python3 -P` drops the script's directory from `sys.path`, which breaks sibling imports. `-E` is usually enough to ignore a stray `PYTHONPATH`.
