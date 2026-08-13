# 日月食、掩星与轨道

## 日月食

`context.eclipses` 支持全球日食/月食搜索、指定地点的局部食分和接触时刻：

```python
import taiyin

eph = taiyin.Ephemeris()
ctx = eph.create_context()
start = taiyin.JulianDate.from_double(2460400.5)

global_solar = ctx.eclipses.next_solar_at_ut1(start)
print(global_solar.value.kinds, global_solar.value.maximum)

ctx.configuration.set_observer_location(
    taiyin.ObserverLocation(118.582, 37.449, 20.0)
)
local_solar = ctx.eclipses.next_local_solar_at_ut1(start)
print(local_solar.value.kinds, local_solar.value.magnitude)
```

全球结果提供食型、接触时刻、最大食、影锥几何和最大食地点；局部结果提供站点接触
时刻、太阳高度/方位、食分、遮蔽率及可见性标记。

对指定日食估计时刻，还可取得贝塞尔元素、贝塞尔多项式、路线行、路径曲线和地图产品。
这些接口返回数值几何和经纬度点；投影、制图和 UI 由调用者负责。

## 月掩星和月掩天体

lite 恒星表会自动载入，可直接搜索月掩心宿二等恒星：

```python
event = ctx.occultation.next_geocentric_star_at_ut1("antares", start)
print(event.value.kind, event.value.coordinate)
print(event.value.firstContact, event.value.fourthContact)
```

配置地点后，可用 `next_local_star_at_ut1()` 或 `next_local_body_at_ut1()` 搜索本地可见
掩星。后续的 `*_visibility_at_ut1()` 和 `*_where_at_ut1()` 可生成可见区间、采样或路径。

## 轨道

`context.orbits` 从选中的星历路线导出瞬时轨道根数，并搜索近日点/远日点和交点：

```python
orbit = ctx.orbits.osculating_at_ut1(taiyin.Body.mars, start)
perihelion = ctx.orbits.search_apsis_from_ut1(
    taiyin.Body.mars, taiyin.ApsisKind.pericenter, start
)
print(orbit.value.semiMajorAxisAu, perihelion.value.coordinate)
```

只有在可接受用行星质心近似物理天体时，才应开启
`allow_barycenter_approximation=True`。
