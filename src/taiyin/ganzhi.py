"""Ganzhi (干支) calendar rules in the base :mod:`taiyin` package."""

from dataclasses import dataclass
from enum import Enum

from . import _native


class GanzhiRatHourMode(Enum):
    noSplit = 0
    todayGan = 1
    tomorrowGan = 2


class GanzhiWuxing(Enum):
    water = 0
    wood = 1
    metal = 2
    earth = 3
    fire = 4


class HeavenlyStem(Enum):
    jia = 0
    yi = 1
    bing = 2
    ding = 3
    wu = 4
    ji = 5
    geng = 6
    xin = 7
    ren = 8
    gui = 9


class EarthlyBranch(Enum):
    zi = 0
    chou = 1
    yin = 2
    mao = 3
    chen = 4
    si = 5
    wu = 6
    wei = 7
    shen = 8
    you = 9
    xu = 10
    hai = 11


@dataclass(frozen=True)
class Ganzhi:
    stem_id: int
    branch_id: int

    def __post_init__(self) -> None:
        if not 0 <= self.stem_id <= 9 or not 0 <= self.branch_id <= 11:
            raise ValueError("Ganzhi stem must be 0..9 and branch must be 0..11")
        if self.stem_id % 2 != self.branch_id % 2:
            raise ValueError("Ganzhi stem and branch must have the same yin/yang parity")

    @classmethod
    def from_native(cls, raw: int):
        if raw == 0xFF:
            raise ValueError("0xff is not a valid packed Ganzhi")
        return cls(raw >> 4, raw & 0x0F)

    @property
    def stem(self) -> HeavenlyStem:
        return HeavenlyStem(self.stem_id)

    @property
    def branch(self) -> EarthlyBranch:
        return EarthlyBranch(self.branch_id)

    @property
    def raw(self) -> int:
        return (self.stem_id << 4) | self.branch_id


@dataclass(frozen=True)
class GanzhiFourPillars:
    year: Ganzhi
    month: Ganzhi
    day: Ganzhi
    hour: Ganzhi


class GanzhiApi:
    """Pure Ganzhi calendar rules, available from ``context.ganzhi``."""

    def __init__(self, context):
        self._context = context

    def _native_value(self, function, *args) -> Ganzhi:
        self._context._ensure_open()
        return Ganzhi.from_native(function(*args))

    def make(self, stem_id: int, branch_id: int) -> Ganzhi:
        return self._native_value(_native._ganzhi_make, stem_id, branch_id)

    def advance(self, value: Ganzhi, delta: int) -> Ganzhi:
        return self._native_value(_native._ganzhi_advance, value.raw, delta)

    def month_pillar(self, year_stem_id: int, month_index: int) -> Ganzhi:
        return self._native_value(_native._ganzhi_month_pillar, year_stem_id, month_index)

    def hour_pillar(self, day_stem_id: int, hour_index: int) -> Ganzhi:
        return self._native_value(_native._ganzhi_hour_pillar, day_stem_id, hour_index)

    def day_pillar(self, civil_date) -> Ganzhi:
        return self._native_value(_native._ganzhi_day_pillar, civil_date)

    def nayin_element(self, value: Ganzhi) -> GanzhiWuxing:
        self._context._ensure_open()
        return GanzhiWuxing(_native._ganzhi_nayin_element(value.raw))

    def nayin_id(self, value: Ganzhi) -> int:
        self._context._ensure_open()
        return _native._ganzhi_nayin_id(value.raw)
