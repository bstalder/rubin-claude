---
name: rubin-notebooks
description: Use when reading, editing, executing or committing Jupyter notebooks for Rubin analysis on SDF or the RSP — especially large notebooks (>256 KB) that editor tools refuse, running a subset of cells headlessly with nbclient and the right LSST kernel, long EFD fetches that hang kernels, and repos with nbstripout/black-jupyter pre-commit hooks or a no-data-in-git rule.
---

# Rubin notebooks: edit, run, commit

## Reading and editing large notebooks

Analysis notebooks often exceed the size an editor tool will read, and notebook-edit tools usually require a prior full read. Work on the JSON directly with the helper ([`scripts/nb_cells.py`](scripts/nb_cells.py), standard library only):

```bash
python3 scripts/nb_cells.py list  NB.ipynb            # index + first line of each cell
python3 scripts/nb_cells.py show  NB.ipynb 12 13      # full source
python3 scripts/nb_cells.py grep  NB.ipynb 'select_time_series'
python3 scripts/nb_cells.py set   NB.ipynb 12 new_cell.py   # or '-' for stdin; clears outputs
python3 scripts/nb_cells.py insert NB.ipynb 12 text.md --markdown
```

`jq` works too: `jq '.cells[12].source | join("")' NB.ipynb`. Cell `source` is a **list of strings** in the JSON; join it before regex work. Writing back a single string is valid.

## Running cells headlessly

[`scripts/run_cells.py`](scripts/run_cells.py) runs all cells, or a chosen subset, via nbclient and writes the outputs back:

```bash
python3 scripts/run_cells.py NB.ipynb 0-3 17 18 --kernel <kernel-name> --timeout 900
```

- Include the import and parameter cells the targets depend on. The working directory is the notebook's directory.
- **Kernel choice:**
  - RSP: the LSST kernel (`jupyter kernelspec list`).
  - SDF: a kernel whose launcher runs EUPS setup. Create one with [`scripts/make_sdf_kernel.sh`](scripts/make_sdf_kernel.sh) (writes `~/.local/kernel-launchers/<env>.sh` + kernelspec). The plain `python3` kernel or a bare-conda kernel can't import `lsst.daf.butler`, `lsst.sphgeom` or `lsst.summit.utils`. The first start after setup can take minutes.
- On SDF `jupyter` isn't on PATH; use the stack env's binaries: `/sdf/group/rubin/sw/conda/envs/lsst-scipipe-<ver>/bin/{python3,jupyter}`.
- **Long EFD/ConsDB pulls** (multi-day, high-rate or wide topics) time out in nbclient or hang the kernel. Move them into a standalone builder script (`asyncio.run(...)`, chunked by day) that writes parquet, and have the notebook read the parquet.
- Scheduled CI that runs notebooks with `day_obs = today` (e.g. Times Square) fails during data gaps (no visits → `KeyError`). Pin the window when verifying, and make notebooks exit cleanly on zero rows.

## Committing

- **Never commit data products, tables (csv/json results), caches (parquet/npy) or figures (png/mp4/pdf).** Commit code, notebooks and READMEs; keep products on `/sdf/data/rubin/user/$USER/...` or in a gitignored `data/` dir. Dry-run with `git add -n` before committing.
- Many Rubin repos (e.g. `lsst/sp_notebooks`) run **nbstripout + black-jupyter** pre-commit hooks:
  - The first commit attempt fails while the hooks rewrite the files. Re-`git add` and commit again.
  - The hooks **strip outputs in your working tree**, so copy executed notebooks aside first if you need their outputs.
  - If the only change is in outputs, there's nothing to commit after stripping. Don't report "committed re-executed notebook".
  - black-jupyter can't parse nested same-quote f-strings (`f"{d["k"]}"`); use `'` inside.
  - A fresh clone has no hook: run `pre-commit install --install-hooks` (pre-commit is in the stack env).
- Chain commands as `git commit ... && git push`, not with `;`. A failed commit followed by `; git push` pushes older unpushed commits.
- Never paste tokens, passwords or credential-file contents into notebooks. Notebook outputs get committed and shared.

## Notebook code habits that prevented bugs

- Parameter-cell names leak into later cells: re-running a later cell after changing a parameter silently uses stale globals. Keep derived quantities in functions, and restart-and-run-all before quoting numbers.
- Compute interpretation text from the results (f-strings) instead of hard-coding numbers in markdown that go stale on re-run.
- Keep a dated backup copy before restructuring a notebook (`cp NB.ipynb /sdf/data/rubin/user/$USER/tmp/NB_backup_YYYYMMDD.ipynb`).
