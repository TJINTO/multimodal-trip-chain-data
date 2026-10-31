# Multimodal Trip-Chain Data and Preprocessing

多方式出行链研究的数据处理说明与上海生成样本，涵盖社会车辆、出租/网约车、公交与地铁四种主方式。

## 数据与预处理说明

- [DATASETS.md](DATASETS.md)：巴尔的摩、成都、上海与费城的数据来源、时间口径、研究单元和获取地址。
- [DATA_PREPROCESSING.md](DATA_PREPROCESSING.md)：逐数据源的清洗、空间聚合、24 h 统计、缺失观测处理及样本导出流程。
- [preprocessing_audit.json](preprocessing_audit.json)：已核查文件的数值缺失、零值、低完整性日期及处理脚本版本摘要。

本仓库发布上海生成出行链样本，以及四城数据处理说明；四城原始数据请通过各数据提供方获取。年度平均日、工作日平均日与具体日期的 24 h 合计分别保留原有含义。

For manuscript use: Detailed data preprocessing procedures, including the handling of missing observations, are documented in [DATA_PREPROCESSING.md](DATA_PREPROCESSING.md). Dataset descriptions and original access links are listed in [DATASETS.md](DATASETS.md).

这些记录是模型生成的研究数据，不是真实个体轨迹。每条链表示一次 OD 出行及其链段，不表示一个人的全天活动日程。

## 下载

| 文件 | 内容 |
| --- | --- |
| [shanghai_weighted_trip_chains_20000.csv](data/shanghai_weighted_trip_chains_20000.csv) | 20,000 条已有加权出行链样本，含主方式、OD、链型及恢复流量 |
| [shanghai_r5_query_ods_1000.csv](data/shanghai_r5_query_ods_1000.csv) | 另一批 1,000 个 R5py 查询 OD，含起终点坐标与返回状态 |
| [shanghai_r5_fastest_trip_chains.csv](data/shanghai_r5_fastest_trip_chains.csv) | 其中 998 个 OD 已保存的最短时间方案，含方式序列与分项时间 |
| [shanghai_r5_fastest_trip_chain_legs.csv](data/shanghai_r5_fastest_trip_chain_legs.csv) | 上述方案的 4,626 个有序链段，含线路、站点、距离与时间 |
| [shanghai_r5_used_transit_stops.csv](data/shanghai_r5_used_transit_stops.csv) | 上述链段涉及的公共交通站点坐标 |

CSV 使用 UTF-8 编码。GitHub 页面中的 **Raw** 可获取原始 CSV；也可通过本页 **Code → Download ZIP** 下载全部文件。

## 两组样本的口径

第一组保留项目中已存在的 20,000 条样本，不重新生成。它来自包含 951,844 条方式化 OD 的城市级恢复结果，使用种子 `20260613` 按源结果的各方式流量占比分配抽取数量。

| 主方式 | 标识 | 加权链样本数 | R5 已返回方案数 |
| --- | --- | ---: | ---: |
| 社会车辆 | `motor_vehicle` | 383 | 25 |
| 出租/网约车 | `taxi` | 61 | 4 |
| 公交 | `bus` | 8,215 | 395 |
| 地铁 | `metro` | 11,341 | 574 |
| 合计 | | 20,000 | 998 |

`flow` 是源恢复结果中对应链的流量，不是该样本的扩样权重。不能将本子集的 `flow` 之和解释为上海全市总量，也不能将上述方式占比解释为独立测得的现实方式结构。`cost` 是源模型的成本字段，不应直接当作分钟数。

第二组是已有 R5py 批次输出的整理结果。查询使用上海 OSM 路网和项目构造的研究用 GTFS，设置出发时间为 **2026-06-18 08:00，Asia/Shanghai**。时刻表采用合成班次：公交间隔 600 s、地铁间隔 300 s、服务时段 05:00—23:30。它不是上海官方 GTFS，也不是历史实测运行记录。

公共交通 OD 在原批次中使用 `WALK + TRANSIT` 查询；社会车辆和出租/网约车使用 `CAR` 查询。`mode` 保留请求的主方式，实际路线方式见 `realized_mode_sequence` 及分段表的 `mode`。当前保留每个 OD 已保存的最快方案，未强制其包含请求主方式：826 条包含对应请求主方式，5 条仅有步行；另有 2 个 OD 在已保存批次中没有方案。所有状态均显式保留，便于进一步筛选。

两组样本独立提供，不能假设 `chain_id` 与 `od_id` 跨组一一对应。R5 源 CSV 没有保存路线折线，本仓库提供 OD 与站点坐标、线路和站序相关字段，不能据此声称已发布完整路线几何。

## 使用示例

```python
import pandas as pd

chains = pd.read_csv("data/shanghai_r5_fastest_trip_chains.csv")
legs = pd.read_csv("data/shanghai_r5_fastest_trip_chain_legs.csv")

# 仅保留包含请求主方式的方案。
compatible = chains[chains["requested_mode_present"]]

# 查看一条链的有序链段。
chain_id = compatible.iloc[0]["chain_id"]
print(legs[legs["chain_id"] == chain_id].sort_values("leg_index"))
```

[DATA_DICTIONARY.md](DATA_DICTIONARY.md) 给出字段解释，[manifest.json](manifest.json) 记录来源、导出参数和校验结果。运行 `python validate_data.py` 可在仅依赖 Python 标准库的环境下核对行数、链段关联、时间加和及 SHA-256。

## 来源与使用范围

本次导出仅整理已有生成结果，未重新运行模型或路径查询，未包含真实乘客记录、导航服务原始响应、账户凭据或 API 密钥。生成端点和站点位置表示模型空间载体，不应关联到真实个人。

涉及的开放地图来源为 © OpenStreetMap contributors，参见 [OpenStreetMap copyright](https://www.openstreetmap.org/copyright)。来源及许可说明见 [NOTICE.md](NOTICE.md)。公开本样本不意味着其适用于运营决策或可独立证明生成结果的现实准确性。

English: This repository documents preprocessing for four urban transport datasets and shares generated Shanghai trip-chain samples and saved R5py itinerary outputs. These samples are research artifacts, not observed passenger trajectories. The transit timetable is synthetic. Requested modes and realized itinerary modes are explicitly distinguished.
