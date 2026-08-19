"""Lunar-occultation searches, local visibility, and global path products."""

import math
from dataclasses import dataclass, field
from enum import Enum

from .position import Body, PositionFlag


class OccultationSearchOption(Enum):
    backward = 1 << 32
    oneCandidate = 1 << 33
    filterPartial = 1 << 40
    filterTotal = 1 << 41
    filterGrazing = 1 << 42
    filterCentral = 1 << 43
    filterNoncentral = 1 << 44
    lunarLimbCorrection = 1 << 45

    @property
    def mask(self):
        return self.value


class OccultationVisibilityOption(Enum):
    refraction = 1 << 34

    @property
    def mask(self):
        return self.value


class LunarOccultationKind(Enum):
    none = 0
    lunarStar = 1
    lunarBody = 2
    unknown = -1

    @classmethod
    def from_id(cls, value):
        try:
            return cls(value)
        except ValueError:
            return cls.unknown


class _MaskEnum(Enum):
    @property
    def mask(self):
        return self.value

    @classmethod
    def from_mask(cls, value):
        return frozenset(member for member in cls if value & member.mask)


class OccultationType(_MaskEnum):
    partial = 1 << 0
    total = 1 << 1
    annular = 1 << 2
    grazing = 1 << 3
    central = 1 << 4
    noncentral = 1 << 5
    centralityUnavailable = 1 << 6


class OccultationSampleFlag(_MaskEnum):
    moonAboveHorizon = 1 << 0
    targetAboveHorizon = 1 << 1
    sunBelowHorizon = 1 << 2


class OccultationVisibilityFlag(_MaskEnum):
    hasVisibleSample = 1 << 0
    maximumVisible = 1 << 1
    hasDarkSample = 1 << 2
    maximumDark = 1 << 3
    hasVisibleInterval = 1 << 4
    hasDarkInterval = 1 << 5


@dataclass(frozen=True)
class LunarOccultationPhenomena:
    angularDistanceRadians: object
    diameterRatio: object
    magnitude: object
    obscuration: object
    occultedFraction: object


@dataclass(frozen=True)
class LunarOccultationResult:
    kind: LunarOccultationKind
    coordinate: object
    types: frozenset = field(default_factory=frozenset)
    begin: object = None
    end: object = None
    firstContact: object = None
    secondContact: object = None
    thirdContact: object = None
    fourthContact: object = None
    separationRadians: float = 0.0
    moonRadiusRadians: float = 0.0
    targetRadiusRadians: float = 0.0
    marginRadians: float = 0.0
    phenomena: object = None
    candidate: object = None
    nextSearch: object = None
    candidateCount: int = 0
    iterationCount: int = 0
    evaluationCount: int = 0
    _native: object = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class LunarOccultationVisibilityInterval:
    begin: object
    end: object


@dataclass(frozen=True)
class LunarOccultationVisibilitySample:
    coordinate: object
    moonAltitudeRadians: float
    moonAzimuthRadians: float
    targetAltitudeRadians: float
    targetAzimuthRadians: float
    sunAltitudeRadians: float
    sunAzimuthRadians: float
    flags: frozenset = field(default_factory=frozenset)


@dataclass(frozen=True)
class LunarOccultationLocalVisibility:
    firstContact: object = None
    secondContact: object = None
    maximum: object = None
    thirdContact: object = None
    fourthContact: object = None
    targetRise: object = None
    targetSet: object = None
    visibleBegin: object = None
    visibleEnd: object = None
    darkVisibleBegin: object = None
    darkVisibleEnd: object = None
    visibleIntervals: tuple = field(default_factory=tuple)
    darkVisibleIntervals: tuple = field(default_factory=tuple)
    flags: frozenset = field(default_factory=frozenset)


@dataclass(frozen=True)
class LunarOccultationPathPoint:
    valid: bool
    coordinate: object = None
    longitudeDegrees: object = None
    latitudeDegrees: object = None
    heightMeters: object = None


