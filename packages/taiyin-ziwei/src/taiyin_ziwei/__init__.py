from __future__ import annotations

"""Ziwei Doushu bindings extending :mod:`taiyin`.

The package owns rule catalogs; charts continue to use the caller's Taiyin
calculation and Chinese-calendar contexts.  That keeps calendar policy and
ephemeris routing a single source of truth.
"""

from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
import math
from pathlib import Path
from typing import Any, Mapping, Optional

from taiyin import ChineseCalendarContext, GanzhiRatHourMode
from . import _ziwei_native as _native  # pyright: ignore[reportAttributeAccessIssue]


class _ZiweiEnum(Enum):
    @property
    def id(self):
        return self.value


class ZiweiGender(_ZiweiEnum):
    male = 0
    female = 1


class ZiweiPillarBoundary(_ZiweiEnum):
    solarTerm = 0
    lunar = 1


class ZiweiChartMode(_ZiweiEnum):
    tianPan = 0
    diPan = 1
    renPan = 2


class ZiweiLeapMonthStrategy(_ZiweiEnum):
    asPrevious = 0
    asNext = 1
    splitAfterFifteenth = 2


class ZiweiFlowLevel(_ZiweiEnum):
    decade = 0
    year = 1
    month = 2
    day = 3
    hour = 4


class ZiweiChildhoodStrategy(_ZiweiEnum):
    skip = 0
    sequential = 1


class ZiweiBrightness(_ZiweiEnum):
    none = -1
    xian = 0
    bu = 1
    ping = 2
    li = 3
    de = 4
    wang = 5
    miao = 6


class ZiweiStarCategory(_ZiweiEnum):
    major = 0
    lucky = 1
    minor = 2
    malefic = 3
    cycle = 4
    other = 5


class ZiweiTransformMark(_ZiweiEnum):
    birthYearLu = 0
    birthYearQuan = 1
    birthYearKe = 2
    birthYearJi = 3
    centrifugalLu = 4
    centrifugalQuan = 5
    centrifugalKe = 6
    centrifugalJi = 7
    centripetalLu = 8
    centripetalQuan = 9
    centripetalKe = 10
    centripetalJi = 11


@dataclass(frozen=True)
class ZiweiOptionSelection:
    """Independent option choices for placement, brightness and Si-Hua tables.

    Unspecified fields select the profile's default, which is ``option1`` for
    the bundled catalog.  A selection never reparses TOML; it creates an
    immutable view of an existing :class:`ZiweiDataCatalog` snapshot.
    """

    placementDefault: str = ""
    brightnessDefault: str = ""
    sihuaDefault: str = ""
    masters: str = ""
    placement: Mapping[str, str] = field(default_factory=dict)
    brightness: Mapping[str, str] = field(default_factory=dict)
    sihua: Mapping[str, str] = field(default_factory=dict)

    def _native_value(self) -> dict:
        return {
            "placement_default": self.placementDefault,
            "brightness_default": self.brightnessDefault,
            "sihua_default": self.sihuaDefault,
            "masters": self.masters,
            "placement": dict(self.placement),
            "brightness": dict(self.brightness),
            "sihua": dict(self.sihua),
        }


@dataclass(frozen=True)
class ZiweiBirthOptions:
    ratHourMode: GanzhiRatHourMode = GanzhiRatHourMode.noSplit
    leapMonthStrategy: ZiweiLeapMonthStrategy = (
        ZiweiLeapMonthStrategy.splitAfterFifteenth
    )
    chartMode: ZiweiChartMode = ZiweiChartMode.tianPan
    wuHuDunYearBoundary: ZiweiPillarBoundary = ZiweiPillarBoundary.solarTerm
    sihuaYearBoundary: ZiweiPillarBoundary = ZiweiPillarBoundary.solarTerm
    bodyMasterYearBoundary: ZiweiPillarBoundary = ZiweiPillarBoundary.solarTerm


