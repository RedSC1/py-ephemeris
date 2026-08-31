# 恒星表

默认 wheel 会按进程自动载入 lite TSC1 恒星表，其中包含 2,057 颗恒星、12,242 个别名，
并完整覆盖 Stellarium 中国星官与西方黄道星座连线使用的 HIP 恒星
和西方黄道代表星：

```python
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
ut1 = taiyin.JulianDate.from_double(2460310.5)

antares, star_flags = ctx.stars.at_ut1("antares", ut1)
print(antares.coordinates)
print("执行标记：", star_flags)
print(eph.star_catalog.magnitude_of("角宿一"))
```

恒星表注册是进程级的。可在查询前使用 `eph.star_catalog.add_tsc1(path)` 或
`add_tsf1(path)` 增加文件。若多个文件定义同一别名，先注册的目录/文件顺序会影响
匹配结果；要得到可复现的名称解析，应使用整理过的星表集合。

恒星同样可以用配置好的地球站点计算站心高度角和方位角：

```python
ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 20.0)
)
observed, observed_flags = ctx.stars.observed_at_ut1(
    "antares",
    ut1,
    flags=(taiyin.ObservedFlag.topocentric, taiyin.ObservedFlag.horizontal),
)
print(observed.horizontal)
print("执行标记：", observed_flags)
```

清空进程级星表后的重新加载方式及随附文件路径，见[数据指南](data.md)。
