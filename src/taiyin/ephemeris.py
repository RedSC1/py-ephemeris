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
from .star import StarApi, StarCatalog, load_bundled_lite_catalog
from .heliacal import HeliacalApi
from .astrology import (
    AstrologyApi, CustomAyanamshaModel, CustomAyanamshaRegistration,
    CustomAyanamshaRequest, CustomHouseSystemModel, CustomHouseSystemRegistration,
    CustomHouseSystemRequest,
)
from .time import Time
from typing import Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


def _bundled_data_root() -> str:
    """Return the installed package's default runtime-data directory."""
    return str(Path(__file__).resolve().parent / "data")


class RuntimeDataSourceKind(Enum):
    ephemeris = 1
    earthOrientation = 2
    lunarLimb = 3

    @classmethod
    def from_id(cls, value):
        try:
            return cls(value)
        except ValueError:
            return value


class RuntimeDataSourceFormat(Enum):
    unknown = 0
    opm2 = 1
    spk = 2
    kepler = 3
    semiAnalytic = 4
    fixedStar = 5
    tsc1 = 6
    tkc1 = 7
    custom = 8
    finals2000a = 100
    builtinEop = 101
    tll1 = 200
    memory = 1000

    @classmethod
    def from_id(cls, value):
        try:
            return cls(value)
        except ValueError:
            return value


class RuntimeDataSourceFlag(Enum):
    hasCoverage = 1 << 0
    builtin = 1 << 1
    memory = 1 << 2


@dataclass(frozen=True)
class RuntimeDataSource:
    kind: object
    format: object
    flags: frozenset
    source: str
    itemCount: int
    jdStart: float
    jdEnd: float


def _runtime_data_source(value):
    return RuntimeDataSource(
        RuntimeDataSourceKind.from_id(value["kind"]),
        RuntimeDataSourceFormat.from_id(value["format"]),
        frozenset(flag for flag in RuntimeDataSourceFlag if value["flags"] & flag.value),
        value["source"], value["item_count"], value["jd_start"], value["jd_end"],
    )


class EphemerisContext:
    """An independent calculation context created by :class:`Ephemeris`."""

    def __init__(self, native_context, chinese_calendar_config=None):
        self._native_context = native_context
        self._chinese_calendar_config = (
            chinese_calendar_config or ChineseCalendarConfig.historical_china()
        )
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

    @property
    def last_status(self) -> int:
        """Native status of this context's most recent calculation call."""
        self._ensure_open()
        return self._native_context.last_status

    @property
    def last_operation(self):
        """Name of this context's most recent native calculation, if any."""
        self._ensure_open()
        return self._native_context.last_operation

    @property
    def has_last_diagnostic(self) -> bool:
        """Whether this context has a native diagnostic snapshot to inspect."""
        self._ensure_open()
        return self._native_context.has_last_diagnostic

    @property
    def last_diagnostic(self):
        """Lazily materialize the diagnostic of this context's latest call.

        The native diagnostic storage is owned by this context and is replaced
        by its next calculation. Read this only for debugging; normal calls do
        not construct a Python diagnostic object.
        """
        self._ensure_open()
        value = self._native_context.last_diagnostic
        if value is None:
            return None
        from .position import _diagnostic
        return _diagnostic(value)

    def _call_native_operation(self, operation: str, native_method: str, *args):
        """Invoke one public operation and replace this context's snapshot.

        Long-running operations may perform many internal ephemeris queries.
        They must publish their own diagnostic rather than leaving the context
        pointing at an incidental internal query.
        """
        self._ensure_open()
        native = self._native_context
        native._begin_operation(operation)
        try:
            value = getattr(native, native_method)(*args)
        except Exception:
            # Migrated native calls provide their exact diagnostic before
            # raising.  A legacy binding that cannot yet do so must at least
            # publish the failed outer operation and never leak a prior
            # position-search snapshot to the caller.
            if not native.has_last_diagnostic:
                native._record_last_status(-3, operation)
            raise
        if isinstance(value, dict) and "diagnostic" in value:
            native._record_last_diagnostic(value["diagnostic"], operation)
        elif not native.has_last_diagnostic:
            native._record_last_status(0, operation)
        return value

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("EphemerisContext is closed")

    def close(self) -> None:
        # NativeCalcContext is value-owned by pybind.  Calendar facades share
        # this parent lifecycle and close with their owning context.
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
        return ChineseCalendarContext(
            self, config or self._chinese_calendar_config
        )

    def bazi(self, config=None):
        """Create the optional BaZi facade for this calculation context."""
        self._ensure_open()
        try:
            from taiyin_bazi import _bazi_from_context
        except ModuleNotFoundError as error:
            if error.name == "taiyin_bazi":
                raise ModuleNotFoundError(
                    "BaZi support requires: "
                    "python -m pip install py-ephemeris-bazi"
                ) from None
            raise
        return _bazi_from_context(self, config)

    def ziwei(self, catalog=None, selection=None):
        """Create the optional Ziwei Doushu facade for this context.

        The facade shares this context's Chinese calendar configuration.  Its
        rule catalog is provided by the separately installed
        ``py-ephemeris-ziwei`` package.
        """
        self._ensure_open()
        try:
            from taiyin_ziwei import _ziwei_from_context  # pyright: ignore[reportMissingImports]
        except ModuleNotFoundError as error:
            if error.name == "taiyin_ziwei":
                raise ModuleNotFoundError(
                    "Ziwei Doushu support requires: "
                    "python -m pip install py-ephemeris-ziwei"
                ) from None
            raise
        return _ziwei_from_context(self, catalog, selection)

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close()
        return False


