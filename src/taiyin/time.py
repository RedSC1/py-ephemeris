"""Time-scale helpers exposed from :class:`taiyin.EphemerisContext`."""

from dataclasses import dataclass
from enum import Enum

from . import _native


class TdbModel(Enum):
    fastPeriodic = 0
    sofaFull = 1


@dataclass(frozen=True)
class PreciseTimeScales:
    utc: object
    tai: object
    tt: object
    ut1: object
    tdb: object
    tai_minus_utc_seconds: float
    dut1_seconds: float
    delta_t_seconds: float


@dataclass(frozen=True)
class EstimatedTimeScales:
    ut1: object
    tt: object
    tdb: object
    delta_t_seconds: float


class Time:
    """Time conversions that share an :class:`EphemerisContext` lifecycle."""

    def __init__(self, context):
        self._context = context

    def tt_to_tdb(self, tt, model: TdbModel = TdbModel.fastPeriodic):
        self._context._ensure_open()
        return _native._tt_to_tdb(tt, model.value)

    def tdb_to_tt(self, tdb, model: TdbModel = TdbModel.fastPeriodic):
        self._context._ensure_open()
        return _native._tdb_to_tt(tdb, model.value)

    def estimated_delta_t_from_ut1(self, ut1):
        self._context._ensure_open()
        return _native._estimated_delta_t_from_ut1(ut1)

    def estimated_delta_t_from_tt(self, tt):
        self._context._ensure_open()
        return _native._estimated_delta_t_from_tt(tt)

    def estimated_delta_t_for_decimal_year(self, decimal_year: float):
        self._context._ensure_open()
        return _native._estimated_delta_t_for_decimal_year(decimal_year)

    def julian_day(self, value):
        self._context._ensure_open()
        return _native._julian_day(value)

    def reverse_julian_day(self, value):
        self._context._ensure_open()
        return _native._reverse_julian_day(value)

    def decimal_year(self, value):
        self._context._ensure_open()
        return _native._decimal_year(value)

    def julian_centuries_since_j2000(self, value):
        self._context._ensure_open()
        return _native._julian_centuries_since_j2000(value)

    def julian_millennia_since_j2000(self, value):
        self._context._ensure_open()
        return _native._julian_millennia_since_j2000(value)

    def utc_to_tai(self, utc, tai_minus_utc_seconds: float):
        self._context._ensure_open()
        return _native._utc_to_tai(utc, tai_minus_utc_seconds)

    def tai_to_tt(self, tai):
        self._context._ensure_open()
        return _native._tai_to_tt(tai)

    def utc_to_tt(self, utc, tai_minus_utc_seconds: float):
        self._context._ensure_open()
        return _native._utc_to_tt(utc, tai_minus_utc_seconds)

    def utc_to_ut1(self, utc, dut1_seconds: float):
        self._context._ensure_open()
        return _native._utc_to_ut1(utc, dut1_seconds)

    def tt_to_ut1(self, tt, delta_t_seconds: float):
        self._context._ensure_open()
        return _native._tt_to_ut1(tt, delta_t_seconds)

    def ut1_to_tt(self, ut1, delta_t_seconds: float):
        self._context._ensure_open()
        return _native._ut1_to_tt(ut1, delta_t_seconds)

    def tai_minus_utc(self, utc):
        """Looks up TAI−UTC for a UTC calendar date using the built-in table."""
        self._context._ensure_open()
        return _native._tai_minus_utc(utc)

    def delta_t(self, tai_minus_utc_seconds: float, dut1_seconds: float):
        self._context._ensure_open()
        return _native._delta_t(tai_minus_utc_seconds, dut1_seconds)

    def precise_scales_from_utc(self, utc, tai_minus_utc_seconds: float,
                                dut1_seconds: float,
                                model: TdbModel = TdbModel.fastPeriodic):
        """Builds UTC, TAI, TT, UT1 and TDB from explicit UTC offsets."""
        self._context._ensure_open()
        return _precise_scales(_native._precise_scales_from_utc(
            utc, tai_minus_utc_seconds, dut1_seconds, model.value))

    def estimated_scales_from_ut1(self, ut1, delta_t_seconds: float = None,
                                  model: TdbModel = TdbModel.fastPeriodic):
        """Builds UT1, TT and TDB using explicit or configured estimated Delta-T."""
        self._context._ensure_open()
        if delta_t_seconds is None:
            return _estimated_scales(_native._estimated_scales_from_ut(ut1, model.value))
        return _estimated_scales(_native._scales_from_ut_delta_t(
            ut1, delta_t_seconds, model.value))


def _precise_scales(value) -> PreciseTimeScales:
    return PreciseTimeScales(
        utc=value["utc"], tai=value["tai"], tt=value["tt"], ut1=value["ut1"],
        tdb=value["tdb"], tai_minus_utc_seconds=value["tai_minus_utc_seconds"],
        dut1_seconds=value["dut1_seconds"], delta_t_seconds=value["delta_t_seconds"],
    )


def _estimated_scales(value) -> EstimatedTimeScales:
    return EstimatedTimeScales(
        ut1=value["ut1"], tt=value["tt"], tdb=value["tdb"],
        delta_t_seconds=value["delta_t_seconds"],
    )
