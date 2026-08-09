"""Chinese lunar calendar services on :class:`EphemerisContext`."""

from dataclasses import dataclass
from enum import Enum

from . import _native
from .ganzhi import Ganzhi, GanzhiFourPillars, GanzhiRatHourMode


class ChineseCalendarRuleMode(Enum):
    historicalChina = 0
    astronomical = 1


class ChineseCalendarDayBoundaryMode(Enum):
    fixedUtcOffset = 0
    meanSolarMeridian = 1


class ChineseCalendarMonthName(Enum):
    normal = 0
    thirteen = 1
    laterNine = 2
    altTwelve = 3
    altOne = 4


@dataclass(frozen=True)
class ChineseCalendarConfig:
    ruleMode: ChineseCalendarRuleMode = ChineseCalendarRuleMode.astronomical
    dayBoundaryMode: ChineseCalendarDayBoundaryMode = (
        ChineseCalendarDayBoundaryMode.fixedUtcOffset
    )
    utcOffsetMinutes: int = 480
    calendarMeridianDegrees: float = 0.0

    @classmethod
    def astronomical(cls):
        return cls()

    @classmethod
    def utc_offset(cls, utc_offset_minutes: int):
        return cls(utcOffsetMinutes=utc_offset_minutes)

    @classmethod
    def meridian(cls, longitude_degrees: float):
        return cls(
            dayBoundaryMode=ChineseCalendarDayBoundaryMode.meanSolarMeridian,
            calendarMeridianDegrees=longitude_degrees,
        )


@dataclass(frozen=True)
class SolarDate:
    year: int
    month: int
    day: int


@dataclass(frozen=True)
class LunarDate:
    year: int
    month: int
    day: int
    isLeap: bool
    monthDays: int = 0
    monthName: ChineseCalendarMonthName = ChineseCalendarMonthName.normal


@dataclass(frozen=True)
class ChineseSolarTermEvent:
    indexFromWinterSolstice: int
    targetLongitudeRadians: float
    jdUt: object
    civilDayNumber: int


class ChineseCalendarContext:
    """Chinese calendar rules backed by an owning ephemeris context."""

    def __init__(self, owner, config: ChineseCalendarConfig):
        owner._ensure_open()
        self._owner = owner
        self.config = config
        self._native_context = _native._create_chinese_calendar(
            owner._native_context,
            config.ruleMode.value,
            config.dayBoundaryMode.value,
            config.utcOffsetMinutes,
            config.calendarMeridianDegrees,
        )
        self._closed = False

    @property
    def is_closed(self) -> bool:
        return self._closed

    def _ensure_open(self) -> None:
        self._owner._ensure_open()
        if self._closed:
            raise RuntimeError("ChineseCalendarContext is closed")

    def close(self) -> None:
        self._closed = True

    def four_pillars(
        self,
        instant_utc,
        virtual_time,
        *,
        rat_hour_mode: GanzhiRatHourMode = GanzhiRatHourMode.noSplit,
    ) -> GanzhiFourPillars:
        self._ensure_open()
        values = self._native_context.four_pillars(
            instant_utc, virtual_time, rat_hour_mode.value
        )
        return GanzhiFourPillars(*(Ganzhi.from_native(value) for value in values))

    def from_solar(self, solar: SolarDate) -> LunarDate:
        self._ensure_open()
        value = self._native_context.from_solar(solar.year, solar.month, solar.day)
        return LunarDate(
            value["year"], value["month"], value["day"], value["is_leap"],
            value["month_days"], ChineseCalendarMonthName(value["month_name"]),
        )

    def from_lunar(self, lunar: LunarDate) -> SolarDate:
        self._ensure_open()
        value = self._native_context.from_lunar(
            lunar.year, lunar.month, lunar.day, lunar.isLeap, lunar.monthName.value
        )
        return SolarDate(value["year"], value["month"], value["day"])

    def get_month_days(self, lunar_year: int, month: int, is_leap: bool) -> int:
        self._ensure_open()
        return self._native_context.get_month_days(lunar_year, month, is_leap)

    @staticmethod
    def _solar_term(value) -> ChineseSolarTermEvent:
        return ChineseSolarTermEvent(
            value["index"], value["longitude"], value["jd_ut"], value["civil_day_number"]
        )

    def get_specific_jie_qi_ut(self, civil_year: int, term_index_from_vernal_equinox: int):
        self._ensure_open()
        return self._solar_term(self._native_context.get_specific_jie_qi_ut(
            civil_year, term_index_from_vernal_equinox
        ))

    def get_prev_jie_qi_ut(self, jd_ut):
        self._ensure_open()
        return self._solar_term(self._native_context.get_prev_jie_qi_ut(jd_ut))

    def get_next_jie_qi_ut(self, jd_ut):
        self._ensure_open()
        return self._solar_term(self._native_context.get_next_jie_qi_ut(jd_ut))

    def get_prev_jie_ut(self, jd_ut):
        self._ensure_open()
        return self._solar_term(self._native_context.get_prev_jie_ut(jd_ut))

    def get_next_jie_ut(self, jd_ut):
        self._ensure_open()
        return self._solar_term(self._native_context.get_next_jie_ut(jd_ut))

    def get_prev_qi_ut(self, jd_ut):
        self._ensure_open()
        return self._solar_term(self._native_context.get_prev_qi_ut(jd_ut))

    def get_next_qi_ut(self, jd_ut):
        self._ensure_open()
        return self._solar_term(self._native_context.get_next_qi_ut(jd_ut))
