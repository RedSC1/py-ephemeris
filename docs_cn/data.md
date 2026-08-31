# 数据包与外部星历

默认 `Ephemeris()` 使用安装目录内的 `taiyin/data/index.opc`。当前 Python wheel
随附的数据包括：

| 产品 | 用途与范围 |
| --- | --- |
| DE442 衍生主要天体 OPM2 | 默认 AUTO 路线；日、月、行星质心、EMB，约 1550–2650 年 |
| 精确小行星 OPM2 | Ceres、Pallas、Juno、Vesta、Eros、Chiron、Pholus、Nessus、Lilith (1181) |
| 土星/天王星 COB OPM2 | 在覆盖范围内修正物理天体位置 |
| SBDB TKC1 开普勒 tier | 核心天体、前 1000 编号小行星与 PHA 的近似回退 |
| lite TSC1 恒星表 | 2,057 颗恒星、12,242 个别名，完整覆盖 Stellarium 中国星官与西方黄道星座连线使用的 HIP 恒星 |

当前 wheel 不随附 DE441。未来可能提供独立的长时间跨度 DE441 数据包；目前用户可
自行加入 NASA/JPL BSP/SPK、卫星 SPK、小天体 SPK、OPM2、TKC1 或额外星表。

```python
import taiyin

eph = taiyin.Ephemeris(
    data_root="/data/main",
    source_paths=[
        "/data/satellites",
        "/data/asteroids",
        "/data/custom/de441.bsp",
        "/data/custom/extra.opm2",
    ],
)
```

`data_root` 选择一个主数据目录；不指定时使用随包数据。`source_paths` 可接受任意
多个文件或目录，并追加到主目录而非替换它。目录可带各自的 `index.opc`；单独文件则
直接加载，不会生成 OPC。

更多 OPM2、OPC、优先级与星表重载细节，见[英文 bundled-data 文档](../docs/bundled-data.md)。
