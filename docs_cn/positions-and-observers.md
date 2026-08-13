# 位置、观测者与天象

先创建运行时、计算上下文和时间坐标。未指定数据路径时，`Ephemeris()` 会使用
wheel 随附的星历和 OPC 索引：

```python
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
ut1 = taiyin.JulianDate.from_double(2460310.5)

state = ctx.position.state_at_ut1(taiyin.Body.mars, ut1)
assert ctx.last_status == 0
print(state.position_au)
```

`context.position.at_ut1(...)` 直接返回紧凑坐标元组：`(黄经, 黄纬, 距离)`；指定
`PositionFlag.speed` 后附加三个速度值。`state_at_ut1(...)` 返回笛卡尔位置、
速度和加速度，单位为 AU 体系。已知 TT 或 TDB 输入时，应选择对应的方法，
不要把 UTC 民用时间直接当成 UT1。

## 密集位置扫描

常规 `at_*` 方法本身就是紧凑路径，原生计算失败时会直接抛出异常。它返回
`(黄经, 黄纬, 距离)`；指定 `PositionFlag.speed` 后，末尾再附加三个速度值：

```python
flags = (
    taiyin.PositionFlag.radians,
    taiyin.PositionFlag.truepos,
    taiyin.PositionFlag.nonut,
    taiyin.PositionFlag.speed,
)
values = ctx.position.at_ut1(taiyin.Body.mars, ut1, flags)
lon, lat, distance, lon_rate, lat_rate, distance_rate = values
```

`batch_at_tt()` 和 `batch_at_ut1()` 对一组天体采用相同的紧凑返回
形式。Python 热循环中可传入预先合并好的整数 flag mask，避免每次重新组合 flags。

单次计算的路线选择、覆盖范围和时间尺度回退可从 context 的惰性诊断快照
读取；正常成功路径不会构造诊断对象。

## 地球观测者与高度角方位角

先配置观测者，才能请求站心或地平坐标输出：

```python
ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 20.0)
)
ctx.configuration.set_standard_atmosphere()

moon = ctx.observed.at_ut1(
    taiyin.Body.moon,
    ut1,
    flags=(
        taiyin.ObservedFlag.topocentric,
        taiyin.ObservedFlag.horizontal,
        taiyin.ObservedFlag.refraction,
    ),
)
print(moon.horizontal)
print(moon.refractedHorizontal)
```

经度东正西负，纬度北正南负。目前高度角、方位角和大气折射只支持地球观测者。

## 行星天象

`context.phenomena` 可计算日月和行星的相角、照明比例、日距角、视直径、视星等
与视差：

```python
venus = ctx.phenomena.at_ut1(taiyin.Body.venus, ut1)
print(venus.illuminatedFraction)
print(venus.apparentMagnitude)
```

天象方法直接返回结果对象，失败时抛出异常。使用外部数据或覆盖范围边缘的数据时，
可在调用后立即读取 `ctx.last_status` 与 `ctx.last_diagnostic`，确认路线来源和回退信息。
