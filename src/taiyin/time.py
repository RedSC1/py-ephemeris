"""Time-scale helpers exposed from :class:`taiyin.EphemerisContext`."""

from enum import Enum

from . import _native


class TdbModel(Enum):
    fastPeriodic = 0
    sofaFull = 1


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
