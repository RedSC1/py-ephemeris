"""Runtime ownership and calculation contexts.

This module intentionally follows the old public shape while delegating all
native work to the private pybind extension.
"""

from . import _native
from .chinese_calendar import ChineseCalendarConfig, ChineseCalendarContext
from .ganzhi import GanzhiApi
from .position import PositionApi
from .solar_time import SolarTimeApi
from .time import Time
from typing import Optional


class EphemerisContext:
    """An independent calculation context created by :class:`Ephemeris`."""

    def __init__(self, native_context):
        self._native_context = native_context
        self._closed = False
        self.position = PositionApi(self)
        self.solar_time = SolarTimeApi(self)
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

    def create_context(self) -> EphemerisContext:
        return EphemerisContext(super().create_context())

    def clone_context(self, context: EphemerisContext) -> EphemerisContext:
        context._ensure_open()
        # NativeCalcContext is a value type, so its C++ clone is independent.
        return EphemerisContext(context._native_context.clone())

    def register_custom_target(
        self, target_id, *, position_evaluator, state_evaluator=None
    ):
        return _native.register_custom_target(
            target_id, position_evaluator, state_evaluator
        )

    def register_custom_ayanamsha_model(
        self, model_id, evaluator, *, reference_precession_model=-1
    ):
        return _native.register_custom_ayanamsha(
            model_id, evaluator, reference_precession_model
        )

    def register_custom_house_system_model(self, model_id, evaluator, *, fallback=None):
        fallback_id = -1 if fallback is None else fallback
        return _native.register_custom_house_system(model_id, evaluator, fallback_id)
