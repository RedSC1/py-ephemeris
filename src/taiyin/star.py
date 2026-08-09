"""Process-wide fixed-star catalogs and context-owned star calculations."""
import math
from dataclasses import dataclass
from . import _native
from .position import EphemerisResult, PositionFlag, _diagnostic, _normalized_flags, position_flag_mask
from .observed import ApparentPosition, HorizontalCoordinates, HorizontalRates, ObservedFlag, ObservedPosition, _state, observed_flag_mask

@dataclass(frozen=True)
class StarPosition:
    starKey: str
    values: tuple
    flags: frozenset
    @property
    def coordinates(self): return self.values[:3]
    @property
    def rates(self): return self.values[3:]
    @property
    def is_cartesian(self): return PositionFlag.xyz in self.flags
    @property
    def is_equatorial(self): return PositionFlag.equatorial in self.flags
    @property
    def is_radians(self): return PositionFlag.radians in self.flags

@dataclass(frozen=True)
class ApparentStarPosition:
    starKey: str; status: int; diagnostic: object; geometricState: object; apparentState: object
    longitudeRadians: float; latitudeRadians: float; distanceAu: float; lightTimeDays: float; cacheHit: bool

@dataclass(frozen=True)
class ObservedStarPosition:
    starKey: str; status: int; diagnostic: object; apparent: ApparentStarPosition; flags: frozenset
    horizontal: object=None; horizontalRates: object=None; refractedHorizontal: object=None; refractedHorizontalRates: object=None

class StarCatalog:
    def add_tsc1(self,path): _path(path); _native._star_catalog_add_tsc1(path)
    def add_tsc1_bytes(self,data):
        if not data: raise ValueError("data must not be empty")
        _native._star_catalog_add_tsc1_bytes(bytes(data))
    def add_tsf1(self,path): _path(path); _native._star_catalog_add_tsf1(path)
    def clear(self): _native._star_catalog_clear()
    @property
    def count(self): return _native._star_catalog_count()
    def magnitude_of(self,key): _key(key); return _native._star_find_magnitude(key)

class StarApi:
    def __init__(self,context): self._context=context
    def at_tdb(self,key,tdb,tt,flags=()): return self._one("star_at_tdb",key,(tdb,tt),flags)
    def at_tt(self,key,julian_date,flags=()): return self._one("star_at_tt",key,(julian_date,),flags)
    def at_ut1(self,key,julian_date,flags=()): return self._one("star_at_ut1",key,(julian_date,),flags)
    def at_ut1_with_delta_t(self,key,julian_date,delta_t_seconds,flags=()):
        _finite(delta_t_seconds,"delta_t_seconds"); return self._one("star_at_ut1_with_delta_t",key,(julian_date,delta_t_seconds),flags)
    def batch_at_tdb(self,keys,tdb,tt,flags=()): return self._many("stars_at_tdb",keys,(tdb,tt),flags)
    def batch_at_tt(self,keys,julian_date,flags=()): return self._many("stars_at_tt",keys,(julian_date,),flags)
    def batch_at_ut1(self,keys,julian_date,flags=()): return self._many("stars_at_ut1",keys,(julian_date,),flags)
    def batch_at_ut1_with_delta_t(self,keys,julian_date,delta_t_seconds,flags=()):
        _finite(delta_t_seconds,"delta_t_seconds"); return self._many("stars_at_ut1_with_delta_t",keys,(julian_date,delta_t_seconds),flags)
    def observed_at_ut1(self,key,julian_date,flags=()): return self.observed_batch_at_ut1([key],julian_date,flags=flags)[0]
    def observed_batch_at_ut1(self,keys,julian_date,flags=()):
        self._context._ensure_open(); keys=list(keys)
        if not keys: return []
        for key in keys: _key(key)
        frozen=frozenset(flags); _observed_flags(frozen)
        rows=self._context._native_context.observed_stars_at_ut1(keys,julian_date,observed_flag_mask(frozen))
        return [_observed(row,key,frozen) for row,key in zip(rows,keys)]
    def _one(self,method,key,args,flags):
        self._context._ensure_open(); _key(key); frozen=_normalized_flags(flags)
        row=getattr(self._context._native_context,method)(key,*args,position_flag_mask(frozen))
        return EphemerisResult(StarPosition(key,tuple(row["values"]),frozen),_diagnostic(row["diagnostic"]))
    def _many(self,method,keys,args,flags):
        self._context._ensure_open(); keys=list(keys)
        if not keys: return []
        for key in keys: _key(key)
        frozen=_normalized_flags(flags); rows=getattr(self._context._native_context,method)(keys,*args,position_flag_mask(frozen))
        results=[]
        for row,key in zip(rows,keys):
            diagnostic=_diagnostic(row["diagnostic"])
            values=tuple(row["values"]) if diagnostic.status==0 else (math.nan,)*6
            results.append(EphemerisResult(StarPosition(key,values,frozen),diagnostic))
        return results

def _observed(row,key,flags):
    diagnostic=_diagnostic(row["diagnostic"])
    apparent=ApparentStarPosition(key,row["status"],diagnostic,_state(row["geometric_state"]),_state(row["apparent_state"]),row["longitude_radians"],row["latitude_radians"],row["distance_au"],row["light_time_days"],row["cache_hit"])
    horizontal=HorizontalCoordinates(*row["horizontal"]) if ObservedFlag.horizontal in flags or ObservedFlag.refraction in flags else None
    rates=HorizontalRates(*row["horizontal_rates"]) if horizontal and ObservedFlag.speed in flags else None
    refracted=HorizontalCoordinates(*row["refracted_horizontal"]) if ObservedFlag.refraction in flags else None
    refracted_rates=HorizontalRates(*row["refracted_horizontal_rates"]) if refracted and ObservedFlag.speed in flags else None
    return ObservedStarPosition(key,row["status"],diagnostic,apparent,flags,horizontal,rates,refracted,refracted_rates)
def _observed_flags(flags):
    if (ObservedFlag.horizontal in flags or ObservedFlag.refraction in flags) and ObservedFlag.topocentric not in flags: raise ValueError("horizontal output requires topocentric")
def _key(value):
    if not value or "\x00" in value: raise ValueError("starKey must be a non-empty NUL-free string")
def _path(value):
    if not value or "\x00" in value: raise ValueError("path must be a non-empty NUL-free string")
def _finite(value,name):
    if not math.isfinite(value): raise ValueError(name+" must be finite")
