# 字段说明

## 加权出行链：shanghai_weighted_trip_chains_20000.csv

| 字段 | 含义 |
| --- | --- |
| `sample_id` | 本样本内的记录编号 |
| `chain_id` | 源候选链标识；抽样时同一源链可以被重复选中 |
| `origin`, `destination` | 起讫空间单元 ID；主方式决定其为站点或网格，需按字符串读取 |
| `primary_mode` | 主方式：metro、bus、motor_vehicle、taxi |
| `chain_pattern` | 链型，例如 walk+metro+walk、taxi_direct |
| `flow` | 源链恢复流量；不是本子集的扩样权重 |
| `prior` | 源模型候选链先验强度 |
| `cost` | 源模型的链成本；未声明为实际分钟数 |
| `distance_km` | 源模型保存的 OD 空间距离，单位 km；不是导航路网里程 |
| `transfer_count` | 源模型保存的换乘次数 |
| `origin_obs_id`, `destination_obs_id` | 源模型起讫端的边际约束标识，不代表发布了真实个体观测 |
| `chain_index` | 源完整候选集中的索引 |
| `sample_seed` | 已有抽样的随机种子 |
| `sample_mode_target_count` | 该方式的目标抽样记录数 |
| `sample_mode_flow_share` | 源完整结果中该方式的流量占比 |

## R5 查询 OD：shanghai_r5_query_ods_1000.csv

| 字段 | 含义 |
| --- | --- |
| `od_id`, `source_od_id` | 查询 OD 标识、源 OD 标识 |
| `origin`, `destination` | 源起终点空间单元 ID |
| `mode` | 请求的主方式，不一定等于返回路线中的主方式 |
| `od_demand` | 原批次输入的生成 OD 需求值；不代表真实观测 |
| `mode_share` | 原批次保存的 OD 方式分配份额；不是全市方式分担率 |
| `origin_lon`, `origin_lat` | 输入起点经纬度，源查询声明为 WGS84/EPSG:4326 |
| `dest_lon`, `dest_lat` | 输入终点经纬度，源查询声明为 WGS84/EPSG:4326 |
| `pair_origin_id`, `pair_dest_id` | 原查询内部的端点编号 |
| `routing_status` | returned 或 no_plan_in_saved_batch |

## R5 链摘要：shanghai_r5_fastest_trip_chains.csv

除 OD 表的输入字段外，包含：

| 字段 | 含义 |
| --- | --- |
| `chain_id` | 本批次内的链标识，与 od_id 相同；关联分段表 |
| `option` | 原批次返回的方案编号，不保证跨 OD 唯一 |
| `route_chain` | 原批次保存的人类可读线路与站点序列 |
| `realized_mode_sequence` | 根据实际链段构成的方式序列，保留重复方式与步行 |
| `leg_count` | 分段数 |
| `total_travel_minutes` | 所有链段 travel_minutes 与 wait_minutes 的和 |
| `walk_minutes`, `car_minutes`, `transit_minutes` | 按实际链段方式分别累计的运行时间，单位 min |
| `wait_minutes` | 累计等待时间，单位 min |
| `transit_boardings` | 公共交通乘坐段数 |
| `transit_transfers` | max(公共交通乘坐段数−1, 0)；不计步行接入为换乘 |
| `requested_mode_present` | 实际方案是否包含所请求的 bus/subway/car；出租/网约车对应 car |
| `walking_only` | 实际方案是否全部为步行 |

## R5 链段：shanghai_r5_fastest_trip_chain_legs.csv

| 字段 | 含义 |
| --- | --- |
| `chain_id`, `od_id`, `option` | 所属链、OD 与方案 |
| `leg_index` | 链内从 1 开始的连续段序号 |
| `requested_mode` | 原 OD 请求主方式 |
| `mode` | 实际链段方式，例如 walk、bus、subway、car |
| `departure_time` | R5 源输出的链段出发时刻；源字段为空时保留为空，不补造时刻 |
| `travel_minutes` | 链段行进时间，单位 min |
| `wait_minutes` | 链段等待时间，单位 min |
| `distance_m` | R5 保存的链段距离，单位 m |
| `route_id`, `route_name`, `route_short_name` | 研究用 GTFS 线路标识及名称；道路和步行段可为空 |
| `start_stop_id`, `start_stop_name` | 公共交通上车站 ID 及名称 |
| `end_stop_id`, `end_stop_name` | 公共交通下车站 ID 及名称 |

## 公共交通站点：shanghai_r5_used_transit_stops.csv

`stop_id` 对应分段表的站点 ID；`stop_name` 为源站名；`stop_lat`、`stop_lon` 是源 GTFS 中的经纬度；`location_type` 保留源 GTFS 值。

文件中的站点/线路名称按源输出保留，少数源文本存在乱码；未据名称推测或改写实际站点身份。可优先通过 ID 关联记录。