class Ephemeris(_native._EphemerisRuntime):
    """Process-wide Taiyin runtime and factory for calculation contexts."""

    def __init__(
        self,
        source_paths=(),
        data_root="",
        load_packaged_data=True,
        load_builtin_eop=True,
        segment_cache_max_entries=4096,
        strict_discovery=False,
        eop_path="",
        lunar_limb_path="",
    ):
        source_paths = tuple(str(path) for path in source_paths)
        # The wheel installs a complete default data set beside this module.
        # An explicit path still lets an application select another data root.
        data_root = str(data_root) if data_root else _bundled_data_root()
        super().__init__(
            source_paths,
            data_root,
            load_packaged_data,
            load_builtin_eop,
            segment_cache_max_entries,
            strict_discovery,
            str(eop_path) if eop_path else "",
            str(lunar_limb_path) if lunar_limb_path else "",
        )
        self.star_catalog = StarCatalog()
        if load_packaged_data:
            load_bundled_lite_catalog()

    def create_context(
        self, *, chinese_calendar_config=None
    ) -> EphemerisContext:
        if (
            chinese_calendar_config is not None
            and not isinstance(
                chinese_calendar_config, ChineseCalendarConfig
            )
        ):
            raise TypeError(
                "chinese_calendar_config must be ChineseCalendarConfig"
            )
        return EphemerisContext(
            super().create_context(), chinese_calendar_config
        )

    @property
    def registered_data_sources(self):
        """Snapshot of data successfully registered by this process-wide runtime."""
        return tuple(_runtime_data_source(value) for value in super().registered_data_sources)

    def set_ephemeris_source_priority(self, path_or_basename, priority):
        """Override one file's provider-local priority during setup.

        A bare filename applies to all matching loaded files; an exact path is
        more specific. Higher values win inside the provider. Under automatic
        routing this also reorders that provider's model products, but never
        crosses SPK/OPM2/semi-analytical provider boundaries.
        """
        if not isinstance(path_or_basename, str) or not path_or_basename or "\0" in path_or_basename:
            raise ValueError("path_or_basename must be a non-empty NUL-free string")
        if not isinstance(priority, int):
            raise TypeError("priority must be an integer")
        super().set_ephemeris_source_priority(path_or_basename, priority)

    def clear_ephemeris_source_priority(self, path_or_basename):
        if not isinstance(path_or_basename, str) or not path_or_basename or "\0" in path_or_basename:
            raise ValueError("path_or_basename must be a non-empty NUL-free string")
        super().clear_ephemeris_source_priority(path_or_basename)

    def clear_all_ephemeris_source_priorities(self):
        super().clear_all_ephemeris_source_priorities()

    def clone_context(self, context: EphemerisContext) -> EphemerisContext:
        context._ensure_open()
        # NativeCalcContext is a value type, so its C++ clone is independent.
        return EphemerisContext(
            context._native_context.clone(),
            context._chinese_calendar_config,
        )

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

    def register_custom_target(
        self, target_id, *, position_evaluator, state_evaluator=None
    ):
        return _native.register_custom_target(
            target_id, position_evaluator, state_evaluator
        )

    def register_custom_ayanamsha_model(
        self, model_id, evaluator, *, reference_precession_model: object = -1
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
