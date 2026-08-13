"""Chinese lunar calendar services on :class:`EphemerisContext`."""

import math
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

    def __post_init__(self):
        if not isinstance(self.ruleMode, ChineseCalendarRuleMode):
            raise TypeError("ruleMode must be ChineseCalendarRuleMode")
        if not isinstance(
            self.dayBoundaryMode, ChineseCalendarDayBoundaryMode
        ):
            raise TypeError(
                "dayBoundaryMode must be ChineseCalendarDayBoundaryMode"
            )
        if self.ruleMode is ChineseCalendarRuleMode.historicalChina:
            if (
                self.dayBoundaryMode
                is not ChineseCalendarDayBoundaryMode.fixedUtcOffset
                or self.utcOffsetMinutes != 480
            ):
                raise ValueError(
                    "historicalChina requires fixed UTC+08:00 "
                    "(utcOffsetMinutes=480)"
                )
            return
        if (
            self.dayBoundaryMode
            is ChineseCalendarDayBoundaryMode.fixedUtcOffset
        ):
            if (
                not isinstance(self.utcOffsetMinutes, int)
                or isinstance(self.utcOffsetMinutes, bool)
                or not -14 * 60 <= self.utcOffsetMinutes <= 14 * 60
            ):
                raise ValueError(
                    "utcOffsetMinutes must be an integer from -840 to 840"
                )
        elif (
            not isinstance(self.calendarMeridianDegrees, (int, float))
            or isinstance(self.calendarMeridianDegrees, bool)
            or not math.isfinite(self.calendarMeridianDegrees)
            or not -180.0 <= self.calendarMeridianDegrees <= 180.0
        ):
            raise ValueError(
                "calendarMeridianDegrees must be from -180 to 180"
            )

    @classmethod
    def astronomical(cls):
        return cls()

    @classmethod
    def historical_china(cls):
        return cls(
            ruleMode=ChineseCalendarRuleMode.historicalChina,
            dayBoundaryMode=ChineseCalendarDayBoundaryMode.fixedUtcOffset,
            utcOffsetMinutes=480,
        )

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

    @classmethod
    def from_string(cls, year, month_name, day, *, is_leap=None):
        """Builds a lunar date from a traditional Chinese month name.

        Parsing is a Python convenience. The native calendar remains
        responsible for deciding whether the requested month exists in
        ``year`` and whether ``day`` is valid for that particular month.

        Accepted spellings include ``正``/``正月``, ``一`` through ``十二``,
        ``冬`` (eleven), ``腊`` (twelve), ``闰五``, ``后九``, ``拾贰`` and
        ``十三``. A trailing ``月`` is optional.
        """
        if not isinstance(month_name, str):
            raise TypeError("month_name must be a string")
        if not isinstance(day, int) or isinstance(day, bool) or not 1 <= day <= 30:
            raise ValueError("lunar day must be an integer from 1 through 30")
        if is_leap is not None and not isinstance(is_leap, bool):
            raise TypeError("is_leap must be bool or None")

        normalized = month_name.strip().replace("閏", "闰")
        if normalized.endswith("月"):
            normalized = normalized[:-1].strip()
        if not normalized:
            raise ValueError("lunar month name must not be empty")

        special = {
            "十三": (13, True, ChineseCalendarMonthName.thirteen),
            "后九": (9, True, ChineseCalendarMonthName.laterNine),
            "後九": (9, True, ChineseCalendarMonthName.laterNine),
            "拾贰": (12, False, ChineseCalendarMonthName.altTwelve),
            "拾貳": (12, False, ChineseCalendarMonthName.altTwelve),
        }
        if normalized in special:
            month, resolved_leap, historical_name = special[normalized]
            return cls(year, month, day, resolved_leap, 0, historical_name)

        has_leap_prefix = normalized.startswith("闰")
        if has_leap_prefix:
            normalized = normalized[1:].strip()
        month_numbers = {
            "正": 1,
            "一": 1,
            "二": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
            "十一": 11,
            "冬": 11,
            "十二": 12,
            "腊": 12,
            "臘": 12,
        }
        try:
            month = month_numbers[normalized]
        except KeyError:
            raise ValueError("unknown Chinese lunar month name: %r" % month_name)
        resolved_leap = has_leap_prefix if is_leap is None else is_leap
        return cls(
            year,
            month,
            day,
            resolved_leap,
            0,
            ChineseCalendarMonthName.normal,
        )


@dataclass(frozen=True)
class ChineseSolarTermEvent:
    indexFromWinterSolstice: int
    targetLongitudeRadians: float
    jdUt: object
    civilDayNumber: int


@dataclass(frozen=True)
class ChineseNewMoonEvent:
    jdUt: object
    civilDayNumber: int


@dataclass(frozen=True)
class ChineseCalendarMonth:
    lunarYear: int
    month: int
    isLeap: bool
    dayCount: int
    monthName: ChineseCalendarMonthName
    firstCivilDayNumber: int
    astronomicalNewMoonJdUt: object


@dataclass(frozen=True)
class ChineseCalendarYear:
    solarTerms: tuple
    newMoons: tuple
    months: tuple
    solarTermCount: int
    newMoonCount: int
    monthCount: int
    leapMonthIndex: int
    firstWinterSolsticeDayNumber: int
    secondWinterSolsticeDayNumber: int


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

    def calc_year_ut(self, jd_ut) -> ChineseCalendarYear:
        self._ensure_open()
        value = self._native_context.calc_year_ut(jd_ut)
        solar_terms = tuple(self._solar_term(item) for item in value["solar_terms"])
        new_moons = tuple(
            ChineseNewMoonEvent(item["jd_ut"], item["civil_day_number"])
            for item in value["new_moons"]
        )
        months = tuple(
            ChineseCalendarMonth(
                item["lunar_year"], item["month"], item["is_leap"], item["day_count"],
                ChineseCalendarMonthName(item["month_name"]), item["first_civil_day_number"],
                item["astronomical_new_moon_jd_ut"],
            )
            for item in value["months"]
        )
        return ChineseCalendarYear(
            solar_terms, new_moons, months, value["solar_term_count"],
            value["new_moon_count"], value["month_count"], value["leap_month_index"],
            value["first_winter_solstice_day_number"], value["second_winter_solstice_day_number"],
        )
