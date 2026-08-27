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

from taiyin import ChineseCalendarContext, GanzhiRatHourMode, ResultFlag
from . import _ziwei_native as _native  # pyright: ignore[reportAttributeAccessIssue]


class _ZiweiEnum(Enum):
    @property
    def id(self):
        return self.value


class ZiweiGender(_ZiweiEnum):
    male = 0
    female = 1


class ZiweiBureau(_ZiweiEnum):
    water2 = 0
    wood3 = 1
    metal4 = 2
    earth5 = 3
    fire6 = 4


class ZiweiPalace(_ZiweiEnum):
    life = 0
    siblings = 1
    spouse = 2
    children = 3
    wealth = 4
    health = 5
    travel = 6
    friends = 7
    career = 8
    property = 9
    fortune = 10
    parents = 11


class ZiweiAnchorSlot(_ZiweiEnum):
    solarYearStem = 0
    solarYearBranch = 1
    solarMonthStem = 2
    solarMonthBranch = 3
    solarDayStem = 4
    solarDayBranch = 5
    solarHourStem = 6
    solarHourBranch = 7
    lunarYearStem = 8
    lunarYearBranch = 9
    lunarMonthStem = 10
    lunarMonthBranch = 11
    lunarDayStem = 12
    lunarDayBranch = 13
    lunarHourStem = 14
    lunarHourBranch = 15
    bureau = 16
    ziwei = 17
    tianfu = 18
    palaceLife = 19
    palaceSiblings = 20
    palaceSpouse = 21
    palaceChildren = 22
    palaceWealth = 23
    palaceHealth = 24
    palaceTravel = 25
    palaceFriends = 26
    palaceCareer = 27
    palaceProperty = 28
    palaceFortune = 29
    palaceParents = 30


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


class ZiweiFlowMonthPalaceStrategy(_ZiweiEnum):
    """How a leap segment advances the Liu-Nian Dou-Jun month palace."""

    physicalSequence = 0
    effectiveMonth = 1


