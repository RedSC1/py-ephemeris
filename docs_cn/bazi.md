# 八字扩展

八字单独发布，使只需要天文、农历、干支、分宫或日月食的用户不必安装八字 native
extension：

```bash
python -m pip install py-ephemeris py-ephemeris-bazi
```

导入 `taiyin_bazi` 后，基础运行时 `Ephemeris` 才会注册 `create_bazi()`。八字上下文
会继承主包运行时配置的数据目录和外部数据路径。

```python
import taiyin
import taiyin_bazi

eph = taiyin.Ephemeris()
ctx = eph.create_context()
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
instant_utc = local_time.to_julian_date().add_seconds(-8 * 3600)
pillars = ctx.chinese_calendar.four_pillars(instant_utc, local_time)

bazi = eph.create_bazi()
chart = bazi.calc_chart(pillars)
print(chart.hiddenStems, chart.visibleTenGods, chart.nayinIds)
```

## 起运与大运

起运方向需要性别约定：

```python
qiyun = bazi.calc_qiyun(
    instant_utc,
    local_time,
    chart,
    taiyin_bazi.BaziGender.male,
)
dayun = bazi.fill_dayun(local_time, chart, qiyun.value, 10)
print(qiyun.value.startCivilTime, dayun)
```

四柱和 `BaziChart` 本身不区分性别。`BaziContextConfig` 可选择起运时间模型、方向
模型和大运边界约定。

## 规则与分析接口

`BaziContext` 包括十神、藏干、十二长生、干支关系、流年/月/日/时、小运、大运、
人元司令、神煞与盘内关系分析。例如：

```python
year_ten_god = bazi.get_ten_god(
    pillars.day.stem_id, pillars.year.stem_id
)
relations = bazi.collect_chart_relations(chart)
print(year_ten_god, relations)
```

可运行代码见[八字扩展示例](../docs/examples/bazi_extension.md)；完整函数表在
[英文 API Reference](../docs/api.md)。
