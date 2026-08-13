"""Calculate a BaZi extension demo (requires py-ephemeris-bazi)."""

import taiyin
import taiyin_bazi


def main() -> None:
    local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
    instant_utc = local_time.to_julian_date().add_seconds(-8 * 3600)

    eph = taiyin.Ephemeris()
    context = eph.create_context()

    pillars = context.chinese_calendar.four_pillars(instant_utc, local_time)
    bazi = eph.create_bazi()
    chart = bazi.calc_chart(pillars)
    print("Four pillars:", pillars)
    print("BaZi chart:", chart)

    # Gender is required only for Qi-Yun direction; this is a demo convention.
    qiyun = bazi.calc_qiyun(
        instant_utc,
        local_time,
        chart,
        taiyin_bazi.BaziGender.male,
    )
    print("Qi-Yun:", qiyun.value)
    print(
        "Year-stem Ten God:",
        bazi.get_ten_god(pillars.day.stem_id, pillars.year.stem_id),
    )


if __name__ == "__main__":
    main()
