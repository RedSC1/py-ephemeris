"""Position and Cartesian-state models for :class:`taiyin.EphemerisContext`."""

from dataclasses import dataclass
from enum import Enum


class Body(Enum):
    ssb = 0
    mercury_barycenter = 1
    venus_barycenter = 2
    emb = 3
    mars_barycenter = 4
    jupiter_barycenter = 5
    saturn_barycenter = 6
    uranus_barycenter = 7
    neptune_barycenter = 8
    pluto_barycenter = 9
    sun = 10
    mercury = 199
    venus = 299
    moon = 301
    earth = 399
    phobos = 401
    deimos = 402
    mars = 499
    io = 501
    europa = 502
    ganymede = 503
    callisto = 504
    jupiter = 599
    saturn = 699
    uranus = 799
    triton = 801
    neptune = 899
    charon = 901
    nix = 902
    hydra = 903
    kerberos = 904
    styx = 905
    pluto = 999

    @property
    def id(self):
        return self.value


class PositionFlag(Enum):
    speed = 1 << 0
    xyz = 1 << 1
    equatorial = 1 << 2
    radians = 1 << 3
    truepos = 1 << 4
    no_aberr = 1 << 5
    no_gdefl = 1 << 6
    astrometric = 1 << 7
    nonut = 1 << 8
    topocentric = 1 << 9
    allow_barycenter_approx = 1 << 10

    @property
    def mask(self):
        return self.value


class ApparentFrame(Enum):
    icrf = 0
    true_equator_of_date = 1
    true_ecliptic_of_date = 2
    j2000_mean_equator = 3
    j2000_ecliptic = 4
    mean_equator_of_date = 5
    mean_ecliptic_of_date = 6
    cirs = 7
    unknown = -1

    @classmethod
    def from_id(cls, value):
        try:
            return cls(value)
        except ValueError:
            return cls.unknown


def position_flag_mask(flags):
    if isinstance(flags, int):
        return flags
    return sum(flag.mask for flag in flags)


def _normalized_flags(flags):
    if isinstance(flags, int):
        return frozenset(flag for flag in PositionFlag if flags & flag.mask)
    return frozenset(flags)


def _target_id(value):
    return value.id if isinstance(value, Body) else int(value)


@dataclass(frozen=True)
class Vector3:
    x: float
    y: float
    z: float

    def __iter__(self):
        return iter((self.x, self.y, self.z))

    def __getitem__(self, index):
        return (self.x, self.y, self.z)[index]


@dataclass(frozen=True)
class Position:
    coordinates: tuple
    rates: object
    flags: frozenset


@dataclass(frozen=True)
class CartesianState:
    position_au: Vector3
    velocity_au_per_day: Vector3
    acceleration_au_per_day2: Vector3


@dataclass(frozen=True)
class EphemerisDiagnostic:
    status: int
    target_id: int
    center_id: int
    frame: ApparentFrame
    raw_frame_id: int
    jd_tdb: object
    candidate_count: int
    attempted_method_id: int
    nearest_coverage_start: float
    nearest_coverage_end: float
    component_target_id: int
    component_center_id: int
    component_method_id: int
    time_scale_route: int
    raw_time_scale_route_id: int
    time_scale_fallback_reason: int
    raw_time_scale_fallback_reason_id: int
    time_scale_flags: int
    tai_minus_utc_seconds: float
    dut1_seconds: float
    delta_t_seconds: float


@dataclass(frozen=True)
class EphemerisResult:
    value: object
    diagnostic: EphemerisDiagnostic


class PositionApi:
    """Position and Cartesian-state calculations for one native context."""

    def __init__(self, context):
        self._context = context

    def at_tdb(self, body, tdb, tt, flags=()):
        self._context._ensure_open()
        return _position_result(self._context._native_context.position_at_tdb(
            _target_id(body), tdb, tt, position_flag_mask(flags)), flags)

    def at_tt(self, body, tt, flags=()):
        self._context._ensure_open()
        return _position_result(self._context._native_context.position_at_tt(
            _target_id(body), tt, position_flag_mask(flags)), flags)

    def at_ut1(self, body, ut1, flags=()):
        self._context._ensure_open()
        return _position_result(self._context._native_context.position_at_ut1(
            _target_id(body), ut1, position_flag_mask(flags)), flags)

    def at_ut1_with_delta_t(self, body, ut1, delta_t_seconds, flags=()):
        self._context._ensure_open()
        return _position_result(self._context._native_context.position_at_ut1_with_delta_t(
            _target_id(body), ut1, delta_t_seconds, position_flag_mask(flags)), flags)

    def at_utc(self, body, utc, flags=()):
        self._context._ensure_open()
        return _position_result(self._context._native_context.position_at_utc(
            _target_id(body), utc, position_flag_mask(flags)), flags)

    def batch_at_tt(self, bodies, tt, flags=()):
        self._context._ensure_open()
        rows = self._context._native_context.positions_at_tt(
            [_target_id(body) for body in bodies], tt, position_flag_mask(flags))
        return [_position_result(row, flags) for row in rows]

    def batch_at_ut1(self, bodies, ut1, flags=()):
        self._context._ensure_open()
        rows = self._context._native_context.positions_at_ut1(
            [_target_id(body) for body in bodies], ut1, position_flag_mask(flags))
        return [_position_result(row, flags) for row in rows]

    def state_at_tdb(self, body, tdb, tt, flags=()):
        self._context._ensure_open()
        return _state_result(self._context._native_context.state_at_tdb(
            _target_id(body), tdb, tt, position_flag_mask(flags)))

    def state_at_tt(self, body, tt, flags=()):
        self._context._ensure_open()
        return _state_result(self._context._native_context.state_at_tt(
            _target_id(body), tt, position_flag_mask(flags)))

    def state_at_ut1(self, body, ut1, flags=()):
        self._context._ensure_open()
        return _state_result(self._context._native_context.state_at_ut1(
            _target_id(body), ut1, position_flag_mask(flags)))


def _diagnostic(value):
    return EphemerisDiagnostic(
        status=value["status"], target_id=value["target_id"], center_id=value["center_id"],
        frame=ApparentFrame.from_id(value["frame"]), raw_frame_id=value["frame"],
        jd_tdb=value["jd_tdb"], candidate_count=value["candidate_count"],
        attempted_method_id=value["attempted_method_id"],
        nearest_coverage_start=value["nearest_coverage_start"],
        nearest_coverage_end=value["nearest_coverage_end"],
        component_target_id=value["component_target_id"],
        component_center_id=value["component_center_id"],
        component_method_id=value["component_method_id"],
        time_scale_route=value["time_scale_route"],
        raw_time_scale_route_id=value["time_scale_route"],
        time_scale_fallback_reason=value["time_scale_fallback_reason"],
        raw_time_scale_fallback_reason_id=value["time_scale_fallback_reason"],
        time_scale_flags=value["time_scale_flags"],
        tai_minus_utc_seconds=value["tai_minus_utc_seconds"],
        dut1_seconds=value["dut1_seconds"], delta_t_seconds=value["delta_t_seconds"],
    )


def _position_result(value, flags):
    normalized = _normalized_flags(flags)
    values = value["values"]
    return EphemerisResult(
        Position(tuple(values[:3]), tuple(values[3:]) if PositionFlag.speed in normalized else None,
                 normalized),
        _diagnostic(value["diagnostic"]),
    )


def _state_result(value):
    return EphemerisResult(
        CartesianState(Vector3(*value["position_au"]), Vector3(*value["velocity_au_per_day"]),
                       Vector3(*value["acceleration_au_per_day2"])),
        _diagnostic(value["diagnostic"]),
    )
