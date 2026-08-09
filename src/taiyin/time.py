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
