"""Longitude, aspect, station, and lunar-phase event searches."""

import math
from dataclasses import dataclass, field
from enum import Enum

from .position import EphemerisResult, PositionFlag, _diagnostic, _target_id, position_flag_mask
from .configuration import ObserverLocation


class EventSearchOption(Enum):
    reverse = 1 << 32
    refraction = 1 << 33
    noRefraction = 1 << 34

    @property
    def mask(self):
        return self.value


@dataclass(frozen=True)
class LongitudeStation:
    coordinate: object
    longitudeRadians: float


@dataclass(frozen=True)
class ExactAspectEvent:
    coordinate: object
    aspectRadians: float


class GreatestElongationKind(Enum):
    eastern = 1 << 0
    western = 1 << 1
    unknown = 0

    @classmethod
    def from_mask(cls, value):
        return cls(value) if value in (cls.eastern.value, cls.western.value) else cls.unknown


class SolarTransitKind(Enum):
    partial = 1 << 0
    fullDisk = 1 << 1

    @classmethod
    def from_mask(cls, value):
        return frozenset(item for item in cls if value & item.value)


class SolarTransitVisibilityFlag(Enum):
    visibleAtObserver = 1 << 8
    t1Visible = 1 << 9
    t2Visible = 1 << 10
    greatestVisible = 1 << 11
    t3Visible = 1 << 12
    t4Visible = 1 << 13

    @classmethod
    def from_mask(cls, value):
        return frozenset(item for item in cls if value & item.value)


@dataclass(frozen=True)
class EventPhenomena:
    phaseAngleRadians: float
    illuminatedFraction: float
    solarElongationRadians: float
    apparentDiameterRadians: float
    apparentMagnitude: float
    horizontalParallaxRadians: object


@dataclass(frozen=True)
class GreatestElongationEvent:
    bodyId: int
    coordinate: object
    elongationRadians: float
    relativeLongitudeRadians: float
    kind: GreatestElongationKind
    iterationCount: int
    evaluationCount: int
    phenomena: EventPhenomena


@dataclass(frozen=True)
class MinimumAngularSeparationEvent:
    bodyAId: int
    bodyBId: int
    coordinate: object
    separationRadians: float
    separationRateRadiansPerDay: float
    iterationCount: int
    evaluationCount: int


@dataclass(frozen=True)
class SolarTransitEvent:
    bodyId: int
    kinds: frozenset
    greatest: object
    minimumSeparationRadians: float
    sunRadiusRadians: float
    bodyRadiusRadians: float
    t1: object
    t2: object
    t3: object
    t4: object
    iterationCount: int
    evaluationCount: int
    _native: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class LocalSolarTransitEvent:
    global_: SolarTransitEvent
    topocentric: SolarTransitEvent
    visibilityFlags: frozenset
    contactSunAltitudeDegrees: tuple
    contactSunAzimuthDegrees: tuple
    sunrise: object
    sunset: object


def _finite(value, name):
    if not math.isfinite(value):
        raise ValueError(name + " must be finite")


def _capacity(value):
    if not isinstance(value, int) or value <= 0:
        raise ValueError("max_results must be a positive integer")


def _interval(start, end):
    if not start.to_double() < end.to_double():
        raise ValueError("start must be before end")


def _body_pair(body_a, body_b):
    first, second = _target_id(body_a), _target_id(body_b)
    if first == second:
        raise ValueError("body_a and body_b must be distinct")
    return first, second


def _event_flags(position_flags, options=(), allowed_options=()):
    values = () if isinstance(position_flags, int) else position_flags
    unsupported = {PositionFlag.xyz, PositionFlag.equatorial} & set(values)
    if unsupported:
        raise ValueError("event searches require ecliptic spherical coordinates")
    unsupported_options = set(options) - set(allowed_options)
    if unsupported_options:
        raise ValueError("options contains an unsupported event-search option")
    if EventSearchOption.refraction in options and EventSearchOption.noRefraction in options:
        raise ValueError("refraction and noRefraction cannot both be selected")
    return position_flag_mask(position_flags) | sum(option.mask for option in options)


def _inner_planet(body):
    body_id = _target_id(body)
    if body_id not in (199, 299):
        raise ValueError("solar-transit and elongation searches support Mercury or Venus only")
    return body_id


