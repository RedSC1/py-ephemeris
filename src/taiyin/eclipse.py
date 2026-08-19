"""Global lunar and solar eclipse solving and searches."""

import math
from dataclasses import dataclass, field
from enum import Enum

from ._native import LocalSolarEclipseCircumstances, SolarEclipseWhere  # pyright: ignore[reportMissingImports, reportAttributeAccessIssue]
from .position import PositionFlag


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


class SolarEclipseRouteOption(Enum):
    lunarLimbCorrection = 1 << 38

    @property
    def mask(self):
        return self.value


class SolarEclipseRouteCurveKind(Enum):
    partialBeginA=0; partialBeginB=1; partialEndA=2; partialEndB=3
    sunriseMaximumA=4; sunriseMaximumB=5; sunsetMaximumA=6; sunsetMaximumB=7
    centerLine=8; penumbralNorth=9; penumbralSouth=10; coreNorth=11; coreSouth=12
    halfMagnitudeNorth=13; halfMagnitudeSouth=14; umbraOutline=15; penumbraOutline=16
    terminator=17; coreBeginHorizon=18; coreEndHorizon=19
    halfMagnitudeSunriseA=20; halfMagnitudeSunriseB=21
    halfMagnitudeSunsetA=22; halfMagnitudeSunsetB=23


class SolarEclipseRouteProductFlag(Enum):
    hasCenterLine=1 << 0
    hasCoreLimits=1 << 1
    hasPenumbralLimits=1 << 2
    hasCorePolygon=1 << 3
    crossesAntimeridian=1 << 4
    hasHalfMagnitudeLimits=1 << 5
    hasPenumbralPolygon=1 << 6
    hasHalfMagnitudePolygon=1 << 7

    @classmethod
    def from_mask(cls, value):
        return frozenset(member for member in cls if value & member.value)


class SolarEclipseRouteProductPointKind(Enum):
    coreNorth=0
    coreSouth=1
    polygonClose=2
    penumbralNorth=3
    penumbralSouth=4
    halfMagnitudeNorth=5
    halfMagnitudeSouth=6
    coreBeginHorizon=7
    coreEndHorizon=8


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
class SolarBesselianElements:
    tHours: float
    x: float
    y: float
    zeta: float
    dDegrees: float
    muDegrees: float
    l1: float
    l2: float
    f1Degrees: float
    f2Degrees: float
    tanF1: float
    tanF2: float
    gamma: float


@dataclass(frozen=True)
class SolarBesselianPolynomial:
    coefficientCount = 8

    referenceEpoch: object
    spanHours: float
    sampleStepHours: float
    degree: int
    f1Degrees: float
    f2Degrees: float
    tanF1: float
    tanF2: float
    center: SolarBesselianElements
    maxResidual: SolarBesselianElements
    xCoefficients: tuple
    yCoefficients: tuple
    zetaCoefficients: tuple
    dDegreesCoefficients: tuple
    muDegreesCoefficients: tuple
    l1Coefficients: tuple
    l2Coefficients: tuple
    _native: object = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class SolarEclipseRoutePoint:
    coordinateTt: object = None
    coordinateUt1: object = None
    latitudeDegrees: object = None
    longitudeDegrees: object = None
    elevationMeters: object = None
    sunAltitudeDegrees: object = None
    sunAzimuthDegrees: object = None

    @property
    def intersects_earth(self):
        return self.latitudeDegrees is not None and self.longitudeDegrees is not None


@dataclass(frozen=True)
class SolarEclipseRouteRow:
    coordinateTt: object
    coordinateUt1: object
    centerLine: SolarEclipseRoutePoint
    penumbralNorthLimit: SolarEclipseRoutePoint
    penumbralSouthLimit: SolarEclipseRoutePoint
    northLimit: SolarEclipseRoutePoint
    southLimit: SolarEclipseRoutePoint
    halfMagnitudeNorthLimit: SolarEclipseRoutePoint
    halfMagnitudeSouthLimit: SolarEclipseRoutePoint
    pathWidthKilometers: object = None
    durationSeconds: object = None
    sunAltitudeDegrees: object = None
    sunAzimuthDegrees: object = None

    @property
    def has_route(self):
        return any(point.intersects_earth for point in (
            self.centerLine,self.penumbralNorthLimit,self.penumbralSouthLimit,
            self.northLimit,self.southLimit))


@dataclass(frozen=True)
class SolarEclipseRouteCurvePoint:
    coordinateTt: object
    coordinateUt1: object
    kind: SolarEclipseRouteCurveKind
    latitudeDegrees: float
    longitudeDegrees: float