@dataclass(frozen=True)
class ZiweiFlowOptions:
    boundary: ZiweiPillarBoundary = ZiweiPillarBoundary.lunar
    ratHourMode: GanzhiRatHourMode = GanzhiRatHourMode.noSplit
    childhoodStrategy: ZiweiChildhoodStrategy = ZiweiChildhoodStrategy.skip


@dataclass(frozen=True)
class ZiweiStar:
    id: int
    key: str
    category: ZiweiStarCategory


@dataclass(frozen=True)
class ZiweiTransformSet:
    lu: int
    quan: int
    ke: int
    ji: int


@dataclass(frozen=True)
class ZiweiChartSummary:
    gender: ZiweiGender
    bureauId: int
    bodyPalaceBranch: int
    lifeMaster: int
    bodyMaster: int
    transforms: ZiweiTransformSet
    palaceStems: tuple[int, ...]


@dataclass(frozen=True)
class ZiweiDecadeLimit:
    index: int
    startAge: int
    endAge: int
    startYear: int
    endYear: int
    isChildhood: bool
    lifePalaceBranch: int


@dataclass(frozen=True)
class ZiweiSmallLimit:
    virtualAge: int
    stemId: int
    branchId: int


@dataclass(frozen=True)
class ZiweiFlowResolution:
    effectiveBirthYear: int
    effectiveTargetYear: int
    targetMonth: int
    targetMonthSequence: int
    targetDay: int
    targetHourIndex: int
    targetRatHourSegment: int
    targetMonthIsLeap: bool
    decade: ZiweiDecadeLimit
    smallLimit: ZiweiSmallLimit


def _transform(value: Mapping[str, int]) -> ZiweiTransformSet:
    return ZiweiTransformSet(value["lu"], value["quan"], value["ke"], value["ji"])


def _flow(value: Mapping[str, Any]) -> ZiweiFlowResolution:
    decade = value["decade"]
    small = value["small_limit"]
    return ZiweiFlowResolution(
        value["effective_birth_year"], value["effective_target_year"],
        value["target_month"], value["target_month_sequence"], value["target_day"],
        value["target_hour_index"], value["target_rat_hour_segment"],
        value["target_month_is_leap"],
        ZiweiDecadeLimit(
            decade["index"], decade["start_age"], decade["end_age"],
            decade["start_year"], decade["end_year"], decade["is_childhood"],
            decade["life_palace"],
        ),
        ZiweiSmallLimit(small["virtual_age"], small["stem"], small["branch"]),
    )


class ZiweiDataCatalog:
    """A reloadable TOML catalog shared by lightweight Ziwei contexts."""

    def __init__(self, profilePath: Optional[str | Path] = None):
        self.profilePath = Path(profilePath) if profilePath else _default_profile_path()
        self._native = _native.NativeZiweiDataCatalog(str(self.profilePath))

    @property
    def generation(self) -> int:
        return self._native.generation

    def reload(self) -> None:
        self._native.reload()


@lru_cache(maxsize=1)
def _default_catalog() -> ZiweiDataCatalog:
    return ZiweiDataCatalog()


def _default_profile_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "rules" / "default.toml"


