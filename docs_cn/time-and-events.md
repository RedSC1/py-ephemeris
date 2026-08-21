# 时间、太阳时与事件

`AstroDateTime` 表示民用日历时间。传入天文算法前，调用者应明确完成时区转换。
例如固定 UTC+08:00：

```python
import taiyin

local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
utc = local_time.to_julian_date().add_seconds(-8 * 3600)
```

这个固定偏移只适用于已确定是 UTC+08:00 的输入。接收任意地点或历史日期时，
应先在应用层按适用的时区/历史偏移解析成 UTC。

`context.time` 提供 UTC、TAI、TT、UT1、TDB 的转换及 Delta-T 辅助函数；
`context.solar_time` 提供均太阳时、真太阳时和均时差计算。

`at_utc()` 默认要求闰秒表和 EOP 覆盖请求日期，数据不可用时会明确报错。
如果应用明确接受低精度估算，可开启：

```python
ctx.time.set_allow_utc_out_of_range_estimate(True)
```

回退路线会将输入的 UTC 民用时间近似解释为 UT1，再使用已配置的 Delta-T
模型。该 bool 不影响任何 `*_at_ut1()` 函数；这些函数始终将输入解释为 UT1。

```python
eph = taiyin.Ephemeris()
ctx = eph.create_context()
scales, scale_flags = ctx.time.precise_scales_from_utc(utc)
equation, equation_flags = ctx.solar_time.equation_of_time_at_ut1(scales.ut1)
print(scales.tt, scales.ut1, equation.equationSeconds)
print("执行标记：", scale_flags | equation_flags)
```

`LocalMeanSolarTime.from_ut1()` 可先按经度得到地方平太阳时，随后
`context.solar_time.mean_to_apparent()` 加入均时差得到地方视太阳时（真太阳时）。
其 `coordinate` 可通过 `context.time.reverse_julian_day()` 还原成钟表字段。排盘时应保留
原 UTC 瞬间作为真实计算时刻，不能把校正后的真太阳钟表再次按民用时区转换成 UTC。
完整调用链见[八字真太阳时排盘](bazi.md#真太阳时排盘)和
[紫微真太阳时排盘](ziwei.md#真太阳时排盘)。

## 天象事件与可见性

事件搜索需要给出区间或估计时刻：

```python
start = taiyin.JulianDate.from_double(2460400.5)
end = taiyin.JulianDate.from_double(2460420.5)

phases, phase_flags = ctx.events.lunar_phase_crossings_at_ut1(
    0.0, start, end, max_step_days=1.0
)
stations, station_flags = ctx.events.longitude_stations_at_ut1(
    taiyin.Body.mercury, start, end, max_step_days=0.25
)
print(phases, stations)
print("执行标记：", phase_flags | station_flags)
```

`context.events` 还支持黄经交点、相位、合冲刑等精确相位、最大距角、最近角距及
水星/金星凌日。`context.visibility` 则用于日月、行星、恒星的升降、中天与晨昏蒙影。
这些可见性搜索会读取上下文已配置的观测地点。
