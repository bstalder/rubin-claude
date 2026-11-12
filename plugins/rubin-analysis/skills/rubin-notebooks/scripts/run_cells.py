#!/usr/bin/env python3
"""Execute a notebook, or just selected cells, with nbclient and write outputs back.

  run_cells.py NB                         run every cell
  run_cells.py NB 0 2 5-9                 run only these cells (0-based, ranges ok), in order
  run_cells.py NB --kernel lsst-scipipe-14.0.0 --timeout 900
  run_cells.py NB --copy out.ipynb        write the executed notebook elsewhere

Running a subset builds a mini-notebook from those cells only. Include the
import/parameter cells the targets depend on. The working directory is the
notebook's directory. Needs nbformat + nbclient (present in the LSST envs).

Kernel: on the RSP use the LSST kernel name shown by `jupyter kernelspec list`.
On SDF use a kernel whose launcher runs EUPS setup (see the rubin-notebooks skill).
"""
import argparse
import asyncio
import os
import sys

import nbformat
from nbclient import NotebookClient


def parse_indices(tokens, n):
    out = []
    for t in tokens:
        if "-" in t:
            a, b = t.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(t))
    bad = [i for i in out if not 0 <= i < n]
    if bad:
        sys.exit(f"cell indices out of range: {bad} (notebook has {n} cells)")
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("notebook")
    p.add_argument("cells", nargs="*")
    p.add_argument("--kernel", default=os.environ.get("RUBIN_KERNEL"))
    p.add_argument("--timeout", type=int, default=600, help="per-cell timeout in seconds")
    p.add_argument("--copy", help="write result here instead of in place")
    p.add_argument("--allow-errors", action="store_true")
    a = p.parse_args()

    nb = nbformat.read(a.notebook, as_version=4)
    kernel = a.kernel or nb.metadata.get("kernelspec", {}).get("name")
    idx = parse_indices(a.cells, len(nb.cells)) if a.cells else list(range(len(nb.cells)))

    mini = nbformat.v4.new_notebook()
    mini.metadata = nb.metadata.copy()
    mini.cells = [nb.cells[i] for i in idx]
    client = NotebookClient(
        mini, timeout=a.timeout, kernel_name=kernel, allow_errors=a.allow_errors,
        startup_timeout=300,  # EUPS setup + first lsst import can take minutes on a cold cache
        resources={"metadata": {"path": os.path.dirname(os.path.abspath(a.notebook))}},
    )
    err = None
    try:
        asyncio.run(client.async_execute())
    except Exception as e:  # keep partial outputs
        err = e
    for i, c in zip(idx, mini.cells):  # same objects, order preserved
        nb.cells[i] = c
    nbformat.write(nb, a.copy or a.notebook)
    print(f"ran {len(idx)} cells with kernel {kernel!r} -> {a.copy or a.notebook}")
    if err:
        print(f"stopped on error: {type(err).__name__}: {str(err)[:2000]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
