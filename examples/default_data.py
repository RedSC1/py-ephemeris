"""Use the data bundled with the ``taiyin`` wheel.

Run after installing py-ephemeris. No DLL path or ephemeris-data path is
required for these default calculations.
"""

import taiyin


def main() -> None:
    eph = taiyin.Ephemeris()
    context = eph.create_context()
    jd = taiyin.JulianDate.from_double(2460310.5)

    # AUTO chooses the DE442-derived major-body OPM2 product where available.
    mars, mars_flags = context.position.state_at_ut1(taiyin.Body.mars, jd)
    print("Mars SSB state:", mars.position_au, mars_flags)

    # The selected precise asteroid OPM2 files are included too.
    ceres, ceres_flags = context.position.state_at_ut1(2000001, jd)
    print("Ceres SSB state:", ceres.position_au, ceres_flags)

    # The bundled lite star catalog is loaded by Ephemeris().
    antares, antares_flags = context.stars.at_ut1("antares", jd)
    print("Antares coordinates:", antares.coordinates, antares_flags)


if __name__ == "__main__":
    main()
