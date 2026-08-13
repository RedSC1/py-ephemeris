# py-ephemeris（“Taiyin”）

[English README](README.md) · [功能指南](docs_cn/index.md) · [API Reference（English）](docs/api.md) ·
[精度与性能](docs_cn/accuracy-and-performance.md)

`py-ephemeris` 是 [Taiyin Ephemeris](https://github.com/RedSC1/taiyin-ephemeris)
C++ 天文历算内核的 Python 绑定。

本仓库是 monorepo：根目录发布基础包 `py-ephemeris`，
[`packages/taiyin-bazi`](packages/taiyin-bazi/) 发布独立的八字扩展包
`py-ephemeris-bazi`。两者共享同一份源码与 Git 历史，但用户按需分别安装。

- PyPI 包名：`py-ephemeris`
- Python 导入名：`taiyin`
- 八字扩展包：`py-ephemeris-bazi`，导入名为 `taiyin_bazi`

```bash
python -m pip install py-ephemeris
```

这是 preview 版本。直接 pybind11 绑定已经可用，但 1.0 前仍可能添加兼容性 API。
用户不需要手动寻找或加载 Taiyin DLL。

## 快速开始：计算恒星黄道星盘

下面用一组固定的 UTC+08:00 时间和地点计算 Lahiri 恒星黄道经度：

```python
import math
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)  # UTC+08:00
instant_utc = local_time.to_julian_date().add_seconds(-8 * 3600)

ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 0.0)
)
degrees = lambda radians: math.degrees(radians) % 360.0

for body in (
    taiyin.Body.sun, taiyin.Body.moon, taiyin.Body.mercury,
    taiyin.Body.venus, taiyin.Body.mars, taiyin.Body.jupiter,
    taiyin.Body.saturn,
):
    position = ctx.astrology.sidereal_position_at_ut1(
        body, instant_utc, ayanamsha=taiyin.Ayanamsha.lahiri
    )
    print(f"{body.name:8}", degrees(position.value.siderealLongitudeRadians))
```

`Ephemeris()` 会自动加载 wheel 随附的数据。核心数值 API 的角度单位是弧度，
示例仅在输出时转成度数。后续代码可复用这里的 `eph`、`ctx`、`local_time` 和
`instant_utc`。

## 农历与干支历

```python
# 公历日期 → 农历日期。
lunar = ctx.chinese_calendar.from_solar(taiyin.SolarDate(2003, 3, 13))
print("农历：", lunar)

# 同一民用时间和天文瞬间 → 年、月、日、时四柱。
pillars = ctx.chinese_calendar.four_pillars(instant_utc, local_time)
print("四柱：", pillars)
print("日柱纳音：", ctx.ganzhi.nayin_element(pillars.day))
```

农历、节气、干支和四柱均属于主包 `taiyin`。详见
[农历与干支历指南](docs_cn/chinese-calendar-and-ganzhi.md)。

## 分宫制

分宫制、ayanamsha、岁差和章动均属于主包，无需安装八字扩展：

```python
houses = ctx.astrology.houses_at_ut1(
    instant_utc, system=taiyin.HouseSystem.porphyry
)
print("上升点：", degrees(houses.ascendantRadians))
print("十二宫头：", [degrees(value) for value in houses.cuspLongitudesRadians])
```

## 八字扩展

八字以单独的 native wheel 发布：

```bash
python -m pip install py-ephemeris-bazi
```

```python
import taiyin_bazi

# 导入 taiyin_bazi 后，eph 才提供 create_bazi()。
bazi = eph.create_bazi()
chart = bazi.calc_chart(pillars)
qiyun = bazi.calc_qiyun(
    instant_utc,
    local_time,
    chart,
    taiyin_bazi.BaziGender.male,
)
year_ten_god = bazi.get_ten_god(
    pillars.day.stem_id,
    pillars.year.stem_id,
)

print("起运时间：", qiyun.value.startCivilTime)
print("起运年龄：", qiyun.value.startAgeYears)
print("年干十神：", year_ten_god)
print("透干十神：", chart.visibleTenGods)
```

性别仅用于起运方向约定；四柱和 `BaziChart` 本身不区分性别。详见
[八字指南](docs_cn/bazi.md)。

## 随附数据

默认 wheel 包含大约 1550–2650 年范围的 DE442 衍生主要天体 OPM2 数据、
部分小行星 OPM2、土星/天王星形心修正、近似开普勒回退轨道，以及 lite 恒星表。
DE441 不在当前 Python wheel 内；可通过 `data_root` 或 `source_paths` 增加
外部 DE441、BSP/SPK、卫星或小天体文件。

完整说明见 [数据包与外部数据指南](docs_cn/data.md)。

## 文档

- [中文功能指南索引](docs_cn/index.md)
- [可运行示例说明（英文）](docs/examples/)
- [完整 API Reference（英文）](docs/api.md)

对于短命令行脚本，Python 的对象回收已足够；长时间运行的应用可以显式调用
`close()`，或使用 context manager。
