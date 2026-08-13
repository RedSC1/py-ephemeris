"""Equation of time and local mean/apparent solar-time conversions."""

import math
from dataclasses import dataclass



def _longitude(value):
    if not math.isfinite(value) or value < -math.pi or value > math.pi:
        raise ValueError("longitudeRadians must be finite and in [-pi, pi]")
    return value


@dataclass(frozen=True)
class LocalMeanSolarTime:
    coordinate: object
    longitudeRadians: float

    @classmethod
    def from_ut1(cls, ut1, *, longitudeRadians):
        longitude = _longitude(longitudeRadians)
        return cls(ut1.add_seconds(longitude * 86400.0 / (2.0 * math.pi)), longitude)

    def to_ut1(self):
        return self.coordinate.add_seconds(-self.longitudeRadians * 86400.0 / (2.0 * math.pi))


@dataclass(frozen=True)
class LocalApparentSolarTime:
    coordinate: object
    longitudeRadians: float

    @classmethod
    def from_coordinate(cls, coordinate, *, longitudeRadians):
        return cls(coordinate, _longitude(longitudeRadians))


@dataclass(frozen=True)
class EquationOfTime:
    ut1: object
    tt: object
    equationDays: float
    equationSeconds: float
    apparentSunRightAscensionRadians: float
    greenwichApparentSiderealTimeRadians: float


class SolarTimeApi:
    """Solar-time service owned by an :class:`EphemerisContext`."""

    def __init__(self, context):
        self._context = context

    def equation_of_time_at_ut1(self, ut1):
        self._context._ensure_open()
        return _equation_result(self._context._call_native_operation(
            "SolarTime.equation_of_time_at_ut1", "equation_of_time_at_ut1", ut1))

    def equation_of_time_at_tt(self, tt):
        self._context._ensure_open()
        return _equation_result(self._context._call_native_operation(
            "SolarTime.equation_of_time_at_tt", "equation_of_time_at_tt", tt))

    def mean_to_apparent(self, local_mean):
        self._context._ensure_open()
        value = self._context._call_native_operation("SolarTime.local_mean_to_apparent_solar_time", "local_mean_to_apparent_solar_time",
            local_mean.coordinate, _longitude(local_mean.longitudeRadians))
        return LocalApparentSolarTime.from_coordinate(
            value["coordinate"], longitudeRadians=local_mean.longitudeRadians)

    def apparent_to_mean(self, local_apparent):
        self._context._ensure_open()
        value = self._context._call_native_operation("SolarTime.local_apparent_to_mean_solar_time", "local_apparent_to_mean_solar_time",
            local_apparent.coordinate, _longitude(local_apparent.longitudeRadians))
        return LocalMeanSolarTime(value["coordinate"], local_apparent.longitudeRadians)


def _equation_result(value):
    return EquationOfTime(
        ut1=value["ut1"], tt=value["tt"], equationDays=value["equation_days"],
        equationSeconds=value["equation_seconds"],
        apparentSunRightAscensionRadians=value["apparent_sun_right_ascension_radians"],
        greenwichApparentSiderealTimeRadians=value[
            "greenwich_apparent_sidereal_time_radians"],
    )
