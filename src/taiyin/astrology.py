"""Sidereal coordinates, lunar points, and astrological houses."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from .position import (
    ApparentFrame, Body, PositionFlag,
    _normalized_flags, _target_id, position_flag_mask,
)


class AyanamshaModel:
    @property
    def id(self):
        raise NotImplementedError


class Ayanamsha(AyanamshaModel, Enum):
    faganBradley = 0
    lahiri = 1
    raman = 3
    krishnamurti = 5
    galacticCenter0Sagittarius = 17
    trueChitra = 27

    @property
    def id(self):
        return self.value


class CustomAyanamshaModel(AyanamshaModel):
    def __init__(self, model_id):
        _custom_id(model_id)
        self._id = model_id

    @property
    def id(self):
        return self._id

    def __eq__(self, other):
        return isinstance(other, CustomAyanamshaModel) and self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return "CustomAyanamshaModel({})".format(self.id)


class HouseSystemModel:
    @property
    def id(self):
        raise NotImplementedError


class HouseSystem(HouseSystemModel, Enum):
    wholeSign = 0
    equal = 1
    porphyry = 2
    placidus = 3
    koch = 4
    regiomontanus = 5
    campanus = 6
    alcabitius = 7
    polichPage = 8
    morinus = 9

    @property
    def id(self):
        return self.value

    @classmethod
    def from_id_or_none(cls, value):
        try:
            return cls(value)
        except ValueError:
            return None


class CustomHouseSystemModel(HouseSystemModel):
    def __init__(self, model_id):
        _custom_id(model_id)
        self._id = model_id

    @property
    def id(self):
        return self._id

    def __eq__(self, other):
        return isinstance(other, CustomHouseSystemModel) and self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return "CustomHouseSystemModel({})".format(self.id)


class PrecessionModel(Enum):
    vondrak2011 = 0
    iau2006 = 1
    iau1976 = 2
    newcomb1895 = 3

    @property
    def id(self):
        return self.value


class SiderealPrecessionPolicy(Enum):
    compensateToReference = 0
    rawReferenceOffset = 1 << 36
    useReferencePrecession = 1 << 37

    @property
    def mask(self):
        return self.value


class SiderealReferencePlane(Enum):
    meanEclipticOfDate = (0, False)
    meanEclipticAtEpoch = (1 << 32, True)
    solarSystemInvariable = (1 << 33, True)
    meanEclipticJ2000 = (1 << 34, False)

    def __init__(self, mask, requires_reference_epoch):
        self._mask = mask
        self._requires_reference_epoch = requires_reference_epoch

    @property
    def mask(self):
        return self._mask

    @property
    def requires_reference_epoch(self):
        return self._requires_reference_epoch


class SiderealCoordinateFrame(Enum):
    meanEclipticOfDate = 0
    meanEquatorOfDate = 1
    trueEquatorOfDate = 2
    fixedMeanEclipticAtEpoch = 3
    solarSystemInvariable = 4
    j2000Ecliptic = 5
    unknown = -1

    @classmethod
    def from_id(cls, value):
        try:
            return cls(value)
        except ValueError:
            return cls.unknown


@dataclass(frozen=True)
class SiderealReferenceEpoch:
    coordinate: object
    is_ut1: bool = False

    @classmethod
    def tt(cls, coordinate):
        return cls(coordinate, False)

    @classmethod
    def ut1(cls, coordinate):
        return cls(coordinate, True)


class LunarNodeKind(Enum):
    ascending = 0
    descending = 1

    @property
    def id(self):
        return self.value


class LunarApsisDefinition(Enum):
    delaunayMean = 0
    osculatingTwoBody = 1
    de441FittedNatural = 2
    unknown = -1

    @classmethod
    def from_id(cls, value):
        try:
            return cls(value)
        except ValueError:
            return cls.unknown


class HouseResultFlag(Enum):
    usedFallback = 1 << 0
    fallbackPorphyry = 1 << 1
    speedUnavailable = 1 << 2

    @classmethod
    def from_mask(cls, value):
        return frozenset(item for item in cls if value & item.value)


@dataclass(frozen=True)
class CustomAyanamshaRequest:
    julian_date_tt: object
    raw_flags: int

    @property
    def flags(self):
        return _normalized_flags(self.raw_flags)

    def has_flag(self, flag):
        return flag in self.flags


@dataclass(frozen=True)
class CustomHouseSystemRequest:
    armc_radians: float
    observer_latitude_radians: float
    true_obliquity_radians: float
    ascendant_radians: float
    midheaven_radians: float


class CustomAyanamshaRegistration:
    """Owns a process-wide callback registration and its custom model."""

    def __init__(self, native, model):
        self._native = native
        self.model = model

    @property
    def is_closed(self):
        return self._native.is_closed

    def close(self):
        self._native.close()


class CustomHouseSystemRegistration:
    """Owns a process-wide house callback registration and its model."""

    def __init__(self, native, model):
        self._native = native
        self.model = model

    @property
    def is_closed(self):
        return self._native.is_closed

    def close(self):
        self._native.close()


@dataclass(frozen=True)
class SiderealPosition:
    target: object
    ayanamsha: AyanamshaModel
    precessionPolicy: SiderealPrecessionPolicy
    referencePlane: SiderealReferencePlane
    referenceEpoch: object
    coordinateFrame: SiderealCoordinateFrame
    rawCoordinateFrameId: int
    tropicalLongitudeRadians: float
    siderealLongitudeRadians: float
    latitudeRadians: float
    distanceAu: float
    tropicalLongitudeRateRadiansPerDay: float
    siderealLongitudeRateRadiansPerDay: float
    flags: frozenset = field(default_factory=frozenset)

    @property
    def unshiftedLongitudeRadians(self):
        return self.tropicalLongitudeRadians

    @property
    def unshiftedLongitudeRateRadiansPerDay(self):
        return self.tropicalLongitudeRateRadiansPerDay


@dataclass(frozen=True)
class SiderealCoordinates:
    target: object
    ayanamsha: AyanamshaModel
    precessionPolicy: SiderealPrecessionPolicy
    referencePlane: SiderealReferencePlane
    referenceEpoch: object
    coordinateFrame: SiderealCoordinateFrame
    rawCoordinateFrameId: int
    values: tuple
    flags: frozenset = field(default_factory=frozenset)

    def __post_init__(self):
        if len(self.values) != 6:
            raise ValueError("values must contain six values")
        object.__setattr__(self, "values", tuple(self.values))
        object.__setattr__(self, "flags", frozenset(self.flags))

    @property
    def coordinates(self):
        return self.values[:3]

    @property
    def rates(self):
        return self.values[3:]

    @property
    def isCartesian(self):
        return PositionFlag.xyz in self.flags

    @property
    def isEquatorial(self):
        return PositionFlag.equatorial in self.flags

    @property
    def isRadians(self):
        return PositionFlag.radians in self.flags


@dataclass(frozen=True)
class LunarNodePosition:
    kind: LunarNodeKind
    referenceFrame: ApparentFrame
    rawReferenceFrameId: int
    longitudeRadians: float
    longitudeRateRadiansPerDay: float
    flags: frozenset = field(default_factory=frozenset)


@dataclass(frozen=True)
class LunarApsisPosition:
    referenceFrame: ApparentFrame
    rawReferenceFrameId: int
    definition: LunarApsisDefinition
    rawDefinitionId: int
    longitudeRadians: float
    latitudeRadians: float
    longitudeRateRadiansPerDay: float
    latitudeRateRadiansPerDay: float
    distanceAu: object
    distanceRateAuPerDay: object
    extrapolated: bool
    flags: frozenset = field(default_factory=frozenset)


@dataclass(frozen=True)
class Houses:
    requestedSystemId: int
    resolvedSystemId: int
    rawFlags: int
    armcRadians: float
    ascendantRadians: float
    midheavenRadians: float
    vertexRadians: float
    eastPointRadians: float
    armcRateRadiansPerDay: float
    ascendantRateRadiansPerDay: float
    midheavenRateRadiansPerDay: float
    vertexRateRadiansPerDay: float
    eastPointRateRadiansPerDay: float
    flags: frozenset
    cuspLongitudesRadians: tuple
    cuspLongitudeRatesRadiansPerDay: tuple

    def __post_init__(self):
        if len(self.cuspLongitudesRadians) != 12 or len(self.cuspLongitudeRatesRadiansPerDay) != 12:
            raise ValueError("houses must contain twelve cusps and twelve rates")
        object.__setattr__(self, "flags", frozenset(self.flags))
        object.__setattr__(self, "cuspLongitudesRadians", tuple(self.cuspLongitudesRadians))
        object.__setattr__(self, "cuspLongitudeRatesRadiansPerDay", tuple(self.cuspLongitudeRatesRadiansPerDay))

    @property
    def requestedSystem(self):
        return _house_model(self.requestedSystemId)

    @property
    def resolvedSystem(self):
        return _house_model(self.resolvedSystemId)


@dataclass(frozen=True)
class HousePosition:
    houseNumber: int
    fraction: float
    continuousHousePosition: float


class AstrologyApi:
    """Sidereal, lunar-point, and house calculations for one context."""

    def __init__(self, context):
        self._context = context

    def ayanamsha_at_tt(self, tt, *, ayanamsha: AyanamshaModel = Ayanamsha.faganBradley,
                         precession_policy=SiderealPrecessionPolicy.compensateToReference):
        self._context._ensure_open()
        return self._context._operation_result(self._context._call_native_operation(
            "Astrology.ayanamsha_at_tt", "ayanamsha_at_tt",
            _model_id(ayanamsha), tt, precession_policy.mask))

    def sidereal_position_at_tt(self, target, tt, **options):
        return self._sidereal_position("sidereal_position_at_tt", target, tt, options)

    def sidereal_position_at_ut1(self, target, ut1, **options):
        return self._sidereal_position("sidereal_position_at_ut1", target, ut1, options)

    def sidereal_coordinates_at_tt(self, target, tt, **options):
        return self._sidereal_coordinates("sidereal_coordinates_at_tt", target, tt, options)

    def sidereal_coordinates_at_ut1(self, target, ut1, **options):
        return self._sidereal_coordinates("sidereal_coordinates_at_ut1", target, ut1, options)

    def lunar_true_node_at_tt(self, tt, *, kind=LunarNodeKind.ascending, flags=()):
        return self._lunar_node("lunar_true_node_at_tt", tt, kind, flags, _LUNAR_PHYSICAL)

    def lunar_true_node_at_ut1(self, ut1, *, kind=LunarNodeKind.ascending, flags=()):
        return self._lunar_node("lunar_true_node_at_ut1", ut1, kind, flags, _LUNAR_PHYSICAL)

    def lunar_mean_node_at_tt(self, tt, *, kind=LunarNodeKind.ascending, flags=()):
        return self._lunar_node("lunar_mean_node_at_tt", tt, kind, flags, _LUNAR_MEAN)

    def lunar_mean_node_at_ut1(self, ut1, *, kind=LunarNodeKind.ascending, flags=()):
        return self._lunar_node("lunar_mean_node_at_ut1", ut1, kind, flags, _LUNAR_MEAN)

    def lunar_mean_apogee_at_tt(self, tt, *, flags=()):
        return self._lunar_apsis("lunar_mean_apogee_at_tt", tt, flags, _LUNAR_MEAN)

    def lunar_mean_apogee_at_ut1(self, ut1, *, flags=()):
        return self._lunar_apsis("lunar_mean_apogee_at_ut1", ut1, flags, _LUNAR_MEAN)

    def lunar_osculating_apogee_at_tt(self, tt, *, flags=()):
        return self._lunar_apsis("lunar_osculating_apogee_at_tt", tt, flags, _LUNAR_PHYSICAL)

    def lunar_osculating_apogee_at_ut1(self, ut1, *, flags=()):
        return self._lunar_apsis("lunar_osculating_apogee_at_ut1", ut1, flags, _LUNAR_PHYSICAL)

    def lunar_fitted_apogee_at_tt(self, tt, *, flags=()):
        return self._lunar_apsis("lunar_fitted_apogee_at_tt", tt, flags, _LUNAR_MEAN)

    def lunar_fitted_apogee_at_ut1(self, ut1, *, flags=()):
        return self._lunar_apsis("lunar_fitted_apogee_at_ut1", ut1, flags, _LUNAR_MEAN)

    def houses_from_armc(self, *, armc_radians, observer_latitude_radians,
                         true_obliquity_radians,
                         system: HouseSystemModel = HouseSystem.porphyry):
        self._context._ensure_open()
        _finite(armc_radians, "armc_radians")
        _finite(observer_latitude_radians, "observer_latitude_radians")
        _finite(true_obliquity_radians, "true_obliquity_radians")
        if not -math.pi / 2 < observer_latitude_radians < math.pi / 2:
            raise ValueError("observer_latitude_radians must be strictly between -pi/2 and pi/2")
        if not 0 < true_obliquity_radians < math.pi / 2:
            raise ValueError("true_obliquity_radians must be strictly between 0 and pi/2")
        return self._context._operation_result(_houses(
            self._context._call_native_operation(
                "Astrology.houses_from_armc", "houses_from_armc",
                armc_radians, observer_latitude_radians, true_obliquity_radians,
                _model_id(system))))

    def houses_at_ut1(self, ut1, *, system=HouseSystem.porphyry):
        self._context._ensure_open()
        return self._context._operation_result(_houses(self._context._call_native_operation(
            "Astrology.houses_at_ut1", "houses_at_ut1", ut1, _model_id(system))))

    def houses_at_tt(self, tt, *, system=HouseSystem.porphyry):
        self._context._ensure_open()
        return self._context._operation_result(_houses(self._context._call_native_operation(
            "Astrology.houses_at_tt", "houses_at_tt", tt, _model_id(system))))

    def house_position_of(self, houses, ecliptic_longitude_radians):
        self._context._ensure_open()
        _finite(ecliptic_longitude_radians, "ecliptic_longitude_radians")
        value = self._context._call_native_operation("Astrology.house_position_of", "house_position_of",
            {"cusp_longitudes_radians": houses.cuspLongitudesRadians}, ecliptic_longitude_radians)
        return self._context._operation_result(
            HousePosition(value["house_number"], value["fraction"], value["continuous_house_position"])
        )

    def has_ayanamsha_model(self, ayanamsha):
        self._context._ensure_open()
        return self._context._native_context.has_ayanamsha_model(_model_id(ayanamsha))

    def has_house_system_model(self, system):
        self._context._ensure_open()
        return self._context._native_context.has_house_system_model(_model_id(system))

    def _sidereal_options(self, options, position):
        allowed = {"ayanamsha", "precession_policy", "reference_plane", "reference_epoch", "flags"}
        unknown = set(options) - allowed
        if unknown:
            raise TypeError("unexpected option: {}".format(next(iter(unknown))))
        ayanamsha = options.get("ayanamsha", Ayanamsha.faganBradley)
        policy = options.get("precession_policy", SiderealPrecessionPolicy.compensateToReference)
        plane = options.get("reference_plane", SiderealReferencePlane.meanEclipticOfDate)
        epoch = options.get("reference_epoch")
        raw_flags = options.get("flags", ())
        normalized = _normalized_flags(raw_flags)
        if position and ({PositionFlag.xyz, PositionFlag.equatorial} & normalized):
            raise ValueError("sidereal positions require ecliptic spherical coordinates")
        normalized = normalized | frozenset((PositionFlag.radians,))
        if plane.requires_reference_epoch != (epoch is not None):
            raise ValueError("{} {} a reference_epoch".format(
                plane.name, "requires" if plane.requires_reference_epoch else "does not accept"))
        native_epoch = None
        epoch_flag = 0
        if epoch is not None:
            if isinstance(epoch, SiderealReferenceEpoch):
                native_epoch = epoch.coordinate
                epoch_flag = (1 << 35) if epoch.is_ut1 else 0
            else:
                raise TypeError("reference_epoch must be SiderealReferenceEpoch")
        flags = position_flag_mask(normalized) | policy.mask | plane.mask | epoch_flag
        return ayanamsha, policy, plane, epoch, normalized, flags, native_epoch

    def _sidereal_position(self, method, target, coordinate, options):
        self._context._ensure_open()
        ayanamsha, policy, plane, epoch, flags, native_flags, native_epoch = self._sidereal_options(options, True)
        value = self._context._call_native_operation("Astrology." + method, method,
            _model_id(ayanamsha), _target_id(target), coordinate, native_flags, native_epoch)
        return self._context._operation_result(SiderealPosition(
            target, ayanamsha, policy, plane, epoch,
            SiderealCoordinateFrame.from_id(value["coordinate_frame_id"]), value["coordinate_frame_id"],
            value["tropical_longitude_radians"], value["sidereal_longitude_radians"],
            value["latitude_radians"], value["distance_au"],
            value["tropical_longitude_rate_radians_per_day"],
            value["sidereal_longitude_rate_radians_per_day"], flags))

    def _sidereal_coordinates(self, method, target, coordinate, options):
        self._context._ensure_open()
        ayanamsha, policy, plane, epoch, _, native_flags, native_epoch = self._sidereal_options(options, False)
        value = self._context._call_native_operation("Astrology." + method, method,
            _model_id(ayanamsha), _target_id(target), coordinate, native_flags, native_epoch)
        flags = _normalized_flags(value["position_flags"])
        return self._context._operation_result(SiderealCoordinates(
            target, ayanamsha, policy, plane, epoch,
            SiderealCoordinateFrame.from_id(value["coordinate_frame_id"]), value["coordinate_frame_id"],
            tuple(value["values"]), flags))

    def _lunar_node(self, method, coordinate, kind, flags, allowed):
        self._context._ensure_open()
        resolved = _lunar_flags(flags, allowed, method)
        value = self._context._call_native_operation("Astrology." + method, method, coordinate, _model_id(kind), position_flag_mask(resolved))
        return self._context._operation_result(LunarNodePosition(
            kind, ApparentFrame.from_id(value["reference_frame_id"]), value["reference_frame_id"],
            value["longitude_radians"], value["longitude_rate_radians_per_day"], resolved))

    def _lunar_apsis(self, method, coordinate, flags, allowed):
        self._context._ensure_open()
        resolved = _lunar_flags(flags, allowed, method)
        value = self._context._call_native_operation("Astrology." + method, method, coordinate, position_flag_mask(resolved))
        return self._context._operation_result(LunarApsisPosition(
            ApparentFrame.from_id(value["reference_frame_id"]), value["reference_frame_id"],
            LunarApsisDefinition.from_id(value["definition"]), value["definition"],
            value["longitude_radians"], value["latitude_radians"],
            value["longitude_rate_radians_per_day"], value["latitude_rate_radians_per_day"],
            _finite_or_none(value["distance_au"]), _finite_or_none(value["distance_rate_au_per_day"]),
            value["extrapolated"], resolved))


_LUNAR_PHYSICAL = frozenset((PositionFlag.truepos, PositionFlag.equatorial, PositionFlag.no_aberr,
                             PositionFlag.no_gdefl, PositionFlag.astrometric, PositionFlag.nonut))
_LUNAR_MEAN = frozenset((PositionFlag.equatorial, PositionFlag.nonut))


def _model_id(value):
    return value.id if hasattr(value, "id") else int(value)


def _custom_id(value):
    if not isinstance(value, int) or value < 10000 or value > 0x7fffffff:
        raise ValueError("id must fit signed 32-bit range and be at least 10000")


def _finite(value, name):
    if not math.isfinite(value):
        raise ValueError(name + " must be finite")


def _finite_or_none(value):
    return value if math.isfinite(value) else None


def _lunar_flags(flags, allowed, calculation):
    resolved = _normalized_flags(flags)
    unsupported = resolved - allowed
    if unsupported:
        raise ValueError("{} does not support {}".format(calculation, ", ".join(item.name for item in unsupported)))
    return resolved


def _house_model(model_id):
    return HouseSystem.from_id_or_none(model_id) or (CustomHouseSystemModel(model_id) if model_id >= 10000 else None)


def _houses(value):
    return Houses(
        value["requested_system_id"], value["resolved_system_id"], value["flags"],
        value["armc_radians"], value["ascendant_radians"], value["midheaven_radians"],
        value["vertex_radians"], value["east_point_radians"], value["armc_rate_radians_per_day"],
        value["ascendant_rate_radians_per_day"], value["midheaven_rate_radians_per_day"],
        value["vertex_rate_radians_per_day"], value["east_point_rate_radians_per_day"],
        HouseResultFlag.from_mask(value["flags"]), tuple(value["cusp_longitudes_radians"]),
        tuple(value["cusp_longitude_rates_radians_per_day"]))
