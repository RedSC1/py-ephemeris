# 紫微排盘时钟（未发布）

`ZiweiClock` 选择实际排盘的虚拟时钟，与农历月份结构、定朔日界配置独立：
`fixedOffset` 为固定偏移，`meanSolar` 为地方平太阳时，`apparentSolar` 为地方
视太阳时（真太阳时）。经度用弧度、东经为正。

注意：新接口明确接收 **UT1**。固定偏移是 UT1 加历法上下文的偏移，并非
UTC/DST 转换。若手上是 UTC，请先走基础时间转换接口，明确是否允许缺 EOP
时估算；不要只换类型名称。

```python
import math
import taiyin
import taiyin_ziwei as zw

ctx = taiyin.Ephemeris().create_context()
ziwei = ctx.ziwei()
clock = zw.ZiweiClock(zw.ZiweiClockMode.apparentSolar, math.radians(118.582))
# 这里明确输入真太阳时钟表字段，不是 UTC+8 的民用时间。
instant, flags = ziwei.chart_time_to_ut1(
    taiyin.AstroDateTime(2003, 3, 13, 14, 15), clock=clock)
chart, flags = ziwei.create_chart_at_ut1(
    instant, gender=zw.ZiweiGender.male, clock=clock)
target, flags = ziwei.step_flow_hour_at_ut1(instant, clock=clock)
flow, flags = chart.set_flow_at_ut1(target.instantUt1, clock=clock)
```

- 正反转换：`chart_time_from_ut1` / `chart_time_to_ut1`。
- 排盘、流运：`create_chart_at_ut1` / `chart.set_flow_at_ut1`。
- 导航：`step_flow_hour_at_ut1` / `step_flow_day_at_ut1`，`direction=1/-1`。
- 反查：`reverse_lookup_tier1_at_ut1(start, end, gender=..., query=..., clock=...)`。

均返回 `(结果, result_flags)`，致命错误抛异常。新导航/反查结果的物理时间字段
叫 `instantUt1`。旧的双时间入口保留，但不会从一对时间自动猜测真太阳时模式。

导航保留分秒。早晚子分开的两种规则下，向前在 22:00–01:00 走一小时，向后
在 23:00–02:00 走一小时，其他时候走两小时；流日走一个虚拟历法日。
真太阳时每次重新反解目标瞬间，不能直接给 UT1 加 86400 秒代替。逆解失败报错。

年/月柱、节气切换仍按物理瞬间判断；紫微农历标签、日/时规则才使用虚拟时钟。
前一个节的虚拟时间在该节的真实瞬间重新计算，不套用今天的均时差。
反查扫描实际时辰边界和有效节界（含历史历法指定日界），返回候选时段起点，
不是精确出生时间。后续流运/导航显式传同一个 clock。

需要配套的基础包和紫微包新构建。正式程序建议 `with` 或关闭所属上下文。

Python 层只转换参数和结果。排盘、流运、导航、反查直接使用 C++ 核心的原始
实现；历法和星历调用通过版本校验的内部桥接复用基础包已有 context，不再维护
另一份 Python 推导规则，也不加载第二套星历运行时。
