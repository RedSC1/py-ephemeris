"""Context configuration types currently needed by event searches."""

from dataclasses import dataclass
from enum import Enum


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