class ZiweiChart:
    """A chart with branch-indexed natal palaces and an optional flow stack."""

    def __init__(self, context, native_chart):
        self._context = context
        self._native = native_chart

    def _ensure_open(self) -> None:
        self._context._ensure_open()

    @property
    def anchors(self) -> tuple[int, ...]:
        self._ensure_open()
        return tuple(self._native.anchors())

    @property
    def summary(self) -> ZiweiChartSummary:
        self._ensure_open()
        value = self._native.summary()
        return ZiweiChartSummary(
            ZiweiGender(value["gender"]), value["bureau"], value["body_palace"],
            value["life_master"], value["body_master"], _transform(value["transforms"]),
            tuple(value["palace_stems"]),
        )

    def star_position(self, star: int | ZiweiStar) -> Optional[int]:
        self._ensure_open()
        result = self._native.star_position(_star_id(star))
        return None if result < 0 else result

    def star_palace(self, star: int | ZiweiStar) -> Optional[int]:
        self._ensure_open()
        result = self._native.star_palace(_star_id(star))
        return None if result < 0 else result

    def brightness(self, star: int | ZiweiStar) -> ZiweiBrightness:
        self._ensure_open()
        return ZiweiBrightness(self._native.brightness(_star_id(star)))

    def palace_stars(self, branch_id: int) -> tuple[ZiweiStar, ...]:
        self._ensure_open()
        return tuple(self._context.star(item) for item in self._native.palace_stars(branch_id))

    def transform_mask(self, star: int | ZiweiStar) -> int:
        self._ensure_open()
        return self._native.transform_mask(_star_id(star))

    def has_transform(self, star: int | ZiweiStar, mark: ZiweiTransformMark) -> bool:
        self._ensure_open()
        if not isinstance(mark, ZiweiTransformMark):
            raise TypeError("mark must be ZiweiTransformMark")
        return self._native.has_transform(_star_id(star), mark.value)

    @property
    def flow_layer_count(self) -> int:
        self._ensure_open()
        return self._native.flow_layer_count

    def set_flow(
        self, instant_utc, virtual_time, *,
        options: ZiweiFlowOptions = ZiweiFlowOptions(),
        deepest_level: ZiweiFlowLevel = ZiweiFlowLevel.hour,
    ) -> ZiweiFlowResolution:
        self._ensure_open()
        if not isinstance(options, ZiweiFlowOptions):
            raise TypeError("options must be ZiweiFlowOptions")
        if not isinstance(deepest_level, ZiweiFlowLevel):
            raise TypeError("deepest_level must be ZiweiFlowLevel")
        facts = _calendar_facts(
            self._context.chinese_calendar, self._context._owner,
            instant_utc, virtual_time, options.ratHourMode,
        )
        return _flow(self._native.set_flow(
            facts, instant_utc, virtual_time, options.boundary.value,
            options.ratHourMode.value, options.childhoodStrategy.value,
            deepest_level.value,
        ))

    def truncate_flow(self, first_removed_level: ZiweiFlowLevel) -> None:
        self._ensure_open()
        if not isinstance(first_removed_level, ZiweiFlowLevel):
            raise TypeError("first_removed_level must be ZiweiFlowLevel")
        self._native.truncate_flow(first_removed_level.value)

    def flow_layer_summary(self, level: ZiweiFlowLevel) -> Mapping[str, Any]:
        self._ensure_open()
        if not isinstance(level, ZiweiFlowLevel):
            raise TypeError("level must be ZiweiFlowLevel")
        value = dict(self._native.flow_layer_summary(level.value))
        value["transforms"] = _transform(value["transforms"])
        return value

    def flow_star_position(self, level: ZiweiFlowLevel, star: int | ZiweiStar) -> Optional[int]:
        self._ensure_open()
        if not isinstance(level, ZiweiFlowLevel):
            raise TypeError("level must be ZiweiFlowLevel")
        result = self._native.flow_star_position(level.value, _star_id(star))
        return None if result < 0 else result

    def flow_palace_stars(self, level: ZiweiFlowLevel, branch_id: int) -> tuple[ZiweiStar, ...]:
        self._ensure_open()
        if not isinstance(level, ZiweiFlowLevel):
            raise TypeError("level must be ZiweiFlowLevel")
        return tuple(
            self._context.star(item)
            for item in self._native.flow_palace_stars(level.value, branch_id)
        )

