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

也可以直接用公历日或农历日加钟表字段排盘：

```python
result, flags = bazi.calculate_solar_day(
    taiyin.SolarDate(2003, 3, 13), hour=14, minute=15,
    gender=taiyin_bazi.BaziGender.male,
)
result, flags = bazi.calculate_lunar_day(
    lunar_date, hour=14, minute=15,
    gender=taiyin_bazi.BaziGender.male,
)
```

农历入口通过绑定的 `bazi.chinese_calendar` 转换，不会另起一套历法配置。

## 真太阳时排盘

部分八字流派会把地方视太阳时（通常简称“真太阳时”）作为排盘时钟。现在直接显式
选择时钟即可；`calculate_local()` 的输入仍是原始民用钟表，内部先确定唯一 UTC 瞬间，
再计算平太阳时或真太阳时。

```python
import math

clock = taiyin_bazi.BaziClock(
    taiyin_bazi.BaziClockMode.apparentSolar,
    math.radians(118.582),
)
result, result_flags = bazi.calculate_local(
    taiyin.AstroDateTime(2003, 3, 13, 14, 15),
    gender=taiyin_bazi.BaziGender.male,
    clock=clock,
)
print(result.clockTime, result.chartTime, result.pillars, result_flags)
```

context 会按已配置的 EOP/外推策略完成 UTC→UT1。`instantUtc` 是物理瞬间，
`clockTime` 是原始民用钟表，`chartTime` 是四柱和起运实际使用的排盘时钟；旧的
`localTime` 是 `chartTime` 的兼容别名。

`ChineseCalendarConfig.local_astronomical_meridian()` 选择的是地方平太阳时日界，并按
当地日界重建天文农历；`utc_offset_minutes` 仍独立表示出生钟表的法定 UTC 偏移。
它不包含均时差，不等于“开启真太阳时”。

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
