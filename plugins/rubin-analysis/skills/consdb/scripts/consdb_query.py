#!/usr/bin/env python3
"""Run one SQL query against ConsDB from SDF or the RSP.

Default path: rubin_nights FastAPI client (needs an RSP token: automatic on the
RSP, ~/.lsst/usdf_rsp or ACCESS_TOKEN[_FILE] elsewhere).
--tap   : use the ConsDB TAP service instead.
--pg    : direct PostgreSQL to the summitdb logical replica (SDF only; libpq
          reads the password from $PGPASSFILE, default ~/.lsst/postgres-credentials.txt).

Examples
  consdb_query.py "select max(day_obs) from cdb_lsstcam.visit1"
  consdb_query.py "select * from cdb_lsstcam.exposure where day_obs = 20261110" -o exp.parquet
"""
import argparse
import logging
import os
import sys
import warnings

import pandas as pd

PG_HOST = os.environ.get("CONSDB_HOST", "usdf-summitdb-logical-replica-svc.sdf.slac.stanford.edu")
PG_USER = os.environ.get("CONSDB_USER", "usdf")


def _pgpass_password(passfile: str, database: str) -> str | None:
    """Password for PG_HOST/PG_USER, preferring an exact database match.

    exposurelog, narrativelog and nightreport share one password on the
    replica, but a pgpass file often lists only one of them, so fall back to
    any entry for the same host and user. The value is never printed.
    """
    best = None
    try:
        with open(passfile) as f:
            for line in f:
                p = line.rstrip("\n").split(":")
                if len(p) >= 5 and p[0] == PG_HOST and p[3] == PG_USER:
                    if p[2] in (database, "*"):
                        return ":".join(p[4:])
                    best = best or ":".join(p[4:])
    except FileNotFoundError:
        pass
    return best


def query_pg(sql: str, database: str = "exposurelog") -> pd.DataFrame:
    import sqlalchemy

    passfile = os.environ.setdefault("PGPASSFILE", os.path.expanduser("~/.lsst/postgres-credentials.txt"))
    url = sqlalchemy.engine.URL.create(
        "postgresql", username=PG_USER, password=_pgpass_password(passfile, database),
        host=PG_HOST, port=5432, database=database,
    )
    return pd.read_sql(sql, sqlalchemy.create_engine(url))


def query_http(sql: str, tap: bool = False) -> pd.DataFrame:
    from rubin_nights.connections import get_clients

    clients = get_clients()
    return clients["consdb_tap" if tap else "consdb"].query(sql)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("sql")
    p.add_argument("-o", "--out", help="write .parquet or .csv instead of printing")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--pg", action="store_true", help="direct PostgreSQL (SDF only)")
    g.add_argument("--tap", action="store_true", help="ConsDB TAP instead of FastAPI")
    p.add_argument("--database", default="exposurelog", help="Postgres database for --pg")
    a = p.parse_args()

    warnings.filterwarnings("ignore")
    logging.disable(logging.WARNING)
    df = query_pg(a.sql, a.database) if a.pg else query_http(a.sql, a.tap)

    if a.out:
        (df.to_parquet if a.out.endswith(".parquet") else df.to_csv)(a.out)
        print(f"{len(df)} rows -> {a.out}", file=sys.stderr)
    else:
        with pd.option_context("display.max_rows", 200, "display.width", 250, "display.max_columns", 50):
            print(df)
    return 0


if __name__ == "__main__":
    sys.exit(main())
