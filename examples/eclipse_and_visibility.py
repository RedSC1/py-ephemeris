"""Search a local solar eclipse and the next sunrise with bundled data."""

import taiyin


def main() -> None:
    eph = taiyin.Ephemeris()
    context = eph.create_context()
    context.configuration.set_geocentric_observer(
        observer_id=taiyin.Body.earth.id,
        center_id=taiyin.Body.earth.id,
    )
    context.configuration.set_observer_location(
        taiyin.ObserverLocation(118.582, 37.449, 20.0)
    )
    context.configuration.set_standard_atmosphere()

    # UT+08:00 midnight on 2024-01-01, converted to UTC for the search.
    start = taiyin.AstroDateTime(2024, 1, 1).to_julian_date().add_seconds(-8 * 3600)
    end = start.add_seconds(2 * 86400)

    sunrise = context.visibility.solar_rise_set_at_ut1(
        start,
        end,
        event=taiyin.VisibilityEventKind.rise,
    )
    print("Next sunrise:", sunrise.coordinate)

    eclipse = context.eclipses.next_local_solar_at_ut1(start)
    print("Local eclipse kinds:", eclipse.kinds)
    print("Local greatest time:", eclipse.maximum)
    print("Local magnitude:", eclipse.magnitude)


if __name__ == "__main__":
    main()
