# Data Preprocessing Procedures

This document describes the inspected data adapters and saved experiment settings. It covers four-city marginal-flow preparation and the export of the Shanghai trip-chain samples. Documentation and aggregate checks were added on 31 October 2026; no model or routing experiment was rerun for this update.

## Common representation

Records retain dataset/city, source year, date or statistical-period label, spatial-unit ID, mode, target direction, value, coordinates and source grain. Unit IDs are treated as strings; numeric-looking IDs ending in `.0` are normalized where the adapters require it. Records sharing an aggregation key are summed. This is spatial/temporal aggregation, not a claim that arbitrary duplicate source records were identified and removed.

The daily tasks use `daily_24h`. For Shanghai and Chengdu this is a sum of the available intra-day records. Baltimore is already an annual-average-day product; Philadelphia is already a fall average-weekday product. Neither average-day product is expanded into measured hourly observations. A missing whole date is not synthesized by these adapters.

## Missing observations and zero values

| Situation | Implemented handling | Interpretation |
| --- | --- | --- |
| An explicit numeric zero in a source value | Retained in aggregation; sparse loaders may omit storing that zero internally | A recorded zero is not counted as a missing numeric value |
| A missing or nonnumeric value in the Baltimore/SEPTA numeric adapters | `to_numeric(errors="coerce")`, then zero fill; negative values clipped to zero | A computational convention, not a statistical estimate of the missing observation |
| A unit absent from a particular marginal group but present in the chosen support | Zero-filled on that support; the replacement preparation adapter records support expansion in its notes | Does not prove that an unreported unit had no trips |
| A low-total Shanghai daily directional group | Excluded by the recorded daily-total threshold | No interpolation of the excluded day |
| A missing coordinate | Omitted from geographic operations/crops requiring coordinates, or retained as missing in source snapshots | No invented coordinates for missing spatial observations |
| A missing required schema field or incomplete required SEPTA real-feature index | Preparation raises an error | Missing inputs are not replaced with passenger-flow labels |
| An absent optional numeric external-feature field | Some feature adapters encode zero for computation | Must not be interpreted as verified absence of population, POIs or service |
| R5 fails to return a saved itinerary for an OD | The query OD is retained with `no_plan_in_saved_batch`; no leg is fabricated | Separate from a zero-flow observation |
| R5 segment departure time is blank | Left blank in the public export | No inferred departure timestamp is inserted |

The audit of the inspected Shanghai inflow/outflow columns, SEPTA boarding/alighting columns and Chengdu input numeric fields found **no missing/nonnumeric values**. Thus the numeric zero-fill rule should not be described as imputing a measured number of missing cells in those particular files. Missing station-time rows or unreported events are a different issue: this audit did not establish a complete expected time-slot inventory. Zero counts in processed tables must not be used to estimate a raw-data missingness rate.

There is no spatial or temporal interpolation, forward filling, or learned passenger-flow imputation in the inspected preparation routines. Existing model priors and synthetic timetable assumptions belong to generation/routing, rather than observation repair.

## Baltimore-MPO

1. Read `Origin_Zone_ID`, `Destination_Zone_ID` and `All_Day_Average_Day_car_All_Purpose` from the 2017 annual-average-day person-OD table in chunks.
2. Normalize zone IDs and numerically parse the car-person-trip values. Nonnumeric/missing values become zero and negative values are clipped to zero by the adapter.
3. Sum by origin for outflow and by destination for inflow. Join the published TAZ shapes by `TAZ10`, obtain their centroids and transform these to longitude/latitude.
4. Construct both directions on the available native TAZ support. If a supported zone has no aggregated entry, use zero for its marginal value. The regional support comprises 2,922 zones.
5. The saved study-core procedure determines an activity-weighted centre from `JUR=1` Baltimore City zones, then selects regional zones within a 15 km radius. The retained benchmark has 597 zones. This centre uses aggregated activity; it should not be described as a completely observation-independent boundary.

The inspected final snapshot has 597 rows per direction, with no missing coordinates, missing marginal values or zero marginal values. Raw OD-cell missingness was not recomputed in this release. Regional marginal flows are computed **before** the core crop, so retained-zone inflows/outflows can include travel to or from outside the retained core; the crop does not reconstruct all trips as internal trips.

The 2017 annual-average-day value is used as supplied. The preparation does not divide an annual sum by 365 or average daily files to recreate it. One trip contributes once to total departures and once to total arrivals; adding the two marginal totals would double-count trips.

## Chengdu-DIDI

1. Read seven daily demand files and seven daily response files for 8–14 August 2016. Use `longitude`, `latitude`, `hour` and `value`.
2. Filter points against the configured geographic bbox; valid hours are 0–23. The loader converts invalid numeric values through its safe parser, clips values at zero, and stores only positive values. Records outside the bbox or with invalid hours are skipped. The audited input fields contain no missing/nonnumeric values.
3. Map points to regular-grid IDs using the configured origin and cell size; sum values per hour and grid. Where a coarser-grid factor is configured, aggregate grid IDs and values consistently.
4. For a daily task, **sum** hourly values separately for demand and response. Preserve the recorded study support and support policy; the reported benchmark uses 734 grid units. Missing unit entries receive zero when aligned to that support, without asserting complete event observation.
5. Join external grid features by grid ID. Support variants such as external-feature support and target-active support must remain identifiable; their results are not interchangeable. The original demand/response fields are not converted into matched order-level OD observations.

