"""Direct Python bindings for Taiyin Ephemeris."""

from . import _native
from ._native import JulianDate, NativeContext as EphemerisContext, __version__, binding_backend


class Ephemeris(_native._EphemerisRuntime):
    """Process-wide Taiyin runtime and factory for independent contexts.

    Native data is initialized once by the process-wide Taiyin runtime. Each
    call to :meth:`create_context` returns an independent calculation context.
    """

    def register_custom_target(self, target_id, *, position, state=None):
        return _native.register_custom_target(target_id, position, state)

    def register_custom_ayanamsha_model(
        self, model_id, evaluator, *, reference_precession_model=-1
    ):
        return _native.register_custom_ayanamsha(
            model_id, evaluator, reference_precession_model
        )

    def register_custom_house_system_model(self, model_id, evaluator, *, fallback=-1):
        return _native.register_custom_house_system(model_id, evaluator, fallback)


__all__ = [
    "Ephemeris",
    "EphemerisContext",
    "JulianDate",
    "__version__",
    "binding_backend",
]
