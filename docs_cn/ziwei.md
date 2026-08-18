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
chart = ziwei.calculate_local(
    local_time,
    gender=taiyin_ziwei.ZiweiGender.male,
)

print(chart.anchors.ziwei)
life = chart.palace(taiyin_ziwei.ZiweiPalace.life)
print(life.branchId, life.stemId, [star.key for star in life.stars])
```

`chart.anchors` 是 31 个稳定锚点的 `ZiweiAnchors` 对象。可用
`ZiweiAnchorSlot` 查询任意槽位，例如
`chart.anchors[ZiweiAnchorSlot.palaceCareer]`；`ziwei`、`tianfu` 也有快捷属性。

`chart.palaces` 返回命宫至父母宫顺序的十二个 `ZiweiPalaceState`，其中包含实际地支宫位、
宫干和星曜。`star_position()`、`star_palace()` 可反向查询单颗星曜。

## 规则、流运与反查

默认 TOML 规则随 `taiyin_ziwei` wheel 一起发布。`ZiweiDataCatalog()` 只解析一次；
`reload()` 后新建上下文使用新快照，已有上下文和已排出的盘保持原有规则。

`chart.set_flow()` 默认叠加大限、流年、流月、流日、流时五层，也可用 `deepest_level`
只算到指定层。早晚子时不要手动加两个小时，应使用
`next_flow_hour_target()` / `previous_flow_hour_target()`；它们会按 13 个逻辑时辰处理。

`reverse_lookup_tier1()` 按禄存、红鸾、左辅、右弼、文昌、文曲、三台、八座、紫微等条件
枚举可能的逻辑出生时段，并逐个用正向排盘验证。结果是时辰槽位，不是伪造的分钟级出生时间。

完整可运行脚本见 [Ziwei 示例](../docs/examples/ziwei_extension.md)。
