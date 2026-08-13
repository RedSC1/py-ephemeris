"""Rise, set, twilight, and meridian-transit visibility searches."""

import math
from dataclasses import dataclass
from enum import Enum

from .position import Body, _target_id, position_flag_mask


class VisibilityEventKind(Enum):
    rise = 1
    set = 2
    upperTransit = 3
    lowerTransit = 4

    @property
    def id(self): return self.value
    @property
    def is_rise_or_set(self): return self in (self.rise, self.set)
    @property
    def is_transit(self): return self in (self.upperTransit, self.lowerTransit)


class VisibilityLimb(Enum):
    upper = 1
    center = 2
    lower = 3
    @property
    def id(self): return self.value


class TwilightKind(Enum):
    civil = 1
    nautical = 2
    astronomical = 3
    @property
    def id(self): return self.value


class VisibilityAltitudeState(Enum):
    notFound = 0
    crosses = 1
    alwaysAbove = 2
    alwaysBelow = 3
    tangent = 4
    unknown = -1
    @classmethod
    def from_id(cls, value):
        try: return cls(value)
        except ValueError: return cls.unknown


class VisibilityCrossingDirection(Enum):
    any = 0
    rising = 1
    setting = 2
    unknown = -1
    @classmethod
    def from_id(cls, value):
        try: return cls(value)
        except ValueError: return cls.unknown


class VisibilityFlag(Enum):
    refraction = 1 << 0
    fixedDiscSize = 1 << 1
    noRefraction = 1 << 2
    strictMeteorology = 1 << 32
    @property
    def mask(self): return self.value


@dataclass(frozen=True)
class VisibilityEvent:
    requestedEvent: VisibilityEventKind
    altitudeState: VisibilityAltitudeState
    crossingDirection: VisibilityCrossingDirection
    coordinate: object
    residualRadians: float
    minimumResidualRadians: float
    maximumResidualRadians: float
    minimumResidualCoordinate: object
    maximumResidualCoordinate: object
    sampleCount: int
    refineCount: int
    @property
    def is_found(self): return self.coordinate is not None


@dataclass(frozen=True)
class SolarRiseSetFastResult:
    altitudeState: VisibilityAltitudeState
    rise: object
    set: object
    sampleCount: int
    refineCount: int


@dataclass(frozen=True)
class SolarTransitFastResult:
    coordinate: object
    altitudeRadians: float
    azimuthRadians: float
    sampleCount: int
    refineCount: int


