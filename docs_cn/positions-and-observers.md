# 位置、观测者与天象

先创建运行时、计算上下文和时间坐标。未指定数据路径时，`Ephemeris()` 会使用
wheel 随附的星历和 OPC 索引：

```python
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
ut1 = taiyin.JulianDate.from_double(2460310.5)

state, state_flags = ctx.position.state_at_ut1(taiyin.Body.mars, ut1)
assert ctx.last_status == 0
print(state.position_au)
print(state_flags)
```

`context.position.at_ut1(...)` 返回 `(坐标, result_flags)`；其中坐标是紧凑坐标元组：
`(黄经, 黄纬, 距离)`；指定 `PositionFlag.speed` 后附加三个速度值。
`state_at_ut1(...)` 返回 `(state, result_flags)`，其中 `state` 包含笛卡尔位置、
速度和加速度，单位为 AU 体系。已知 TT 或 TDB 输入时，应选择对应的方法，
不要把 UTC 民用时间直接当成 UT1。

## 视位置改正

新建 context 默认采用普通视位置口径：开启光行时、年周光行差，以及太阳造成的
引力偏折。默认偏折体列表只有太阳；Shapiro 延迟默认不开启。

正常使用无需额外配置。若此前自定义或清空过配置，可显式恢复这三个开关和内置
太阳偏折体：

```python
ctx.configuration.set_apparent_config(taiyin.ApparentConfig(
    flags=frozenset((
        taiyin.ApparentFlag.lightTime,
        taiyin.ApparentFlag.aberration,
        taiyin.ApparentFlag.deflection,
    )),
))
ctx.configuration.use_solar_deflector()
```

`speed` 与这些改正可以同时使用。它会在改正后的位置后面追加三个坐标速度：

```python
jupiter, jupiter_flags = ctx.position.at_ut1(
    taiyin.Body.jupiter,
    ut1,
    flags=(taiyin.PositionFlag.speed,),
)
lon, lat, distance, lon_rate, lat_rate, distance_rate = jupiter
```

若只想对某一次计算关闭某项改正，可分别传 `no_aberr` 或 `no_gdefl`：

```python
without_aberration, aberration_flags = ctx.position.at_ut1(
    taiyin.Body.jupiter,
    ut1,
    flags=(taiyin.PositionFlag.no_aberr,),
)
without_deflection, deflection_flags = ctx.position.at_ut1(
    taiyin.Body.jupiter,
    ut1,
    flags=(taiyin.PositionFlag.no_gdefl,),
)
```

`PositionFlag.astrometric` 保留光行时，但关闭光行差、引力偏折和 Shapiro
延迟；`PositionFlag.truepos` 切换到几何真位置，并连光行时一起关闭。

要替换默认的“仅太阳”偏折体列表，可向 `set_deflectors()` 传入任意可迭代的
`ApparentDeflector` 序列。`solar_deflector_index` 指明其中哪一项是年周光行差和
太阳专用改正所使用的太阳：

```python
solar_rs_au = 1.97412574336e-8
ctx.configuration.set_deflectors(
    [
        taiyin.ApparentDeflector(
            body_id=taiyin.Body.sun.id,
            schwarzschild_radius_au=solar_rs_au,
        ),
        taiyin.ApparentDeflector(
            body_id=taiyin.Body.jupiter.id,
            schwarzschild_radius_au=solar_rs_au * 0.0009547919,
        ),
    ],
    solar_deflector_index=0,
)
```

`set_deflectors()` 会整体替换列表，不是追加。调用 `use_solar_deflector()` 可恢复
内置的“仅太阳”配置。若光行差或引力偏折仍处于开启状态，不要把偏折体列表留空。

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
values, result_flags = ctx.position.at_ut1(taiyin.Body.mars, ut1, flags)
lon, lat, distance, lon_rate, lat_rate, distance_rate = values
```

原生状态失败会抛出 `taiyin.EphemerisError` 的具体子类，例如
`EphemerisRouteError`、`DataFileError`、`TimeScaleError` 或
`EventSearchError`。异常对象的 `status`、`status_code`、`status_name`、
`operation`、`detail` 和 `category` 保存本次调用自己的错误信息，不依赖可能被
其他线程覆盖的 context 最近一次诊断快照。参数类型或 Python 层预校验失败仍使用
`TypeError`/`ValueError`。

`batch_at_tt()` 和 `batch_at_ut1()` 对一组天体采用 `(values, result_flags)` 的紧凑
返回形式。Python 热循环中可传入预先合并好的整数 flag mask，避免每次重新组合 flags。

单次计算的路线选择、覆盖范围和时间尺度回退可从返回的 `result_flags` 读取；context
还保留惰性诊断快照以便调试，正常成功路径不会构造诊断对象。多个线程可以共享已经
配置完成的 context，同时执行只读的位置、状态和搜索计算。每次返回的值与 flags 都属于
各自调用；`last_status`、`last_operation`、`last_diagnostic` 和 `last_result_flags` 只是
最近一次调用的调试快照，并发时可能按任意顺序被覆盖，不能用来配对某一次调用的结果。
配置修改、日历或 chart 修改、回调注册以及 `close()` 不得与活动计算重叠。

这里保证的是并发安全，不是线性加速。标量 OPM2 位置计算本身已经很短，多线程目前会在
进程级缓存元数据上发生竞争，通常应采用顺序调用或 batch；线程更适合粒度较大的独立搜索，
并应在目标机器上按实际 provider 做基准测试。每线程 clone context 可以隔离可变计算状态，
但不会复制进程级星历数据缓存。

## 地球观测者与高度角方位角

先配置观测者，才能请求站心或地平坐标输出：

```python
ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 20.0)
)
ctx.configuration.set_standard_atmosphere()

moon, moon_flags = ctx.observed.at_ut1(
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
print(moon_flags)
```

经度东正西负，纬度北正南负。目前高度角、方位角和大气折射只支持地球观测者。

## 行星天象

`context.phenomena` 可计算日月和行星的相角、照明比例、日距角、视直径、视星等
与视差：

```python
venus, venus_flags = ctx.phenomena.at_ut1(taiyin.Body.venus, ut1)
print(venus.illuminatedFraction)
print(venus.apparentMagnitude)
print(venus_flags)

天象方法返回 `(result, result_flags)`，失败时抛出异常。使用外部数据或覆盖范围边缘的
数据时，可在调用后立即读取 `ctx.last_status` 与 `ctx.last_diagnostic`，确认路线来源
和回退信息。
