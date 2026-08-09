"""Runtime ownership and calculation contexts.

This module intentionally follows the old public shape while delegating all
native work to the private pybind extension.
"""

from . import _native
from .chinese_calendar import ChineseCalendarConfig, ChineseCalendarContext
from .events import EventsApi
from .configuration import ContextConfiguration
from .ganzhi import GanzhiApi
from .position import PositionApi
from .solar_time import SolarTimeApi
from .visibility import VisibilityApi
from .phenomena import PhenomenaApi
from .observed import ObservedApi
from .orbital import OrbitalApi
from .occultation import OccultationApi
from .eclipse import EclipseApi
from .star import StarApi, StarCatalog
from .heliacal import HeliacalApi
from .astrology import (
    AstrologyApi, CustomAyanamshaModel, CustomAyanamshaRegistration,
    CustomAyanamshaRequest, CustomHouseSystemModel, CustomHouseSystemRegistration,
    CustomHouseSystemRequest,
)
from .time import Time
from typing import Optional


class EphemerisContext:
    """An independent calculation context created by :class:`Ephemeris`."""

    def __init__(self, native_context):
        self._native_context = native_context
        self._closed = False
        self.configuration = ContextConfiguration(self)
        self.position = PositionApi(self)
        self.solar_time = SolarTimeApi(self)
        self.visibility = VisibilityApi(self)
        self.phenomena = PhenomenaApi(self)
        self.observed = ObservedApi(self)
        self.orbits = OrbitalApi(self)
        self.occultation = OccultationApi(self)
        self.eclipses = EclipseApi(self)
        self.stars = StarApi(self)
        self.heliacal = HeliacalApi(self)
        self.events = EventsApi(self)
        self.astrology = AstrologyApi(self)
        self.time = Time(self)
        self.ganzhi = GanzhiApi(self)
        self._chinese_calendar = None

    @property
    def is_closed(self) -> bool:
        return self._closed

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("EphemerisContext is closed")

    def close(self) -> None:
        # NativeCalcContext is value-owned by pybind.  The explicit lifecycle
        # hook is retained because later calendar/BaZi child facades need the
        # same parent-close semantics as the old package.
        if self._chinese_calendar is not None:
            self._chinese_calendar.close()
        self._closed = True

    @property
    def chinese_calendar(self) -> ChineseCalendarContext:
        if self._chinese_calendar is None or self._chinese_calendar.is_closed:
            self._chinese_calendar = self.create_chinese_calendar()
        return self._chinese_calendar

    def create_chinese_calendar(
        self, config: Optional[ChineseCalendarConfig] = None
    ) -> ChineseCalendarContext:
        self._ensure_open()
        return ChineseCalendarContext(self, config or ChineseCalendarConfig.astronomical())

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close()
        return False


class Ephemeris(_native._EphemerisRuntime):
    """Process-wide Taiyin runtime and factory for calculation contexts."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.star_catalog = StarCatalog()

    def create_context(self) -> EphemerisContext:
        return EphemerisContext(super().create_context())

    def clone_context(self, context: EphemerisContext) -> EphemerisContext:
        context._ensure_open()
        # NativeCalcContext is a value type, so its C++ clone is independent.
        return EphemerisContext(context._native_context.clone())

    def format_ephemeris_diagnostic(self,diagnostic):
        return super().format_ephemeris_diagnostic({
            "status":diagnostic.status,"target_id":diagnostic.target_id,
            "center_id":diagnostic.center_id,"frame":diagnostic.raw_frame_id,
            "jd_tdb":diagnostic.jd_tdb,"candidate_count":diagnostic.candidate_count,
            "attempted_method_id":diagnostic.attempted_method_id,
            "nearest_coverage_start":diagnostic.nearest_coverage_start,
            "nearest_coverage_end":diagnostic.nearest_coverage_end,
            "component_target_id":diagnostic.component_target_id,
            "component_center_id":diagnostic.component_center_id,
            "component_method_id":diagnostic.component_method_id,
            "time_scale_route":diagnostic.raw_time_scale_route_id,
            "time_scale_fallback_reason":diagnostic.raw_time_scale_fallback_reason_id,
            "time_scale_flags":diagnostic.time_scale_flags,
            "tai_minus_utc_seconds":diagnostic.tai_minus_utc_seconds,
            "dut1_seconds":diagnostic.dut1_seconds,
            "delta_t_seconds":diagnostic.delta_t_seconds,
        })

    def clear_custom_targets(self):
        _native.clear_custom_targets()

    def clear_custom_ayanamsha_models(self):
        _native.clear_custom_ayanamsha_models()

    def clear_custom_house_system_models(self):
        _native.clear_custom_house_system_models()

    def register_builtin_astrology_targets(self):
        _native.register_builtin_astrology_targets()

    def create_bazi(self,config=None):
        from taiyin_bazi import BaziContext
        return BaziContext(self.create_context(),config)

    def register_custom_target(
        self, target_id, *, position_evaluator, state_evaluator=None
    ):
        return _native.register_custom_target(
            target_id, position_evaluator, state_evaluator
        )

    def register_custom_ayanamsha_model(
        self, model_id, evaluator, *, reference_precession_model=-1
    ):
        model = CustomAyanamshaModel(model_id)
        precession_id = getattr(reference_precession_model, "id", reference_precession_model)
        native = _native.register_custom_ayanamsha(
            model.id,
            lambda request: evaluator(CustomAyanamshaRequest(
                request["jd_tt"], request["native_position_flags"])), precession_id
        )
        return CustomAyanamshaRegistration(native, model)

    def register_custom_house_system_model(self, model_id, evaluator, *, fallback=None):
        model = CustomHouseSystemModel(model_id)
        fallback_id = -1 if fallback is None else getattr(fallback, "id", fallback)
        native = _native.register_custom_house_system(
            model.id,
            lambda request: evaluator(CustomHouseSystemRequest(
                request["armc_radians"], request["observer_latitude_radians"],
                request["true_obliquity_radians"], request["ascendant_radians"],
                request["midheaven_radians"])), fallback_id)
        return CustomHouseSystemRegistration(native, model)
