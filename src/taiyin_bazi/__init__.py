"""Optional BaZi bindings for :mod:`taiyin`."""

from dataclasses import dataclass
from enum import Enum

from taiyin import EarthlyBranch,Ganzhi,GanzhiWuxing
from . import _bazi_native as _native


class BaziEarthPalaceMode(Enum):
    fireEarth=0
    waterEarth=1


class BaziTenGod(Enum):
    biJian=0; jieCai=1; shiShen=2; shangGuan=3; pianCai=4
    zhengCai=5; qiSha=6; zhengGuan=7; pianYin=8; zhengYin=9


class BaziStemRelationFlags(Enum):
    combination=1; clash=2; restraint=4


class BaziBranchRelationFlags(Enum):
    combination=1; clash=2; harm=4; destruction=8; punishment=16
    selfPunishment=32; hiddenCombination=64; severance=128


class BaziBranchTripleRelationFlags(Enum):
    combination=1; direction=2; punishment=4


@dataclass(frozen=True)
class BaziContextConfig:
    earthPalaceMode: BaziEarthPalaceMode=BaziEarthPalaceMode.fireEarth
    qiyunDirectionMode: int=0
    qiyunTimeModel: int=0
    dayunBoundaryModel: int=0


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


def _flags(enum,value):
    return frozenset(member for member in enum if value & member.value)


def _element(value):
    return None if value==0xff else GanzhiWuxing(value)


class BaziContext:
    def __init__(self,owner,config=None):
        self._owner=owner
        self._closed=False
        value=config or BaziContextConfig()
        self._native=_native.NativeBaziContext(
            value.earthPalaceMode.value,value.qiyunDirectionMode,
            value.qiyunTimeModel,value.dayunBoundaryModel)

    @property
    def is_closed(self): return self._closed
    def _ensure_open(self):
        if self._closed: raise RuntimeError("BaziContext is closed")
        self._owner._ensure_open()
    def close(self): self._closed=True
    def __enter__(self): self._ensure_open(); return self
    def __exit__(self,*args): self.close(); return False
    def get_kong_wang(self,value):
        self._ensure_open(); return tuple(EarthlyBranch(item) for item in self._native.get_kong_wang(value.raw))
    def get_ten_god(self,day_stem_id,target_stem_id):
        self._ensure_open(); return BaziTenGod(self._native.get_ten_god(day_stem_id,target_stem_id))
    def get_hidden_stems(self,branch_id):
        self._ensure_open(); values=tuple(self._native.get_hidden_stems(branch_id)); return values,len(values)
    def calc_stem_relation(self,a,b):
        self._ensure_open(); value=self._native.calc_stem_relation(a,b)
        return BaziStemRelationResult(_flags(BaziStemRelationFlags,value["flags"]),_element(value["combined_element_id"]))
    def calc_branch_relation(self,a,b):
        self._ensure_open(); value=self._native.calc_branch_relation(a,b)
        return BaziBranchRelationResult(_flags(BaziBranchRelationFlags,value["flags"]),_element(value["combined_element_id"]))
    def calc_branch_triple_relation(self,a,b,c):
        self._ensure_open(); value=self._native.calc_branch_triple_relation(a,b,c)
        return BaziBranchTripleRelationResult(_flags(BaziBranchTripleRelationFlags,value["flags"]),_element(value["combined_element_id"]))
    def get_life_stage(self,stem_id,branch_id,mode=BaziEarthPalaceMode.fireEarth):
        self._ensure_open(); return self._native.get_life_stage(stem_id,branch_id,mode.value)
    def calc_liunian(self,year): self._ensure_open(); return Ganzhi.from_native(self._native.calc_liunian(year))
    def calc_liuyue(self,year_pillar,month_branch): self._ensure_open(); return Ganzhi.from_native(self._native.calc_liuyue(year_pillar.raw,month_branch))
    def calc_liuri(self,civil_date): self._ensure_open(); return Ganzhi.from_native(self._native.calc_liuri(civil_date))
    def calc_liushi(self,day_pillar,hour_index): self._ensure_open(); return Ganzhi.from_native(self._native.calc_liushi(day_pillar.raw,hour_index))


def create_bazi_context(owner,config=None):
    return BaziContext(owner,config)
