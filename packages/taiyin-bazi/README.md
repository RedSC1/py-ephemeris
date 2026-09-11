# py-ephemeris-bazi (Taiyin BaZi)

BaZi bindings for [`py-ephemeris`](https://github.com/RedSC1/py-ephemeris).

```bash
python -m pip install py-ephemeris py-ephemeris-bazi
```

```python
import taiyin
import taiyin_bazi

eph = taiyin.Ephemeris()
ctx = eph.create_context()
local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
instant_utc = local_time.to_julian_date().add_seconds(-8 * 3600)
bazi = ctx.bazi()
result, result_flags = bazi.calculate_local(
    local_time, gender=taiyin_bazi.BaziGender.male
)
print(result.pillars, result.chart, result.qiyun)
print("Execution flags:", result_flags)
```

`EphemerisContext.bazi()` loads this installed extension on demand. The BaZi
context inherits the calculation context's configured data roots and source paths. Its
`chinese_calendar` property is shared by four-pillar, Qi-Yun, and
Renyuan-Siling calculations, so the calendar offset is configured once.

For concurrent chart work, create one `EphemerisContext` and its corresponding
BaZi facade per worker. Native chart, Qi-Yun, DaYun, and Renyuan-Siling work
releases the Python GIL; a single context/facade pair is not reentrant and must
not be used or reconfigured concurrently by multiple threads.

For a source build from this monorepo, run the following from
`packages/taiyin-bazi`. CMake prefers the sibling Taiyin C++ checkout. In an
isolated sdist build it instead fetches the public Taiyin source with Git at
the full immutable commit `df5cedcc90522cf990ee50f1991f74272a79f27b`
(post-beta.11), not a moving branch. Source builds therefore require Git
and network access unless a local checkout is supplied. Wheel users do not
need Git. The core is compiled into the extension.
`TAIYIN_SOURCE_DIR` below is used by the integration tests to locate the C++
checkout's bundled test data; it can also be passed as a CMake define to build
against another local checkout.

```bash
python -m pip install -e ".[test]"
TAIYIN_SOURCE_DIR=../../../taiyin-ephemeris python -m pytest
```

## Custom Shen Sha modules (next release)

```python
from taiyin_bazi import (
    BaziShenShaCatalog, BaziShenShaModule, BaziShenShaRule,
    BaziShenShaTargetKind,
)

catalog = BaziShenShaCatalog().add_module(BaziShenShaModule(
    "my-school", [BaziShenShaRule("day-marker", "Day marker",
        lambda value: value.target_kind == BaziShenShaTargetKind.day)],
))
with catalog:
    with catalog.create_context(disabled_ids=()) as rules:
        # chart is an existing BaziChart from bazi.calc_chart(pillars).
        matches = rules.evaluate(chart, chart.dayPillar, BaziShenShaTargetKind.day)
```

Catalog updates return new objects. Built-ins (`builtin:0` … `builtin:65`)
cannot be overwritten or removed; duplicate module/rule IDs are errors.
`remove_module("my-school")` removes ALL rules in that module from the new
catalog, while existing contexts retain their snapshots and callbacks.
Use `disabled_ids` to disable entries without modifying their definitions.

Predicates receive immutable input containing packed Ganzhi bytes (`pillars`
in year/month/day/hour order), target, target_kind and optional gender. Return
an actual bool; exceptions propagate unchanged. Evaluations retain the GIL;
mutable state captured by callbacks remains the caller's responsibility.
Use `close()` or `with` for catalogs and contexts, especially when a predicate
captures its context or a bound-method owner holding it. Python GC cannot see
these native-held callback cycles. Closing releases this handle's references;
other snapshots and an already-running evaluation retain their own references.
Close is idempotent; subsequent calls raise RuntimeError. Match builtin_id is
None for custom rules.

中文：目录增删均返回新对象，不能覆盖或删除内置规则。移除 `my-school`
会移除新目录中该模块的全部神煞，已有上下文不受影响。回调必须返回 bool；
异常原样抛出，不写入星历 context 的 last_diagnostic。回调求值保留 GIL，
不承诺 Python 线程并行加速；不要把闭包中的可变状态当成自动线程安全。
目录和上下文支持 `close()` / `with`。回调反向引用上下文或持有上下文的对象
时，必须显式关闭以解除 native 引用环；关闭当前对象不影响其他已有快照。
