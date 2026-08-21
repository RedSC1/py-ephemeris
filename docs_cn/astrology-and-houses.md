# 恒星黄道、岁差与分宫制

恒星黄道位置、ayanamsha、月亮交点/近地点、岁差章动模型和分宫制均属于主包
`taiyin`，不需要安装 `py-ephemeris-bazi`。

```python
import math
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
ut1 = taiyin.JulianDate.from_double(2460310.5)
ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 20.0)
)

sun, sun_flags = ctx.astrology.sidereal_position_at_ut1(
    taiyin.Body.sun,
    ut1,
    ayanamsha=taiyin.Ayanamsha.lahiri,
    flags=(taiyin.PositionFlag.speed,),
)
houses, house_flags = ctx.astrology.houses_at_ut1(
    ut1,
    system=taiyin.HouseSystem.porphyry,
)

degrees = lambda radians: math.degrees(radians) % 360.0
print(degrees(sun.siderealLongitudeRadians))
print(sun.siderealLongitudeRateRadiansPerDay)
print(degrees(houses.ascendantRadians))
print("执行标记：", sun_flags | house_flags)
```

`sidereal_position_at_ut1()` 不是另一条独立星历路线。它先使用 context 的回归黄道
位置管线，再应用指定的 ayanamsha 与参考平面策略，因此会继承默认的光行时、年周
光行差和太阳引力偏折设置。传入 `PositionFlag.speed` 后还会返回用于判断逆行的恒星
黄道经度速度；`speed` 与默认太阳偏折体可以同时使用。若确实要切换计算口径，也可
使用[位置指南](positions-and-observers.md#视位置改正)所述的 `no_aberr`、`no_gdefl`、
`astrometric` 和 `truepos`。

内置 ayanamsha 包括 Fagan/Bradley、Lahiri、Raman、Krishnamurti、
Galactic Center 0 Sagittarius 和 True Chitra。内置分宫制包括 Whole Sign、
Equal、Porphyry、Placidus、Koch、Regiomontanus、Campanus、Alcabitius、
Polich/Page 和 Morinus。

API 返回数值弧度和宫头。星座文字、相位解释、盘面符号和 UI 应由 Python 调用层实现。
也可以在 `Ephemeris` 上注册 Python 回调实现自定义 ayanamsha 或分宫制；细节见
[英文 API Reference](../docs/api.md)。