@dataclass(frozen=True)
class LunarOccultationWhereResult:
    centerLineHitsEarth: bool = False
    types: frozenset = field(default_factory=frozenset)
    coordinate: object = None
    centerLineBegin: object = None
    centerLineEnd: object = None
    centerLinePath: tuple = field(default_factory=tuple)
    centerLineMinLongitudeDegrees: object = None
    centerLineMaxLongitudeDegrees: object = None
    centerLineMinLatitudeDegrees: object = None
    centerLineMaxLatitudeDegrees: object = None
    centerLinePathDistanceKilometers: object = None
    outerNorthPath: tuple = field(default_factory=tuple)
    outerSouthPath: tuple = field(default_factory=tuple)
    outerLimitMeanWidthKilometers: object = None
    outerLimitMaxWidthKilometers: object = None
    visibleRegionPolygon: tuple = field(default_factory=tuple)
    visibleRegionMinLongitudeDegrees: object = None
    visibleRegionMaxLongitudeDegrees: object = None
    visibleRegionMinLatitudeDegrees: object = None
    visibleRegionMaxLatitudeDegrees: object = None
    maximumLocation: object = None
    separationRadians: object = None
    moonRadiusRadians: object = None
    targetRadiusRadians: object = None
    marginRadians: object = None
    phenomena: object = None
    localSample: object = None
    visibilityFlags: frozenset = field(default_factory=frozenset)


class OccultationApi:
    def __init__(self, context):
        self._context = context

    def next_geocentric_star_at_ut1(
        self, star_key, start, *, position_flags=(), options=()
    ):
        return self._star_search(
            "next_geocentric_star_occultation_at_ut1",
            star_key,
            start,
            position_flags,
            options,
        )

    def next_local_star_at_ut1(
        self, star_key, start, *, position_flags=(), options=()
    ):
        return self._star_search(
            "next_local_star_occultation_at_ut1",
            star_key,
            start,
            position_flags,
            options,
        )

    def next_geocentric_body_at_ut1(
        self,
        target,
        start,
        *,
        target_radius_kilometers=None,
        position_flags=(),
        options=(),
    ):
        return self._body_search(
            "next_geocentric_body_occultation_at_ut1",
            target,
            start,
            target_radius_kilometers,
            position_flags,
            options,
        )

    def next_local_body_at_ut1(
        self,
        target,
        start,
        *,
        target_radius_kilometers=None,
        position_flags=(),
        options=(),
    ):
        return self._body_search(
            "next_local_body_occultation_at_ut1",
            target,
            start,
            target_radius_kilometers,
            position_flags,
            options,
        )

    def local_star_visibility_at_ut1(self, star_key, occultation, *, options=()):
        self._context._ensure_open()
        _require_star_key(star_key)
        _require_kind(occultation, LunarOccultationKind.lunarStar)
        value = self._context._call_native_operation("Occultation.star_occultation_local_visibility_at_ut1", "star_occultation_local_visibility_at_ut1",
            star_key, _native_occultation(occultation), _mask(options)
        )
        return self._context._operation_result(_visibility(value))

    def local_body_visibility_at_ut1(self, target, occultation, *, options=()):
        self._context._ensure_open()
        _require_target(target)
        _require_kind(occultation, LunarOccultationKind.lunarBody)
        value = self._context._call_native_operation("Occultation.body_occultation_local_visibility_at_ut1", "body_occultation_local_visibility_at_ut1",
            target.id, _native_occultation(occultation), _mask(options)
        )
        return self._context._operation_result(_visibility(value))

    def star_where_at_ut1(
        self, star_key, occultation, *, position_flags=(), visibility_options=()
    ):
        self._context._ensure_open()
        _require_star_key(star_key)
        _require_kind(occultation, LunarOccultationKind.lunarStar)
        value = self._context._call_native_operation("Occultation.star_occultation_where_at_ut1", "star_occultation_where_at_ut1",
            star_key,
            _native_occultation(occultation),
            _position_mask(position_flags) | _mask(visibility_options),
        )
        return self._context._operation_result(_where(value))

    def body_where_at_ut1(
        self,
        target,
        occultation,
        *,
        target_radius_kilometers=None,
        position_flags=(),
        visibility_options=(),
    ):
        self._context._ensure_open()
        _require_target(target)
        _require_kind(occultation, LunarOccultationKind.lunarBody)
        _require_radius(target_radius_kilometers)
        value = self._context._call_native_operation("Occultation.body_occultation_where_at_ut1", "body_occultation_where_at_ut1",
            target.id,
            _native_occultation(occultation),
            target_radius_kilometers,
            _position_mask(position_flags) | _mask(visibility_options),
        )
        return self._context._operation_result(_where(value))

    def _star_search(self, native_name, star_key, start, position_flags, options):
        self._context._ensure_open()
        _require_star_key(star_key)
        value = self._context._call_native_operation("Occultation." + native_name, native_name,
            star_key, start, _position_mask(position_flags) | _mask(options)
        )
        return self._context._operation_result(_occultation(value))

    def _body_search(
        self, native_name, target, start, radius, position_flags, options
    ):
        self._context._ensure_open()
        _require_target(target)
        _require_radius(radius)
        value = self._context._call_native_operation("Occultation." + native_name, native_name,
            target.id,
            start,
            radius,
            _position_mask(position_flags) | _mask(options),
        )
        return self._context._operation_result(_occultation(value))


