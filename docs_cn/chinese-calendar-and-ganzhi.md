# 农历、节气与干支历

农历、节气、干支和四柱都在基础 `taiyin` 包中；不需要 `py-ephemeris-bazi`。

默认采用中国标准历史历法。三个模式把“农历结构”与“用户当地民用时间”区分开：

```python
historical = taiyin.ChineseCalendarConfig.historical_china(9 * 60)
china_astronomical = (
    taiyin.ChineseCalendarConfig.china_standard_astronomical(9 * 60)
)
local_astronomical = (
    taiyin.ChineseCalendarConfig.local_astronomical_utc_offset(9 * 60)
)
vietnam_meridian = taiyin.ChineseCalendarConfig.local_astronomical_meridian(
    105.8,
    utc_offset_minutes=7 * 60,
)
```

前两种分别以中国历史 profile、UTC+08 天文定朔定气生成中国标准农历日期表，再把
这张表的公历日期标签用于用户当地的同名日期；不会把当地钟表字段转换成北京时间。
`local_astronomical_utc_offset()` 才会按当地日界重新给朔和中气归日，并重排月份与
闰月；`local_astronomical_meridian()` 使用地方平太阳时经线完成同一件事，但其中的
`utc_offset_minutes` 仍表示用户的法定/显示钟表时间，经度只决定朔和中气归属哪个
历日。纬度不会改变地心朔或节气的物理时刻。

## 公历与农历转换

```python
import taiyin

ctx = taiyin.Ephemeris().create_context()
lunar, lunar_flags = ctx.chinese_calendar.from_solar(
    taiyin.SolarDate(2003, 3, 13)
)
print(lunar.year, lunar.month, lunar.day, lunar.isLeap, lunar.monthName)

named = taiyin.LunarDate.from_string(2003, "九月", 1)
solar, solar_flags = ctx.chinese_calendar.from_lunar(named)
print(solar)
print("执行标记：", lunar_flags | solar_flags)
```

若输入是一个 UTC/UT 风格的儒略日瞬间，使用 `from_instant_ut()`；它先求配置对应的
当地民用日期，再按所选模式查询农历。
[三模式朔日示例](../docs/examples/chinese_calendar_modes.md)用同一瞬间展示中国标准
日期表与印度当地重排农历的差异。

`LunarDate.from_string()` 支持 `正月`、`冬月`、`腊月`、`闰五月`、`后九月`、
`拾贰` 和 `十三` 等常见写法。字符串解析只构造请求；某月是否存在、是否为闰月和
29/30 天的实际校验仍由 native 农历规则完成。

历史历法中的特殊月份通过现有 `monthName` 与 `isLeap` 字段表达；不要仅凭月份名字
自行猜测是否为闰月。

## 节气与四柱

四柱需要天文 UTC 瞬间和用于民用时辰规则的民用时间：

```python
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
instant_utc = local_time.to_julian_date().add_seconds(-8 * 3600)
pillars, pillar_flags = ctx.chinese_calendar.four_pillars(
    instant_utc, local_time
)

print(pillars.year, pillars.month, pillars.day, pillars.hour)
print("执行标记：", pillar_flags)
print(ctx.ganzhi.nayin_element(pillars.day))
```

`context.chinese_calendar` 还提供年历、前后节气和指定节气查询；
`context.ganzhi` 提供创建/推进干支、月柱、时柱、日柱及纳音 ID/五行等纯规则操作。
干支规则本身也可脱离八字单独用于传统历法。
