"""Compare packaged OPM2 with an original DE442 BSP through public Python APIs."""

from __future__ import annotations

import argparse
import math
import statistics
from pathlib import Path

import taiyin


AU_KILOMETERS = 149_597_870.7
ARCSECONDS_PER_RADIAN = 206_264.80624709636
BODIES = (
    taiyin.Body.sun,
    taiyin.Body.moon,
    taiyin.Body.mercury_barycenter,
    taiyin.Body.venus_barycenter,
    taiyin.Body.mars_barycenter,
    taiyin.Body.jupiter_barycenter,
    taiyin.Body.saturn_barycenter,
    taiyin.Body.uranus_barycenter,
    taiyin.Body.neptune_barycenter,
    taiyin.Body.pluto_barycenter,
)
FLAGS = (
    taiyin.PositionFlag.xyz,
    taiyin.PositionFlag.equatorial,
    taiyin.PositionFlag.radians,
    taiyin.PositionFlag.truepos,
    taiyin.PositionFlag.nonut,
)


def norm(vector) -> float:
    return math.sqrt(sum(value * value for value in vector))


def difference(left, right) -> tuple[float, float]:
    delta_km = norm(tuple(a - b for a, b in zip(left, right))) * AU_KILOMETERS
    cross = (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )
    dot = sum(a * b for a, b in zip(left, right))
    angle_arcseconds = math.atan2(norm(cross), dot) * ARCSECONDS_PER_RADIAN
    return angle_arcseconds, delta_km


def rms(values) -> float:
    return math.sqrt(statistics.fmean(value * value for value in values))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--de442-bsp", type=Path)
    parser.add_argument("--samples", type=int, default=128)
    parser.add_argument("--jd-start", type=float, default=2_300_000.0)
    parser.add_argument("--jd-end", type=float, default=2_680_000.0)
    args = parser.parse_args()
    if args.de442_bsp is not None and not args.de442_bsp.is_file():
        parser.error("--de442-bsp must name an existing file")
    if args.samples < 2:
        parser.error("--samples must be at least 2")
    if not args.jd_start < args.jd_end:
        parser.error("--jd-start must be before --jd-end")

    data_root = Path(taiyin.__file__).resolve().parent / "data"
    ephemeris = taiyin.Ephemeris(data_root=str(data_root))
    eclipse_context = ephemeris.create_context()
    eclipse_context.configuration.set_geocentric_observer(
        observer_id=taiyin.Body.earth.id,
        center_id=taiyin.Body.earth.id,
    )
    solved = eclipse_context.eclipses.solve_solar_at_ut1(
        taiyin.JulianDate.from_double(2_460_409.25),
        options=(taiyin.SolarEclipseSolveOption.includeContacts,),
    )
    pmo_contacts = (
        ("P1", taiyin.SolarEclipseContact.partialBegin, 2_460_409.154317129),
        ("C1", taiyin.SolarEclipseContact.centralBegin, 2_460_409.194432870),
        ("Greatest", taiyin.SolarEclipseContact.greatest, 2_460_409.262037037),
        ("C4", taiyin.SolarEclipseContact.centralEnd, 2_460_409.329490741),
        ("P4", taiyin.SolarEclipseContact.partialEnd, 2_460_409.369687500),
    )
    print("2024-04-08 global solar eclipse versus PMO rounded almanac values")
    print("event        Taiyin JD UT          Taiyin - PMO (seconds)")
    for name, contact, reference in pmo_contacts:
        value = solved.contacts[contact]
        print(
            f"{name:<10} {value.to_double():.9f}"
            f"          {(value.to_double() - reference) * 86400.0:+.3f}"
        )
    route = eclipse_context.eclipses.solar_eclipse_route_row_at_ut1(
        solved.maximum
    )
    print(
        "greatest location difference from rounded PMO: "
        f"latitude {(route.centerLine.latitudeDegrees - 25.285) * 3600.0:+.3f} arcsec, "
        f"longitude {(route.centerLine.longitudeDegrees + 104.143333333333) * 3600.0:+.3f} arcsec"
    )
    eclipse_context.close()

    if args.de442_bsp is None:
        print("\nPass --de442-bsp PATH to add the OPM2-versus-DE442 route comparison.")
        return

    ephemeris = taiyin.Ephemeris(
        data_root=str(data_root), source_paths=[str(args.de442_bsp)]
    )
    opm2 = ephemeris.create_context()
    spk = ephemeris.create_context()
    opm2.configuration.set_route_rule(taiyin.RouteRule.opm2)
    spk.configuration.set_route_rule(taiyin.RouteRule.spk)
    for context in (opm2, spk):
        context.configuration.set_geocentric_observer(
            observer_id=taiyin.Body.earth.id,
            center_id=taiyin.Body.earth.id,
        )

    coordinates = [
        taiyin.JulianDate.from_double(
            args.jd_start
            + (args.jd_end - args.jd_start) * index / (args.samples - 1)
        )
        for index in range(args.samples)
    ]
    print(
        f"DE442 comparison through public Python APIs: {args.samples} samples, "
        f"JD {args.jd_start:.1f}..{args.jd_end:.1f}"
    )
    print("body                      angular RMS/max (arcsec)       vector RMS/max (km)")
    aggregate_angles = []
    aggregate_distances = []
    for body in BODIES:
        angles = []
        distances = []
        for coordinate in coordinates:
            opm2_value = opm2.position.at_ut1(body, coordinate, FLAGS)[:3]
            spk_value = spk.position.at_ut1(body, coordinate, FLAGS)[:3]
            angle, distance = difference(opm2_value, spk_value)
            angles.append(angle)
            distances.append(distance)
        aggregate_angles.extend(angles)
        aggregate_distances.extend(distances)
        print(
            f"{body.name:<25} {rms(angles):10.7f} / {max(angles):10.7f}"
            f"        {rms(distances):10.6f} / {max(distances):10.6f}"
        )
    print(
        f"{'all samples':<25} {rms(aggregate_angles):10.7f} / "
        f"{max(aggregate_angles):10.7f}        "
        f"{rms(aggregate_distances):10.6f} / {max(aggregate_distances):10.6f}"
    )
    opm2.close()
    spk.close()


if __name__ == "__main__":
    main()