def _phenomena(value):
    return LunarOccultationPhenomena(
        angularDistanceRadians=_finite(value["angular_distance_radians"]),
        diameterRatio=_finite(value["diameter_ratio"]),
        magnitude=_finite(value["magnitude"]),
        obscuration=_finite(value["obscuration"]),
        occultedFraction=_finite(value["occulted_fraction"]),
    )


def _occultation(value):
    return LunarOccultationResult(
        kind=LunarOccultationKind.from_id(value["kind"]),
        types=OccultationType.from_mask(value["type_flags"]),
        coordinate=_required_date(value["coordinate"], "occultation maximum"),
        begin=_date(value["begin"]),
        end=_date(value["end"]),
        firstContact=_date(value["first_contact"]),
        secondContact=_date(value["second_contact"]),
        thirdContact=_date(value["third_contact"]),
        fourthContact=_date(value["fourth_contact"]),
        separationRadians=value["separation_radians"],
        moonRadiusRadians=value["moon_radius_radians"],
        targetRadiusRadians=value["target_radius_radians"],
        marginRadians=value["margin_radians"],
        phenomena=_phenomena(value["phenomena"]),
        candidate=_date(value["candidate"]),
        nextSearch=_date(value["next_search"]),
        candidateCount=value["candidate_count"],
        iterationCount=value["iteration_count"],
        evaluationCount=value["evaluation_count"],
        _native=value,
    )


def _sample(value):
    if not value["valid"]:
        return None
    return LunarOccultationVisibilitySample(
        coordinate=_required_date(value["coordinate"], "visibility sample"),
        moonAltitudeRadians=value["moon_altitude_radians"],
        moonAzimuthRadians=value["moon_azimuth_radians"],
        targetAltitudeRadians=value["target_altitude_radians"],
        targetAzimuthRadians=value["target_azimuth_radians"],
        sunAltitudeRadians=value["sun_altitude_radians"],
        sunAzimuthRadians=value["sun_azimuth_radians"],
        flags=OccultationSampleFlag.from_mask(value["visibility_flags"]),
    )


def _interval(value):
    if not value["valid"]:
        raise RuntimeError("native occultation result contains an invalid interval")
    return LunarOccultationVisibilityInterval(
        _required_date(value["begin"], "interval begin"),
        _required_date(value["end"], "interval end"),
    )


def _visibility(value):
    return LunarOccultationLocalVisibility(
        firstContact=_sample(value["first_contact"]),
        secondContact=_sample(value["second_contact"]),
        maximum=_sample(value["maximum"]),
        thirdContact=_sample(value["third_contact"]),
        fourthContact=_sample(value["fourth_contact"]),
        targetRise=_date(value["target_rise"]),
        targetSet=_date(value["target_set"]),
        visibleBegin=_date(value["visible_begin"]),
        visibleEnd=_date(value["visible_end"]),
        darkVisibleBegin=_date(value["dark_visible_begin"]),
        darkVisibleEnd=_date(value["dark_visible_end"]),
        visibleIntervals=tuple(_interval(item) for item in value["visible_intervals"]),
        darkVisibleIntervals=tuple(
            _interval(item) for item in value["dark_visible_intervals"]
        ),
        flags=OccultationVisibilityFlag.from_mask(value["visibility_flags"]),
    )


def _path_point(value):
    return LunarOccultationPathPoint(
        valid=value["valid"],
        coordinate=_date(value["coordinate"]),
        longitudeDegrees=_finite(value["longitude_degrees"]),
        latitudeDegrees=_finite(value["latitude_degrees"]),
        heightMeters=_finite(value["height_meters"]),
    )


