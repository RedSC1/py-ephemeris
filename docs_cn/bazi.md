# 八字扩展

八字单独发布，使只需要天文、农历、干支、分宫或日月食的用户不必安装八字 native
extension：

```bash
python -m pip install py-ephemeris py-ephemeris-bazi
```

`EphemerisContext.bazi()` 会按需加载已安装的 `taiyin_bazi` 扩展。八字上下文会
继承该计算上下文的数据与历法策略，并共享同一个中国历法上下文。

```python
import taiyin
import taiyin_bazi

eph = taiyin.Ephemeris()
ctx = eph.create_context()
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
instant_utc = local_time.to_julian_date().add_seconds(-8 * 3600)

bazi = ctx.bazi()
result, result_flags = bazi.calculate_local(
    local_time, gender=taiyin_bazi.BaziGender.male
)
print(result.pillars)
print(result.chart.hiddenStems, result.chart.visibleTenGods, result.chart.nayinIds)
print("执行标记：", result_flags)
```

## 起运与大运

起运方向需要性别约定：

```python
dayun = bazi.fill_dayun(local_time, result.chart, result.qiyun, 10)
print(result.qiyun.startCivilTime, dayun)
```

四柱和 `BaziChart` 本身不区分性别。`BaziContextConfig` 可选择起运时间模型、方向
模型和大运边界约定。历法日界和时区则只在共享历法上下文中配置一次，例如：

```python
calendar_config = taiyin.ChineseCalendarConfig.historical_china(-5 * 60)
ctx = eph.create_context(chinese_calendar_config=calendar_config)
bazi = ctx.bazi()
result, result_flags = bazi.calculate_local(
    local_time, gender=taiyin_bazi.BaziGender.male
)
```

这里 `-5 * 60` 表示 UTC-05:00；默认的 `480` 表示 UTC+08:00。起运、人元司令和
四柱会使用同一份配置，不需要在八字参数中再设置一次。

`calculate_local()` 只接收一份当地民用时间，并按上述历法配置推导 UTC。若手上已有
UTC 儒略日，则使用 `bazi.calculate_instant(instant_utc, gender=...)`，当地时间会在
内部推导；两个高层入口都只有一个时间事实来源。

## 真太阳时排盘

部分八字流派会把地方视太阳时（通常简称“真太阳时”）作为出生钟表时间。真实 UTC
瞬间仍应是唯一事实来源：先按出生地经度从该瞬间推导真太阳时，再把结果作为
`virtual_time` 传给四柱和起运接口。不要把真太阳时直接传给 `calculate_local()`，
否则它会把校正后的钟表当成普通民用时间，再应用一次历法时区偏移。

```python
import math

longitude_degrees = 118.582

# 太阳时在定义上使用 UT1。排盘时可把 UTC 儒略日近似视作 UT1；两者差异小于一秒。
solar_ut1 = instant_utc
local_mean = taiyin.LocalMeanSolarTime.from_ut1(
    solar_ut1,
    longitudeRadians=math.radians(longitude_degrees),
)
local_apparent, solar_flags = ctx.solar_time.mean_to_apparent(local_mean)
true_solar_time, clock_flags = ctx.time.reverse_julian_day(
    local_apparent.coordinate
)

pillars, pillar_flags = ctx.chinese_calendar.four_pillars(
    instant_utc,
    true_solar_time,
)
chart = bazi.calc_chart(pillars)
qiyun, qiyun_flags = bazi.calc_qiyun(
    instant_utc,
    true_solar_time,
    chart,
    taiyin_bazi.BaziGender.male,
)
result = taiyin_bazi.BaziResult(
    instantUtc=instant_utc,
    localTime=true_solar_time,
    pillars=pillars,
    chart=chart,
    qiyun=qiyun,
)

result_flags = solar_flags | clock_flags | pillar_flags | qiyun_flags
dayun = bazi.fill_dayun(true_solar_time, chart, qiyun, 10)
print(true_solar_time, result.pillars, dayun, result_flags)
```

若有精确 DUT1，可将 `solar_ut1 = instant_utc` 替换为
`solar_ut1, dut1_flags = ctx.time.utc_to_ut1(instant_utc, dut1_seconds)`，并把
`dut1_flags` 合并进结果标记。传给排盘与起运接口的真实 `instant_utc` 不应改变。

`ChineseCalendarConfig.local_astronomical_meridian()` 选择的是地方平太阳时日界，并按
当地日界重建天文农历；它不包含均时差，不等于“开启真太阳时”。

## 规则与分析接口

`BaziContext` 包括十神、藏干、十二长生、干支关系、流年/月/日/时、小运、大运、
人元司令、神煞与盘内关系分析。例如：

```python
year_ten_god = bazi.get_ten_god(
    result.pillars.day.stem_id, result.pillars.year.stem_id
)
relations = bazi.collect_chart_relations(result.chart)
print(year_ten_god, relations)
```

可运行代码见[八字扩展示例](../docs/examples/bazi_extension.md)；完整函数表在
[英文 API Reference](../docs/api.md)。
