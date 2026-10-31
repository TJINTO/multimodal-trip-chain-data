# Datasets and Access

This page identifies the reused datasets and their statistical units. Original data are obtained from the providers below; this repository distributes the generated Shanghai samples listed in the [README](README.md).

| Dataset | Period and statistical basis | Spatial representation used in the reported four-city benchmark | Source |
| --- | --- | --- | --- |
| Baltimore-MPO | 2017 annual-average-day person OD, primary mode car | 597 traffic analysis zones retained from a regional support of 2,922 zones | [Baltimore Metropolitan Council](https://www.baltometro.org/) |
| Chengdu-DIDI | 8–14 August 2016; hourly demand/response point aggregates summed to daily distributions | 734 grid units in the reported benchmark | [Tianchi dataset 39384](https://tianchi.aliyun.com/dataset/39384) |
| Shanghai-MetroFlow | 1 May–31 August 2017; station inflow/outflow records aggregated to daily totals | 302 metro stations | [Human Mobility Datasets in the Complex Metro System of Shanghai](https://doi.org/10.6084/m9.figshare.28844942) |
| Philadelphia-SEPTA | Fall 2016 average weekday boarding/alighting counts | 6,502 native bus stops in the inner-city study area | [SEPTA Ridership Statistics, Data.gov](https://catalog.data.gov/dataset/septa-ridership-statistics) |

## Source details

**Baltimore.** The inspected adapter reads `Annual_Person_OD.csv` from the MPO person-OD archive and selects `All_Day_Average_Day_car_All_Purpose`. Row and column aggregation produces zonal outflow and inflow. The values are **person trips with car as primary mode**, not detector-counted vehicles. The provider website above is an access portal, not a dataset DOI. The 2017 label identifies the annual-average-day product; it does not provide individual trip dates.

**Chengdu.** The inspected local source contains seven `demand` and seven `response` daily files, with 24,819 and 20,418 point-hour records, respectively. These are scalar point aggregates, not individual order-level OD trajectories. The two directions retain their demand/response semantics.

**Shanghai.** The inspected `metroData_InOutFlow.csv` contains 3,788,892 records, 302 stations and 123 dates. The experiment's daily quality filter removes six low-total dates; see [the exact dates and threshold](DATA_PREPROCESSING.md#shanghai-metroflow). Absence of numeric nulls in this file does not establish complete station-time coverage.

**Philadelphia.** The inspected `Fall_2016_Stop_Summary_(Bus).csv` contains 17,538 route–direction–stop rows and 12,601 unique stop codes. Full-source weekday boarding/alighting totals are 526,296/523,860. Aggregation by stop code and the study-area crop retain 6,502 stops and 427,215/426,566 weekday boardings/alightings. These are period-average weekday counts; they do not contain hourly observations. SEPTA's catalog describes stop summaries as average daily ridership over the reporting period.

## External spatial data

- [OpenStreetMap](https://www.openstreetmap.org/copyright): roads, POIs, transit stops and route relations, subject to the coverage and timestamp of the local downloads.
- [WorldPop](https://hub.worldpop.org/): gridded population. Station service-area exposure must be distinguished from population in disjoint TAZ polygons. The inspected Philadelphia provenance identifies the 2016 USA raster.
- Transit GTFS used for routing must be identified separately from ridership observations. The Shanghai R5 examples in this repository use a **research synthetic GTFS timetable**, with daily 2026 service, rather than an official 2017 schedule.

The selected study supports and preprocessing rules are documented in [DATA_PREPROCESSING.md](DATA_PREPROCESSING.md). Source rights remain with the respective providers; see [NOTICE.md](NOTICE.md).