class ZiweiRatHourSegment(_ZiweiEnum):
    """Which Zi segment a logical flow-hour target belongs to."""

    none = 0
    unified = 1
    early = 2
    late = 3


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
    """Independent choices for placement, brightness, Si-Hua, and life-stage tables.

    Unspecified fields select the profile's default, which is ``option1`` for
    the bundled catalog.  A selection never reparses TOML; it creates an
    immutable view of an existing :class:`ZiweiDataCatalog` snapshot.

    ``longevity`` selects all twelve life-stage stars together.  It cannot be
    expressed through the per-star ``placement`` mapping: use ``option1`` for
    the bundled water/earth convention or ``option2`` for fire/earth.
    """

    placementDefault: str = ""
    brightnessDefault: str = ""
    sihuaDefault: str = ""
    masters: str = ""
    longevity: str = ""
    placement: Mapping[str, str] = field(default_factory=dict)
    brightness: Mapping[str, str] = field(default_factory=dict)
    sihua: Mapping[str, str] = field(default_factory=dict)

    def _native_value(self) -> dict:
        return {
            "placement_default": self.placementDefault,
            "brightness_default": self.brightnessDefault,
            "sihua_default": self.sihuaDefault,
            "masters": self.masters,
            "longevity": self.longevity,
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
    wuHuDunYearBoundary: ZiweiPillarBoundary = ZiweiPillarBoundary.lunar
    sihuaYearBoundary: ZiweiPillarBoundary = ZiweiPillarBoundary.lunar
    bodyMasterYearBoundary: ZiweiPillarBoundary = ZiweiPillarBoundary.lunar


@dataclass(frozen=True)
class ZiweiFlowOptions:
    boundary: ZiweiPillarBoundary = ZiweiPillarBoundary.lunar
    ratHourMode: GanzhiRatHourMode = GanzhiRatHourMode.noSplit
    childhoodStrategy: ZiweiChildhoodStrategy = ZiweiChildhoodStrategy.skip
    flowMonthPalaceStrategy: ZiweiFlowMonthPalaceStrategy = (
        ZiweiFlowMonthPalaceStrategy.physicalSequence
    )


@dataclass(frozen=True)
class ZiweiTier1ReverseQuery:
    """Optional physical-palace filters for finite birth-time reverse lookup.

    Each supplied value is a branch ID from 0 (Zi) through 11 (Hai).  At
    least one field must be supplied.  Results are logical birth-time slots,
    not minute-precise reconstructions.
    """

    lucunBranch: Optional[int] = None
    hongluanBranch: Optional[int] = None
    zuofuBranch: Optional[int] = None
    youbiBranch: Optional[int] = None
    wenchangBranch: Optional[int] = None
    wenquBranch: Optional[int] = None
    santaiBranch: Optional[int] = None
    bazuoBranch: Optional[int] = None
    ziweiBranch: Optional[int] = None


@dataclass(frozen=True)
class ZiweiReverseLookupCandidate:
    instantUtc: Any
    virtualTime: Any
    lunarDate: Any
    hourBranch: int
    ratHourSegment: ZiweiRatHourSegment


@dataclass(frozen=True)
class ZiweiFlowHourTarget:
    instantUtc: Any
    virtualTime: Any
    ratHourSegment: ZiweiRatHourSegment


@dataclass(frozen=True)
class ZiweiFlowDayTarget:
    instantUtc: Any
    virtualTime: Any


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
    bureau: ZiweiBureau
    bodyPalaceBranch: int
    lifeMaster: int
    bodyMaster: int
    transforms: ZiweiTransformSet
    palaceStems: tuple[int, ...]

    @property
    def bureauId(self) -> int:
        """Stable numeric bureau ID retained for compact serialization."""
        return self.bureau.value


@dataclass(frozen=True)
class ZiweiAnchors:
    """The 31 stable natal anchors, addressable by :class:`ZiweiAnchorSlot`."""

    values: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.values) != len(ZiweiAnchorSlot):
            raise ValueError("Ziwei anchors must contain exactly 31 values")

    def __len__(self) -> int:
        return len(self.values)

    def __iter__(self):
        return iter(self.values)

    def __getitem__(self, slot: int | ZiweiAnchorSlot) -> int:
        if isinstance(slot, ZiweiAnchorSlot):
            return self.values[slot.value]
        return self.values[slot]

    def get(self, slot: ZiweiAnchorSlot) -> int:
        if not isinstance(slot, ZiweiAnchorSlot):
            raise TypeError("slot must be ZiweiAnchorSlot")
        return self.values[slot.value]

    @property
    def bureau(self) -> ZiweiBureau:
        return ZiweiBureau(self.get(ZiweiAnchorSlot.bureau))

    @property
    def ziwei(self) -> int:
        return self.get(ZiweiAnchorSlot.ziwei)

    @property
    def tianfu(self) -> int:
        return self.get(ZiweiAnchorSlot.tianfu)

    def palace_position(self, palace: ZiweiPalace) -> int:
        if not isinstance(palace, ZiweiPalace):
            raise TypeError("palace must be ZiweiPalace")
        return self.values[ZiweiAnchorSlot.palaceLife.value + palace.value]