class VisibilityApi:
    def __init__(self, context): self._context = context

    def moon_rise_set_at_ut1(self, start, end, *, event, limb=VisibilityLimb.upper,
                             horizon_altitude_radians=None, flags=()):
        return self._rise_set("moon_rise_set_at_ut1", start, end, event, limb, horizon_altitude_radians, flags)

    def moon_transit_at_ut1(self, start, end, *, event):
        return self._transit("moon_transit_at_ut1", start, end, event)

    def planet_rise_set_at_ut1(self, body, start, end, *, event, limb=VisibilityLimb.upper,
                               horizon_altitude_radians=None, flags=()):
        if _target_id(body) not in _PLANET_IDS: raise ValueError("body must be a physical planet from Mercury through Pluto")
        return self._rise_set("planet_rise_set_at_ut1", start, end, event, limb, horizon_altitude_radians, flags, _target_id(body), False)

    def planet_transit_at_ut1(self, body, start, end, *, event, flags=()):
        if _target_id(body) not in _PLANET_IDS: raise ValueError("body must be a physical planet from Mercury through Pluto")
        return self._transit("planet_transit_at_ut1", start, end, event, _target_id(body), position_flag_mask(flags))

    def solar_rise_set_at_ut1(self, start, end, *, event, limb=VisibilityLimb.upper,
                              horizon_altitude_radians=None, flags=()):
        return self._rise_set("solar_rise_set_at_ut1", start, end, event, limb, horizon_altitude_radians, flags)

    def solar_twilight_at_ut1(self, start, end, *, event, twilight):
        _interval(start, end); _rise_or_set(event); self._context._ensure_open()
        return _event(self._context._call_native_operation(
            "Visibility.solar_twilight_at_ut1", "solar_twilight_at_ut1",
            start, end, event.id, twilight.id), event)

    def solar_transit_at_ut1(self, start, end, *, event):
        return self._transit("solar_transit_at_ut1", start, end, event)

    def solar_rise_set_fast_at_tt(self, center, observer, *, limb=VisibilityLimb.upper,
                                  horizon_altitude_radians=0.0, flags=()):
        self._context._ensure_open(); _observer(observer); _finite(horizon_altitude_radians, "horizon_altitude_radians")
        value = self._context._call_native_operation("Visibility.solar_rise_set_fast_at_tt", "solar_rise_set_fast_at_tt",
            center, observer.longitude_degrees, observer.latitude_degrees, observer.height_meters,
            limb.id, horizon_altitude_radians, visibility_flag_mask(flags))
        return SolarRiseSetFastResult(VisibilityAltitudeState.from_id(value["altitude_state"]),
            _date_or_none(value["rise"]), _date_or_none(value["set"]), value["sample_count"], value["refine_count"])

    def solar_transit_fast_at_tt(self, center, observer):
        self._context._ensure_open(); _observer(observer)
        value = self._context._call_native_operation("Visibility.solar_transit_fast_at_tt", "solar_transit_fast_at_tt",
            center, observer.longitude_degrees, observer.latitude_degrees, observer.height_meters)
        return SolarTransitFastResult(_date_or_none(value["coordinate"]), value["altitude_radians"],
            value["azimuth_radians"], value["sample_count"], value["refine_count"])

    def star_rise_set_at_ut1(self, star_key, start, end, *, event, horizon_altitude_radians=None, flags=()):
        _star(star_key); _interval(start, end); _rise_or_set(event); self._context._ensure_open(); _horizon(horizon_altitude_radians)
        return _event(self._context._call_native_operation("Visibility.star_rise_set_at_ut1", "star_rise_set_at_ut1",
            star_key, start, end, event.id, horizon_altitude_radians,
            visibility_flag_mask(flags, allows_fixed_disc_size=False)), event)

    def star_transit_at_ut1(self, star_key, start, end, *, event):
        _star(star_key); return self._transit("star_transit_at_ut1", start, end, event, star_key)

    def _rise_set(self, method, start, end, event, limb, horizon, flags, target=None, fixed=True):
        _interval(start, end); _rise_or_set(event); self._context._ensure_open(); _horizon(horizon)
        mask = visibility_flag_mask(flags, allows_fixed_disc_size=fixed)
        args = (start, end, event.id, limb.id if limb is not None else None, horizon, mask)
        if target is not None: args = (target,) + args
        return _event(self._context._call_native_operation("Visibility." + method, method, *args), event)

    def _transit(self, method, start, end, event, target=None, flags=None):
        _interval(start, end); _transit(event); self._context._ensure_open()
        args = (start, end, event.id) if target is None else (target, start, end, event.id)
        if flags is not None: args = args + (flags,)
        return _event(self._context._call_native_operation("Visibility." + method, method, *args), event)


_PLANET_IDS = frozenset((199, 299, 499, 599, 699, 799, 899, 999))

def visibility_flag_mask(flags, *, allows_fixed_disc_size=True):
    flags = frozenset(flags)
    if VisibilityFlag.refraction in flags and VisibilityFlag.noRefraction in flags: raise ValueError("refraction and noRefraction cannot both be selected")
    if not allows_fixed_disc_size and VisibilityFlag.fixedDiscSize in flags: raise ValueError("fixedDiscSize is supported only for Sun and Moon searches")
    return sum(flag.mask for flag in flags)

def _event(value, requested):
    return VisibilityEvent(requested, VisibilityAltitudeState.from_id(value["altitude_state"]),
        VisibilityCrossingDirection.from_id(value["crossing_direction"]), _date_or_none(value["coordinate"]),
        value["residual_radians"], value["minimum_residual_radians"], value["maximum_residual_radians"],
        _date_or_none(value["minimum_residual_coordinate"]), _date_or_none(value["maximum_residual_coordinate"]),
        value["sample_count"], value["refine_count"])

def _date_or_none(value): return value if math.isfinite(value.day_fraction) else None
def _finite(value, name):
    if not math.isfinite(value): raise ValueError(name + " must be finite")
def _horizon(value):
    if value is not None: _finite(value, "horizon_altitude_radians")
def _interval(start, end):
    if not start.to_double() < end.to_double(): raise ValueError("end must be later than start")
def _rise_or_set(event):
    if not event.is_rise_or_set: raise ValueError("event must be rise or set")
def _transit(event):
    if not event.is_transit: raise ValueError("event must be upperTransit or lowerTransit")
def _star(value):
    if not value or "\x00" in value: raise ValueError("star_key must be a non-empty NUL-free string")
def _observer(value):
    for name in ("longitude_degrees", "latitude_degrees", "height_meters"): _finite(getattr(value, name), "observer." + name)
    if not -90 <= value.latitude_degrees <= 90: raise ValueError("observer.latitude_degrees must be in [-90, 90]")