def _where(value):
    coordinate = _date(value["coordinate"])
    longitude = _finite(value["longitude_degrees"])
    latitude = _finite(value["latitude_degrees"])
    height = _finite(value["height_meters"])
    maximum = None
    if coordinate is not None and None not in (longitude, latitude, height):
        maximum = LunarOccultationPathPoint(
            True, coordinate, longitude, latitude, height
        )
    return LunarOccultationWhereResult(
        centerLineHitsEarth=value["center_line_hits_earth"],
        types=OccultationType.from_mask(value["type_flags"]),
        coordinate=coordinate,
        centerLineBegin=_date(value["center_line_begin"]),
        centerLineEnd=_date(value["center_line_end"]),
        centerLinePath=tuple(_path_point(item) for item in value["center_line_path"]),
        centerLineMinLongitudeDegrees=_finite(value["center_line_min_longitude_degrees"]),
        centerLineMaxLongitudeDegrees=_finite(value["center_line_max_longitude_degrees"]),
        centerLineMinLatitudeDegrees=_finite(value["center_line_min_latitude_degrees"]),
        centerLineMaxLatitudeDegrees=_finite(value["center_line_max_latitude_degrees"]),
        centerLinePathDistanceKilometers=_finite(value["center_line_path_distance_kilometers"]),
        outerNorthPath=tuple(_path_point(item) for item in value["outer_north_path"]),
        outerSouthPath=tuple(_path_point(item) for item in value["outer_south_path"]),
        outerLimitMeanWidthKilometers=_finite(value["outer_limit_mean_width_kilometers"]),
        outerLimitMaxWidthKilometers=_finite(value["outer_limit_max_width_kilometers"]),
        visibleRegionPolygon=tuple(
            _path_point(item) for item in value["visible_region_polygon"]
        ),
        visibleRegionMinLongitudeDegrees=_finite(value["visible_region_min_longitude_degrees"]),
        visibleRegionMaxLongitudeDegrees=_finite(value["visible_region_max_longitude_degrees"]),
        visibleRegionMinLatitudeDegrees=_finite(value["visible_region_min_latitude_degrees"]),
        visibleRegionMaxLatitudeDegrees=_finite(value["visible_region_max_latitude_degrees"]),
        maximumLocation=maximum,
        separationRadians=_finite(value["separation_radians"]),
        moonRadiusRadians=_finite(value["moon_radius_radians"]),
        targetRadiusRadians=_finite(value["target_radius_radians"]),
        marginRadians=_finite(value["margin_radians"]),
        phenomena=_phenomena(value["phenomena"]),
        localSample=_sample(value["local_sample"]),
        visibilityFlags=OccultationVisibilityFlag.from_mask(value["visibility_flags"]),
    )


def _date(value):
    return value if math.isfinite(value.day_fraction) else None


def _required_date(value, name):
    result = _date(value)
    if result is None:
        raise RuntimeError(f"native occultation result has no {name}")
    return result


def _finite(value):
    return value if math.isfinite(value) else None


def _native_occultation(value):
    if value._native is None:
        raise ValueError("occultation must be a result returned by this runtime")
    return value._native


def _mask(flags):
    return sum(flag.mask for flag in (flags or ()))


def _position_mask(flags):
    supported = {
        PositionFlag.truepos,
        PositionFlag.astrometric,
        PositionFlag.no_aberr,
        PositionFlag.no_gdefl,
    }
    if any(flag not in supported for flag in (flags or ())):
        raise ValueError(
            "position_flags must contain only truepos, astrometric, no_aberr, and no_gdefl"
        )
    return _mask(flags)


def _require_star_key(value):
    if not isinstance(value, str) or not value or "\0" in value:
        raise ValueError("star_key must be non-empty and contain no NUL character")


def _require_target(value):
    unsupported = {Body.ssb, Body.emb, Body.sun, Body.moon, Body.earth}
    if not isinstance(value, Body) or value in unsupported:
        raise ValueError(
            "target must not be the Moon, Earth, Earth-Moon barycenter, Sun, or solar-system barycenter"
        )


def _require_kind(value, expected):
    if not isinstance(value, LunarOccultationResult) or value.kind is not expected:
        raise ValueError(f"occultation must be a {expected.name} result")


def _require_radius(value):
    if value is not None and (not math.isfinite(value) or value < 0):
        raise ValueError(
            "target_radius_kilometers must be finite and greater than or equal to zero"
        )