class ZiweiContext:
    """Ziwei calculations that share one Taiyin Chinese-calendar context."""

    def __init__(self, calendar: ChineseCalendarContext, catalog=None, selection=None):
        if not isinstance(calendar, ChineseCalendarContext):
            raise TypeError("calendar must be taiyin.ChineseCalendarContext")
        if catalog is None:
            catalog = _default_catalog()
        if not isinstance(catalog, ZiweiDataCatalog):
            raise TypeError("catalog must be ZiweiDataCatalog")
        if selection is None:
            selection = ZiweiOptionSelection()
        if not isinstance(selection, ZiweiOptionSelection):
            raise TypeError("selection must be ZiweiOptionSelection")
        self._calendar = calendar
        self._owner = calendar._owner
        self._catalog = catalog
        self._native: Any = _native.NativeZiweiContext(
            catalog._native._core_context_capsule(), selection._native_value()
        )
        self._closed = False

    @property
    def chinese_calendar(self) -> ChineseCalendarContext:
        return self._calendar

    @property
    def generation(self) -> int:
        self._ensure_open()
        return self._native.generation

    @property
    def star_count(self) -> int:
        self._ensure_open()
        return self._native.star_count

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("ZiweiContext is closed")
        self._owner._ensure_open()
        self._calendar._ensure_open()

    def close(self) -> None:
        self._native = None
        self._closed = True

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, *args):
        self.close()
        return False

    def find_star(self, key: str) -> Optional[ZiweiStar]:
        self._ensure_open()
        if not isinstance(key, str):
            raise TypeError("key must be a string")
        star_id = self._native.find_star(key)
        return None if star_id < 0 else self.star(star_id)

    def star(self, star_id: int) -> ZiweiStar:
        self._ensure_open()
        value = self._native.star_metadata(star_id)
        return ZiweiStar(value["id"], value["key"], ZiweiStarCategory(value["category"]))

    def create_chart(
        self, instant_utc, virtual_time, *, gender: ZiweiGender,
        options: ZiweiBirthOptions = ZiweiBirthOptions(),
    ) -> ZiweiChart:
        self._ensure_open()
        if not isinstance(gender, ZiweiGender):
            raise TypeError("gender must be ZiweiGender")
        if not isinstance(options, ZiweiBirthOptions):
            raise TypeError("options must be ZiweiBirthOptions")
        facts = _calendar_facts(
            self._calendar, self._owner, instant_utc, virtual_time,
            options.ratHourMode,
        )
        native_chart = self._native.create_chart(
            facts, instant_utc, virtual_time, gender.value, options.ratHourMode.value,
            options.leapMonthStrategy.value, options.chartMode.value,
            options.wuHuDunYearBoundary.value, options.sihuaYearBoundary.value,
            options.bodyMasterYearBoundary.value,
        )
        return ZiweiChart(self, native_chart)

    def _calendar_offset_seconds(self) -> float:
        config = self._calendar.config
        if config.dayBoundaryMode.value == 0:
            return config.utcOffsetMinutes * 60.0
        return config.calendarMeridianDegrees * 240.0

    def calculate_local(self, local_time, *, gender: ZiweiGender,
                        options: ZiweiBirthOptions = ZiweiBirthOptions()) -> ZiweiChart:
        self._ensure_open()
        instant_utc = local_time.to_julian_date().add_seconds(-self._calendar_offset_seconds())
        return self.create_chart(instant_utc, local_time, gender=gender, options=options)

    def calculate_instant(self, instant_utc, *, gender: ZiweiGender,
                          options: ZiweiBirthOptions = ZiweiBirthOptions()) -> ZiweiChart:
        self._ensure_open()
        local_jd = instant_utc.add_seconds(self._calendar_offset_seconds())
        local_time = self._owner.time.reverse_julian_day(local_jd)
        return self.create_chart(instant_utc, local_time, gender=gender, options=options)


def _star_id(value: int | ZiweiStar) -> int:
    if isinstance(value, ZiweiStar):
        return value.id
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise TypeError("star must be a ZiweiStar or integer StarId")


def _logical_civil_day(jd, clock, rat_hour_mode: GanzhiRatHourMode) -> int:
    """Use the exact same local-day labelling as the C++ Ziwei adapter."""
    day_number = jd.day_number
    fraction = jd.day_fraction
    if rat_hour_mode is GanzhiRatHourMode.noSplit and clock.hour >= 23:
        fraction += 1.0 / 24.0
    return day_number + math.floor(fraction + 0.5)