@dataclass(frozen=True)
class ZiweiPalaceState:
    palace: ZiweiPalace
    branchId: int
    stemId: int
    stars: tuple[ZiweiStar, ...]


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
    targetEffectiveMonth: int
    targetMonthSequence: int
    targetMonthName: int
    targetPalaceMonthIndex: int
    targetMonthBuildingBranch: int
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
        value["target_month"], value["target_effective_month"],
        value["target_month_sequence"], value["target_month_name"],
        value["target_palace_month_index"],
        value["target_month_building_branch"], value["target_day"],
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
    def anchors(self) -> ZiweiAnchors:
        self._ensure_open()
        return ZiweiAnchors(tuple(self._native.anchors()))

    @property
    def summary(self) -> ZiweiChartSummary:
        self._ensure_open()
        value = self._native.summary()
        return ZiweiChartSummary(
            ZiweiGender(value["gender"]), ZiweiBureau(value["bureau"]), value["body_palace"],
            value["life_master"], value["body_master"], _transform(value["transforms"]),
            tuple(value["palace_stems"]),
        )

    @property
    def palaces(self) -> tuple[ZiweiPalaceState, ...]:
        """The twelve natal palaces in semantic (Life through Parents) order."""
        self._ensure_open()
        anchors = self.anchors
        stems = self.summary.palaceStems
        return tuple(
            ZiweiPalaceState(
                palace, anchors.palace_position(palace),
                stems[anchors.palace_position(palace)],
                self.palace_stars(anchors.palace_position(palace)),
            )
            for palace in ZiweiPalace
        )

    def palace(self, palace: ZiweiPalace) -> ZiweiPalaceState:
        """Return one named natal palace with its physical branch and stars."""
        if not isinstance(palace, ZiweiPalace):
            raise TypeError("palace must be ZiweiPalace")
        return self.palaces[palace.value]

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
    ) -> tuple[ZiweiFlowResolution, ResultFlag]:
        self._ensure_open()
        if not isinstance(options, ZiweiFlowOptions):
            raise TypeError("options must be ZiweiFlowOptions")
        if not isinstance(deepest_level, ZiweiFlowLevel):
            raise TypeError("deepest_level must be ZiweiFlowLevel")
        facts, result_flags = _calendar_facts(
            self._context.chinese_calendar, self._context._owner,
            instant_utc, virtual_time, options.ratHourMode,
        )
        return (
            _flow(self._native.set_flow(
                facts, instant_utc, virtual_time, options.boundary.value,
                options.ratHourMode.value, options.childhoodStrategy.value,
                options.flowMonthPalaceStrategy.value,
                deepest_level.value,
            )),
            result_flags,
        )

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
    ) -> tuple[ZiweiChart, ResultFlag]:
        self._ensure_open()
        if not isinstance(gender, ZiweiGender):
            raise TypeError("gender must be ZiweiGender")
        if not isinstance(options, ZiweiBirthOptions):
            raise TypeError("options must be ZiweiBirthOptions")
        facts, result_flags = _calendar_facts(
            self._calendar, self._owner, instant_utc, virtual_time,
            options.ratHourMode,
        )
        native_chart = self._native.create_chart(
            facts, instant_utc, virtual_time, gender.value, options.ratHourMode.value,
            options.leapMonthStrategy.value, options.chartMode.value,
            options.wuHuDunYearBoundary.value, options.sihuaYearBoundary.value,
            options.bodyMasterYearBoundary.value,
        )
        return ZiweiChart(self, native_chart), result_flags

    def _civil_clock_offset_seconds(self) -> float:
        """Return the clock offset, independent of the calendar day boundary."""
        return self._calendar.config.utcOffsetMinutes * 60.0

    def calculate_local(
        self,
        local_time,
        *,
        gender: ZiweiGender,
        options: ZiweiBirthOptions = ZiweiBirthOptions(),
    ) -> tuple[ZiweiChart, ResultFlag]:
        self._ensure_open()
        instant_utc = local_time.to_julian_date().add_seconds(
            -self._civil_clock_offset_seconds()
        )
        return self.create_chart(instant_utc, local_time, gender=gender, options=options)

    def calculate_instant(
        self,
        instant_utc,
        *,
        gender: ZiweiGender,
        options: ZiweiBirthOptions = ZiweiBirthOptions(),
    ) -> tuple[ZiweiChart, ResultFlag]:
        self._ensure_open()
        local_jd = instant_utc.add_seconds(self._civil_clock_offset_seconds())
        local_time, time_flags = self._owner.time.reverse_julian_day(local_jd)
        chart, chart_flags = self.create_chart(
            instant_utc, local_time, gender=gender, options=options
        )
        return chart, chart_flags | time_flags

    def step_flow_hour_target(
        self, instant_utc, virtual_time, *,
        rat_hour_mode: GanzhiRatHourMode = GanzhiRatHourMode.noSplit,
        direction: int = 1,
    ) -> ZiweiFlowHourTarget:
        """Move to the canonical center of the adjacent logical flow hour.

        In split-Rat modes this walks ``Early Zi -> Chou -> ... -> Late Zi
        -> Early Zi`` as thirteen slots.  The returned UTC instant and local
        clock continue to describe the same event.
        """
        self._ensure_open()
        _require_rat_hour_mode(rat_hour_mode)
        _require_step_direction(direction)
        return _step_flow_hour_target(
            self._owner, instant_utc, virtual_time, rat_hour_mode, direction
        )

    def next_flow_hour_target(
        self, instant_utc, virtual_time, *,
        rat_hour_mode: GanzhiRatHourMode = GanzhiRatHourMode.noSplit,
    ) -> ZiweiFlowHourTarget:
        return self.step_flow_hour_target(
            instant_utc, virtual_time, rat_hour_mode=rat_hour_mode, direction=1
        )

    def previous_flow_hour_target(
        self, instant_utc, virtual_time, *,
        rat_hour_mode: GanzhiRatHourMode = GanzhiRatHourMode.noSplit,
    ) -> ZiweiFlowHourTarget:
        return self.step_flow_hour_target(
            instant_utc, virtual_time, rat_hour_mode=rat_hour_mode, direction=-1
        )

    def step_flow_day_target(
        self, instant_utc, virtual_time, *, direction: int = 1,
    ) -> ZiweiFlowDayTarget:
        """Move one local civil flow day, retaining exact wall-clock fields."""
        self._ensure_open()
        _require_step_direction(direction)
        next_clock = _shift_local_civil_day(self._owner, virtual_time, direction)
        return ZiweiFlowDayTarget(
            instant_utc.add_seconds(direction * 86400.0), next_clock
        )

    def next_flow_day_target(self, instant_utc, virtual_time) -> ZiweiFlowDayTarget:
        return self.step_flow_day_target(instant_utc, virtual_time, direction=1)

    def previous_flow_day_target(self, instant_utc, virtual_time) -> ZiweiFlowDayTarget:
        return self.step_flow_day_target(instant_utc, virtual_time, direction=-1)

    def reverse_lookup_tier1(
        self, start_instant_utc, end_instant_utc, start_virtual_time, *,
        gender: ZiweiGender, query: ZiweiTier1ReverseQuery,
        options: ZiweiBirthOptions = ZiweiBirthOptions(),
    ) -> tuple[tuple[ZiweiReverseLookupCandidate, ...], ResultFlag]:
        """Find logical birth-time slots whose selected Tier-1 stars match.

        The search uses this context's existing Chinese-calendar policy and
        data routes.  ``start_virtual_time`` must describe the same event as
        ``start_instant_utc``; it is then advanced as canonical logical hours.
        """
        self._ensure_open()
        if not isinstance(gender, ZiweiGender):
            raise TypeError("gender must be ZiweiGender")
        if not isinstance(query, ZiweiTier1ReverseQuery):
            raise TypeError("query must be ZiweiTier1ReverseQuery")
        if not isinstance(options, ZiweiBirthOptions):
            raise TypeError("options must be ZiweiBirthOptions")
        _validate_reverse_query(query)
        if end_instant_utc.seconds_difference(start_instant_utc) < 0.0:
            raise ValueError("end_instant_utc must not be before start_instant_utc")

        star_filters = _reverse_star_filters(self, query)
        instant = start_instant_utc
        virtual_time = start_virtual_time
        result = []
        result_flags = ResultFlag.none
        while end_instant_utc.seconds_difference(instant) >= 0.0:
            chart, chart_flags = self.create_chart(
                instant, virtual_time, gender=gender, options=options
            )
            result_flags |= chart_flags
            if all(chart.star_position(star) == branch
                   for star, branch in star_filters):
                lunar, lunar_flags = self._calendar.from_instant_ut(instant)
                pillars, pillar_flags = self._calendar.four_pillars(
                    instant, virtual_time, rat_hour_mode=options.ratHourMode
                )
                result_flags |= lunar_flags | pillar_flags
                hour_branch = pillars.hour.branch.value
                result.append(ZiweiReverseLookupCandidate(
                    instant, virtual_time, lunar, hour_branch,
                    _rat_hour_segment(virtual_time, options.ratHourMode, hour_branch),
                ))
            next_target = self.step_flow_hour_target(
                instant, virtual_time, rat_hour_mode=options.ratHourMode
            )
            if next_target.instantUtc.seconds_difference(instant) <= 0.0:
                raise RuntimeError("Ziwei reverse lookup did not advance")
            instant = next_target.instantUtc
            virtual_time = next_target.virtualTime
        return tuple(result), result_flags


