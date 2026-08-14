"""Compare the three Chinese-calendar modes at a new-moon boundary."""

import taiyin


def lunar_label(value: taiyin.LunarDate) -> str:
    return f"{value.year}-{value.month}-{value.day} ({value.monthName.name})"


def main() -> None:
    eph = taiyin.Ephemeris()
    instant_ut = taiyin.AstroDateTime(
        2026, 8, 12, 17, 40
    ).to_julian_date()

    # The new moon is 2026-08-12 17:36:45 UT: 01:36 in Beijing on
    # August 13, but 23:06 in India on August 12.
    beijing = eph.create_context(
        chinese_calendar_config=taiyin.ChineseCalendarConfig.historical_china(
            8 * 60
        )
    )
    india_historical = eph.create_context(
        chinese_calendar_config=taiyin.ChineseCalendarConfig.historical_china(
            5 * 60 + 30
        )
    )
    india_china_astronomical = eph.create_context(
        chinese_calendar_config=(
            taiyin.ChineseCalendarConfig.china_standard_astronomical(
                5 * 60 + 30
            )
        )
    )
    india_local_astronomical = eph.create_context(
        chinese_calendar_config=(
            taiyin.ChineseCalendarConfig.local_astronomical_utc_offset(
                5 * 60 + 30
            )
        )
    )

    print(
        "Beijing / China historical:",
        lunar_label(beijing.chinese_calendar.from_instant_ut(instant_ut)),
    )
    print(
        "India / China historical:",
        lunar_label(
            india_historical.chinese_calendar.from_instant_ut(instant_ut)
        ),
    )
    print(
        "India / China-standard astronomical:",
        lunar_label(
            india_china_astronomical.chinese_calendar.from_instant_ut(
                instant_ut
            )
        ),
    )
    print(
        "India / local astronomical:",
        lunar_label(
            india_local_astronomical.chinese_calendar.from_instant_ut(
                instant_ut
            )
        ),
    )

    special = india_historical.chinese_calendar.from_solar(
        taiyin.SolarDate(23, 12, 2)
    )
    print("Historical alternate month:", lunar_label(special))


if __name__ == "__main__":
    main()
