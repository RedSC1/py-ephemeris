"""Context configuration types currently needed by event searches."""

from dataclasses import dataclass
from enum import Enum
import math


@dataclass(frozen=True)
class ObserverLocation:
    longitude_degrees: float
    latitude_degrees: float
    height_meters: float = 0.0


class RouteRule(Enum):
    automatic = 0
    opm2 = 1
    spk = 2
    semiAnalytic = 3

    @property
    def id(self):
        return self.value


@dataclass(frozen=True)
class Atmosphere:
    pressure_mbar: float = 1013.25
    temperature_celsius: float = 15.0
    relative_humidity_percent: float = 0.0
    wavelength_micrometer: float = 0.55


@dataclass(frozen=True)
class AstroModelConfig:
    tdb_model_id: int = 0
    precession_model_id: int = 1
    nutation_model_id: int = 1
    obliquity_model_id: int = 0
    frame_route_id: int = 0


class ApparentFlag(Enum):
    lightTime = 1 << 0
    spherical = 1 << 2
    aberration = 1 << 3
    deflection = 1 << 4
    velocity = 1 << 5
    acceleration = 1 << 6
    shapiroDelay = 1 << 7

    @property
    def mask(self):
        return self.value

class AtmospherePolicyFlag(Enum):
    allowStandardFallback = 1 << 0
    @property
    def mask(self): return self.value

class HeliacalVisibilityModel(Enum):
    belokrylov2011 = 0
    schaefer1993 = 1
    @property
    def id(self): return self.value


class RefractionModel(Enum):
    bennett=0
    skyfield=1
    hybrid=2
    auerStandish=3
    sofa=4
    @property
    def id(self): return self.value


class ShapiroDelayModel(Enum):
    standard=0
    @property
    def id(self): return self.value


class EclipseShadowModel(Enum):
    nasaDanjon=0
    chauvenet=1
    geometric=2
    rawDanjon=3
    @property
    def id(self): return self.value


class EclipseMoonRadiusModel(Enum):
    almanac=0
    mean=1
    @property
    def id(self): return self.value


@dataclass(frozen=True)
class ApparentDeflector:
    body_id: int
    schwarzschild_radius_au: float
    limit: float = 0.0


@dataclass(frozen=True)
class ApparentConfig:
    flags: frozenset = frozenset((
        ApparentFlag.lightTime,
        ApparentFlag.aberration,
        ApparentFlag.deflection,
    ))
    output_frame: int = 2
    light_time_method_id: int = 0
    shapiro_delay_model_id: int = 0
    aberration_model_id: int = 0
    deflection_model_id: int = 0
    max_light_time_iterations: int = 8
    light_time_tolerance_days: float = 1e-13
    matrix_derivative_step_days: float = 1e-3

    def __post_init__(self):
        object.__setattr__(self, "flags", frozenset(self.flags))