def _star_id(value: int | ZiweiStar) -> int:
    if isinstance(value, ZiweiStar):
        return value.id
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise TypeError("star must be a ZiweiStar or integer StarId")


def _require_step_direction(direction: int) -> None:
    if isinstance(direction, bool) or direction not in (-1, 1):
        raise ValueError("direction must be -1 or 1")


def _require_rat_hour_mode(rat_hour_mode: GanzhiRatHourMode) -> None:
    if not isinstance(rat_hour_mode, GanzhiRatHourMode):
        raise TypeError("rat_hour_mode must be GanzhiRatHourMode")


def _clock_with_fields(clock, *, hour: Optional[int] = None,
                       minute: Optional[int] = None,
                       second: Optional[float] = None):
    """Rebuild a public AstroDateTime without relying on native internals."""
    return type(clock)(
        clock.year, clock.month, clock.day,
        clock.hour if hour is None else hour,
        clock.minute if minute is None else minute,
        clock.second if second is None else second,
    )


def _shift_local_civil_day(owner, clock, direction: int):
    """Mirror C++ ``shift_target_by_local_days`` exactly at public API level."""
    shifted, _ = owner.time.reverse_julian_day(
        clock.to_julian_date().add_seconds(direction * 86400.0)
    )
    return _clock_with_fields(
        shifted, hour=clock.hour, minute=clock.minute, second=clock.second
    )