def _observer(value):
    for item in (value.longitude_degrees, value.latitude_degrees, value.height_meters):
        _finite(item, "observer coordinate")
    if not -90.0 <= value.latitude_degrees <= 90.0:
        raise ValueError("observer latitude must be in [-90, 90]")
    return value


def _maybe_date(value):
    return value if math.isfinite(value.day_fraction) else None


def _solar_transit(value):
    return SolarTransitEvent(
        bodyId=value["body_id"], kinds=SolarTransitKind.from_mask(value["kind"]),
        greatest=value["greatest"], minimumSeparationRadians=value["minimum_separation_radians"],
        sunRadiusRadians=value["sun_radius_radians"], bodyRadiusRadians=value["body_radius_radians"],
        t1=_maybe_date(value["t1"]), t2=_maybe_date(value["t2"]),
        t3=_maybe_date(value["t3"]), t4=_maybe_date(value["t4"]),
        iterationCount=value["iteration_count"], evaluationCount=value["evaluation_count"], _native=value,
    )


def _local_solar_transit(value):
    return LocalSolarTransitEvent(
        global_=_solar_transit(value["global"]), topocentric=_solar_transit(value["topocentric"]),
        visibilityFlags=SolarTransitVisibilityFlag.from_mask(value["visibility_flags"]),
        contactSunAltitudeDegrees=tuple(value["contact_sun_altitude_degrees"]),
        contactSunAzimuthDegrees=tuple(value["contact_sun_azimuth_degrees"]),
        sunrise=_maybe_date(value["sunrise"]), sunset=_maybe_date(value["sunset"]),
    )


def _single(value):
    return EphemerisResult(value["coordinate"], _diagnostic(value["diagnostic"]))


def _dates(value):
    return EphemerisResult(list(value["values"]), _diagnostic(value["diagnostic"]))