@dataclass(frozen=True)
class SolarEclipseRouteProductPoint:
    coordinateTt: object
    coordinateUt1: object
    kind: SolarEclipseRouteProductPointKind
    sourceCurveKind: SolarEclipseRouteCurveKind
    latitudeDegrees: float
    longitudeDegrees: float
    unwrappedLongitudeDegrees: float


@dataclass(frozen=True)
class SolarEclipseRouteProductSummary:
    flags: frozenset = field(default_factory=frozenset)
    curvePointCount: int = 0
    centerLineCount: int = 0
    coreNorthCount: int = 0
    coreSouthCount: int = 0
    coreBeginHorizonCount: int = 0
    coreEndHorizonCount: int = 0
    penumbralNorthCount: int = 0
    penumbralSouthCount: int = 0
    halfMagnitudeNorthCount: int = 0
    halfMagnitudeSouthCount: int = 0
    corePolygonPointCount: int = 0
    penumbralPolygonPointCount: int = 0
    halfMagnitudePolygonPointCount: int = 0
    polygonPointCount: int = 0
    minimumLatitudeDegrees: object = None
    maximumLatitudeDegrees: object = None
    minimumUnwrappedLongitudeDegrees: object = None
    maximumUnwrappedLongitudeDegrees: object = None


@dataclass(frozen=True)
class SolarEclipseRouteProduct:
    points: tuple = field(default_factory=tuple)
    summary: SolarEclipseRouteProductSummary = field(
        default_factory=SolarEclipseRouteProductSummary
    )


@dataclass(frozen=True)
class LocalSolarEclipseBoundary:
    centerKinds: frozenset = field(default_factory=frozenset)
    centerLongitudeDegrees: object = None
    centerLatitudeDegrees: object = None
    umbraNorthLongitudeDegrees: object = None
    umbraNorthLatitudeDegrees: object = None
    umbraSouthLongitudeDegrees: object = None
    umbraSouthLatitudeDegrees: object = None
    penumbraNorthLongitudeDegrees: object = None
    penumbraNorthLatitudeDegrees: object = None
    penumbraSouthLongitudeDegrees: object = None
    penumbraSouthLatitudeDegrees: object = None
    umbraWidthKilometers: object = None

    @property
    def has_central_path(self):
        return bool(self.centerKinds)


