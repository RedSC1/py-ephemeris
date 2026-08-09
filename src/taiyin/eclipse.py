"""Global lunar and solar eclipse solving and searches."""

import math
from dataclasses import dataclass, field
from enum import Enum

from .position import EphemerisResult, PositionFlag, _diagnostic


class EclipseKind(Enum):
    penumbral = 1 << 0
    partial = 1 << 1
    total = 1 << 2
    annular = 1 << 3
    hybrid = 1 << 4
    central = 1 << 5
    noncentral = 1 << 6

    @property
    def mask(self):
        return self.value

    @classmethod
    def from_mask(cls, value):
        return frozenset(member for member in cls if value & member.mask)


class LunarEclipseContact(Enum):
    penumbralBegin = 0
    partialBegin = 1
    totalBegin = 2
    greatest = 3
    totalEnd = 4
    partialEnd = 5
    penumbralEnd = 6


class SolarEclipseContact(Enum):
    partialBegin = 0
    centralBegin = 1
    greatest = 2
    centralEnd = 3
    partialEnd = 4


class LocalSolarEclipseContact(Enum):
    partialBegin = 0
    centralBegin = 1
    centralEnd = 2
    partialEnd = 3
    greatest = 4


class LunarEclipseSolveOption(Enum):
    includeContacts = 1 << 33
    lunarLimbCorrection = 1 << 38

    @property
    def mask(self):
        return self.value


class LunarEclipseSearchOption(Enum):
    includeContacts = 1 << 33
    excludePenumbral = 1 << 34
    backward = 1 << 35
    lunarLimbCorrection = 1 << 38

    @property
    def mask(self):
        return self.value


class SolarEclipseSolveOption(Enum):
    includeContacts = 1 << 33
    lunarLimbCorrection = 1 << 38

    @property
    def mask(self):
        return self.value


class SolarEclipseSearchOption(Enum):
    includeContacts = 1 << 33
    backward = 1 << 35
    lunarLimbCorrection = 1 << 38

    @property
    def mask(self):
        return self.value


class LocalLunarEclipseVisibilityOption(Enum):
    refraction = 1 << 37

    @property
    def mask(self):
        return self.value


class LocalSolarEclipseVisibilityOption(Enum):
    refraction = 1 << 37
    strictMeteorology = 1 << 32

    @property
    def mask(self):
        return self.value


class LocalLunarEclipseVisibilityFlag(Enum):
    visibleAtObserver = 1 << 7
    maximumVisible = 1 << 8
    partialBeginVisible = 1 << 9
    totalBeginVisible = 1 << 10
    totalEndVisible = 1 << 11
    partialEndVisible = 1 << 12
    penumbralBeginVisible = 1 << 13
    penumbralEndVisible = 1 << 14

    @classmethod
    def from_mask(cls, value):
        return frozenset(member for member in cls if value & member.value)


class LocalSolarEclipseVisibilityFlag(Enum):
    visibleAtObserver = 1 << 7
    maximumVisible = 1 << 8
    partialBeginVisible = 1 << 9
    centralBeginVisible = 1 << 10
    centralEndVisible = 1 << 11
    partialEndVisible = 1 << 12

    @classmethod
    def from_mask(cls, value):
        return frozenset(member for member in cls if value & member.value)


@dataclass(frozen=True)
class LunarEclipseResult:
    kinds: frozenset = field(default_factory=frozenset)
    maximum: object = None
    deltaTSeconds: object = None
    umbralMagnitude: object = None
    penumbralMagnitude: object = None
    axisDistanceRadians: object = None
    umbraRadiusRadians: object = None
    penumbraRadiusRadians: object = None
    moonRadiusRadians: object = None
    contacts: dict = field(default_factory=dict)
    _native: object = field(default=None, repr=False, compare=False)

    @property
    def has_eclipse(self):
        return bool(self.kinds)