class EventsApi:
    """The non-transit event-search family owned by an :class:`EphemerisContext`."""

    def __init__(self, context):
        self._context = context

    def recommended_longitude_search_step_days(self, body):
        self._context._ensure_open()
        return self._context._native_context.recommended_longitude_search_step_days(_target_id(body))

    def recommended_aspect_search_step_days(self, body_a, body_b):
        self._context._ensure_open()
        first, second = _body_pair(body_a, body_b)
        return self._context._native_context.recommended_aspect_search_step_days(first, second)

    def solar_longitude_at_ut1(self, target_longitude_radians, estimate, *, position_flags=(), options=()):
        return self._scalar("solar_longitude_at_ut1", target_longitude_radians, estimate,
                            _event_flags(position_flags, options, (EventSearchOption.reverse,)))

    def solar_longitude_at_tt(self, target_longitude_radians, estimate, *, position_flags=(), options=()):
        return self._scalar("solar_longitude_at_tt", target_longitude_radians, estimate,
                            _event_flags(position_flags, options, (EventSearchOption.reverse,)))

    def moon_longitude_at_ut1(self, target_longitude_radians, estimate, *, position_flags=(), options=()):
        return self._scalar("moon_longitude_at_ut1", target_longitude_radians, estimate,
                            _event_flags(position_flags, options, (EventSearchOption.reverse,)))

    def moon_longitude_at_tt(self, target_longitude_radians, estimate, *, position_flags=(), options=()):
        return self._scalar("moon_longitude_at_tt", target_longitude_radians, estimate,
                            _event_flags(position_flags, options, (EventSearchOption.reverse,)))

    def longitude_crossings_at_ut1(self, body, target_longitude_radians, start, end, *, max_step_days, max_results=16, position_flags=()):
        return self._longitude_crossings("longitude_crossings_at_ut1", body, target_longitude_radians,
                                         start, end, max_step_days, max_results, position_flags)

    def longitude_crossings_at_tt(self, body, target_longitude_radians, start, end, *, max_step_days, max_results=16, position_flags=()):
        return self._longitude_crossings("longitude_crossings_at_tt", body, target_longitude_radians,
                                         start, end, max_step_days, max_results, position_flags)

    def longitude_stations_at_ut1(self, body, start, end, *, max_step_days, max_results=16, position_flags=()):
        return self._stations("longitude_stations_at_ut1", body, start, end, max_step_days, max_results, position_flags)

    def longitude_stations_at_tt(self, body, start, end, *, max_step_days, max_results=16, position_flags=()):
        return self._stations("longitude_stations_at_tt", body, start, end, max_step_days, max_results, position_flags)

    def aspect_crossings_at_ut1(self, body_a, body_b, aspect_radians, start, end, *, max_step_days, max_results=16, position_flags=()):
        return self._aspects("aspect_crossings_at_ut1", body_a, body_b, aspect_radians, start, end, max_step_days, max_results, position_flags)

    def aspect_crossings_at_tt(self, body_a, body_b, aspect_radians, start, end, *, max_step_days, max_results=16, position_flags=()):
        return self._aspects("aspect_crossings_at_tt", body_a, body_b, aspect_radians, start, end, max_step_days, max_results, position_flags)

    def exact_aspects_at_ut1(self, body_a, body_b, aspect_separations_radians, start, end, *, max_step_days, max_results=16, position_flags=()):
        return self._exact_aspects("exact_aspects_at_ut1", body_a, body_b, aspect_separations_radians, start, end, max_step_days, max_results, position_flags)

    def exact_aspects_at_tt(self, body_a, body_b, aspect_separations_radians, start, end, *, max_step_days, max_results=16, position_flags=()):
        return self._exact_aspects("exact_aspects_at_tt", body_a, body_b, aspect_separations_radians, start, end, max_step_days, max_results, position_flags)

    def lunar_phase_crossings_at_ut1(self, phase_radians, start, end, *, max_step_days, max_results=16, position_flags=()):
        return self._phases("lunar_phase_crossings_at_ut1", phase_radians, start, end, max_step_days, max_results, position_flags)

    def lunar_phase_crossings_at_tt(self, phase_radians, start, end, *, max_step_days, max_results=16, position_flags=()):
        return self._phases("lunar_phase_crossings_at_tt", phase_radians, start, end, max_step_days, max_results, position_flags)

    def greatest_elongation_at_ut1(self, body, start, end, *, position_flags=()):
        self._context._ensure_open(); _interval(start, end)
        value = self._context._native_context.greatest_elongation_at_ut1(
            _inner_planet(body), start, end, _event_flags(position_flags))
        phenomena = value["phenomena"]
        parallax = phenomena["horizontal_parallax_radians"]
        return EphemerisResult(GreatestElongationEvent(
            bodyId=value["body_id"], coordinate=value["coordinate"],
            elongationRadians=value["elongation_radians"],
            relativeLongitudeRadians=value["relative_longitude_radians"],
            kind=GreatestElongationKind.from_mask(value["kind"]),
            iterationCount=value["iteration_count"], evaluationCount=value["evaluation_count"],
            phenomena=EventPhenomena(
                phenomena["phase_angle_radians"], phenomena["illuminated_fraction"],
                phenomena["solar_elongation_radians"], phenomena["apparent_diameter_radians"],
                phenomena["apparent_magnitude"], parallax if math.isfinite(parallax) else None)),
            _diagnostic(value["diagnostic"]))

    def minimum_angular_separation_at_ut1(self, body_a, body_b, start, end, *, max_step_days, position_flags=()):
        return self._minimum_separation("minimum_angular_separation_at_ut1", body_a, body_b, start, end, max_step_days, position_flags)

    def minimum_angular_separation_at_tt(self, body_a, body_b, start, end, *, max_step_days, position_flags=()):
        return self._minimum_separation("minimum_angular_separation_at_tt", body_a, body_b, start, end, max_step_days, position_flags)

    def next_solar_transit_at_ut1(self, body, start, *, position_flags=(), options=()):
        self._context._ensure_open()
        if not isinstance(position_flags, int) and PositionFlag.topocentric in position_flags:
            raise ValueError("solar-transit searches require geocentric position flags")
        value = self._context._native_context.next_solar_transit_at_ut1(
            _inner_planet(body), start,
            _event_flags(position_flags, options, (EventSearchOption.reverse,)))
        return EphemerisResult(_solar_transit(value), _diagnostic(value["diagnostic"]))

    def local_solar_transit_at_ut1(self, global_transit, observer, *, position_flags=(), options=()):
        self._context._ensure_open(); observer = _observer(observer)
        if not isinstance(position_flags, int) and PositionFlag.topocentric in position_flags:
            raise ValueError("solar-transit searches require geocentric position flags")
        value = self._context._native_context.local_solar_transit_at_ut1(
            global_transit._native, observer.longitude_degrees, observer.latitude_degrees,
            observer.height_meters, _event_flags(position_flags, options,
                (EventSearchOption.refraction, EventSearchOption.noRefraction)))
        return EphemerisResult(_local_solar_transit(value), _diagnostic(value["diagnostic"]))

    def next_local_solar_transit_at_ut1(self, body, start, observer, *, position_flags=(), options=()):
        self._context._ensure_open(); observer = _observer(observer)
        if not isinstance(position_flags, int) and PositionFlag.topocentric in position_flags:
            raise ValueError("solar-transit searches require geocentric position flags")
        value = self._context._native_context.next_local_solar_transit_at_ut1(
            _inner_planet(body), start, observer.longitude_degrees, observer.latitude_degrees,
            observer.height_meters, _event_flags(position_flags, options,
                (EventSearchOption.reverse, EventSearchOption.refraction, EventSearchOption.noRefraction)))
        return EphemerisResult(_local_solar_transit(value), _diagnostic(value["diagnostic"]))

    def _scalar(self, method, target, estimate, flags):
        self._context._ensure_open(); _finite(target, "target_longitude_radians")
        return _single(getattr(self._context._native_context, method)(target, estimate, flags))

    def _longitude_crossings(self, method, body, target, start, end, step, capacity, flags):
        self._context._ensure_open(); _finite(target, "target_longitude_radians"); _interval(start, end); _finite(step, "max_step_days"); _capacity(capacity)
        if step <= 0: raise ValueError("max_step_days must be positive")
        return _dates(getattr(self._context._native_context, method)(_target_id(body), target, start, end, step, _event_flags(flags), capacity))

    def _stations(self, method, body, start, end, step, capacity, flags):
        self._context._ensure_open(); _interval(start, end); _finite(step, "max_step_days"); _capacity(capacity)
        if step <= 0: raise ValueError("max_step_days must be positive")
        value = getattr(self._context._native_context, method)(_target_id(body), start, end, step, _event_flags(flags), capacity)
        return EphemerisResult([LongitudeStation(row["coordinate"], row["longitude_radians"]) for row in value["values"]], _diagnostic(value["diagnostic"]))

    def _aspects(self, method, body_a, body_b, aspect, start, end, step, capacity, flags):
        self._context._ensure_open(); first, second = _body_pair(body_a, body_b); _finite(aspect, "aspect_radians"); _interval(start, end); _finite(step, "max_step_days"); _capacity(capacity)
        if step <= 0: raise ValueError("max_step_days must be positive")
        return _dates(getattr(self._context._native_context, method)(first, second, aspect, start, end, step, _event_flags(flags), capacity))

    def _exact_aspects(self, method, body_a, body_b, aspects, start, end, step, capacity, flags):
        self._context._ensure_open(); first, second = _body_pair(body_a, body_b); _interval(start, end); _finite(step, "max_step_days"); _capacity(capacity)
        if not aspects: raise ValueError("aspect_separations_radians must not be empty")
        if step <= 0: raise ValueError("max_step_days must be positive")
        for aspect in aspects: _finite(aspect, "aspect_separations_radians")
        value = getattr(self._context._native_context, method)(first, second, list(aspects), start, end, step, _event_flags(flags), capacity)
        return EphemerisResult([ExactAspectEvent(row["coordinate"], row["aspect_radians"]) for row in value["values"]], _diagnostic(value["diagnostic"]))

    def _phases(self, method, phase, start, end, step, capacity, flags):
        self._context._ensure_open(); _finite(phase, "phase_radians"); _interval(start, end); _finite(step, "max_step_days"); _capacity(capacity)
        if step <= 0: raise ValueError("max_step_days must be positive")
        return _dates(getattr(self._context._native_context, method)(phase, start, end, step, _event_flags(flags), capacity))

    def _minimum_separation(self, method, body_a, body_b, start, end, step, flags):
        self._context._ensure_open(); first, second = _body_pair(body_a, body_b); _interval(start, end); _finite(step, "max_step_days")
        if step <= 0: raise ValueError("max_step_days must be positive")
        value = getattr(self._context._native_context, method)(first, second, start, end, step, _event_flags(flags))
        return EphemerisResult(MinimumAngularSeparationEvent(
            value["body_a_id"], value["body_b_id"], value["coordinate"],
            value["separation_radians"], value["separation_rate_radians_per_day"],
            value["iteration_count"], value["evaluation_count"]), _diagnostic(value["diagnostic"]))
