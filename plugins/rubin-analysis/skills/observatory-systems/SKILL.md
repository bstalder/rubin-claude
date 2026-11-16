---
name: observatory-systems
description: Use when interpreting Rubin summit hardware behaviour in telemetry or logs — MTDome louvers (motorized vs pneumatic, index/drive mapping, which report state), aperture shutter and LWS, TMA azimuth encoder heads, M2/camera hexapod motion and slips, AOS calibration blocks that dither focus, Dynalene coolant and dew-point limits, operational weather limits, and the 2025–2026 operations timeline (storm, downtime, data gaps). Dated facts — re-verify the ones that drift.
---

# Observatory systems: facts that change how you read the data

Every item carries the date it was established. Hardware configuration changes, so re-check anything that matters to a conclusion with a quick query.

## MTDome louvers (LLBV), aperture shutter, LWS

- **Two kinds of louver.**
  - *Motorized (drive) louvers:* B1, E1, E2, H1, H2, M1 report in `lsst.sal.MTDome.louvers` (array indices 2, 11, 12, 20, 21, 29).
  - *Pneumatic louvers:* A1, C1, D1, F2, G2, I1, L1, N1 are **working from 2026-11-10 onward**. Their open/closed state is **not in the EFD**: their array slots read 0, so a 0 does *not* mean closed or broken. Get their state from operators or the logs. Before 2026-11-10, don't assume they were operational.
- **Motorized louver mechanics.** Louver index *i* is driven by drives **2i (A) and 2i+1 (B)**.
  - `positionActual` is the mean of the two `encoderHeadCalibrated` values (~57 counts per %), so A/B desync shows up only in the A−B encoder offset.
  - `driveTemperature` always reads 0.
  - **Two parallelism-fault modes (verified 2026-11-13).** Nov–Dec 2025 (H1, M1, E1): both drives moving, A gradually outruns B by ~15–20 counts, then trip. 2026 (B1 02-18, E1 06-19, B1 11-08): **drive B side does not move at all** while A moves ~65–75 counts to the trip. In the 2026 cases drive B is electrically live: it draws the same ~1.8–3.7 A as A and its actual torque tracks its command up to the 12 Nm limit, yet its encoder doesn't change. Isolated single-louver drive faults (x002) preceded those faults by 1–9 h.
  - `logevent_brakesEngaged.brakes` is a bitmask with bit n = `Brake` enum value n (LOUVER_B1 = 7, E1 = 16, H1 = 25, M1 = 34). There is **one bit per louver, covering both drives' brakes**, with no per-drive brake signal. ts_xml doesn't say whether it is the commanded output or brake feedback.
  - `command_resetDrivesLouvers.reset[68]` is indexed by **drive** (2i, 2i+1), not by louver. Resets logged with only `reset11` (Jun 2026, for E1, whose drives are 22/23) and an all-False reset (2026-11-08 12:39) did nothing for the faulted louver.
  - Fault codes: see the efd skill's topic reference.
- Historically (2025–26) F/G louvers weren't commissioned and were excluded from night configurations. The rear access door (RAD, 180°) is always closed at night. During much of 2026 the louvers were 100 % open from May onward.
- **LWS** (light/wind screen) reduces the effective aperture-shutter area from **200 m² to 119 m²**.
- Shutter close time from full open: ~560 s until 2025-05-14, ~143 s until 2026-07-07, ~80 s from 2026-07-08. Dome open = `apertureShutter.positionActual0 > 5 %`.
- Plot dome/wind quantities against azimuth **relative to the shutter axis**, wrapped to −180°…+180°.

## Telescope mount (TMA)

- Azimuth has 4 encoder heads; losses appear as `MTMount.logevent_warning` codes 714–717. Since ~June 2026 a head loss during tracking gives a ~80 kN·m torque kick and a ~3.3–3.6″ jump (≈1.3″ on sky), versus ~2 kN·m / 0.02″ earlier. **For any tracking "impulse", check these warnings first.**
- When a user quotes an exposure start time from ConsDB, it's TAI (37 s ahead of UTC).

