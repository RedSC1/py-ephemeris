# 时间、太阳时与事件

已知物理瞬间时，优先使用带时区的 Python 标准库 `datetime`：

```python
from datetime import datetime, timedelta, timezone
import taiyin

instant = datetime(
    2003, 3, 13, 14, 15,
    tzinfo=timezone(timedelta(hours=8)),
)
utc = taiyin.JulianDate.from_datetime(instant)
unix_utc = taiyin.JulianDate.from_timestamp(instant.timestamp())

# 历法或术数接口还需要当地钟表字段时，另行保留 AstroDateTime。
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
```

`JulianDate.from_datetime()` 会拒绝没有时区的 naive datetime，不会偷偷采用服务器
本地时区。转换直接拆分天数、秒和微秒，不先经过 `datetime.timestamp()` 的浮点结果。
`JulianDate.from_timestamp()` 则遵循 Python 习惯，接受单位为**秒**的 Unix `int` 或
`float`。这两个入口只确定物理瞬间，不会读取或覆盖中国历法 context 的时区与日界。

`context.time` 提供 UTC、TAI、TT、UT1、TDB 的转换及 Delta-T 辅助函数；
`context.solar_time` 提供均太阳时、真太阳时和均时差计算。由 context 自动选择
闰秒、EOP、Delta-T 和 TDB 模型的常用路线如下：

`at_utc()` 默认要求闰秒表和 EOP 覆盖请求日期，数据不可用时会明确报错。
如果应用明确接受低精度估算，可开启：

```python
ctx.time.set_allow_utc_out_of_range_estimate(True)
```

回退路线会将输入的 UTC 民用时间近似解释为 UT1，再使用已配置的 Delta-T
模型。它同样适用于自动反向转换，并通过 `ResultFlag.timeScaleFallback` 报告。
该 bool 不影响任何 `*_at_ut1()` 函数；这些函数始终将输入解释为 UT1。

```python
eph = taiyin.Ephemeris()
ctx = eph.create_context()
scales, scale_flags = ctx.time.scales_from_utc(utc)
equation, equation_flags = ctx.solar_time.equation_of_time_at_ut1(scales.ut1)
print(scales.tt, scales.ut1, equation.equationSeconds)
print("执行标记：", scale_flags | equation_flags)

utc_again, utc_flags = ctx.time.tdb_to_utc(scales.tdb)
ut1_again, ut1_flags = ctx.time.tdb_to_ut1(scales.tdb)
utc_clock, clock_flags = ctx.time.utc_calendar_from_ut1(scales.ut1)
```

自动返回 UTC 的入口包括 `tai_to_utc()`、`tt_to_utc()`、`ut1_to_utc()` 和
`tdb_to_utc()`；自动返回 UT1 的入口包括 `utc_to_ut1()`、`tai_to_ut1()`、
`tt_to_ut1()` 和 `tdb_to_ut1()`。传入显式的 `dut1_seconds` 或
`delta_t_seconds` 时仍走底层偏移路线。`calendar_from_ut1()` 只把 UT1 坐标格式化
为钟表字段，`utc_calendar_from_ut1()` 则会先完成物理上的 UT1→UTC 转换。
TAI、TT 或 TDB 反算的结果若正好落在 split UTC 无法表示的插入闰秒上，会抛出
`UtcLeapSecondRepresentationError`，不会静默挪到相邻一秒。UT1 坐标本身无法区分
该闰秒与紧随其后的午夜，因此 `ut1_to_utc()` 会返回可表示的次日 `00:00:00`。

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