The input audit found 24,819 demand rows and 20,418 response rows. The audit does not infer hidden trips or the number of absent point-hour records from those row counts.

## Shanghai-MetroFlow

1. Read `date`, `startTime`, `station`, `inFlow` and `outFlow` in chunks. Pad the time string to six digits and derive the hour. Group by date, hour and station, summing inflow/outflow separately. The source loader keeps nonnegative directional values.
2. Join station information and external station features by station ID. The experiment retains a stable 302-station support; groups are aligned to the recorded support rather than selecting only the current day's positive-flow stations.
3. For `daily_24h`, sum the available hourly station values for each direction. Within-support missing entries are represented numerically as zero; absent source intervals are not interpolated.
4. In the four-city preparation wrapper, apply the saved threshold `min_daily_total = 1,000,000` to **each daily directional group**, using its sum over stations. Drop groups below this threshold. This is a coarse low-completeness screen, not proof of interval-by-interval completeness for the retained days.

The inspected source contains 3,788,892 records spanning 123 dates, 1 May–31 August 2017. All inflow/outflow cells are finite, nonnegative numbers. Both directions fall below the threshold on:

| Excluded date | Inflow total | Outflow total |
| --- | ---: | ---: |
| 2017-05-04 | 11,132 | 11,132 |
| 2017-05-08 | 3,470 | 3,470 |
| 2017-05-09 | 7,453 | 7,453 |
| 2017-06-16 | 24,940 | 24,940 |
| 2017-06-27 | 964 | 964 |
| 2017-06-28 | 6,840 | 6,840 |

Applying this wrapper's quality rule leaves 117 dates and 234 daily directional groups. Other saved artifacts can use a different date subset; the exported Shanghai chain samples retain their original provenance and are not regenerated by this documentation update.

## Philadelphia-SEPTA

1. Read `Fall_2016_Stop_Summary_(Bus).csv`. Required fields include `Stop_Code`, `Stop`, `Lat`, `Lon`, `WKDY_ONS` and `WKDY_OFFS`.
2. Normalize stop codes. Parse weekday boarding/alighting values numerically, fill invalid cells with zero and clip negatives at zero. The inspected source has no invalid/missing numeric values in these columns or in its coordinates.
3. Aggregate route–direction–stop rows by **native `Stop_Code`**. Sum `WKDY_ONS` and `WKDY_OFFS` separately. When rows share a stop code, obtain coordinates as a boarding-plus-alighting-weighted mean of valid coordinates; if all weights are zero, use their unweighted mean. This aggregation does not merge different stop codes merely because they lie within 150 m.
4. Keep stops in the fixed inner-city bbox: longitude −75.245 to −75.020 and latitude 39.900 to 40.075. This retains 6,502 of 12,601 source stops. Retained mean-weekday totals are 427,215 boardings and 426,566 alightings.
5. Join real OSM and WorldPop features by stop ID. The strict feature-loading option requires complete coverage of the expected stop IDs and raises an error if entries are missing. Population exposure from overlapping station service areas is treated separately from disjoint-zone population.

Direction aliases in the inspected adapter are important: **`WKDY_ONS` → `bus_tap_out` → production/out**, while **`WKDY_OFFS` → `bus_tap_in` → attraction/in**. These aliases express spatial departure/arrival direction; readers should use the original boarding/alighting definition when interpreting them. The processed snapshot contains 179 zero-boarding stops and 181 zero-alighting stops; these are not missing-cell counts. Hourly bus ridership is not inferred from this average-weekday summary.

## Shanghai public sample export

The weighted sample is copied from the existing 20,000-row sample, using its saved seed `20260613` and mode-flow allocation. No additional reweighting is applied. `flow` remains the source recovered chain flow; summing the subset does not recover the city total.

The R5 sample is a separate existing 1,000-OD batch. Join its saved fastest-option table to the segment table on `(od_id, requested mode, option)`, sort segments, and assign consecutive one-based leg indices. Convert timedelta fields to minutes. Recompute walking, car, transit and waiting components from the **actual segment modes**. Total itinerary time equals the sum of segment travel and waiting times.

Retain all 1,000 query ODs, including the two without saved plans. The 998 returned plans contain 4,626 segments. Keep requested and realized modes separate: 826 returned plans contain the requested mode and five are walking-only. This export does not force a different mode or create segments to conceal those outcomes.

Include only transit stops referenced by those saved segments. All referenced stop IDs resolve in the source research GTFS. The original segment CSV omitted polylines; this publication therefore does not invent route geometry. Segment departure timestamps that were blank remain blank.

The R5 query uses an OSM network and synthetic 2026 GTFS, departing at 08:00 on 18 June 2026. It must not be treated as observed 2017 travel times. The weighted sample and R5 sample have separate IDs and cannot be assumed to join one-to-one.

## Audit and validation

[preprocessing_audit.json](preprocessing_audit.json) records aggregate numeric checks, low-total Shanghai groups, processed Baltimore/Philadelphia checks and hashes of the inspected preparation scripts. Counts in that file describe the inspected snapshots and do not imply that the entire raw-data preparation pipeline is packaged in this repository.

[manifest.json](manifest.json) records the Shanghai export provenance. [SHA256SUMS](SHA256SUMS) covers the five published data CSVs. Run `python validate_data.py` to verify those checksums, row counts, stop references, consecutive leg indices and chain-time sums.
