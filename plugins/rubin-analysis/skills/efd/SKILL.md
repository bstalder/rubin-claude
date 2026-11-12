---
name: efd
description: Use when pulling Rubin Engineering and Facility Database (EFD / Sasquatch InfluxDB) telemetry or events — lsst.sal.* topics for ESS weather/dew point/turbulence, MTDome, MTMount, MTM1M3, MTM2, MTHexapod, Scheduler observatoryStatus, Watcher alarms — from SDF or the RSP. Covers the two clients, chunking for high-rate topics and InfluxDB bucket limits, InfluxQL quirks, time scales, and a catalog of verified topic/field/index names.
---

# EFD (Engineering and Facility Database)

## Clients

Both work on the RSP and on SDF.

```python
# 1. lsst_efd_client (async). Inside Jupyter use `await`; in scripts use asyncio.run().
from lsst_efd_client import EfdClient
client = EfdClient("usdf_efd")                    # db_name="lsst.obsenv" etc. for other DBs
df = await client.select_time_series("lsst.sal.ESS.airFlow", ["speed", "direction"],
                                     t_start, t_end, index=301)   # astropy Time
df = await client.influxql_query('SELECT ... FROM "efd"."autogen"."lsst.sal.X" WHERE ...')

# 2. rubin_nights (sync, token-based, same object get_clients() returns)
from rubin_nights.connections import get_clients
efd = get_clients()["efd"]
df = efd.select_time_series("lsst.sal.ESS.airFlow", ["speed"], t_start, t_end, index=301)
df = efd.query("SELECT mean(speed) FROM ... GROUP BY time(1m)")
```

- `index=` is the SAL index (`salIndex`). Many topics are multi-instance (ESS sensors, MTHexapod 1 = camera / 2 = M2, Scheduler 1 = Simonyi).
- **Results are UTC** (tz-aware index). ConsDB `obs_start` is **TAI** (+37 s). Convert before joining.
- **`get_schema()` fails from SDF** (`Cannot connect to host sasquatch-schema-registry.sasquatch:8081`). To discover fields, use `get_fields(topic)` or run `select_time_series(topic, "*", …)` on a 5-minute window.
- The rubin_nights client can log "EFD service not available from USDF" and fall back to an empty client. If that happens, use `EfdClient("usdf_efd")` directly.

## Volume and chunking

- **High-rate topics:** daily-chunk them and cache to parquet. `MTM1M3.imsData` and `MTM1M3.hardpointActuatorData` are ~50 Hz; two weeks is ~50–60 M rows per topic.
- **Wide topics:** `MTM1M3TS.thermalData` has 96 columns at ~2 Hz and hits transfer limits over multi-week windows. Chunk by day and concatenate.
- **InfluxDB max-select-buckets is 20 000.** `GROUP BY time(1m)` over more than ~14 days fails, so chunk 10 days. For 1-s aggregates, chunk 3 h.
- **Long multi-day fetches:** in a notebook they time out or hang the kernel. Use a standalone script with `asyncio.run()` that writes parquet, then load the parquet in the notebook.
- **Parquet:** `df.to_parquet` throws `ArrowNotImplementedError` on interval/categorical columns (e.g. `pd.cut` output). Stringify them first.

## InfluxQL traps

- A field called `name` (Watcher alarms) collides with the keyword. Quote and alias it: `SELECT "name" AS alarm_name …`. Unquoted it returns the measurement name or gives a 400. `select_time_series` with `"name"` in the field list errors with "found NAME".
- Regex filters match substrings: an alarm regex `ess` also matches "Pr**ess**ure". Anchor it.
- **EFD state gaps:** don't carry the last state forward across long gaps. For example, `Scheduler.logevent_observatoryStatus` has a 67.6-day gap 2026-07-20 → 2026-09-25. Treat gaps longer than about a day as *uncovered*.
- Intervals reconstructed from open/close events (e.g. a dome-open helper) can leave a NaN close time that runs to the end of the range and wrongly marks whole nights as open. For dome-open state, use the continuous `MTDome.apertureShutter.positionActual0 > 5 %`.

## Topic catalog

See [references/topics.md](references/topics.md) for verified topic, field and index names: weather tower, dew point, glass thermocouples, turbulence, dust, dome, mount encoder heads, M1M3, M2, hexapods, AOS, Scheduler state bits and Watcher thresholds. Data sources often stop publishing, so check the last sample before you rely on one: the DIMM stopped on 2026-07-14 10:46 UTC and RINGSS on 2026-06-15, as of Nov 2026.
