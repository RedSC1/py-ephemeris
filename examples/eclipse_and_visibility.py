"""Search a local solar eclipse and the next sunrise with bundled data."""

import taiyin


def main() -> None:
    eph = taiyin.Ephemeris()
    context = eph.create_context()
    context.configuration.set_observer_location(
        taiyin.ObserverLocation(118.582, 37.449, 20.0)
    )

    # UT+08:00 midnight on 2024-01-01, converted to UTC for the search.
    start = taiyin.AstroDateTime(2024, 1, 1).to_julian_date().add_seconds(-8 * 3600)
    end = start.add_seconds(2 * 86400)

    sunrise = context.visibility.solar_rise_set_at_ut1(
        start,
        end,
        event=taiyin.VisibilityEventKind.rise,
    )
    print("Next sunrise:", sunrise.value.coordinate)

    eclipse = context.eclipses.next_local_solar_at_ut1(start)
    print("Local eclipse kinds:", eclipse.value.kinds)
    print("Local greatest time:", eclipse.value.maximum)
    print("Local magnitude:", eclipse.value.magnitude)


if __name__ == "__main__":
    main()
