# Verified EFD topics, fields and indices

These were verified from live queries during 2025–2026 early-operations analyses. Every topic in the tables was re-checked to return data on 2026-11-10/11, except where noted.

To find a sensor's last sample: `SELECT last(<field>) FROM "efd"."autogen"."<topic>" WHERE salIndex = N`. Topic and field names change with ts_xml releases, so if something returns empty, probe a short window with `"*"` before concluding that there's no data.

## Weather and environment (ESS)

| What | Topic / field | Index | Notes |
|---|---|---|---|
| Outside wind (weather tower) | `lsst.sal.ESS.airFlow` `speed`, `direction` | 301 | Use a 1-min resample for spec/threshold work (ConsDB `wind_speed` goes stale at high wind) |
| Outside pressure | `lsst.sal.ESS.pressure` `pressureItem0` | 301 | **Pa** (~74 345 at altitude), ~0.3 Hz |
| Outside temperature / dew point / RH | `lsst.sal.ESS.temperature`, `.dewPoint`, `.relativeHumidity` | 301 | |
| Precipitation | `lsst.sal.ESS.logevent_precipitation` | 301 | only ever reports `raining`, never `snowing` |
| Camera-area dew point | `lsst.sal.ESS.dewPoint` `dewPointItem` | 111 (Camera-ESS01) | used by the Watcher Dynalene alarm |
| M1M3 glass thermocouples | `lsst.sal.ESS.temperature` `temperatureItem0..15` | 114–117 (m1m3-ts-01..04, 16 ch each) | `MTM1M3TS.glassTemperature` **does not exist**. ESS:115 `temperatureItem3` tracks the 64-channel median best (rms 0.04 °C). ESS:114 runs ~0.13 °C cold. |
| Inside turbulence, TMA platform | `lsst.sal.ESS.airTurbulence` `speedMagnitude`, `sonicTemperatureStdDev` | 110 | **silent since 2026-07-20** (checked 2026-11-11) |
| Inside turbulence, top ring | same | 123–126 | speed saturates at **8.6 m/s** (fill-value artefact); clip it |
| Dust | `lsst.sal.ESS.particleMeasurements` `numberConcentration0..4` | 127, 128, 129 | ~1 Hz |
| Glitches | | | Td > T (RH ≈ 95 %) samples occur; mask Td > T + 0.5 °C |
| Old `lsst.sal.Environment.*` (2019-12 → 2021-02) | | | wind has hours-long > 25 m/s values; unreliable |
| Cloud nowcast | `lsst.sal.WeatherForecast.hourlyTrend` (meteoblue) | | shortest-lead forecast as a nowcast; gap 2025-01-16 → 2025-04-16 |

## Dome (MTDome)

- `lsst.sal.MTDome.azimuth.positionActual`: dome azimuth (ConsDB has none).
- `lsst.sal.MTDome.apertureShutter.positionActual0/1` (%): dome open = `positionActual0 > 5`. Full-open → closed time was ~560 s until 2025-05-14, ~143 s until 2026-07-07, and ~80 s from 2026-07-08.
- `lsst.sal.MTDome.louvers`: see the observatory-systems skill for the louver index → drive map and which louvers report.
- `lsst.sal.MTDome.logevent_louversEnabled.faultCode`: x001 parallelism, x002 drives in fault, x003 local-box e-stop, x004 torque saturated.

## Mount (MTMount)

- `lsst.sal.MTMount.elevation` / `.azimuth` `actualPosition`: ~14 Hz.
- `lsst.sal.MTMount.logevent_warning` codes **714–717** = azimuth encoder heads 1–4 (`encoderHeadReadReferenceAZ0..3`; value 0 = lost). For any mount "impulse" or tracking jump, check these first.
- Elevation-error single-sample spikes of ~0.65″ can be a timestamp artefact: the demand time is offset by −50 ms and the torque doesn't respond.

## Mirrors and hexapods

- `lsst.sal.MTM1M3.imsData` (~50 Hz): xPosition … zRotation.
- `lsst.sal.MTM1M3.hardpointActuatorData` `measuredForce0..5` (~50 Hz).
- `lsst.sal.MTM1M3.appliedBalanceForces` `mx`, `my`. The force controller's mirror-moment fault band is ±11 000 N·m (ts_config_mttcs `MTM1M3/v1/_init.yaml`).
- `lsst.sal.MTM2.positionIMS` (~20 Hz).
- `lsst.sal.MTHexapod.application` `demand0..5`, `position0..5`: index 1 = camera hexapod, 2 = M2 hexapod. `demand ≈ position` with a nonzero demand ptp means the hexapod is being *commanded*.
- `lsst.sal.MTHexapod.logevent_inPosition`: **don't** use `ackcmd` COMPLETE (it arrives ~30 ms after the command and doesn't mean the move finished). `moveInSteps` splits large moves into ~1000 µm sub-steps and `inPosition` goes True briefly between them. The end of the move is the *last* True with no later False before the next `startIntegration`.
- `lsst.sal.MTHexapod.logevent_uncompensatedPosition` fires only on commanded moves. `logevent_compensationMode` holds the LUT compensation enabled flag.
- M2 hexapod strut speed was cut from 500 to 100 µm/s in late 2025, so M2 z moves run at ~75 µm/s effective (a 4 mm move takes ~50–70 s). The camera hexapod stays at 500.
- `lsst.sal.MTAOS.logevent_wavefrontError`: Zernikes per wavefront visit. It's sparse for some test blocks.

## Observatory state

- `lsst.sal.Scheduler.logevent_observatoryStatus`, salIndex 1, bitmask: DAYTIME=1, OPERATIONAL=2, FAULT=4, **WEATHER=8**, DOWNTIME=16, IDLE=32. It exists from **2026-02-25**. Observers set WEATHER by hand; FAULT is automatic. Some old `rubin_nights` builds lack `observatory_status.get_obs_status_messages`, so query the topic directly.
- Watcher alarms: `lsst.sal.Watcher.logevent_alarm` (quote the `name` field). Thresholds recovered from the alarm text:
  - RH > 80 % (weather tower).
  - Dew-point depression < 2.0 °C "Close the dome" (2.5 serious, 3.0 check).
  - M1M3/M2/camera RH 70/80/90 %.
  - Wind ≈ 15 m/s sustained / ≈ 18 m/s gust (from log statements).
- Watcher `DewPointDepression.DynaleneNearElWrap` = MTCamera `tel_utiltrunk_UT.coolPipeSplyTemp` − ESS:111 dew point; warning 4.0, critical 3.5. Whether it's active depends on the deployed ts_config_ocs Watcher version.
- Dynalene coolant: HVAC `dynTMAsupTS01` (TMA supply) and the camera `coolPipeSplyTemp` read 1–2 °C warmer than the chiller setpoint. Use the measured value at the location you care about, not setpoint − offset.
