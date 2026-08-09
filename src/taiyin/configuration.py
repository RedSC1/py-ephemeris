"""Context configuration types currently needed by event searches."""

from dataclasses import dataclass
from enum import Enum
import math


@dataclass(frozen=True)
class ObserverLocation:
    longitude_degrees: float
    latitude_degrees: float
    height_meters: float = 0.0


class RouteRule(Enum):
    automatic = 0
    opm2 = 1
    spk = 2
    semiAnalytic = 3

    @property
    def id(self):
        return self.value


class ApparentFlag(Enum):
    lightTime = 1 << 0
    spherical = 1 << 2
    aberration = 1 << 3
    deflection = 1 << 4
    velocity = 1 << 5
    acceleration = 1 << 6
    shapiroDelay = 1 << 7

    @property
    def mask(self):
        return self.value


@dataclass(frozen=True)
class ApparentConfig:
    flags: frozenset = frozenset()
    output_frame: int = 2

    def __post_init__(self):
        object.__setattr__(self, "flags", frozenset(self.flags))


class ContextConfiguration:
    """The context policy controls used by the Events module."""

    def __init__(self, context):
        self._context = context

    def set_geocentric_observer(self, *, observer_id, center_id):
        self._context._ensure_open()
        self._context._native_context.set_geocentric_observer(observer_id, center_id)

    def set_observer_location(self, location):
        self._context._ensure_open()
        for coordinate in (
            location.longitude_degrees, location.latitude_degrees, location.height_meters):
            if not isinstance(coordinate, (int, float)) or not math.isfinite(coordinate):
                raise ValueError("observer coordinates must be finite")
        if not -90.0 <= location.latitude_degrees <= 90.0:
            raise ValueError("observer latitude must be in [-90, 90]")
        self._context._native_context.set_observer_location(
            location.longitude_degrees, location.latitude_degrees, location.height_meters)

    def set_standard_atmosphere(self):
        self._context._ensure_open()
        self._context._native_context.set_standard_atmosphere()

    def use_solar_deflector(self):
        self._context._ensure_open()
        self._context._native_context.use_solar_deflector()

    def set_apparent_config(self, config):
        self._context._ensure_open()
        self._context._native_context.set_apparent_config(
            sum(flag.mask for flag in config.flags), config.output_frame)

    def set_route_rule(self, route_rule):
        self._context._ensure_open()
        self._context._native_context.set_route_rule(route_rule.id)