@dataclass(frozen=True)
class SolarEclipseResult:
    kinds: frozenset = field(default_factory=frozenset)
    maximum: object = None
    deltaTSeconds: object = None
    axisDistanceKilometers: object = None
    penumbraRadiusKilometers: object = None
    coreRadiusKilometers: object = None
    penumbralMarginKilometers: object = None
    centralMarginKilometers: object = None
    maximumLatitudeDegrees: object = None
    maximumLongitudeDegrees: object = None
    contacts: dict = field(default_factory=dict)

    @property
    def has_eclipse(self):
        return bool(self.kinds)


@dataclass(frozen=True)
class LocalLunarEclipseContact:
    coordinate: object
    moonAltitudeDegrees: object
    moonAzimuthDegrees: object


@dataclass(frozen=True)
class LocalLunarEclipseResult:
    kinds: frozenset = field(default_factory=frozenset)
    visibility: frozenset = field(default_factory=frozenset)
    maximum: object = None
    deltaTSeconds: object = None
    umbralMagnitude: object = None
    penumbralMagnitude: object = None
    contacts: dict = field(default_factory=dict)
    moonrise: object = None
    moonset: object = None

    @property
    def has_eclipse(self):
        return bool(self.kinds)


@dataclass(frozen=True)
class LocalSolarEclipseResult:
    kinds: frozenset = field(default_factory=frozenset)
    visibility: frozenset = field(default_factory=frozenset)
    maximum: object = None
    deltaTSeconds: object = None
    magnitude: object = None
    obscuration: object = None
    sunAltitudeDegrees: object = None
    sunAzimuthDegrees: object = None
    contacts: dict = field(default_factory=dict)
    positionAngleC1Degrees: object = None
    positionAngleC4Degrees: object = None
    vertexAngleC1Degrees: object = None
    vertexAngleC4Degrees: object = None
    sunriseMagnitude: object = None
    sunsetMagnitude: object = None
    durationSeconds: object = None
    moonSunRadiusRatio: object = None

    @property
    def has_eclipse(self):
        return bool(self.kinds)


@dataclass(frozen=True)
class LocalSolarEclipseCircumstances:
    coordinate: object
    deltaTSeconds: object
    magnitude: float
    obscuration: float
    centerSeparationDegrees: float
    sunAngularRadiusDegrees: float
    moonAngularRadiusDegrees: float
    sunAltitudeDegrees: float
    sunAzimuthDegrees: float


