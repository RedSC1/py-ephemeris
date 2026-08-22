"""Time-scale helpers exposed from :class:`taiyin.EphemerisContext`."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from . import _native
from .result_flags import ResultFlag


class UtcLeapSecondRepresentationError(ValueError):
    """A split UTC Julian date cannot represent the inserted leap second."""


class TimeScaleConvergenceError(RuntimeError):
    """An automatic inverse time-scale conversion did not converge."""


class TdbModel(Enum):
    fastPeriodic = 0
    sofaFull = 1


class DeltaTModel(Enum):
    estimatedDefault = 0


class EphemerisFamily(Enum):
    unknown = 0
    de431 = 431
    de441 = 441


@dataclass(frozen=True)
class PreciseTimeScales:
    utc: Any
    tai: Any
    tt: Any
    ut1: Any
    tdb: Any
    tai_minus_utc_seconds: float
    dut1_seconds: float
    delta_t_seconds: float


@dataclass(frozen=True)
class EstimatedTimeScales:
    ut1: Any
    tt: Any
    tdb: Any
    delta_t_seconds: float


class Time:
    """Time conversions that share an :class:`EphemerisContext` lifecycle."""

    def __init__(self, context):
        self._context = context

    def set_allow_utc_out_of_range_estimate(self, allow: bool):
        """Allow UTC APIs to fall back to a UT1 + Delta-T approximation."""
        self._context._ensure_open()
        if not isinstance(allow, bool):
            raise TypeError("allow must be a bool")
        self._context._native_context.set_allow_utc_out_of_range_estimate(allow)

    def set_tdb_model(self, model):
        self._context._ensure_open()
        if not isinstance(model, TdbModel):
            raise ValueError("model must be a TdbModel")
        self._context._native_context.set_tdb_model(model.value)

    def set_delta_t_model(self, model, family=EphemerisFamily.unknown):
        self._context._ensure_open()
        if not isinstance(model, DeltaTModel) or not isinstance(family, EphemerisFamily):
            raise ValueError("model and family must use their time model enums")
        self._context._native_context.set_delta_t_model(model.value, family.value)

    def tt_to_tdb(self, tt, model: TdbModel = TdbModel.fastPeriodic):
        self._context._ensure_open()
        return _result(_native._tt_to_tdb(tt, model.value))

    def tdb_to_tt(self, tdb, model: TdbModel = TdbModel.fastPeriodic):
        self._context._ensure_open()
        return _result(_native._tdb_to_tt(tdb, model.value))

    def estimated_delta_t_from_ut1(self, ut1):
        self._context._ensure_open()
        return _result(_native._estimated_delta_t_from_ut1(ut1))

    def estimated_delta_t_from_tt(self, tt):
        self._context._ensure_open()
        return _result(_native._estimated_delta_t_from_tt(tt))

    def estimated_delta_t_for_decimal_year(self, decimal_year: float):
        self._context._ensure_open()
        return _result(_native._estimated_delta_t_for_decimal_year(decimal_year))

    def julian_day(self, value):
        self._context._ensure_open()
        return _result(_native._julian_day(value))

    def reverse_julian_day(self, value):
        self._context._ensure_open()
        return _result(_native._reverse_julian_day(value))

    def decimal_year(self, value):
        self._context._ensure_open()
        return _result(_native._decimal_year(value))

    def julian_centuries_since_j2000(self, value):
        self._context._ensure_open()
        return _result(_native._julian_centuries_since_j2000(value))

    def julian_millennia_since_j2000(self, value):
        self._context._ensure_open()
        return _result(_native._julian_millennia_since_j2000(value))

    def utc_to_tai(self, utc, tai_minus_utc_seconds: float):
        self._context._ensure_open()
        return _result(_native._utc_to_tai(utc, tai_minus_utc_seconds))

    def tai_to_tt(self, tai):
        self._context._ensure_open()
        return _result(_native._tai_to_tt(tai))

    def utc_to_tt(self, utc, tai_minus_utc_seconds: float):
        self._context._ensure_open()
        return _result(_native._utc_to_tt(utc, tai_minus_utc_seconds))

    def utc_to_ut1(self, utc, dut1_seconds: Optional[float] = None):
        self._context._ensure_open()
        if dut1_seconds is None:
            scales, flags = self._scales_from_utc_julian_date(utc)
            return scales.ut1, flags
        return _result(_native._utc_to_ut1(utc, dut1_seconds))

    def tt_to_ut1(self, tt, delta_t_seconds: Optional[float] = None):
        self._context._ensure_open()
        if delta_t_seconds is None:
            return self._invert_scale_to_ut1(tt, lambda scales: scales.tt)
        return _result(_native._tt_to_ut1(tt, delta_t_seconds))

    def ut1_to_tt(self, ut1, delta_t_seconds: float):
        self._context._ensure_open()
        return _result(_native._ut1_to_tt(ut1, delta_t_seconds))

    def tai_minus_utc(self, utc):
        """Looks up TAI−UTC for a UTC calendar date using the built-in table."""
        self._context._ensure_open()
        return _result(_native._tai_minus_utc(utc))

    def delta_t(self, tai_minus_utc_seconds: float, dut1_seconds: float):
        self._context._ensure_open()
        return _result(_native._delta_t(tai_minus_utc_seconds, dut1_seconds))

    def precise_scales_from_utc(
        self, utc, tai_minus_utc_seconds: float, dut1_seconds: float,
        model: TdbModel = TdbModel.fastPeriodic,
    ):
        """Build UTC, TAI, TT, UT1 and TDB from explicit UTC offsets."""
        self._context._ensure_open()
        return _result(_precise_scales(_native._precise_scales_from_utc(
            utc, tai_minus_utc_seconds, dut1_seconds, model.value)))

    def scales_from_utc(self, utc):
        """Build all scales using this context's EOP/leap-second policy.

        ``utc`` may be a UTC :class:`JulianDate` or an :class:`AstroDateTime`
        whose fields are interpreted as UTC. Successful estimation is reported
        with :attr:`ResultFlag.timeScaleFallback`.
        """
        self._context._ensure_open()
        if isinstance(utc, _native.JulianDate):
            utc, _ = self.reverse_julian_day(utc)
        if not isinstance(utc, _native.AstroDateTime):
            raise TypeError("utc must be JulianDate or AstroDateTime")
        value, flags = self._context._native_context.scales_from_utc(utc)
        return _precise_scales(value), ResultFlag(flags)

    def tai_to_utc(self, tai):
        """Convert TAI to UTC using the runtime leap-second table."""
        self._context._ensure_open()
        candidate = _copy_julian_date(tai)
        flags = ResultFlag.none
        for _ in range(_INVERSE_SCALE_ITERATIONS):
            calendar, calendar_flags = self.reverse_julian_day(candidate)
            offset, offset_flags = self.tai_minus_utc(calendar)
            flags |= calendar_flags | offset_flags
            evaluated = _copy_julian_date(candidate).add_seconds(offset)
            correction = tai.seconds_difference(evaluated)
            candidate = candidate.add_seconds(correction)
            if abs(correction) <= _INVERSE_SCALE_TOLERANCE_SECONDS:
                return candidate, flags
        raise UtcLeapSecondRepresentationError(
            "the physical instant is an inserted UTC leap second, which "
            "JulianDate cannot represent"
        )

    def tt_to_utc(self, tt):
        """Convert TT to UTC using the runtime leap-second table."""
        self._context._ensure_open()
        tai = _copy_julian_date(tt).add_seconds(-32.184)
        return self.tai_to_utc(tai)

    def ut1_to_utc(self, ut1):
        """Convert UT1 to UTC according to this context's EOP policy."""
        self._context._ensure_open()
        return self._invert_utc_scale(ut1, lambda scales: scales.ut1)

    def tdb_to_utc(self, tdb, model: TdbModel = TdbModel.fastPeriodic):
        """Convert TDB to UTC using the configured leap-second data."""
        self._context._ensure_open()
        tt, tt_flags = self.tdb_to_tt(tdb, model)
        utc, utc_flags = self.tt_to_utc(tt)
        return utc, tt_flags | utc_flags

    def tai_to_ut1(self, tai):
        """Convert TAI to UT1 through TT and the context's time policy."""
        self._context._ensure_open()
        tt, tt_flags = self.tai_to_tt(tai)
        ut1, ut1_flags = self.tt_to_ut1(tt)
        return ut1, tt_flags | ut1_flags

    def tdb_to_ut1(self, tdb, model: TdbModel = TdbModel.fastPeriodic):
        """Convert TDB to UT1 through TT and the context's time policy."""
        self._context._ensure_open()
        tt, tt_flags = self.tdb_to_tt(tdb, model)
        ut1, ut1_flags = self.tt_to_ut1(tt)
        return ut1, tt_flags | ut1_flags

    def calendar_from_ut1(self, ut1):
        """Format a UT1 coordinate as UT1 calendar fields without conversion."""
        self._context._ensure_open()
        return self.reverse_julian_day(ut1)

    def utc_calendar_from_ut1(self, ut1):
        """Convert UT1 to UTC and format the result as UTC calendar fields."""
        self._context._ensure_open()
        utc, utc_flags = self.ut1_to_utc(ut1)
        calendar, calendar_flags = self.reverse_julian_day(utc)
        return calendar, utc_flags | calendar_flags

    def estimated_scales_from_ut1(
        self, ut1, delta_t_seconds: Optional[float] = None,
        model: TdbModel = TdbModel.fastPeriodic,
    ):
        """Build UT1, TT and TDB using explicit or configured estimated Delta-T."""
        self._context._ensure_open()
        if delta_t_seconds is None:
            value = _native._estimated_scales_from_ut(ut1, model.value)
        else:
            value = _native._scales_from_ut_delta_t(ut1, delta_t_seconds, model.value)
        return _result(_estimated_scales(value))

    def _scales_from_utc_julian_date(self, utc):
        return self.scales_from_utc(utc)

    def _invert_utc_scale(self, target, select):
        candidate = _copy_julian_date(target)
        flags = ResultFlag.none
        for _ in range(_INVERSE_SCALE_ITERATIONS):
            scales, scale_flags = self._scales_from_utc_julian_date(candidate)
            flags |= scale_flags
            correction = target.seconds_difference(select(scales))
            candidate = candidate.add_seconds(correction)
            if abs(correction) <= _INVERSE_SCALE_TOLERANCE_SECONDS:
                return candidate, flags
        raise TimeScaleConvergenceError(
            "automatic conversion to UTC did not converge"
        )

    def _invert_scale_to_ut1(self, target, select):
        candidate = _copy_julian_date(target)
        flags = ResultFlag.none
        for _ in range(_INVERSE_SCALE_ITERATIONS):
            scales, scale_flags = self._scales_from_utc_julian_date(candidate)
            flags |= scale_flags
            correction = target.seconds_difference(select(scales))
            if abs(correction) <= _INVERSE_SCALE_TOLERANCE_SECONDS:
                return scales.ut1.add_seconds(correction), flags
            candidate = candidate.add_seconds(correction)
        raise TimeScaleConvergenceError(
            "automatic conversion to UT1 did not converge"
        )


def _result(value):
    return value, ResultFlag.none


def _copy_julian_date(value):
    return _native.JulianDate(value.day_number, value.day_fraction)


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


_INVERSE_SCALE_ITERATIONS = 6
_INVERSE_SCALE_TOLERANCE_SECONDS = 0.5e-9
