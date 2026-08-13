# 功能指南

[English README](../README.md) · [中文 README](../README.zh-CN.md) ·
[完整 API Reference（English）](../docs/api.md)

本目录按任务组织，面向“我想算什么”的使用场景；具体函数参数、所有枚举和
返回类型请查询英文 [API Reference](../docs/api.md)。

| 指南 | 主要 API / 功能 |
| --- | --- |
| [位置、观测者与天象](positions-and-observers.md) | `context.position`、`context.observed`、`context.phenomena` |
| [时间、太阳时与事件](time-and-events.md) | `context.time`、`context.solar_time`、`context.events`、`context.visibility` |
| [日月食、掩星与轨道](eclipses-occultations-orbits.md) | `context.eclipses`、`context.occultation`、`context.orbits` |
| [恒星表](fixed-stars.md) | `eph.star_catalog`、`context.stars` |
| [恒星黄道、岁差与分宫制](astrology-and-houses.md) | `context.astrology` |
| [农历、节气与干支历](chinese-calendar-and-ganzhi.md) | `context.chinese_calendar`、`context.ganzhi` |
| [八字扩展](bazi.md) | `taiyin_bazi`、`ctx.bazi()` |
| [数据包与外部星历](data.md) | `Ephemeris(...)`、OPC、`data_root`、`source_paths` |
| [精度与性能](accuracy-and-performance.md) | 数据/路线精度范围与可复现基准 |

现有可运行脚本及其说明在 [`docs/examples/`](../docs/examples/)；示例说明暂时以
英文为主，代码本身可直接运行。
