"""Optional BaZi bindings created through :class:`taiyin.Ephemeris`."""

from dataclasses import dataclass, field
from enum import Enum

from taiyin import (
    EarthlyBranch,
    EphemerisResult,
    Ganzhi,
    GanzhiFourPillars,
    GanzhiWuxing,
)
from taiyin.position import _diagnostic

from . import _bazi_native as _native


class _BaziEnum(Enum):
    @property
    def id(self):
        return self.value

    @property
    def mask(self):
        return self.value


class BaziEarthPalaceMode(_BaziEnum):
    fireEarth = 0
    waterEarth = 1


class BaziGender(_BaziEnum):
    female = 0
    male = 1


class BaziQiyunDirectionMode(_BaziEnum):
    yearStemGender = 0


class BaziQiyunTimeModel(_BaziEnum):
    traditionalCalendar = 0
    julianYear = 1
    tropicalYear = 2


class BaziDayunBoundaryModel(_BaziEnum):
    civilYears = 0
    julianYears = 1
    tropicalYears = 2


class BaziRenyuanSilingTableModel(_BaziEnum):
    sanMingTongHui = 0
    common = 1


class BaziRenyuanSilingTimeModel(_BaziEnum):
    elapsed24Hours = 0
    localCivilDays = 1


class BaziRenyuanSilingOriginKind(_BaziEnum):
    stem = 0
    genEarth = 1
    kunEarth = 2


class BaziTenGod(_BaziEnum):
    biJian = 0
    jieCai = 1
    shiShen = 2
    shangGuan = 3
    pianCai = 4
    zhengCai = 5
    qiSha = 6
    zhengGuan = 7
    pianYin = 8
    zhengYin = 9


class BaziStemRelationFlags(_BaziEnum):
    combination = 1
    clash = 2
    restraint = 4


class BaziBranchRelationFlags(_BaziEnum):
    combination = 1
    clash = 2
    harm = 4
    destruction = 8
    punishment = 16
    selfPunishment = 32
    hiddenCombination = 64
    severance = 128


class BaziBranchTripleRelationFlags(_BaziEnum):
    combination = 1
    direction = 2
    punishment = 4


class BaziShenShaTargetKind(_BaziEnum):
    year = 0
    month = 1
    day = 2
    hour = 3
    mingGong = 4
    shenGong = 5
    taiYuan = 6
    taiXi = 7
    daYun = 8
    flowYear = 9
    flowMonth = 10
    flowDay = 11
    flowHour = 12


class BaziRelationKind(_BaziEnum):
    stemCombination = 0
    stemClash = 1
    stemRestraint = 2
    branchCombination = 3
    branchClash = 4
    branchHarm = 5
    branchDestruction = 6
    branchTriplePunishment = 7
    branchPunishment = 8
    branchSelfPunishment = 9
    branchTripleCombination = 10
    branchTripleDirection = 11
    branchHalfCombination = 12
    branchArchingCombination = 13
    branchHiddenCombination = 14
    branchSeverance = 15


class BaziRelationPillarFlags(_BaziEnum):
    year = 1 << 0
    month = 1 << 1
    day = 1 << 2
    hour = 1 << 3
    mingGong = 1 << 4
    shenGong = 1 << 5
    taiYuan = 1 << 6
    taiXi = 1 << 7
    primary = 0x0F
    extra = 0xF0
    all = 0xFF

    @classmethod
    def fold(cls, value):
        return frozenset(
            item
            for item in (
                cls.year,
                cls.month,
                cls.day,
                cls.hour,
                cls.mingGong,
                cls.shenGong,
                cls.taiYuan,
                cls.taiXi,
            )
            if value & item.value
        )


class BaziShenShaId(_BaziEnum):
    tianYiGuiRen = 0
    yiMa = 1
    xianChiTaoHua = 2
    hongLuan = 3
    tianXi = 4
    yangRen = 5
    feiRen = 6
    fuXingGuiRen = 7
    zaiSha = 8
    jieSha = 9
    wangShen = 10
    kongWang = 11
    tianChuGuiRenXun = 12
    tianChuGuiRen = 13
    deXiuGuiRen = 14
    tianYiMedicine = 15
    xueRen = 16
    yueDeHe = 17
    gouSha = 18
    jiaoSha = 19
    yuanChen = 20
    guChen = 21
    guaSu = 22
    hongYanSha = 23
    jinYu = 24
    jinShen = 25
    tianSheDay = 26
    liuXia = 27
    sangMen = 28
    diaoKe = 29
    piMa = 30
    tongZi = 31
    tianDeHe = 32
    sanQiTian = 33
    sanQiDi = 34
    sanQiRen = 35
    jiangXing = 36
    huaGai = 37
    kuiGang = 38
    shiLingDay = 39
    baZhuanDay = 40
    liuXiuDay = 41
    jiuChouDay = 42
    siFeiDay = 43
    shiEDaBai = 44
    tianLuoDiWang = 45
    yinChaYangCuo = 46
    guLuanSha = 47
    gongLu = 48
    gongGui = 49
    diZhuan = 50
    tianZhuan = 51
    taiJiGuiRen = 52
    wenChangGuiRen = 53
    guoYinGuiRen = 54
    tianDeGuiRen = 55
    yueDeGuiRen = 56
    luShen = 57
    riGanXueTang = 58
    riGanCiGuan = 59
    zhengXueTang = 60
    zhengCiGuan = 61
    guanGuiXueTang = 62
    guanGuiCiGuan = 63
    guanXingXueTang = 64
    xueTangHuiGui = 65


