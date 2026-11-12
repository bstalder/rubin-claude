---
name: observing-logs
description: Use when the question is "what happened on night X" or "was Y mentioned in the logs" for Rubin Observatory — searching the narrative log, night report or exposure log, reading time-lost/fault/weather entries, attributing time loss, converting day_obs to UTC/Chile time, or reading ROSP/OBS Jira tickets anonymously. Works on SDF and the RSP.
---

# Observing logs: narrative log, night report, exposure log

## Quick answer: search a night

```bash
python3 scripts/log_search.py 20261110 -r 'louv|pneum' --night-report
python3 scripts/log_search.py 20261101 20261110 --time-lost
python3 scripts/log_search.py 20261110 --by-added -r dome   # entries written after the fact
```

The script is in this skill's `scripts/` directory. It needs any python with `rubin_nights` (the stack env on SDF, or the LSST kernel on the RSP) plus an RSP token (automatic on the RSP; `~/.lsst/usdf_rsp` on SDF).

When you report results, say what you searched: the date range, whether you selected on `date_begin` or `date_added`, the regex, and how many entries were searched. A null result is only meaningful with that context. Also check the night report: daytime work (e.g. louver or LWS tests) is often only in the night report's "Daytime" section, not in the narrative log.

## Time conventions

- **day_obs N** runs from N 12:00 UTC to N+1 12:00 UTC.
- Chile is UTC−3 in summer (roughly Sep–Apr) and UTC−4 in winter. "Yesterday" from a user in Chile is usually the previous day_obs.
- Log timestamps are UTC. ConsDB `obs_start` is **TAI** (UTC + 37 s).

## Clients

```python
from rubin_nights.connections import get_clients
c = get_clients()
nl = c["narrative_log"].query_log(t_start, t_end)        # astropy Times; selects on date_begin
nr_list = c["night_report"].query_night_report(day_obs)[0]
el = c["exposure_log"].query_log(t_start, t_end)
```

- Narrative-log columns: `id, date_begin, date_end, date_added, message_text, user_id, is_human, is_valid, time_lost, time_lost_type, category, components, components_json, systems, subsystems, cscs, primary_software_components, primary_hardware_components, urls, tags, level, parent_id`.
- Night-report fields: `day_obs, summary, weather, maintel_summary, auxtel_summary, observers_crew, date_sent, confluence_url, is_valid, parent_id`.

**Direct Postgres (SDF only):** use the summitdb logical replica, databases `narrativelog` (table `message`) and `nightreport` (table `nightreport`), same user and password as ConsDB (see the consdb skill). `consdb/scripts/consdb_query.py --pg --database narrativelog "<sql>"` works.

## Traps

1. **`time_lost` units differ by access path.** The REST API returns float **hours**. In Postgres it's an `interval` whose **seconds field holds hours** (`00:00:06.57` = 6.57 h), so `extract(epoch from time_lost)` gives hours, not seconds.
2. `time_lost_type ∈ {fault, weather}`. Narrative-log time-lost entries capture only ~20 % of Simonyi weather hours (many are AuxTel), so they aren't usable for time accounting on their own. For state, use EFD `Scheduler.logevent_observatoryStatus` (see the efd skill).
3. `date_begin` ≠ `date_added`. Operators often log events hours later or backdate them. Search by both when completeness matters.
4. **Night-report formats:** rows with `telescope IS NULL` are the unified format (2025-06-26 onward, with `weather`, `maintel_summary`); `telescope = 'Simonyi'` rows cover 2024-06 → 2025-06. Filter `is_valid`.
5. Gaps exist: e.g. zero narrative-log entries 2026-09-10 → 09-18 during the storm-recovery/downtime period. Absence of entries isn't absence of activity.
6. Domain rule for time-loss attribution: a freezing night (likely snow or icing) keeps the dome closed until an icing inspection is done. Charge the whole night to WEATHER, even if the sky clears later. Mid-July → 1 Sep 2026 (storm) counts as catastrophe/weather downtime, not fault. Curated overrides live in the `lsst/sp_notebooks` repo (`tracking_hub/ops/observatory_state_overrides/`, with a `category` column), referenced from the ROSP Jira tickets.

## Jira (read-only, no credentials)

Some Jira projects on `rubinobs.atlassian.net` allow anonymous read. Others don't: as of 2026-11-11, ROSP was readable and OBS was not ("Issue does not exist or you do not have permission").

```bash
curl -s "https://rubinobs.atlassian.net/rest/api/2/issue/ROSP-24?fields=summary,description,status"
curl -s "https://rubinobs.atlassian.net/rest/api/2/issue/ROSP-24/comment"
```

Descriptions come back in wiki markup. For non-public projects, or for commenting and editing, ask the user: they need their own Atlassian account or connector.
