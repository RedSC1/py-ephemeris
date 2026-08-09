"""Apparent and observed positions for major solar-system bodies."""
from dataclasses import dataclass
from enum import Enum
from .position import Body, CartesianState, Vector3, _diagnostic, _target_id

class ObservedFlag(Enum):
    speed=1<<0; topocentric=1<<1; horizontal=1<<2; refraction=1<<3; truePosition=1<<4
    astrometric=1<<5; noAberration=1<<6; noGravitationalDeflection=1<<7; strictMeteorology=1<<32
    @property
    def mask(self): return self.value

def observed_flag_mask(flags): return sum(flag.mask for flag in flags)

@dataclass(frozen=True)
class HorizontalCoordinates: azimuthRadians: float; altitudeRadians: float; distanceAu: float
@dataclass(frozen=True)
class HorizontalRates: azimuthRadiansPerDay: float; altitudeRadiansPerDay: float; distanceAuPerDay: float
@dataclass(frozen=True)
class ApparentPosition:
    body: object; bodyMaskBit: int; status: int; diagnostic: object; geometricState: CartesianState
    apparentState: CartesianState; longitudeRadians: float; latitudeRadians: float; distanceAu: float
    lightTimeDays: float; cacheHit: bool
@dataclass(frozen=True)
class ObservedPosition:
    body: object; status: int; diagnostic: object; apparent: ApparentPosition; flags: frozenset
    horizontal: object=None; horizontalRates: object=None; refractedHorizontal: object=None; refractedHorizontalRates: object=None

class ObservedApi:
    def __init__(self,context): self._context=context
    def at_ut1(self,body,julian_date,flags=()): return self.batch_at_ut1([body],julian_date,flags=flags)[0]
    def at_utc(self,body,utc,flags=()): return self.batch_at_utc([body],utc,flags=flags)[0]
    def batch_at_ut1(self,bodies,julian_date,flags=()): return self._batch("observed_at_ut1",bodies,julian_date,flags)
    def batch_at_utc(self,bodies,utc,flags=()): return self._batch("observed_at_utc",bodies,utc,flags)
    def _batch(self,method,bodies,coordinate,flags):
        self._context._ensure_open(); bodies=list(bodies)
        if not bodies: return []
        if len(bodies)>10: raise ValueError("bodies must contain at most ten major bodies")
        ids=[_target_id(body) for body in bodies]
        if any(value not in _IDS for value in ids): raise ValueError("observed positions support ten major bodies only")
        frozen=frozenset(flags)
        if (ObservedFlag.horizontal in frozen or ObservedFlag.refraction in frozen) and ObservedFlag.topocentric not in frozen:
            raise ValueError("horizontal output requires topocentric")
        rows=getattr(self._context._native_context,method)(ids,coordinate,observed_flag_mask(frozen))
        return [_read(row,body,frozen) for row,body in zip(rows,bodies)]

_IDS=frozenset((10,301,199,299,499,599,699,799,899,999))
def _state(value): return CartesianState(Vector3(*value[0]),Vector3(*value[1]),Vector3(*value[2]))
def _read(row,body,flags):
    diagnostic=_diagnostic(row["diagnostic"])
    apparent=ApparentPosition(body,row["body_mask_bit"],row["status"],diagnostic,_state(row["geometric_state"]),_state(row["apparent_state"]),row["longitude_radians"],row["latitude_radians"],row["distance_au"],row["light_time_days"],row["cache_hit"])
    horizontal=HorizontalCoordinates(*row["horizontal"]) if ObservedFlag.horizontal in flags else None
    rates=HorizontalRates(*row["horizontal_rates"]) if ObservedFlag.speed in flags and horizontal else None
    refracted=HorizontalCoordinates(*row["refracted_horizontal"]) if ObservedFlag.refraction in flags else None
    refracted_rates=HorizontalRates(*row["refracted_horizontal_rates"]) if ObservedFlag.speed in flags and refracted else None
    return ObservedPosition(body,row["status"],diagnostic,apparent,flags,horizontal,rates,refracted,refracted_rates)