@dataclass(frozen=True)
class BaziContextConfig:
    earthPalaceMode: BaziEarthPalaceMode = BaziEarthPalaceMode.fireEarth
    qiyunDirectionMode: BaziQiyunDirectionMode = (
        BaziQiyunDirectionMode.yearStemGender
    )
    qiyunTimeModel: BaziQiyunTimeModel = BaziQiyunTimeModel.traditionalCalendar
    dayunBoundaryModel: BaziDayunBoundaryModel = BaziDayunBoundaryModel.civilYears


@dataclass(frozen=True)
class BaziChart:
    yearPillar: Ganzhi
    monthPillar: Ganzhi
    dayPillar: Ganzhi
    hourPillar: Ganzhi
    mingGong: Ganzhi
    shenGong: Ganzhi
    taiYuan: Ganzhi
    taiXi: Ganzhi
    hiddenStemCount: tuple = ()
    hiddenStems: tuple = ()
    visibleTenGods: tuple = ()
    hiddenTenGods: tuple = ()
    lifeStages: tuple = ()
    nayinIds: tuple = ()
    _native_value: object = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class BaziRelation:
    kind: BaziRelationKind
    pillarMask: frozenset
    combinedElementId: object = None


@dataclass(frozen=True)
class BaziStemRelationResult:
    flags: frozenset
    combinedElementId: object


@dataclass(frozen=True)
class BaziBranchRelationResult:
    flags: frozenset
    combinedElementId: object


@dataclass(frozen=True)
class BaziBranchTripleRelationResult:
    flags: frozenset
    combinedElementId: object


@dataclass(frozen=True)
class BaziQiyunResult:
    direction: int
    timeModel: BaziQiyunTimeModel
    referenceJieIndex: int
    jieIntervalDays: float
    startAgeYears: float
    offsetYears: int
    offsetMonths: int
    offsetDays: int
    offsetHours: int
    offsetMinutes: int
    offsetSeconds: float
    referenceJieJdUt: object
    startJdUt: object
    startCivilTime: object
    _native_value: object = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class BaziDayun:
    index: int
    ganzhi: Ganzhi
    startVirtualAge: int
    endVirtualAge: int
    startJdUt: object
    endJdUt: object
    startCivilTime: object
    endCivilTime: object


@dataclass(frozen=True)
class BaziXiaoyun:
    age: int
    ganzhi: Ganzhi


@dataclass(frozen=True)
class BaziRenyuanSilingSegment:
    stemId: int
    originKind: BaziRenyuanSilingOriginKind
    segmentIndex: int
    startDay: float
    endDay: float


@dataclass(frozen=True)
class BaziRenyuanSilingResult:
    tableModel: BaziRenyuanSilingTableModel
    timeModel: BaziRenyuanSilingTimeModel
    monthBranchId: int
    stemId: int
    originKind: BaziRenyuanSilingOriginKind
    segmentIndex: int
    previousJieIndex: int
    daysSinceJie: float
    segmentStartDay: float
    segmentEndDay: float
    previousJieJdUt: object


def _enum_value(value):
    return value.value if isinstance(value, Enum) else int(value)


def _flags(enum, value):
    return frozenset(member for member in enum if value & member.value)


def _element(value):
    return None if value == 0xFF else GanzhiWuxing(value)


def _chart(value):
    if not isinstance(value, BaziChart) or value._native_value is None:
        raise TypeError("chart must be a BaziChart returned by calc_chart")
    return value._native_value


def _read_chart(value):
    pillars = tuple(Ganzhi.from_native(item) for item in value["pillars"])
    extra = tuple(Ganzhi.from_native(item) for item in value["extra"])
    return BaziChart(
        *pillars,
        *extra,
        hiddenStemCount=tuple(value["hidden_stem_count"]),
        hiddenStems=tuple(tuple(row) for row in value["hidden_stems"]),
        visibleTenGods=tuple(value["visible_ten_gods"]),
        hiddenTenGods=tuple(tuple(row) for row in value["hidden_ten_gods"]),
        lifeStages=tuple(value["life_stages"]),
        nayinIds=tuple(value["nayin_ids"]),
        _native_value=value,
    )


