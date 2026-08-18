"""Create a Ziwei Doushu chart and its annual-through-hourly flow layers.

Requires both ``py-ephemeris`` and ``py-ephemeris-ziwei``.
"""

import taiyin
import taiyin_ziwei


def main() -> None:
    eph = taiyin.Ephemeris()
    ctx = eph.create_context()
    ziwei = ctx.ziwei()

    local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
    chart = ziwei.calculate_local(
        local_time,
        gender=taiyin_ziwei.ZiweiGender.male,
    )

    print("Bureau:", chart.summary.bureau)
    print("Ziwei physical branch:", chart.anchors.ziwei)
    for palace in chart.palaces:
        print(palace.palace.name, palace.branchId, palace.stemId,
              [star.key for star in palace.stars])

    target_local = taiyin.AstroDateTime(2025, 3, 13, 14, 15)
    target_utc = target_local.to_julian_date().add_seconds(-8 * 3600)
    flow = chart.set_flow(target_utc, target_local)
    print("Flow decade:", flow.decade)
    print("Flow-year life palace:", chart.flow_layer_summary(
        taiyin_ziwei.ZiweiFlowLevel.year
    )["life_palace"])


if __name__ == "__main__":
    main()
