# 农历、节气与干支历

农历、节气、干支和四柱都在基础 `taiyin` 包中；不需要 `py-ephemeris-bazi`。

## 公历与农历转换

```python
import taiyin

ctx = taiyin.Ephemeris().create_context()
lunar = ctx.chinese_calendar.from_solar(taiyin.SolarDate(2003, 3, 13))
print(lunar.year, lunar.month, lunar.day, lunar.isLeap, lunar.monthName)

named = taiyin.LunarDate.from_string(2003, "九月", 1)
solar = ctx.chinese_calendar.from_lunar(named)
print(solar)
```

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
pillars = ctx.chinese_calendar.four_pillars(instant_utc, local_time)

print(pillars.year, pillars.month, pillars.day, pillars.hour)
print(ctx.ganzhi.nayin_element(pillars.day))
```

`context.chinese_calendar` 还提供年历、前后节气和指定节气查询；
`context.ganzhi` 提供创建/推进干支、月柱、时柱、日柱及纳音 ID/五行等纯规则操作。
干支规则本身也可脱离八字单独用于传统历法。