def _read_qiyun(value):
    return BaziQiyunResult(
        direction=value["direction"],
        timeModel=BaziQiyunTimeModel(value["time_model"]),
        referenceJieIndex=value["reference_jie_index"],
        jieIntervalDays=value["jie_interval_days"],
        startAgeYears=value["start_age_years"],
        offsetYears=value["offset_years"],
        offsetMonths=value["offset_months"],
        offsetDays=value["offset_days"],
        offsetHours=value["offset_hours"],
        offsetMinutes=value["offset_minutes"],
        offsetSeconds=value["offset_seconds"],
        referenceJieJdUt=value["reference_jie_jd_ut"],
        startJdUt=value["start_jd_ut"],
        startCivilTime=value["start_civil_time"],
        _native_value=value,
    )


class BaziContext:
    """BaZi calculations owned by a base ephemeris context."""

    def __init__(self, owner, config=None, runtime_config=None):
        self._owner = owner
        self._closed = False
        value = config or BaziContextConfig()
        runtime = runtime_config or {}
        self._native = _native.NativeBaziContext(
            _enum_value(value.earthPalaceMode),
            _enum_value(value.qiyunDirectionMode),
            _enum_value(value.qiyunTimeModel),
            _enum_value(value.dayunBoundaryModel),
            runtime.get("source_paths", ()),
            runtime.get("data_root", ""),
            runtime.get("load_packaged_data", True),
            runtime.get("strict_discovery", False),
        )

    @property
    def is_closed(self):
        return self._closed

    def _ensure_open(self):
        if self._closed:
            raise RuntimeError("BaziContext is closed")
        self._owner._ensure_open()

    def close(self):
        if not self._closed:
            self._native = None
            self._closed = True

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, *args):
        self.close()
        return False

    def get_kong_wang(self, value):
        self._ensure_open()
        return tuple(
            EarthlyBranch(item) for item in self._native.get_kong_wang(value.raw)
        )

    def get_ten_god(self, day_stem_id, target_stem_id):
        self._ensure_open()
        return BaziTenGod(self._native.get_ten_god(day_stem_id, target_stem_id))

    def get_hidden_stems(self, branch_id):
        self._ensure_open()
        values = tuple(self._native.get_hidden_stems(branch_id))
        return values, len(values)

    def calc_stem_relation(self, a, b):
        self._ensure_open()
        value = self._native.calc_stem_relation(a, b)
        return BaziStemRelationResult(
            _flags(BaziStemRelationFlags, value["flags"]),
            _element(value["combined_element_id"]),
        )

    def calc_branch_relation(self, a, b):
        self._ensure_open()
        value = self._native.calc_branch_relation(a, b)
        return BaziBranchRelationResult(
            _flags(BaziBranchRelationFlags, value["flags"]),
            _element(value["combined_element_id"]),
        )

    def calc_branch_triple_relation(self, a, b, c):
        self._ensure_open()
        value = self._native.calc_branch_triple_relation(a, b, c)
        return BaziBranchTripleRelationResult(
            _flags(BaziBranchTripleRelationFlags, value["flags"]),
            _element(value["combined_element_id"]),
        )

    def get_life_stage(
        self, stem_id, branch_id, mode=BaziEarthPalaceMode.fireEarth
    ):
        self._ensure_open()
        return self._native.get_life_stage(stem_id, branch_id, _enum_value(mode))

    def calc_liunian(self, year):
        self._ensure_open()
        return Ganzhi.from_native(self._native.calc_liunian(year))

    def calc_liuyue(self, year_pillar, month_branch):
        self._ensure_open()
        return Ganzhi.from_native(
            self._native.calc_liuyue(year_pillar.raw, month_branch)
        )

    def calc_liuri(self, civil_date):
        self._ensure_open()
        return Ganzhi.from_native(self._native.calc_liuri(civil_date))

    def calc_liushi(self, day_pillar, hour_index):
        self._ensure_open()
        return Ganzhi.from_native(
            self._native.calc_liushi(day_pillar.raw, hour_index)
        )

    def calc_chart(self, pillars):
        self._ensure_open()
        if not isinstance(pillars, GanzhiFourPillars):
            raise TypeError("pillars must be GanzhiFourPillars")
        return _read_chart(
            self._native.calc_chart(
                [
                    pillars.year.raw,
                    pillars.month.raw,
                    pillars.day.raw,
                    pillars.hour.raw,
                ]
            )
        )

    def calc_xiaoyun(self, chart, direction, age):
        self._ensure_open()
        return Ganzhi.from_native(
            self._native.calc_xiaoyun(_chart(chart), direction, age)
        )

    def fill_xiaoyun(self, chart, direction, start_age, requested_count):
        self._ensure_open()
        values = self._native.fill_xiaoyun(
            _chart(chart), direction, start_age, requested_count
        )
        return tuple(
            BaziXiaoyun(item["age"], Ganzhi.from_native(item["ganzhi"]))
            for item in values
        )

    def calc_qiyun(
        self, birth_jd_ut, birth_civil_time, chart, gender, calendar=None
    ):
        self._ensure_open()
        if calendar is not None:
            calendar._ensure_open()
        result = self._native.calc_qiyun(
            birth_jd_ut,
            birth_civil_time,
            _chart(chart),
            _enum_value(gender),
        )
        return EphemerisResult(
            _read_qiyun(result["value"]), _diagnostic(result["diagnostic"])
        )

    def fill_dayun(
        self, birth_civil_time, chart, qiyun, requested_count
    ):
        self._ensure_open()
        if not isinstance(qiyun, BaziQiyunResult) or qiyun._native_value is None:
            raise TypeError("qiyun must be a BaziQiyunResult returned by calc_qiyun")
        values = self._native.fill_dayun(
            birth_civil_time,
            _chart(chart),
            qiyun._native_value,
            requested_count,
        )
        return tuple(
            BaziDayun(
                index=item["index"],
                ganzhi=Ganzhi.from_native(item["ganzhi"]),
                startVirtualAge=item["start_virtual_age"],
                endVirtualAge=item["end_virtual_age"],
                startJdUt=item["start_jd_ut"],
                endJdUt=item["end_jd_ut"],
                startCivilTime=item["start_civil_time"],
                endCivilTime=item["end_civil_time"],
            )
            for item in values
        )

    def calc_renyuan_siling(
        self,
        instant_jd_ut,
        chart,
        table_model=BaziRenyuanSilingTableModel.sanMingTongHui,
        time_model=BaziRenyuanSilingTimeModel.elapsed24Hours,
        calendar=None,
    ):
        self._ensure_open()
        if calendar is not None:
            calendar._ensure_open()
        result = self._native.calc_renyuan_siling(
            instant_jd_ut,
            _chart(chart),
            _enum_value(table_model),
            _enum_value(time_model),
        )
        value = result["value"]
        mapped = BaziRenyuanSilingResult(
            tableModel=BaziRenyuanSilingTableModel(value["table_model"]),
            timeModel=BaziRenyuanSilingTimeModel(value["time_model"]),
            monthBranchId=value["month_branch_id"],
            stemId=value["stem_id"],
            originKind=BaziRenyuanSilingOriginKind(value["origin_kind"]),
            segmentIndex=value["segment_index"],
            previousJieIndex=value["previous_jie_index"],
            daysSinceJie=value["days_since_jie"],
            segmentStartDay=value["segment_start_day"],
            segmentEndDay=value["segment_end_day"],
            previousJieJdUt=value["previous_jie_jd_ut"],
        )
        return EphemerisResult(mapped, _diagnostic(result["diagnostic"]))

    def get_renyuan_siling_segments(
        self,
        month_branch_id,
        table_model=BaziRenyuanSilingTableModel.sanMingTongHui,
    ):
        self._ensure_open()
        return tuple(
            BaziRenyuanSilingSegment(
                stemId=item["stem_id"],
                originKind=BaziRenyuanSilingOriginKind(item["origin_kind"]),
                segmentIndex=item["segment_index"],
                startDay=item["start_day"],
                endDay=item["end_day"],
            )
            for item in self._native.get_renyuan_siling_segments(
                month_branch_id, _enum_value(table_model)
            )
        )

    def collect_chart_relations(
        self, chart, pillar_mask=0xFF, relation_mask=0xFFFF
    ):
        self._ensure_open()
        return tuple(
            BaziRelation(
                BaziRelationKind(item["kind"]),
                BaziRelationPillarFlags.fold(item["pillar_mask"]),
                _element(item["combined_element_id"]),
            )
            for item in self._native.collect_chart_relations(
                _chart(chart), pillar_mask, relation_mask
            )
        )

    def collect_target_shen_sha(
        self, chart, target, target_kind, gender=None
    ):
        self._ensure_open()
        words = self._native.collect_target_shen_sha(
            _chart(chart),
            target.raw,
            _enum_value(target_kind),
            None if gender is None else _enum_value(gender),
        )
        result = set()
        for word_index, word in enumerate(words):
            for bit in range(64):
                value = word_index * 64 + bit
                if value < 66 and word & (1 << bit):
                    result.add(BaziShenShaId(value))
        return result


def create_bazi_context(owner, config=None, runtime_config=None):
    return BaziContext(owner, config, runtime_config)


__all__ = [name for name in globals() if name.startswith("Bazi")]
