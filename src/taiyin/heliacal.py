"""Heliacal visibility calculations and event searches."""
import math
from dataclasses import dataclass
from enum import Enum
from .position import Body, PositionFlag, _target_id, position_flag_mask

class HeliacalEventKind(Enum):
    morningFirst=1; morningLast=2; eveningFirst=3; eveningLast=4; unknown=-1
    @property
    def id(self): return self.value
    @classmethod
    def from_id(cls,value):
        try:return cls(value)
        except ValueError:return cls.unknown
class HeliacalFlag(Enum):
    includeMoonlight=1<<32; strictMeteorology=1<<33
    @property
    def mask(self):return self.value
@dataclass(frozen=True)
class HeliacalVisibilityConditions:
    extinctionMagnitudePerAirmass: object=None; skyBrightnessNanolambert: object=None; nightSkyBrightnessNanolambert: object=None
@dataclass(frozen=True)
class HeliacalVisibilityResult:
    visible:bool; modelId:int; extinctionModelId:int; twilightModelId:int; moonlightModelId:int; visualThresholdModelId:int
    targetMagnitude:float; limitingMagnitude:float; targetAltitudeRadians:float; targetAzimuthRadians:float; sunAltitudeRadians:float
    sunAzimuthRadians:float; targetSunSeparationRadians:float; airmass:float; extinctionMagnitudePerAirmass:float
    extinctionMagnitude:float; skyBrightnessNanolambert:float; moonlightBrightnessNanolambert:float
    thresholdIlluminanceFootcandles:float; targetIlluminanceFootcandles:float; visibilityMarginMagnitude:float
    requiredSunAltitudeRadians:object; solarDepressionMarginRadians:object
@dataclass(frozen=True)
class HeliacalVisibilitySearchResult:
    event:HeliacalEventKind; coordinate:object; windowStart:object; windowEnd:object; scannedDayCount:int
    sampledWindowCount:int; visibilityEvaluationCount:int; visibility:HeliacalVisibilityResult

class HeliacalApi:
    def __init__(self,context):self._context=context
    def body_at_ut1(self,target,ut1,*,position_flags=(),flags=(),conditions=HeliacalVisibilityConditions()):
        _body(target);return self._calc("heliacal_body_at_ut1",(_target_id(target),ut1),position_flags,flags,conditions)
    def star_at_ut1(self,key,ut1,*,position_flags=(),flags=(),conditions=HeliacalVisibilityConditions()):
        _key(key);return self._calc("heliacal_star_at_ut1",(key,ut1),position_flags,flags,conditions)
    def next_body_event_at_ut1(self,target,start,*,event,max_search_days,position_flags=(),flags=(),conditions=HeliacalVisibilityConditions()):
        _body(target);return self._search("heliacal_next_body_at_ut1",(_target_id(target),start),event,max_search_days,position_flags,flags,conditions)
    def next_star_event_at_ut1(self,key,start,*,event,max_search_days,position_flags=(),flags=(),conditions=HeliacalVisibilityConditions()):
        _key(key);return self._search("heliacal_next_star_at_ut1",(key,start),event,max_search_days,position_flags,flags,conditions)
    def _calc(self,method,args,position_flags,flags,conditions):
        self._context._ensure_open();mask=_mask(position_flags,flags);c=_conditions(conditions)
        raw=self._context._call_native_operation("Heliacal." + method, method, *args, mask, c)
        return _result(raw)
    def _search(self,method,args,event,days,position_flags,flags,conditions):
        self._context._ensure_open()
        if event is HeliacalEventKind.unknown:raise ValueError("event must be known")
        if not math.isfinite(days) or days<=0:raise ValueError("max_search_days must be positive and finite")
        raw=self._context._call_native_operation("Heliacal." + method, method, *args, event.id, days, _mask(position_flags,flags), _conditions(conditions))
        value=HeliacalVisibilitySearchResult(HeliacalEventKind.from_id(raw["event_kind"]),raw["coordinate"],raw["window_start"],raw["window_end"],raw["scanned_day_count"],raw["sampled_window_count"],raw["visibility_evaluation_count"],_result(raw["visibility"]))
        return value
def _result(v):
    keys=("visible","model_id","extinction_model_id","twilight_model_id","moonlight_model_id","visual_threshold_model_id","target_magnitude","limiting_magnitude","target_altitude_radians","target_azimuth_radians","sun_altitude_radians","sun_azimuth_radians","target_sun_separation_radians","airmass","extinction_magnitude_per_airmass","extinction_magnitude","sky_brightness_nanolambert","moonlight_brightness_nanolambert","threshold_illuminance_footcandles","target_illuminance_footcandles","visibility_margin_magnitude")
    values=[v[k] for k in keys];values.extend((_finite_none(v["required_sun_altitude_radians"]),_finite_none(v["solar_depression_margin_radians"])))
    return HeliacalVisibilityResult(*values)
def _conditions(c):
    for value in (c.extinctionMagnitudePerAirmass,c.skyBrightnessNanolambert,c.nightSkyBrightnessNanolambert):
        if value is not None and (not math.isfinite(value) or value<=0):raise ValueError("condition values must be positive and finite")
    return {"extinction":c.extinctionMagnitudePerAirmass,"sky":c.skyBrightnessNanolambert,"night":c.nightSkyBrightnessNanolambert}
def _mask(position_flags,flags):
    allowed={PositionFlag.truepos,PositionFlag.astrometric,PositionFlag.no_aberr,PositionFlag.no_gdefl};p=frozenset(position_flags)
    if p-allowed:raise ValueError("unsupported heliacal position flag")
    return position_flag_mask(p)|sum(flag.mask for flag in flags)
def _body(v):
    if _target_id(v) in (0,10,301,399):raise ValueError("unsupported heliacal body")
def _key(v):
    if not v or "\x00" in v:raise ValueError("star_key must be non-empty and NUL-free")
def _finite_none(v):return v if math.isfinite(v) else None