class EclipseApi:
    def __init__(self, context):
        self._context = context

    def _call_native(self, name, *args):
        """Run one public eclipse operation and retain its outer diagnostic.

        Native eclipse searches make many internal ephemeris evaluations.  The
        context snapshot must describe this public eclipse operation, never an
        incidental Sun/Moon position evaluation performed during the search.
        """
        return self._context._call_native_operation(f"Eclipse.{name}", name, *args)

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

    def solar_besselian_elements_at_tt(self, coordinate, *, time_offset_hours=0.0):
        if not math.isfinite(time_offset_hours):
            raise ValueError("time_offset_hours must be finite")
        value=self._call_native("solar_besselian_elements_at_tt",coordinate,time_offset_hours)
        return self._context._operation_result(_besselian_elements(value))

    def solar_besselian_polynomial_at_tt(self, coordinate, *, span_hours=3.0,
                                         sample_step_hours=0.25, degree=3):
        if not math.isfinite(span_hours) or span_hours <= 0:
            raise ValueError("span_hours must be positive and finite")
        if not math.isfinite(sample_step_hours) or sample_step_hours <= 0:
            raise ValueError("sample_step_hours must be positive and finite")
        if not isinstance(degree,int) or not 0 <= degree <= 7:
            raise ValueError("degree must be in 0..7")
        value=self._call_native("solar_besselian_polynomial_at_tt",
            coordinate,span_hours,sample_step_hours,degree)
        return self._context._operation_result(_besselian_polynomial(value))

    def evaluate_solar_besselian_polynomial(self, polynomial, time_offset_hours):
        if not isinstance(polynomial,SolarBesselianPolynomial) or polynomial._native is None:
            raise ValueError("polynomial must be returned by solar_besselian_polynomial_at_tt")
        if not math.isfinite(time_offset_hours):
            raise ValueError("time_offset_hours must be finite")
        return self._context._operation_result(_besselian_elements(self._call_native(
            "evaluate_solar_besselian_polynomial", polynomial._native,time_offset_hours)))

    def solar_eclipse_route_row_at_tt(self, coordinate, *, position_flags=(), options=()):
        return self._route_row("solar_eclipse_route_row_at_tt",coordinate,position_flags,options)

    def solar_eclipse_route_row_at_ut1(self, coordinate, *, position_flags=(), options=()):
        return self._route_row("solar_eclipse_route_row_at_ut1",coordinate,position_flags,options)

    def solar_eclipse_where_at_tt(self, coordinate, *, position_flags=(), options=()):
        return self._where("solar_eclipse_where_at_tt",coordinate,position_flags,options)

    def solar_eclipse_where_at_ut1(self, coordinate, *, position_flags=(), options=()):
        return self._where("solar_eclipse_where_at_ut1",coordinate,position_flags,options)

    def solar_eclipse_route_at_tt(self,start,end,*,step_minutes=1.0,max_rows=400,
                                  position_flags=(),options=()):
        return self._route("solar_eclipse_route_at_tt",start,end,step_minutes,max_rows,position_flags,options)

    def solar_eclipse_route_at_ut1(self,start,end,*,step_minutes=1.0,max_rows=400,
                                   position_flags=(),options=()):
        return self._route("solar_eclipse_route_at_ut1",start,end,step_minutes,max_rows,position_flags,options)

    def solar_eclipse_route_curves_at_tt(self,coordinate,*,route_sample_count=400,
                                         position_flags=(),options=()):
        return self._curves("solar_eclipse_route_curves_at_tt",coordinate,route_sample_count,position_flags,options)

    def solar_eclipse_route_curves_at_ut1(self,coordinate,*,route_sample_count=400,
                                          position_flags=(),options=()):
        return self._curves("solar_eclipse_route_curves_at_ut1",coordinate,route_sample_count,position_flags,options)

    def solar_eclipse_route_product_at_tt(self,coordinate,*,route_sample_count=400,
                                          position_flags=(),options=()):
        return self._product("solar_eclipse_route_product_at_tt",coordinate,route_sample_count,position_flags,options)

    def solar_eclipse_route_product_at_ut1(self,coordinate,*,route_sample_count=400,
                                           position_flags=(),options=()):
        return self._product("solar_eclipse_route_product_at_ut1",coordinate,route_sample_count,position_flags,options)

    def solar_eclipse_route_map_product_at_tt(self,coordinate,*,route_sample_count=400,
                                              position_flags=(),options=()):
        return self._product("solar_eclipse_route_map_product_at_tt",coordinate,route_sample_count,position_flags,options)

    def solar_eclipse_route_map_product_at_ut1(self,coordinate,*,route_sample_count=400,
                                               position_flags=(),options=()):
        return self._product("solar_eclipse_route_map_product_at_ut1",coordinate,route_sample_count,position_flags,options)

    def local_solar_eclipse_boundary_at_tt(self,coordinate,*,longitude_degrees,
                                           latitude_degrees):
        return self._boundary("local_solar_eclipse_boundary_at_tt",coordinate,
                              longitude_degrees,latitude_degrees)

    def local_solar_eclipse_boundary_at_ut1(self,coordinate,*,longitude_degrees,
                                            latitude_degrees):
        return self._boundary("local_solar_eclipse_boundary_at_ut1",coordinate,
                              longitude_degrees,latitude_degrees)

    def _local_lunar(self, name, eclipse, options):
        if not isinstance(eclipse, LunarEclipseResult) or eclipse._native is None:
            raise ValueError("eclipse must be a lunar result returned by this runtime")
        if not any(eclipse.contacts.values()):
            raise ValueError("lunar eclipse contacts are required")
        value = self._call_native(name, eclipse._native, _mask(options))
        return self._context._operation_result(_local_lunar_result(value))

    def _next_local(self, name, start, kinds, flags, mapper):
        value = self._call_native(name, start, kinds, flags)
        return self._context._operation_result(mapper(value))

    def _solve_local_solar(self, name, estimate, position_flags, options, visibility_options):
        flags = _flags(position_flags, options) | _local_solar_mask(visibility_options) | (1 << 33)
        value = self._call_native(name, estimate, flags)
        return self._context._operation_result(_local_solar_result(value))

    def _circumstances(self, name, coordinate):
        return self._context._operation_result(self._call_native(name, coordinate))

    def _route_row(self,name,coordinate,position_flags,options):
        value=self._call_native(name, coordinate, _route_flags(position_flags,options))
        return self._context._operation_result(_route_row(value))

    def _where(self,name,coordinate,position_flags,options):
        # The native call itself records the diagnostic in this context.  Keep
        # this particular one-epoch map primitive as thin as pyswisseph's
        # ``sol_eclipse_where`` wrapper: no generic dispatch, dict, dataclass,
        # or EphemerisResult is constructed on its success path.
        self._context._ensure_open()
        return self._context._operation_result(self._context._call_native_operation(
            f"Eclipse.{name}", name, coordinate,
            _route_flags(position_flags, options)))

    def _route(self,name,start,end,step_minutes,max_rows,position_flags,options):
        if start.to_double()>end.to_double(): raise ValueError("start must not be after end")
        if not math.isfinite(step_minutes) or step_minutes<=0: raise ValueError("step_minutes must be positive and finite")
        if not isinstance(max_rows,int) or max_rows<=0: raise ValueError("max_rows must be a positive integer")
        value=self._call_native(name, start,end,step_minutes,
            _route_flags(position_flags,options),max_rows)
        return self._context._operation_result(
            [_route_row(row) for row in value["values"]])

    def _curves(self,name,coordinate,sample_count,position_flags,options):
        _require_route_sample_count(sample_count)
        value=self._call_native(name, coordinate,
            _route_flags(position_flags,options),sample_count)
        return self._context._operation_result([SolarEclipseRouteCurvePoint(
            coordinateTt=row["coordinate_tt"],coordinateUt1=row["coordinate_ut1"],
            kind=SolarEclipseRouteCurveKind(row["kind"]),latitudeDegrees=row["latitude_degrees"],
            longitudeDegrees=row["longitude_degrees"]) for row in value["values"]])

    def _product(self,name,coordinate,sample_count,position_flags,options):
        _require_route_sample_count(sample_count)
        value=self._call_native(name, coordinate,
            _route_flags(position_flags,options),sample_count)
        return self._context._operation_result(_route_product(value))

    def _boundary(self,name,coordinate,longitude_degrees,latitude_degrees):
        if not math.isfinite(longitude_degrees):
            raise ValueError("longitude_degrees must be finite")
        if not math.isfinite(latitude_degrees) or not -90<=latitude_degrees<=90:
            raise ValueError("latitude_degrees must be finite and in -90..90")
        value=self._call_native(name,
            coordinate,longitude_degrees,latitude_degrees)
        return self._context._operation_result(_boundary(value))

    def _single(self, name, coordinate, kinds, flags, mapper, has_kinds=False):
        value = self._call_native(name, coordinate, kinds, flags) if has_kinds else self._call_native(name, coordinate, flags)
        return self._context._operation_result(mapper(value))

    def _range(self, name, start, end, capacity, kinds, flags, mapper):
        if start.to_double() >= end.to_double():
            raise ValueError("start must be before end")
        if not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("max_results must be a positive integer")
        value = self._call_native(name,
            start, end, kinds, flags, capacity
        )
        return self._context._operation_result([mapper(row) for row in value["values"]])


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