class EclipseApi:
    def __init__(self, context):
        self._context = context

    def solve_lunar_at_tt(self, estimate, *, position_flags=(), options=()):
        return self._single("solve_lunar_eclipse_at_tt", estimate, 0,
                            _flags(position_flags, options), _lunar)

    def solve_lunar_at_ut1(self, estimate, *, position_flags=(), options=()):
        return self._single("solve_lunar_eclipse_at_ut1", estimate, 0,
                            _flags(position_flags, options), _lunar)

    def next_lunar_at_tt(self, start, *, kinds=(), position_flags=(), options=()):
        return self._single("next_lunar_eclipse_at_tt", start, _kind_mask(kinds, True),
                            _flags(position_flags, options), _lunar, True)

    def next_lunar_at_ut1(self, start, *, kinds=(), position_flags=(), options=()):
        return self._single("next_lunar_eclipse_at_ut1", start, _kind_mask(kinds, True),
                            _flags(position_flags, options), _lunar, True)

    def lunar_eclipses_at_tt(self, start, end, *, max_results=16, kinds=(),
                             position_flags=(), options=()):
        return self._range("lunar_eclipses_at_tt", start, end, max_results,
                           _kind_mask(kinds, True), _range_flags(position_flags, options), _lunar)

    def lunar_eclipses_at_ut1(self, start, end, *, max_results=16, kinds=(),
                              position_flags=(), options=()):
        return self._range("lunar_eclipses_at_ut1", start, end, max_results,
                           _kind_mask(kinds, True), _range_flags(position_flags, options), _lunar)

    def solve_solar_at_tt(self, estimate, *, position_flags=(), options=()):
        return self._single("solve_solar_eclipse_at_tt", estimate, 0,
                            _flags(position_flags, options), _solar)

    def solve_solar_at_ut1(self, estimate, *, position_flags=(), options=()):
        return self._single("solve_solar_eclipse_at_ut1", estimate, 0,
                            _flags(position_flags, options), _solar)

    def next_solar_at_tt(self, start, *, kinds=(), position_flags=(), options=()):
        return self._single("next_solar_eclipse_at_tt", start, _kind_mask(kinds, False),
                            _flags(position_flags, options), _solar, True)

    def next_solar_at_ut1(self, start, *, kinds=(), position_flags=(), options=()):
        return self._single("next_solar_eclipse_at_ut1", start, _kind_mask(kinds, False),
                            _flags(position_flags, options), _solar, True)

    def solar_eclipses_at_tt(self, start, end, *, max_results=16, kinds=(),
                             position_flags=(), options=()):
        return self._range("solar_eclipses_at_tt", start, end, max_results,
                           _kind_mask(kinds, False), _range_flags(position_flags, options), _solar)

    def solar_eclipses_at_ut1(self, start, end, *, max_results=16, kinds=(),
                              position_flags=(), options=()):
        return self._range("solar_eclipses_at_ut1", start, end, max_results,
                           _kind_mask(kinds, False), _range_flags(position_flags, options), _solar)

    def local_lunar_visibility_at_tt(self, eclipse, *, options=()):
        return self._local_lunar("local_lunar_visibility_at_tt", eclipse, options)

    def local_lunar_visibility_at_ut1(self, eclipse, *, options=()):
        return self._local_lunar("local_lunar_visibility_at_ut1", eclipse, options)

    def next_local_lunar_at_tt(self, start, *, kinds=(), position_flags=(),
                               options=(), visibility_options=()):
        return self._next_local("next_local_lunar_eclipse_at_tt", start,
            _kind_mask(kinds, True), _flags(position_flags, options) | _mask(visibility_options),
            _local_lunar_result)

    def next_local_lunar_at_ut1(self, start, *, kinds=(), position_flags=(),
                                options=(), visibility_options=()):
        return self._next_local("next_local_lunar_eclipse_at_ut1", start,
            _kind_mask(kinds, True), _flags(position_flags, options) | _mask(visibility_options),
            _local_lunar_result)

    def solve_local_solar_at_tt(self, estimate, *, position_flags=(), options=(),
                                visibility_options=()):
        return self._solve_local_solar("solve_local_solar_eclipse_at_tt", estimate,
            position_flags, options, visibility_options)

    def solve_local_solar_at_ut1(self, estimate, *, position_flags=(), options=(),
                                 visibility_options=()):
        return self._solve_local_solar("solve_local_solar_eclipse_at_ut1", estimate,
            position_flags, options, visibility_options)

    def next_local_solar_at_tt(self, start, *, kinds=(), position_flags=(), options=(),
                               visibility_options=()):
        flags = _flags(position_flags, options) | _local_solar_mask(visibility_options) | (1 << 33)
        return self._next_local("next_local_solar_eclipse_at_tt", start,
            _kind_mask(kinds, False), flags, _local_solar_result)

    def next_local_solar_at_ut1(self, start, *, kinds=(), position_flags=(), options=(),
                                visibility_options=()):
        flags = _flags(position_flags, options) | _local_solar_mask(visibility_options) | (1 << 33)
        return self._next_local("next_local_solar_eclipse_at_ut1", start,
            _kind_mask(kinds, False), flags, _local_solar_result)

    def local_solar_circumstances_at_tt(self, coordinate):
        return self._circumstances("local_solar_circumstances_at_tt", coordinate)

    def local_solar_circumstances_at_ut1(self, coordinate):
        return self._circumstances("local_solar_circumstances_at_ut1", coordinate)

    def _local_lunar(self, name, eclipse, options):
        self._context._ensure_open()
        if not isinstance(eclipse, LunarEclipseResult) or eclipse._native is None:
            raise ValueError("eclipse must be a lunar result returned by this runtime")
        if not any(eclipse.contacts.values()):
            raise ValueError("lunar eclipse contacts are required")
        value = getattr(self._context._native_context, name)(eclipse._native, _mask(options))
        return EphemerisResult(_local_lunar_result(value), _diagnostic(value["diagnostic"]))

    def _next_local(self, name, start, kinds, flags, mapper):
        self._context._ensure_open()
        value = getattr(self._context._native_context, name)(start, kinds, flags)
        return EphemerisResult(mapper(value), _diagnostic(value["diagnostic"]))

    def _solve_local_solar(self, name, estimate, position_flags, options, visibility_options):
        self._context._ensure_open()
        flags = _flags(position_flags, options) | _local_solar_mask(visibility_options) | (1 << 33)
        value = getattr(self._context._native_context, name)(estimate, flags)
        return EphemerisResult(_local_solar_result(value), _diagnostic(value["diagnostic"]))

    def _circumstances(self, name, coordinate):
        self._context._ensure_open()
        value = getattr(self._context._native_context, name)(coordinate)
        result = LocalSolarEclipseCircumstances(
            coordinate=value["coordinate"], deltaTSeconds=_finite(value["delta_t_seconds"]),
            magnitude=value["magnitude"], obscuration=value["obscuration"],
            centerSeparationDegrees=value["center_separation_degrees"],
            sunAngularRadiusDegrees=value["sun_angular_radius_degrees"],
            moonAngularRadiusDegrees=value["moon_angular_radius_degrees"],
            sunAltitudeDegrees=value["sun_altitude_degrees"],
            sunAzimuthDegrees=value["sun_azimuth_degrees"],
        )
        return EphemerisResult(result, _diagnostic(value["diagnostic"]))

    def _single(self, name, coordinate, kinds, flags, mapper, has_kinds=False):
        self._context._ensure_open()
        method = getattr(self._context._native_context, name)
        value = method(coordinate, kinds, flags) if has_kinds else method(coordinate, flags)
        return EphemerisResult(mapper(value), _diagnostic(value["diagnostic"]))

    def _range(self, name, start, end, capacity, kinds, flags, mapper):
        self._context._ensure_open()
        if start.to_double() >= end.to_double():
            raise ValueError("start must be before end")
        if not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("max_results must be a positive integer")
        value = getattr(self._context._native_context, name)(
            start, end, kinds, flags, capacity
        )
        return EphemerisResult(
            [mapper(row) for row in value["values"]],
            _diagnostic(value["diagnostic"]),
        )


