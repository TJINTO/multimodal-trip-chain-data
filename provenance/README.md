# 数据溯源与网页证据 / Data Provenance

[metadata.csv](../metadata.csv) 是来源级溯源清单，覆盖结构化数据来源、新闻、报告、百科和学术材料。[artifacts.csv](artifacts.csv) 是本地实际数据文件的哈希清单。二者通过 `data_id` 与 `source_data_ids` 关联。

## 本次整理范围

- 24条来源记录：13条结构化数据、数据目录或接口来源，11条非结构化或文献材料。
- 28个本地文件的 SHA-256：涵盖原始需求/响应聚合文件、上下车统计、人口/POI特征、GTFS及引用网页先验的实现文件。本次不重新上传这些原始文件。
- 15条来源成功提取了文本；4篇百科文本按许可公开，其他成功获取的全文仅保留在研究本地缓存。
- 已登记的原始来源、仅用于本次核查的材料、新补充但未用于原实验的材料分别标记。新增材料没有被写回模型或用于重跑实验。

完整状态见 [summary.json](summary.json)。13/11是来源类型统计，不表示所有来源均成功抓取，也不表示所有来源均进入了模型。

## 关键字段

| 字段 | 含义 |
| --- | --- |
| `data_id` | 来源唯一编号，STR为结构化来源，TXT为文本/文献来源 |
| `source_url` | 项目登记的来源地址；可能是数据目录、API端点或文章，不保证是可直接下载原始文件的地址 |
| `platform` | 数据提供方、发布平台或镜像站 |
| `timestamp` | 本次抓取/请求尝试结束时间，格式为 `YYYY-MM-DD HH:MM:SS`，精确到秒 |
| `timezone` | 本清单使用 Asia/Shanghai，即 UTC+08:00 |
| `capture_timestamp_iso` | 带时区的同一时间；未发起抓取时留空 |
| `timestamp_basis` | 区分本次核查时间与未抓取状态 |
| `historical_recorded_at` | 原项目已记录的日期或时间；未记录则留空 |
| `historical_time_basis` | 说明历史字段是下载日期、先验生成日期，还是特征管线完成时间，不能混同为网页抓取时刻 |
| `snapshot_url` | 指向固定 Git 提交中的文本快照或抓取回执；必须结合 `snapshot_type` 解读 |
| `snapshot_type` | 区分真实文本快照、仅元数据回执，以及外部存档；回执不等于网页全文快照 |
| `content_hash` | 成功提取并规范化后的纯文本 SHA-256；失败、JS空壳、仅HEAD及未请求的来源留空 |
| `response_sha256` | 本次响应内容字节的独立哈希；错误页也可能有该值，不能当作正文哈希 |
| `extraction_method` | HTML/JSON/PDF文本提取及规范化方法 |
| `used_for` | 项目中登记的用途或本次核查用途，不将文献链接自动解释为数值标定证据 |
| `evidence_role` | 区分原项目登记、源数据家族核查、补充材料、仅审计材料 |
| `source_locator` | 项目中能定位该来源或用途的相对文件名/字段 |
| `publication_date`, `temporal_scope` | 原材料发表日期与数据适用年代，均不同于抓取时间 |
| `capture_status`, `http_status` | 正文抓取、JS空壳、403、超时、仅请求头、未请求等实际状态 |
| `publisher_snapshot_url` | 从已抓取百科页面读取的原站永久修订链接，不是猜测拼接的版本号 |
| `external_archive_url` | 经存档服务查询并验证端点可访问的第三方存档；没有核实到则为空 |
| `external_archive_matches_content_hash` | 本次没有把外部存档正文与当前正文做哈希匹配，不应假定二者相同 |
| `rights_status` | 内容公开范围与许可说明 |
| `artifact_ids` | 关联到实际本地数据文件的哈希记录 |

## 时间与版本