def _besselian_elements(value):
    return SolarBesselianElements(
        value["t_hours"],value["x"],value["y"],value["zeta"],value["d_degrees"],
        value["mu_degrees"],value["l1"],value["l2"],value["f1_degrees"],
        value["f2_degrees"],value["tan_f1"],value["tan_f2"],value["gamma"])


def _besselian_polynomial(value):
    return SolarBesselianPolynomial(
        referenceEpoch=value["reference_epoch"],spanHours=value["span_hours"],
        sampleStepHours=value["sample_step_hours"],degree=value["degree"],
        f1Degrees=value["f1_degrees"],f2Degrees=value["f2_degrees"],
        tanF1=value["tan_f1"],tanF2=value["tan_f2"],
        center=_besselian_elements(value["center"]),maxResidual=_besselian_elements(value["max_residual"]),
        xCoefficients=tuple(value["x_coefficients"]),yCoefficients=tuple(value["y_coefficients"]),
        zetaCoefficients=tuple(value["zeta_coefficients"]),
        dDegreesCoefficients=tuple(value["d_degrees_coefficients"]),
        muDegreesCoefficients=tuple(value["mu_degrees_coefficients"]),
        l1Coefficients=tuple(value["l1_coefficients"]),l2Coefficients=tuple(value["l2_coefficients"]),
        _native=value)


def _route_point(value):
    return SolarEclipseRoutePoint(
        coordinateTt=_date(value["coordinate_tt"]),coordinateUt1=_date(value["coordinate_ut1"]),
        latitudeDegrees=_finite(value["latitude_degrees"]),longitudeDegrees=_finite(value["longitude_degrees"]),
        elevationMeters=_finite(value["elevation_meters"]),sunAltitudeDegrees=_finite(value["sun_altitude_degrees"]),
        sunAzimuthDegrees=_finite(value["sun_azimuth_degrees"]))


