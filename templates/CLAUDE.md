# Project notes for Claude: <repo name>

<!-- Starter for a Rubin analysis repo. Keep what applies, delete the rest.
     General Rubin knowledge comes from the rubin-analysis plugin skills;
     put only THIS repo's specifics here. -->

## Environment

- Runs on: <SDF interactive node over SSH | RSP (usdf-rsp) | both>
- Notebook kernel: `<kernel name>`. On SDF it must run EUPS setup (see the rubin-notebooks skill; create it with `make_sdf_kernel.sh`).
- Standalone scripts that import `lsst.*` on SDF:
  `bash -c 'source /sdf/group/rubin/sw/loadLSST.bash; setup lsst_distrib; python3 script.py'`
- Data/caches go to `/sdf/data/rubin/user/$USER/<project>/` (not the repo, not `/tmp`).

## Repo rules

- Never commit data, caches or figures. Only code, notebooks (outputs stripped) and READMEs.
- Pre-commit hooks: <nbstripout / black-jupyter / none>. The first commit attempt may fail while the hooks rewrite files; re-add and commit.
- Default branch: `main`. Ask before pushing.

## Project specifics

- Data window: <day_obs range>. Re-check with `max(day_obs)` before quoting results.
- Key notebooks and their run order: <...>
- Builder scripts that write caches: <script → output>
- Conventions (names, units, plot orientation): <...>
