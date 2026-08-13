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

sun = ctx.astrology.sidereal_position_at_ut1(
    taiyin.Body.sun,
    ut1,
    ayanamsha=taiyin.Ayanamsha.lahiri,
)
houses = ctx.astrology.houses_at_ut1(
    ut1,
    system=taiyin.HouseSystem.porphyry,
)

degrees = lambda radians: math.degrees(radians) % 360.0
print(degrees(sun.siderealLongitudeRadians))
print(degrees(houses.ascendantRadians))
```

内置 ayanamsha 包括 Fagan/Bradley、Lahiri、Raman、Krishnamurti、
Galactic Center 0 Sagittarius 和 True Chitra。内置分宫制包括 Whole Sign、
Equal、Porphyry、Placidus、Koch、Regiomontanus、Campanus、Alcabitius、
Polich/Page 和 Morinus。

API 返回数值弧度和宫头。星座文字、相位解释、盘面符号和 UI 应由 Python 调用层实现。
也可以在 `Ephemeris` 上注册 Python 回调实现自定义 ayanamsha 或分宫制；细节见
[英文 API Reference](../docs/api.md)。
