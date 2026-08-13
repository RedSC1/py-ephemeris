"""Calculate a BaZi extension demo (requires py-ephemeris-bazi)."""

import taiyin
import taiyin_bazi


def main() -> None:
    local_time = taiyin.AstroDateTime(2003, 3, 13, 14, 15)

    eph = taiyin.Ephemeris()
    ctx = eph.create_context()
    bazi = ctx.bazi()
    # Gender controls Qi-Yun direction; the pillars and chart are gender-neutral.
    result = bazi.calculate_local(
        local_time,
        gender=taiyin_bazi.BaziGender.male,
    )
    print("Four pillars:", result.pillars)
    print("BaZi chart:", result.chart)
    print("Qi-Yun:", result.qiyun)
    print(
        "Year-stem Ten God:",
        bazi.get_ten_god(
            result.pillars.day.stem_id, result.pillars.year.stem_id
        ),
    )


if __name__ == "__main__":
    main()