此次网页核查发生于2026年11月1日。它不能追溯性地证明研究早期曾在相同秒数抓取过相同网页。历史来源只记录了日期时，保留日期粒度；没有历史时间时不以文件修改时间或人为指定时刻代替。

`snapshot_url` 中的 Git 提交号固定快照版本，便于读者在仓库后续更新后访问同一份文件。GitHub文本快照不是 Internet Archive 或 Perma.cc 的独立网页存档。新闻和报告未获得再分发许可时，仅公开自建抓取回执与哈希，不公开全文；相应 `snapshot_type` 明确标为回执。

本次没有核实到可用的外部存档端点，因此外部存档链接保持为空。百科另提供原站修订链接及按许可公开的文本快照。见 [ATTRIBUTION.md](ATTRIBUTION.md)。

## 哈希计算与核验

纯文本规范化方法：Unicode NFC；将连续空白压缩为一个空格；去除首尾空白；追加单个LF；按UTF-8编码后计算SHA-256。HTML先移除脚本、样式及导航，优先提取article/main正文；JSON先解析并按键排序；PDF使用pypdf 5.9.0提取文本。具体分支写入每条记录。

```python
import hashlib
from pathlib import Path

data = Path("provenance/snapshots/TXT001.txt").read_bytes()
print(hashlib.sha256(data).hexdigest())
```

对公开快照，可将此值与 `metadata.csv` 中的 `content_hash` 比较。对未公开全文的来源，哈希对应研究本地缓存中的规范化文本。重新抓取动态网页可能得到不同内容，不能仅凭不一致就判定原数据遭到篡改。

哈希一致仅证明当前字节与登记内容一致；它不能独立证明内容事实正确、抓取时间得到第三方认证，或数据从未被“连同哈希一起”修改。固定提交、原站修订链接、抓取状态与历史记录需要结合使用。

`artifacts.csv` 的 `artifact_hash` 针对实际文件原始字节，不做文本规范化；`audit_read_timestamp` 只是本次读取核查时间，并非原始下载时刻。未公开的原始人口、客流和供给文件不能仅凭来源网页的哈希重建。

## 使用范围与证据强度

- TXT001—TXT003在旧版上海阻抗先验中被引用。登记引用不代表本次已验证它们能支持所有速度参数；尤其是TXT003，其实际主题是出租车移动传感网络与道路空气污染，应进一步核查用于道路速度先验的具体依据。
- TXT004用于核查2016年成都轨道网络规模。该报道属于邻近月份的公开规模证据，不是逐个OD的时间或客流标签。
- TXT005的公交候车设施数量不等于原生公交站点数量。
- TXT006报告中的496条与551条分别对应2015年末、2016年末，不能将二者解释为精确的2016年8月站线清单。
- TXT008用于文献身份核查；TXT009—TXT011为本次补充百科材料，均不声称已用于原始OD生成。
- 本次没有整理真实社交用户评论，也没有因示例提及微博/百度百科而补造相应来源。

## 版权与复现

原始新闻、第三方报告、API响应和来源数据的权利归各提供方。仅百科文本按其许可和署名要求公开。抓取失败和访问受限状态原样保留，不通过登录、验证码或付费墙绕过限制。

[scripts/registry.py](scripts/registry.py) 提供规范化和抓取逻辑，[scripts/capture_sources.py](scripts/capture_sources.py) 可在新的输出目录重新核查来源。[scripts/validate_provenance.py](scripts/validate_provenance.py) 校验公开记录的关联和哈希。重新抓取会形成新的时间、内容和状态，不能覆盖解释为本次原始抓取。

English: The registry separates original provenance records from new audit captures. Capture timestamps have second-level resolution and an explicit timezone. Unknown historical timestamps remain unknown. Full text is redistributed only where licensed; otherwise metadata, capture receipts and hashes are provided. Hash agreement establishes byte consistency, not factual accuracy or independent timestamp attestation.
