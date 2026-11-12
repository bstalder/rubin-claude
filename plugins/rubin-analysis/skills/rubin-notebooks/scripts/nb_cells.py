#!/usr/bin/env python3
"""Inspect and edit Jupyter notebooks that are too large for an editor tool.

  nb_cells.py list NB [--width 120]          index, type, first line of every cell
  nb_cells.py show NB N [N ...]              full source of cells N
  nb_cells.py grep NB REGEX                  cells whose source matches
  nb_cells.py set  NB N FILE                 replace cell N source with FILE ('-' = stdin);
                                             clears its outputs/execution_count
  nb_cells.py insert NB N FILE [--markdown]  insert a new cell after N (-1 = at top)
  nb_cells.py strip NB                       remove all outputs (like nbstripout)

Only the standard library is used, so any python3 works.
"""
import json
import re
import sys
import uuid


def load(path):
    with open(path) as f:
        return json.load(f)


def save(nb, path):
    with open(path, "w") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")


def src(cell):
    s = cell.get("source", "")
    return "".join(s) if isinstance(s, list) else s


def read_text(arg):
    return sys.stdin.read() if arg == "-" else open(arg).read()


def new_cell(text, markdown=False):
    c = {"cell_type": "markdown" if markdown else "code", "id": uuid.uuid4().hex[:8],
         "metadata": {}, "source": text}
    if not markdown:
        c.update(outputs=[], execution_count=None)
    return c


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, path, rest = argv[1], argv[2], argv[3:]
    nb = load(path)
    cells = nb["cells"]
    if cmd == "list":
        w = int(rest[rest.index("--width") + 1]) if "--width" in rest else 120
        for i, c in enumerate(cells):
            first = src(c).strip().replace("\n", " ⏎ ")[:w]
            print(f"[{i}] {c['cell_type'][:4]}: {first}")
    elif cmd == "show":
        for n in map(int, rest):
            print(f"===== [{n}] {cells[n]['cell_type']} id={cells[n].get('id')}\n{src(cells[n])}")
    elif cmd == "grep":
        rx = re.compile(rest[0])
        for i, c in enumerate(cells):
            for ln in src(c).splitlines():
                if rx.search(ln):
                    print(f"[{i}] {ln}")
    elif cmd == "set":
        n = int(rest[0])
        cells[n]["source"] = read_text(rest[1])
        if cells[n]["cell_type"] == "code":
            cells[n]["outputs"], cells[n]["execution_count"] = [], None
        save(nb, path)
    elif cmd == "insert":
        n = int(rest[0])
        cells.insert(n + 1, new_cell(read_text(rest[1]), "--markdown" in rest))
        save(nb, path)
    elif cmd == "strip":
        for c in cells:
            if c["cell_type"] == "code":
                c["outputs"], c["execution_count"] = [], None
        save(nb, path)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