def _lunar(value):
    kinds = EclipseKind.from_mask(value["kind"])
    if not kinds:
        return LunarEclipseResult()
    return LunarEclipseResult(
        kinds=kinds,
        maximum=_date(value["maximum"]),
        deltaTSeconds=_finite(value["delta_t_seconds"]),
        umbralMagnitude=_finite(value["umbral_magnitude"]),
        penumbralMagnitude=_finite(value["penumbral_magnitude"]),
        axisDistanceRadians=_finite(value["axis_distance_radians"]),
        umbraRadiusRadians=_finite(value["umbra_radius_radians"]),
        penumbraRadiusRadians=_finite(value["penumbra_radius_radians"]),
        moonRadiusRadians=_finite(value["moon_radius_radians"]),
        contacts={kind: _date(value["contacts"][kind.value]) for kind in LunarEclipseContact},
        _native=value,
    )


def _solar(value):
    kinds = EclipseKind.from_mask(value["kind"])
    if not kinds:
        return SolarEclipseResult()
    return SolarEclipseResult(
        kinds=kinds,
        maximum=_date(value["maximum"]),
        deltaTSeconds=_finite(value["delta_t_seconds"]),
        axisDistanceKilometers=_finite(value["axis_distance_kilometers"]),
        penumbraRadiusKilometers=_finite(value["penumbra_radius_kilometers"]),
        coreRadiusKilometers=_finite(value["core_radius_kilometers"]),
        penumbralMarginKilometers=_finite(value["penumbral_margin_kilometers"]),
        centralMarginKilometers=_finite(value["central_margin_kilometers"]),
        maximumLatitudeDegrees=_finite(value["maximum_latitude_degrees"]),
        maximumLongitudeDegrees=_finite(value["maximum_longitude_degrees"]),
        contacts={kind: _date(value["contacts"][kind.value]) for kind in SolarEclipseContact},
    )


