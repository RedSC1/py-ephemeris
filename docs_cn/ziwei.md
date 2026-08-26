# 紫微斗数扩展

紫微斗数以独立 native 扩展发布，既不属于基础天文/历法包，也不依赖八字包：

```bash
python -m pip install py-ephemeris py-ephemeris-ziwei
```

紫微上下文从已有的 `EphemerisContext` 创建，而不是重新创建另一套星历运行时：

```python
import taiyin
import taiyin_ziwei

eph = taiyin.Ephemeris()
ctx = eph.create_context()
ziwei = ctx.ziwei()
```

因此中国历法模式、历史改历、日界、时区以及已加载的数据源都会与 `ctx` 保持一致。

## 本命盘

`calculate_local()` 接收当地民用时间，并按绑定历法上下文推导 UTC；若手头已有 UTC
儒略日，使用 `calculate_instant()`。不要同时传两份独立的时间事实。

```python
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
chart, chart_flags = ziwei.calculate_local(
    local_time,
    gender=taiyin_ziwei.ZiweiGender.male,
)

print(chart.anchors.ziwei)
print("执行标记：", chart_flags)
life = chart.palace(taiyin_ziwei.ZiweiPalace.life)
print(life.branchId, life.stemId, [star.key for star in life.stars])
```

## 真太阳时排盘

真太阳时紫微盘应从唯一的 UTC 物理瞬间和出生地经度推导地方视太阳钟表，再调用底层
`create_chart()`。不要把校正后的真太阳时传给 `calculate_local()`；该方法会把它当成
普通民用时间，再按历法配置反推一次 UTC。

```python
import math

local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
instant_utc = local_time.to_julian_date().add_seconds(-8 * 3600)
solar_ut1 = instant_utc  # UTC−UT1 小于一秒；已知 DUT1 时可调用 utc_to_ut1()。

local_mean = taiyin.LocalMeanSolarTime.from_ut1(
    solar_ut1,
    longitudeRadians=math.radians(118.582),
)
local_apparent, solar_flags = ctx.solar_time.mean_to_apparent(local_mean)
true_solar_time, clock_flags = ctx.time.reverse_julian_day(
    local_apparent.coordinate
)

chart, chart_flags = ziwei.create_chart(
    instant_utc,
    true_solar_time,
    gender=taiyin_ziwei.ZiweiGender.male,
)
result_flags = solar_flags | clock_flags | chart_flags
print(true_solar_time, chart.anchors.ziwei, result_flags)
```

`create_chart()` 仍按真实瞬间和绑定的 `ChineseCalendarContext` 确定农历日期；真太阳时
钟表会影响虚拟时间、四柱、早晚子时与相关节气日序。如果校正结果跨过午夜，并且所用
流派还要求农历日期也在真太阳午夜换日，目前尚未实现这种独立的历法日界口径。

`ChineseCalendarConfig.local_astronomical_meridian()` 使用地方平太阳时日界，不等于加入
均时差后的真太阳时。

`chart.anchors` 是 31 个稳定锚点的 `ZiweiAnchors` 对象。可用
`ZiweiAnchorSlot` 查询任意槽位，例如
`chart.anchors[ZiweiAnchorSlot.palaceCareer]`；`ziwei`、`tianfu` 也有快捷属性。

`chart.palaces` 返回命宫至父母宫顺序的十二个 `ZiweiPalaceState`，其中包含实际地支宫位、
宫干和星曜。`star_position()`、`star_palace()` 可反向查询单颗星曜。

## 规则、流运与反查

默认 TOML 规则随 `taiyin_ziwei` wheel 一起发布。`ZiweiDataCatalog()` 只解析一次；
`reload()` 后新建上下文使用新快照，已有上下文和已排出的盘保持原有规则。

各规则维度可独立选择。十二长生不支持逐星混搭，而是通过
`ZiweiOptionSelection(longevity="option2")` 整体切换：默认 `option1` 为水土同申；
`option2` 为火土同寅，仅影响土五局的十二长生序列，不改变主星、庙旺或年四化。

`chart.set_flow()` 返回 `(resolution, result_flags)`，默认叠加大限、流年、流月、
流日、流时五层，也可用 `deepest_level` 只算到指定层。早晚子时不要手动加两个小时，应使用
`next_flow_hour_target()` / `previous_flow_hour_target()`；它们会按 13 个逻辑时辰处理。

流月结果会分别保留书写月、流派折算后的有效月、物理月序、月建地支和流月命宫序号。
默认 `ZiweiFlowMonthPalaceStrategy.physicalSequence` 让每个实际朔望月推进一次流月命宫；
若所用流派要求闰月按折算后的月份安流月命宫，可在 `ZiweiFlowOptions` 中选择
`effectiveMonth`。这个选项只改变命宫推进规则，不会篡改历法给出的闰月和月建事实。

`reverse_lookup_tier1()` 返回 `(candidates, result_flags)`，按禄存、红鸾、左辅、右弼、
文昌、文曲、三台、八座、紫微等条件枚举可能的逻辑出生时段，并逐个用正向排盘验证。
结果是时辰槽位，不是伪造的分钟级出生时间。

完整可运行脚本见 [Ziwei 示例](../docs/examples/ziwei_extension.md)。