class ContextConfiguration:
    """The context policy controls used by the Events module."""

    def __init__(self, context):
        self._context = context

    def reset(self):
        self._context._ensure_open()
        self._context._native_context.reset_configuration()
        self._context.time._synchronize_tdb_model_id(0)

    def set_geocentric_observer(self, *, observer_id, center_id):
        self._context._ensure_open()
        self._context._native_context.set_geocentric_observer(observer_id, center_id)

    def set_observer_location(self, location):
        self._context._ensure_open()
        for coordinate in (
            location.longitude_degrees, location.latitude_degrees, location.height_meters):
            if not isinstance(coordinate, (int, float)) or not math.isfinite(coordinate):
                raise ValueError("observer coordinates must be finite")
        if not -90.0 <= location.latitude_degrees <= 90.0:
            raise ValueError("observer latitude must be in [-90, 90]")
        self._context._native_context.set_observer_location(
            location.longitude_degrees, location.latitude_degrees, location.height_meters)

    def clear_observer_location(self):
        self._context._ensure_open()
        self._context._native_context.clear_observer_location()

    def set_simple_topocentric_observer(self,location,*,ut1,tt):
        self._validate_location(location)
        self._context._native_context.set_simple_topocentric_observer(
            location.longitude_degrees,location.latitude_degrees,location.height_meters,ut1,tt)

    def set_precise_topocentric_observer(self,location,*,utc,tt):
        self._validate_location(location)
        self._context._native_context.set_precise_topocentric_observer(
            location.longitude_degrees,location.latitude_degrees,location.height_meters,utc,tt)

    def set_topocentric_observer_offset(self,offset):
        self._context._ensure_open()
        values=tuple(offset.position_au)+tuple(offset.velocity_au_per_day)+tuple(offset.acceleration_au_per_day2)
        if len(values)!=9 or any(not math.isfinite(value) for value in values):
            raise ValueError("observer offset coordinates must be finite")
        self._context._native_context.set_topocentric_observer_offset(values)

    def set_standard_atmosphere(self):
        self._context._ensure_open()
        self._context._native_context.set_standard_atmosphere()

    def set_atmosphere(self,atmosphere):
        self._context._ensure_open()
        values=(atmosphere.pressure_mbar,atmosphere.temperature_celsius,
                atmosphere.relative_humidity_percent,atmosphere.wavelength_micrometer)
        if any(not math.isfinite(value) for value in values):
            raise ValueError("atmosphere values must be finite")
        self._context._native_context.set_atmosphere(*values)

    def set_meteorological_range_km(self,range_km):
        self._context._ensure_open()
        if not math.isfinite(range_km) or range_km<1:
            raise ValueError("range_km must be finite and at least 1")
        self._context._native_context.set_meteorological_range_km(range_km)

    def set_atmosphere_policy(self, flags):
        self._context._ensure_open()
        self._context._native_context.set_atmosphere_policy(sum(flag.mask for flag in flags))

    def set_heliacal_visibility_model(self, model):
        self._context._ensure_open()
        self._context._native_context.set_heliacal_visibility_model(model.id)

    def set_astro_models(self,config):
        self._context._ensure_open()
        self._context._native_context.set_astro_models(
            config.tdb_model_id,config.precession_model_id,config.nutation_model_id,
            config.obliquity_model_id,config.frame_route_id)
        self._context.time._synchronize_tdb_model_id(config.tdb_model_id)

    def set_celestial_pole_offset(self,*,dx_radians,dy_radians,
                                  dx_rate_rad_per_day=0.0,dy_rate_rad_per_day=0.0):
        self._context._ensure_open()
        values=(dx_radians,dy_radians,dx_rate_rad_per_day,dy_rate_rad_per_day)
        if any(not math.isfinite(value) for value in values):
            raise ValueError("celestial pole offsets must be finite")
        self._context._native_context.set_celestial_pole_offset(*values)

    def set_refraction_model(self,model):
        self._context._ensure_open()
        self._context._native_context.set_refraction_model(model.id)

    def use_solar_deflector(self):
        self._context._ensure_open()
        self._context._native_context.use_solar_deflector()

    def clear_deflectors(self):
        self._context._ensure_open()
        self._context._native_context.clear_deflectors()

    def set_deflectors(self,deflectors,*,solar_deflector_index=-1):
        self._context._ensure_open()
        values=tuple(deflectors)
        if (not isinstance(solar_deflector_index,int)
                or solar_deflector_index < -1
                or solar_deflector_index >= len(values)):
            raise ValueError("solar_deflector_index must satisfy -1 <= index < deflector count")
        for value in values:
            if not isinstance(value.body_id,int) or not -0x80000000<=value.body_id<=0x7fffffff:
                raise ValueError("deflector body_id must fit int32")
            if (not math.isfinite(value.schwarzschild_radius_au)
                    or value.schwarzschild_radius_au<0):
                raise ValueError("schwarzschild_radius_au must be finite and non-negative")
            if not math.isfinite(value.limit) or value.limit<0:
                raise ValueError("deflector limit must be finite and non-negative")
        self._context._native_context.set_deflectors(
            [value.body_id for value in values],
            [value.schwarzschild_radius_au for value in values],
            [value.limit for value in values],solar_deflector_index)

    def set_light_time_iteration(self,*,max_iterations,tolerance_days):
        self._context._ensure_open()
        if not isinstance(max_iterations,int) or not 0<=max_iterations<=0x7fffffff:
            raise ValueError("max_iterations must fit the non-negative int32 range")
        if not math.isfinite(tolerance_days) or tolerance_days<0:
            raise ValueError("tolerance_days must be finite and non-negative")
        self._context._native_context.set_light_time_iteration(max_iterations,tolerance_days)

    def enable_shapiro_delay(self,model=ShapiroDelayModel.standard):
        self._context._ensure_open()
        self._context._native_context.enable_shapiro_delay(model.id)

    def disable_shapiro_delay(self):
        self._context._ensure_open()
        self._context._native_context.disable_shapiro_delay()

    def set_eclipse_models(self,*,shadow,moon_radius):
        self._context._ensure_open()
        self._context._native_context.set_eclipse_models(shadow.id,moon_radius.id)

    def set_apparent_config(self, config):
        self._context._ensure_open()
        if config.output_frame==-1:
            raise ValueError("output_frame must not be unknown")
        if config.max_light_time_iterations<0:
            raise ValueError("max_light_time_iterations must be non-negative")
        if (not math.isfinite(config.light_time_tolerance_days)
                or config.light_time_tolerance_days<0):
            raise ValueError("light_time_tolerance_days must be finite and non-negative")
        if (not math.isfinite(config.matrix_derivative_step_days)
                or config.matrix_derivative_step_days<=0):
            raise ValueError("matrix_derivative_step_days must be finite and positive")
        if ApparentFlag.shapiroDelay in config.flags and ApparentFlag.lightTime not in config.flags:
            raise ValueError("Shapiro delay requires lightTime")
        self._context._native_context.set_apparent_config(
            sum(flag.mask for flag in config.flags),config.output_frame,
            config.light_time_method_id,config.shapiro_delay_model_id,
            config.aberration_model_id,config.deflection_model_id,
            config.max_light_time_iterations,config.light_time_tolerance_days,
            config.matrix_derivative_step_days)

    def set_route_rule(self, route_rule):
        self._context._ensure_open()
        self._context._native_context.set_route_rule(route_rule.id)

    def _validate_location(self,location):
        self._context._ensure_open()
        for coordinate in (location.longitude_degrees,location.latitude_degrees,location.height_meters):
            if not isinstance(coordinate,(int,float)) or not math.isfinite(coordinate):
                raise ValueError("observer coordinates must be finite")
        if not -90<=location.latitude_degrees<=90:
            raise ValueError("observer latitude must be in [-90, 90]")