def _route_row(value):
    return SolarEclipseRouteRow(
        coordinateTt=value["coordinate_tt"],coordinateUt1=value["coordinate_ut1"],
        centerLine=_route_point(value["center_line"]),
        penumbralNorthLimit=_route_point(value["penumbral_north_limit"]),
        penumbralSouthLimit=_route_point(value["penumbral_south_limit"]),
        northLimit=_route_point(value["north_limit"]),southLimit=_route_point(value["south_limit"]),
        halfMagnitudeNorthLimit=_route_point(value["half_magnitude_north_limit"]),
        halfMagnitudeSouthLimit=_route_point(value["half_magnitude_south_limit"]),
        pathWidthKilometers=_finite(value["path_width_kilometers"]),durationSeconds=_finite(value["duration_seconds"]),
        sunAltitudeDegrees=_finite(value["sun_altitude_degrees"]),sunAzimuthDegrees=_finite(value["sun_azimuth_degrees"]))


def _route_product(value):
    points=tuple(SolarEclipseRouteProductPoint(
        coordinateTt=row["coordinate_tt"],coordinateUt1=row["coordinate_ut1"],
        kind=SolarEclipseRouteProductPointKind(row["kind"]),
        sourceCurveKind=SolarEclipseRouteCurveKind(row["source_curve_kind"]),
        latitudeDegrees=row["latitude_degrees"],longitudeDegrees=row["longitude_degrees"],
        unwrappedLongitudeDegrees=row["unwrapped_longitude_degrees"])
        for row in value["points"])
    summary=value["summary"]
    return SolarEclipseRouteProduct(points=points,summary=SolarEclipseRouteProductSummary(
        flags=SolarEclipseRouteProductFlag.from_mask(summary["flags"]),
        curvePointCount=summary["curve_point_count"],centerLineCount=summary["center_line_count"],
        coreNorthCount=summary["core_north_count"],coreSouthCount=summary["core_south_count"],
        coreBeginHorizonCount=summary["core_begin_horizon_count"],
        coreEndHorizonCount=summary["core_end_horizon_count"],
        penumbralNorthCount=summary["penumbral_north_count"],
        penumbralSouthCount=summary["penumbral_south_count"],
        halfMagnitudeNorthCount=summary["half_magnitude_north_count"],
        halfMagnitudeSouthCount=summary["half_magnitude_south_count"],
        corePolygonPointCount=summary["core_polygon_point_count"],
        penumbralPolygonPointCount=summary["penumbral_polygon_point_count"],
        halfMagnitudePolygonPointCount=summary["half_magnitude_polygon_point_count"],
        polygonPointCount=summary["polygon_point_count"],
        minimumLatitudeDegrees=_finite(summary["minimum_latitude_degrees"]),
        maximumLatitudeDegrees=_finite(summary["maximum_latitude_degrees"]),
        minimumUnwrappedLongitudeDegrees=_finite(summary["minimum_unwrapped_longitude_degrees"]),
        maximumUnwrappedLongitudeDegrees=_finite(summary["maximum_unwrapped_longitude_degrees"])))


def _boundary(value):
    return LocalSolarEclipseBoundary(
        centerKinds=EclipseKind.from_mask(value["center_kind"]),
        centerLongitudeDegrees=_finite(value["center_longitude_degrees"]),
        centerLatitudeDegrees=_finite(value["center_latitude_degrees"]),
        umbraNorthLongitudeDegrees=_finite(value["umbra_north_longitude_degrees"]),
        umbraNorthLatitudeDegrees=_finite(value["umbra_north_latitude_degrees"]),
        umbraSouthLongitudeDegrees=_finite(value["umbra_south_longitude_degrees"]),
        umbraSouthLatitudeDegrees=_finite(value["umbra_south_latitude_degrees"]),
        penumbraNorthLongitudeDegrees=_finite(value["penumbra_north_longitude_degrees"]),
        penumbraNorthLatitudeDegrees=_finite(value["penumbra_north_latitude_degrees"]),
        penumbraSouthLongitudeDegrees=_finite(value["penumbra_south_longitude_degrees"]),
        penumbraSouthLatitudeDegrees=_finite(value["penumbra_south_latitude_degrees"]),
        umbraWidthKilometers=_finite(value["umbra_width_kilometers"]))


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


def _route_flags(position_flags,options):
    if any(flag is not PositionFlag.truepos for flag in (position_flags or ())):
        raise ValueError("position_flags may contain only truepos")
    return _mask(position_flags)|_mask(options)


def _require_route_sample_count(value):
    if not isinstance(value,int) or not 32<=value<=4096:
        raise ValueError("route_sample_count must be in 32..4096")


def _date(value):
    return value if math.isfinite(value.day_fraction) else None


def _finite(value):
    return value if math.isfinite(value) else None
