#!/usr/bin/env python3
"""Search the Rubin narrative log (and optionally the night report) by day_obs and regex.

Works on the RSP and on SDF (rubin_nights + RSP token). day_obs N covers
N 12:00 UTC -> N+1 12:00 UTC.

Examples
  log_search.py 20261110 -r 'louv|pneum'
  log_search.py 20261101 20261110 -r 'dome' --night-report
  log_search.py 20261110 --time-lost            # only entries with time_lost > 0
  log_search.py 20261110 --by-added             # also catch entries added late
"""
import argparse
import logging
import re
import sys
import warnings

import pandas as pd
from astropy.time import Time, TimeDelta


def dayobs_to_utc(day_obs: int) -> Time:
    s = str(day_obs)
    return Time(f"{s[:4]}-{s[4:6]}-{s[6:]}T12:00:00", scale="utc")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("day_obs_start", type=int)
    p.add_argument("day_obs_end", type=int, nargs="?", help="inclusive; default = start")
    p.add_argument("-r", "--regex", help="case-insensitive regex on message_text")
    p.add_argument("--time-lost", action="store_true", help="only entries with time_lost > 0")
    p.add_argument("--by-added", action="store_true",
                   help="select on date_added instead of date_begin (entries logged after the fact)")
    p.add_argument("--night-report", action="store_true", help="also print night reports")
    p.add_argument("-o", "--out", help="write matching narrative-log rows to csv/parquet")
    a = p.parse_args()

    warnings.filterwarnings("ignore")
    logging.disable(logging.WARNING)
    from rubin_nights.connections import get_clients

    c = get_clients()
    d1 = a.day_obs_end or a.day_obs_start
    t0, t1 = dayobs_to_utc(a.day_obs_start), dayobs_to_utc(d1) + TimeDelta(1, format="jd")

    if a.by_added:
        # widen the date_begin window, then filter on date_added
        df = c["narrative_log"].query_log(t0 - TimeDelta(30, format="jd"), t1 + TimeDelta(30, format="jd"))
        added = pd.to_datetime(df["date_added"], utc=True)
        df = df[(added >= t0.datetime.isoformat() + "+00:00") & (added < t1.datetime.isoformat() + "+00:00")]
    else:
        df = c["narrative_log"].query_log(t0, t1)
    n_all = len(df)
    if a.regex and n_all:
        df = df[df["message_text"].str.contains(a.regex, flags=re.I, regex=True, na=False)]
    if a.time_lost and len(df):
        df = df[df["time_lost"].astype(float) > 0]  # REST API returns float HOURS

    print(f"# narrative log {a.day_obs_start}..{d1}: {len(df)} of {n_all} entries match")
    for _, r in df.iterrows():
        tl = f" | time_lost {float(r['time_lost']):.2f} h ({r['time_lost_type']})" if float(r["time_lost"] or 0) > 0 else ""
        comp = r.get("components") or r.get("component") or ""
        print(f"\n--- begin {r['date_begin']} | added {r['date_added']} | {r['user_id']} | {comp}{tl}")
        print(str(r["message_text"]).strip())
    if a.out and len(df):
        (df.to_parquet if a.out.endswith(".parquet") else df.to_csv)(a.out)

    if a.night_report:
        days = pd.date_range(str(a.day_obs_start), str(d1), freq="D")
        for d in (int(x.strftime("%Y%m%d")) for x in days):
            try:
                reports = c["night_report"].query_night_report(d)[0]
            except Exception as e:  # noqa: BLE001
                print(f"\n# night report {d}: error {e}")
                continue
            for nr in reports:
                txt = "\n".join(str(nr.get(k) or "") for k in ("summary", "weather", "maintel_summary"))
                if a.regex and not re.search(a.regex, txt, re.I):
                    continue
                print(f"\n=== night report {nr.get('day_obs')} (sent {nr.get('date_sent')})\n{txt.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
