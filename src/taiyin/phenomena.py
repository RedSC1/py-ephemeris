"""Physical and apparent phenomena for major solar-system bodies."""
import math
from dataclasses import dataclass
from enum import Enum
from .position import Body, PositionFlag, _target_id, position_flag_mask

class PhenomenaOrigin(Enum):
    geocentric = 0
    topocentric = 1

@dataclass(frozen=True)
class BodyPhenomena:
    body: object; phaseAngleRadians: float; illuminatedFraction: float; solarElongationRadians: float
    apparentDiameterRadians: float; apparentMagnitude: float; geocentricHorizontalParallaxRadians: object
    origin: PhenomenaOrigin; flags: frozenset

class PhenomenaApi:
    def __init__(self, context): self._context = context
    def at_tt(self, body, tt, *, origin=PhenomenaOrigin.geocentric, flags=()): return self._at("phenomena_at_tt", body, tt, origin, flags)
    def at_ut1(self, body, ut1, *, origin=PhenomenaOrigin.geocentric, flags=()): return self._at("phenomena_at_ut1", body, ut1, origin, flags)
    def _at(self, method, body, coordinate, origin, flags):
        self._context._ensure_open(); body_id = _target_id(body)
        if body_id not in (10,301,199,299,499,599,699,799,899,999): raise ValueError("body must be the Sun, Moon, or a physical planet through Pluto")
        frozen=frozenset(flags)
        if PositionFlag.topocentric in frozen: raise ValueError("use origin for topocentric phenomena")
        mask=position_flag_mask(frozen) | (PositionFlag.topocentric.mask if origin is PhenomenaOrigin.topocentric else 0)
        value=self._context._call_native_operation("Phenomena." + method, method, body_id, coordinate, mask); p=value["horizontal_parallax_radians"]
        return self._context._operation_result(BodyPhenomena(body,value["phase_angle_radians"],value["illuminated_fraction"],value["solar_elongation_radians"],value["apparent_diameter_radians"],value["apparent_magnitude"],p if math.isfinite(p) else None,origin,frozen))