def _rat_hour_segment(clock, rat_hour_mode: GanzhiRatHourMode,
                      hour_branch: int) -> ZiweiRatHourSegment:
    if hour_branch != 0:
        return ZiweiRatHourSegment.none
    if rat_hour_mode is GanzhiRatHourMode.noSplit:
        return ZiweiRatHourSegment.unified
    return (ZiweiRatHourSegment.late if clock.hour >= 23
            else ZiweiRatHourSegment.early)


def _step_flow_hour_target(owner, instant_utc, virtual_time,
                           rat_hour_mode: GanzhiRatHourMode,
                           direction: int) -> ZiweiFlowHourTarget:
    """Public-type transcription of C++ ``step_flow_hour_target``.

    The native Ziwei wheel purposely excludes the astronomy/calendar runtime,
    so this tiny conversion stays in Python.  Its slot arithmetic and clock
    pairing are kept line-for-line equivalent to the C++ helper.
    """
    split_rat = rat_hour_mode is not GanzhiRatHourMode.noSplit
    slot_count = 13 if split_rat else 12
    logical_day_shift = 0
    if split_rat:
        slot = 12 if virtual_time.hour >= 23 else ((virtual_time.hour + 1) // 2) % 12
    else:
        slot = ((virtual_time.hour + 1) // 2) % 12
        if virtual_time.hour >= 23:
            logical_day_shift = 1

    next_slot = slot + direction
    if next_slot < 0:
        next_slot += slot_count
        logical_day_shift -= 1
    elif next_slot >= slot_count:
        next_slot -= slot_count
        logical_day_shift += 1

    day_start = _clock_with_fields(virtual_time, hour=0, minute=0, second=0.0)
    target_day = _shift_local_civil_day(owner, day_start, logical_day_shift)
    center = (0.5 if next_slot == 0 else 23.5 if split_rat and next_slot == 12
              else next_slot * 2.0)
    hour = int(center)
    minute = 30 if center - hour >= 0.5 else 0
    target_clock = _clock_with_fields(target_day, hour=hour, minute=minute, second=0.0)
    delta_seconds = target_clock.to_julian_date().seconds_difference(
        virtual_time.to_julian_date()
    )
    segment = (ZiweiRatHourSegment.early if split_rat and next_slot == 0
               else ZiweiRatHourSegment.late if split_rat and next_slot == 12
               else ZiweiRatHourSegment.unified if not split_rat and next_slot == 0
               else ZiweiRatHourSegment.none)
    return ZiweiFlowHourTarget(
        instant_utc.add_seconds(delta_seconds), target_clock, segment
    )


_REVERSE_FIELD_STARS = (
    ("lucunBranch", "lucun"),
    ("hongluanBranch", "hongluan"),
    ("zuofuBranch", "zuofu"),
    ("youbiBranch", "youbi"),
    ("wenchangBranch", "wenchang"),
    ("wenquBranch", "wenqu"),
    ("santaiBranch", "santai"),
    ("bazuoBranch", "bazuo"),
    ("ziweiBranch", "ziwei"),
)


def _validate_reverse_query(query: ZiweiTier1ReverseQuery) -> None:
    values = [getattr(query, field_name) for field_name, _ in _REVERSE_FIELD_STARS]
    if not any(value is not None for value in values):
        raise ValueError("Ziwei Tier-1 reverse lookup requires at least one constraint")
    for value in values:
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 12:
            raise ValueError("Ziwei Tier-1 branch constraints must be integers from 0 through 11")


def _reverse_star_filters(context: ZiweiContext,
                          query: ZiweiTier1ReverseQuery) -> tuple[tuple[ZiweiStar, int], ...]:
    result = []
    for field_name, key in _REVERSE_FIELD_STARS:
        branch = getattr(query, field_name)
        if branch is None:
            continue
        star = context.find_star(key)
        if star is None:
            raise RuntimeError("Ziwei default catalog is missing Tier-1 star: " + key)
        result.append((star, branch))
    return tuple(result)


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
    lunar, result_flags = calendar.from_instant_ut(instant_utc)
    pillars, pillar_flags = calendar.four_pillars(
        instant_utc, virtual_time, rat_hour_mode=rat_hour_mode
    )
    result_flags |= pillar_flags
    previous_jie, jie_flags = calendar.get_prev_jie_ut(instant_utc)
    result_flags |= jie_flags
    virtual_jd = virtual_time.to_julian_date()
    clock_offset_seconds = virtual_jd.seconds_difference(instant_utc)
    jie_virtual = previous_jie.jdUt.add_seconds(clock_offset_seconds)
    jie_clock, time_flags = owner.time.reverse_julian_day(jie_virtual)
    result_flags |= time_flags
    solar_day = (
        _logical_civil_day(virtual_jd, virtual_time, rat_hour_mode)
        - _logical_civil_day(jie_virtual, jie_clock, rat_hour_mode)
        + 1
    )
    if not 1 <= solar_day <= 65535:
        raise RuntimeError("Ziwei solar day from previous Jie is outside its supported range")
    first_solar, first_solar_flags = calendar.from_lunar(
        type(lunar)(lunar.year, lunar.month, 1, lunar.isLeap, 0, lunar.monthName)
    )
    result_flags |= first_solar_flags
    first_day = taiyin_day_number(
        type(virtual_time)(first_solar.year, first_solar.month, first_solar.day, 12)
    )
    target_identity = (
        lunar.year, lunar.month, lunar.isLeap, lunar.monthName,
    )
    months_by_first_day = {}
    # The target calcY() window is authoritative if overlapping windows use
    # competing historical labels for the same physical lunation.
    for offset_days in (0, -220, 220):
        year, year_flags = calendar.calc_year_ut(
            instant_utc.add_seconds(offset_days * 86400)
        )
        result_flags |= year_flags
        for month in year.months:
            identity = (
                month.lunarYear, month.month, month.isLeap, month.monthName,
            )
            existing = months_by_first_day.get(month.firstCivilDayNumber)
            if existing is None or (
                identity == target_identity
                and (
                    existing.lunarYear,
                    existing.month,
                    existing.isLeap,
                    existing.monthName,
                ) != target_identity
            ):
                months_by_first_day[month.firstCivilDayNumber] = month
    ordered_starts = sorted(months_by_first_day)
    try:
        target_index = ordered_starts.index(first_day)
    except ValueError as error:
        raise RuntimeError("Ziwei could not resolve the lunar month sequence") from error
    target_month = months_by_first_day[first_day]
    if (
        target_month.lunarYear,
        target_month.month,
        target_month.isLeap,
        target_month.monthName,
    ) != target_identity:
        raise RuntimeError("Ziwei calendar windows disagree about the target lunar month")
    lunar_month_sequence = 1 + sum(
        months_by_first_day[day].lunarYear == lunar.year
        for day in ordered_starts[:target_index]
    )
    if not 0 <= target_month.monthBuildingBranch <= 11:
        raise RuntimeError("Ziwei calendar produced an invalid month-building branch")
    return (
        {
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
            "lunar_month_building_branch": target_month.monthBuildingBranch,
        },
        result_flags,
    )


def taiyin_day_number(clock) -> int:
    jd = clock.to_julian_date()
    return jd.day_number + math.floor(jd.day_fraction + 0.5)


def _ziwei_from_context(owner, catalog=None, selection=None, *, calendar=None):
    """Create the optional Ziwei facade from an owning calculation context."""
    from taiyin import ChineseCalendarContext, EphemerisContext

    if not isinstance(owner, EphemerisContext):
        raise TypeError("owner must be taiyin.EphemerisContext")
    if calendar is None:
        calendar = owner.chinese_calendar
    if not isinstance(calendar, ChineseCalendarContext):
        raise TypeError("calendar must be taiyin.ChineseCalendarContext")
    if calendar._owner is not owner:
        raise ValueError("calendar must belong to this EphemerisContext")
    calendar._ensure_open()
    return ZiweiContext(calendar, catalog, selection)


__all__ = [
    "ZiweiAnchorSlot", "ZiweiAnchors", "ZiweiBirthOptions", "ZiweiBrightness",
    "ZiweiBureau", "ZiweiChart", "ZiweiChartMode", "ZiweiChartSummary",
    "ZiweiChildhoodStrategy", "ZiweiContext",
    "ZiweiDataCatalog", "ZiweiDecadeLimit", "ZiweiFlowLevel",
    "ZiweiFlowMonthPalaceStrategy",
    "ZiweiFlowDayTarget", "ZiweiFlowHourTarget", "ZiweiFlowOptions",
    "ZiweiFlowResolution", "ZiweiGender",
    "ZiweiLeapMonthStrategy", "ZiweiOptionSelection", "ZiweiPillarBoundary",
    "ZiweiPalace", "ZiweiPalaceState", "ZiweiRatHourSegment",
    "ZiweiReverseLookupCandidate", "ZiweiSmallLimit", "ZiweiStar",
    "ZiweiStarCategory", "ZiweiTier1ReverseQuery",
    "ZiweiTransformMark", "ZiweiTransformSet",
]