def _local_lunar_result(value):
    contacts = {}
    for contact in LunarEclipseContact:
        coordinate = _date(value["contacts"][contact.value])
        contacts[contact] = None if coordinate is None else LocalLunarEclipseContact(
            coordinate, _finite(value["altitudes"][contact.value]),
            _finite(value["azimuths"][contact.value]))
    return LocalLunarEclipseResult(
        kinds=EclipseKind.from_mask(value["kind"]),
        visibility=LocalLunarEclipseVisibilityFlag.from_mask(value["visibility_flags"]),
        maximum=_date(value["maximum"]), deltaTSeconds=_finite(value["delta_t_seconds"]),
        umbralMagnitude=_finite(value["umbral_magnitude"]),
        penumbralMagnitude=_finite(value["penumbral_magnitude"]), contacts=contacts,
        moonrise=_date(value["moonrise"]), moonset=_date(value["moonset"]),
    )


def _local_solar_result(value):
    return LocalSolarEclipseResult(
        kinds=EclipseKind.from_mask(value["kind"]),
        visibility=LocalSolarEclipseVisibilityFlag.from_mask(value["kind"]),
        maximum=_date(value["maximum"]), deltaTSeconds=_finite(value["delta_t_seconds"]),
        magnitude=_finite(value["magnitude"]), obscuration=_finite(value["obscuration"]),
        sunAltitudeDegrees=_finite(value["sun_altitude_degrees"]),
        sunAzimuthDegrees=_finite(value["sun_azimuth_degrees"]),
        contacts={kind: _date(value["contacts"][kind.value]) for kind in LocalSolarEclipseContact},
        positionAngleC1Degrees=_finite(value["position_angle_c1_degrees"]),
        positionAngleC4Degrees=_finite(value["position_angle_c4_degrees"]),
        vertexAngleC1Degrees=_finite(value["vertex_angle_c1_degrees"]),
        vertexAngleC4Degrees=_finite(value["vertex_angle_c4_degrees"]),
        sunriseMagnitude=_finite(value["sunrise_magnitude"]),
        sunsetMagnitude=_finite(value["sunset_magnitude"]),
        durationSeconds=_finite(value["duration_seconds"]),
        moonSunRadiusRatio=_finite(value["moon_sun_radius_ratio"]),
    )


def _flags(position_flags, options):
    if any(flag is not PositionFlag.truepos for flag in (position_flags or ())):
        raise ValueError("position_flags may contain only truepos")
    return sum(flag.mask for flag in (position_flags or ())) + sum(
        flag.mask for flag in (options or ())
    )


def _range_flags(position_flags, options):
    if any(getattr(option, "name", "") == "backward" for option in (options or ())):
        raise ValueError("backward is not valid for interval searches")
    return _flags(position_flags, options)


def _kind_mask(kinds, lunar):
    supported = ({EclipseKind.penumbral, EclipseKind.partial, EclipseKind.total}
                 if lunar else {EclipseKind.partial, EclipseKind.total,
                                EclipseKind.annular, EclipseKind.hybrid})
    if any(kind not in supported for kind in (kinds or ())):
        raise ValueError("unsupported eclipse kind filter")
    return sum(kind.mask for kind in (kinds or ()))


def _mask(flags):
    return sum(flag.mask for flag in (flags or ()))


def _local_solar_mask(options):
    options = tuple(options or ())
    if (LocalSolarEclipseVisibilityOption.strictMeteorology in options
            and LocalSolarEclipseVisibilityOption.refraction not in options):
        raise ValueError("strictMeteorology requires refraction")
    return _mask(options)


def _date(value):
    return value if math.isfinite(value.day_fraction) else None


def _finite(value):
    return value if math.isfinite(value) else None
