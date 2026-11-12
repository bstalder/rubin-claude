# rubin-claude

Claude Code skills for analysing Rubin Observatory data. They work on the
USDF/S3DF interactive nodes (SSH) and on the Rubin Science Platform (RSP).

The skills capture what took real debugging time during 2025–2026 early
operations: how to reach each data service from each environment, which
columns and topics hold what, which values are traps, and the statistical
checks that kept results honest. Claude loads a skill only when a task matches
its description, so installing all of them costs almost nothing until they're
needed.

| Skill | Use it for |
|---|---|
| `rubin-environment` | SDF vs RSP detection, LSST stack/kernel setup, tokens and pgpass, storage, resource limits, batch jobs |
| `consdb` | ConsDB access (FastAPI/TAP/Postgres), `cdb_lsstcam` schema, value traps (TAI times, NaN DIMM, stale wind, null Zernikes) |
| `efd` | EFD clients, chunking, InfluxQL quirks, verified topic/field/index catalog |
| `observing-logs` | narrative log, night report, exposure log, time-lost units, Jira read |
| `butler-and-archives` | Butler repos (main, embargo, DP2), LFA, alert archive, allskycam, DREAM, sims, Astro Data Lab |
| `rubin-notebooks` | editing big notebooks, running cells headlessly, SDF kernels, nbstripout/no-data commits |
| `observatory-systems` | louvers (motorized vs pneumatic), shutter/LWS, TMA encoder heads, hexapods/AOS blocks, coolant and dew-point limits, operations timeline |
| `analysis-methods` | within-night fixed effects + placebo, spec-verdict taxonomy, max-statistic nulls, requirement-document traps, prior results |

Helper scripts (inside the skills):

- `consdb/scripts/consdb_query.py`: one SQL query to ConsDB, through HTTP or Postgres.
- `observing-logs/scripts/log_search.py`: regex search of the narrative log and night report by day_obs.
- `rubin-notebooks/scripts/nb_cells.py`: list, show, grep and edit cells of large notebooks.
- `rubin-notebooks/scripts/run_cells.py`: execute all or some cells with nbclient.
- `rubin-notebooks/scripts/make_sdf_kernel.sh`: SDF Jupyter kernel that runs EUPS setup.

For building and testing LSST Science Pipelines packages against a weekly
(`pytest`, `scons`, `pipetask` under EUPS), also install the **`lsst-eups`**
skill from DM's [lsst-dm/agent-skills](https://github.com/lsst-dm/agent-skills).

## Install

### As a Claude Code plugin (recommended)

Inside Claude Code:

```
/plugin marketplace add bstalder/rubin-claude
/plugin install rubin-analysis@rubin-claude
```

Update later with `/plugin marketplace update rubin-claude`.

### As plain skills (symlinks)

Use this if you prefer it, or if you also use other agents:

```bash
git clone https://github.com/bstalder/rubin-claude
cd rubin-claude && ./install.sh          # symlinks into ~/.claude/skills/
```

## One-time setup per user

1. **RSP token, for HTTP services (ConsDB, logs, EFD).** On the RSP this is
   automatic. On SDF, create a token
   ([guide](https://rsp.lsst.io/v/usdfprod/guides/auth/creating-user-tokens.html)),
   save it as `~/.lsst/usdf_rsp`, then run `chmod 600 ~/.lsst/usdf_rsp`.
2. **Optional, SDF only: Postgres pgpass** for direct ConsDB/log/Butler
   database access. Set `PGPASSFILE` to point at it.
3. **SDF Jupyter kernel that can import `lsst.*`:**
   `plugins/rubin-analysis/skills/rubin-notebooks/scripts/make_sdf_kernel.sh`.
4. Optional: copy [`templates/CLAUDE.md`](templates/CLAUDE.md) into your
   analysis repo and edit it.

Claude reads credentials only through libraries (`rubin_nights`, libpq,
boto). The skills tell it never to print or copy secret files.

## Keeping it current

Facts in these skills are dated. Hardware, stack versions and data windows
change, and each skill says how to re-verify. When you find something new or
wrong, open an issue or PR, and include the date and the query that shows it.

## Layout

```
.claude-plugin/marketplace.json      marketplace definition (this repo)
plugins/rubin-analysis/
  .claude-plugin/plugin.json
  skills/<name>/SKILL.md             one skill per directory (+ scripts/, references/)
templates/CLAUDE.md                  starter project instructions
install.sh                           symlink installer (alternative to the plugin)
```

## License

BSD 3-Clause, the same as [lsst-dm/agent-skills](https://github.com/lsst-dm/agent-skills). See [LICENSE](LICENSE).