## Hexapods and AOS

- MTHexapod salIndex **1 = camera, 2 = M2**.
- M2 strut speed was cut 500 → 100 µm/s in late 2025, so ±4 mm focus sweeps are M2-limited (~75 µm/s effective). The camera hexapod stays at 500.
- `moveInSteps` sub-steps make `inPosition` toggle mid-move; ack COMPLETE ≠ motion done. Details are in the efd topic reference.
- M2 actuators show uncommanded stick-slip transients (act 2/6/3 at ~2–3 per hour) and chatter. Act 3 chatter appears at elevation < 55°, mostly 35–45° at T ≤ 5 °C, and has been rising since 2026-05. The image impact so far is negligible (≤ 0.007″ FWHM).
- **AOS calibration blocks are not passive stares.** `BLOCK-T698`/`T703` usually *command* hexapod focus dithers (tens to hundreds of µm), so Z4 "wander" there is the commanded dither. Some T698 blocks instead freeze M2. Check `MTHexapod.application` demand ptp for each block.
  - `BLOCK-T614` (img_type `cwfs`) is the open-loop focus test.
  - `BLOCK-T709` doesn't exist.
  - During survey the LUT commands focus essentially every exposure, so "hexapod-static" science samples are nearly empty.

## Thermal, humidity and coolant limits

- **Dew-point rules** (Watcher alarm text): dew-point depression < 2.0 °C → "Close the dome" (2.5 serious, 3.0 check); RH > 80 % at the weather tower; M1M3/M2/camera RH 70/80/90 %.
- **Wind:** ≈ 15 m/s sustained / ≈ 18 m/s gust operational practice. The design degraded-ops spec is 20 m/s sustained / 25 m/s gust.
- **Dynalene coolant** reads warmer than its source setpoint along the line: e.g. −2 °C setpoint → ~1.4 °C at the chiller, ~2 °C at the TMA supply, ~3.6 °C at the camera. Use the measured temperature where you need it.
  - Condensation has been observed on **non-insulated Dynalene pipes near the TEA** (Dec 2025, Jan 2026, Feb 2026), mostly with the dome closed and the TMA at horizon.
  - Operating guideline (log, 2026-11-13): when Dynalene − dew point (in-dome ESS:111, as in Watcher `DynaleneNearElWrap`) has been **< 0 °C for ~1 h**, observing pauses for a "non-invasive" Level 8 inspection of the TMA Dynalene lines. Logged wetting came only after 8–52 h below 0 °C (dome closed, TMA at horizon). Inspections after ≤ 6 h below 0 °C (margins down to −3.7 °C) found the lines dry or slightly damp.
- **M1M3 glass temperature** comes from the ESS:114–117 thermocouples, not an `MTM1M3TS` topic.
- The M1M3 force controller's mirror-moment fault band is ±11 000 N·m. Measured wind moments are ~100× below it.

## Operations timeline 2025–2026 (for data windows and attribution)

| Period | What | Note |
|---|---|---|
| 2025-04-15 → 2026-07-13 | LSSTCam commissioning / science-validation on sky | ConsDB science through day_obs 20260713 |
| 2026-02-25 | `Scheduler.logevent_observatoryStatus` starts | before this there is no WEATHER flag |
| 2026-07-14/15 | storm; WEATHER then DOWNTIME set | 2026-07-20 02:02 UTC cascade of faults (power loss) |
| 2026-07-20 → 09-25 | EFD Scheduler status gap (67.6 d) | don't carry state across it |
| mid-Jul → 2026-09-01 | catastrophe / weather downtime (C1) | recovery counts as weather |
| 2026-09-14 → 10-05 | planned downtime (B1) | |
| 2026-10-27 | LSSTCam science resumes; survey visits `BLOCK-407` | |
| DIMM | silent since 2026-07-14; RINGSS since 2026-06-15 | (as of 2026-11) |

Curated time-loss categories and overrides live in `lsst/sp_notebooks` (`tracking_hub/ops/observatory_state_overrides/`) and the ROSP Jira tickets.