def _calendar_facts(calendar, owner, instant_utc, virtual_time, rat_hour_mode):
    """Resolve astronomical calendar facts in the base extension.

    The Ziwei native module intentionally does not link the astronomy runtime.
    This keeps one process-global ephemeris catalog and makes the caller's
    historical/local calendar policy authoritative.
    """
    lunar = calendar.from_instant_ut(instant_utc)
    pillars = calendar.four_pillars(
        instant_utc, virtual_time, rat_hour_mode=rat_hour_mode
    )
    previous_jie = calendar.get_prev_jie_ut(instant_utc)
    virtual_jd = virtual_time.to_julian_date()
    clock_offset_seconds = virtual_jd.seconds_difference(instant_utc)
    jie_virtual = previous_jie.jdUt.add_seconds(clock_offset_seconds)
    jie_clock = owner.time.reverse_julian_day(jie_virtual)
    solar_day = (
        _logical_civil_day(virtual_jd, virtual_time, rat_hour_mode)
        - _logical_civil_day(jie_virtual, jie_clock, rat_hour_mode)
        + 1
    )
    if not 1 <= solar_day <= 65535:
        raise RuntimeError("Ziwei solar day from previous Jie is outside its supported range")
    first_solar = calendar.from_lunar(
        type(lunar)(lunar.year, lunar.month, 1, lunar.isLeap, 0, lunar.monthName)
    )
    first_day = taiyin_day_number(
        type(virtual_time)(first_solar.year, first_solar.month, first_solar.day, 12)
    )
    month_starts = set()
    for offset_days in (-220, 0, 220):
        year = calendar.calc_year_ut(instant_utc.add_seconds(offset_days * 86400))
        for month in year.months:
            if month.lunarYear == lunar.year:
                month_starts.add(month.firstCivilDayNumber)
    ordered_starts = sorted(month_starts)
    try:
        lunar_month_sequence = ordered_starts.index(first_day) + 1
    except ValueError as error:
        raise RuntimeError("Ziwei could not resolve the lunar month sequence") from error
    return {
        "lunar_year": lunar.year,
        "lunar_month": lunar.month,
        "lunar_day": lunar.day,
        "lunar_is_leap": lunar.isLeap,
        "lunar_month_name": lunar.monthName.value,
        "solar_pillars": [
            pillars.year.raw, pillars.month.raw, pillars.day.raw, pillars.hour.raw,
        ],
        "solar_day_from_previous_jie": solar_day,
        "lunar_month_sequence": lunar_month_sequence,
    }


def taiyin_day_number(clock) -> int:
    jd = clock.to_julian_date()
    return jd.day_number + math.floor(jd.day_fraction + 0.5)


def _ziwei_from_context(owner, catalog=None, selection=None):
    """Create the optional Ziwei facade from an owning calculation context."""
    from taiyin import EphemerisContext

    if not isinstance(owner, EphemerisContext):
        raise TypeError("owner must be taiyin.EphemerisContext")
    return ZiweiContext(owner.chinese_calendar, catalog, selection)


__all__ = [
    "ZiweiBirthOptions", "ZiweiBrightness", "ZiweiChart", "ZiweiChartMode",
    "ZiweiChartSummary", "ZiweiChildhoodStrategy", "ZiweiContext",
    "ZiweiDataCatalog", "ZiweiDecadeLimit", "ZiweiFlowLevel",
    "ZiweiFlowOptions", "ZiweiFlowResolution", "ZiweiGender",
    "ZiweiLeapMonthStrategy", "ZiweiOptionSelection", "ZiweiPillarBoundary",
    "ZiweiSmallLimit", "ZiweiStar", "ZiweiStarCategory", "ZiweiTransformMark",
    "ZiweiTransformSet",
]
