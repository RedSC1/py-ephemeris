# 日月食、掩星与轨道

## 日月食

`context.eclipses` 支持全球日食/月食搜索、指定地点的局部食分和接触时刻：

```python
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
start = taiyin.JulianDate.from_double(2460400.5)

global_solar, global_flags = ctx.eclipses.next_solar_at_ut1(start)
print(global_solar.kinds, global_solar.maximum)

ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 20.0)
)
local_solar, local_flags = ctx.eclipses.next_local_solar_at_ut1(start)
print(local_solar.kinds, local_solar.magnitude)
print("执行标记：", global_flags | local_flags)
```

全球结果提供食型、接触时刻、最大食、影锥几何和最大食地点；局部结果提供站点接触
时刻、太阳高度/方位、食分、遮蔽率及可见性标记。

对指定日食估计时刻，还可取得贝塞尔元素、贝塞尔多项式、路线行、路径曲线和地图产品。
这些接口返回数值几何和经纬度点；投影、制图和 UI 由调用者负责。

## 月掩星和月掩天体

lite 恒星表会自动载入，可直接搜索月掩心宿二等恒星：

```python
event, event_flags = ctx.occultation.next_geocentric_star_at_ut1(
    "antares", start
)
print(event.kind, event.coordinate)
print(event.firstContact, event.fourthContact)
print("执行标记：", event_flags)
```

配置地点后，可用 `next_local_star_at_ut1()` 或 `next_local_body_at_ut1()` 搜索本地可见
掩星。后续的 `*_visibility_at_ut1()` 和 `*_where_at_ut1()` 可生成可见区间、采样或路径。

## 轨道

`context.orbits` 从选中的星历路线导出瞬时轨道根数，并搜索近日点/远日点和交点：

```python
# 计算火星在该历元的瞬时密切轨道根数。
orbit, orbit_flags = ctx.orbits.osculating_at_ut1(taiyin.Body.mars, start)
print("半长轴：", orbit.semiMajorAxisAu, "AU")
print("偏心率：", orbit.eccentricity)

# 从该历元向未来搜索火星下一次到达近日点的时刻。
perihelion, perihelion_flags = ctx.orbits.search_apsis_from_ut1(
    taiyin.Body.mars, taiyin.ApsisKind.pericenter, start
)
print("下一次近日点：", perihelion.coordinate)
print("近日点距离：", perihelion.distanceAu, "AU")
print("执行标记：", orbit_flags | perihelion_flags)
```

只有在可接受用行星质心近似物理天体时，才应开启
`allow_barycenter_approximation=True`。
