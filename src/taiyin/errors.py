"""Structured exceptions for failures reported by the native runtime."""

from enum import IntEnum


class StatusCode(IntEnum):
    """Stable status values shared with the Taiyin C and C++ APIs."""

    ok = 0

    invalidArgument = -1
    outOfMemory = -2
    internal = -3
    unsupported = -4

    ephemerisNoRoute = -1001
    ephemerisCoverageGap = -1002
    ephemerisLoadFailed = -1003
    ephemerisEvaluationFailed = -1004
    compositeMissingComponent = -1010
    compositeCoverageGap = -1011
    compositeMethodMismatch = -1012

    fileNotFound = -2001
    badFileFormat = -2002
    unsupportedFileFormat = -2003
    fileDiscoveryFailed = -2004

    eopOutOfRange = -3001
    leapSecondUnavailable = -3002

    eventNotFound = -5001

    runtimeNotInitialized = -6001
    runtimeCacheInsertFailed = -6002
    runtimeRegistryFailed = -6003


class StatusCategory(IntEnum):
    """Broad native status categories."""

    ok = 0
    generic = 1
    ephemeris = 10
    file = 20
    time = 30
    observer = 40
    event = 50
    runtime = 60
    unknown = 999


class EphemerisError(RuntimeError):
    """Base class for a non-success status returned by native code."""

    def __init__(
        self,
        operation,
        status,
        status_name,
        detail,
        category,
    ):
        self.operation = str(operation)
        self.status = _known_or_raw(StatusCode, status)
        self.status_name = str(status_name)
        self.detail = str(detail)
        self.category = _known_or_raw(StatusCategory, category)
        super().__init__(
            f"{self.operation}: {self.detail} "
            f"[{self.status_name}, {int(self.status)}]"
        )

    @property
    def status_code(self):
        """The exact integer status, including future unknown values."""

        return int(self.status)


class InvalidArgumentError(EphemerisError):
    """Native code rejected an otherwise well-formed call argument."""


class OutOfMemoryError(EphemerisError):
    """The native operation could not allocate required memory."""


class InternalCalculationError(EphemerisError):
    """The native runtime encountered an internal invariant failure."""


class UnsupportedOperationError(EphemerisError):
    """The requested operation or configuration is not implemented."""


class EphemerisRouteError(EphemerisError):
    """No usable ephemeris route or route component produced the result."""


class DataFileError(EphemerisError):
    """A required data file could not be found, parsed, or discovered."""


class TimeScaleError(EphemerisError):
    """Required EOP or leap-second data was unavailable."""


class ObserverError(EphemerisError):
    """The configured observer model cannot perform the operation."""


class EventSearchError(EphemerisError):
    """An event search could not find a result within its bounds."""


class RuntimeServiceError(EphemerisError):
    """A process-wide runtime service failed or was not initialized."""


class UnknownNativeError(EphemerisError):
    """Native code returned a status unknown to this Python package."""


def _known_or_raw(enum_type, value):
    raw = int(value)
    try:
        return enum_type(raw)
    except ValueError:
        return raw


def _error_type_for_status(status, category):
    raw_status = int(status)
    if raw_status == StatusCode.invalidArgument:
        return InvalidArgumentError
    if raw_status == StatusCode.outOfMemory:
        return OutOfMemoryError
    if raw_status == StatusCode.internal:
        return InternalCalculationError
    if raw_status == StatusCode.unsupported:
        return UnsupportedOperationError

    raw_category = int(category)
    if raw_category == StatusCategory.ephemeris:
        return EphemerisRouteError
    if raw_category == StatusCategory.file:
        return DataFileError
    if raw_category == StatusCategory.time:
        return TimeScaleError
    if raw_category == StatusCategory.observer:
        return ObserverError
    if raw_category == StatusCategory.event:
        return EventSearchError
    if raw_category == StatusCategory.runtime:
        return RuntimeServiceError
    return UnknownNativeError


def _raise_for_status(operation, status, status_name, detail, category):
    """Raise the public exception corresponding to one native status."""

    if int(status) == StatusCode.ok:
        return
    error_type = _error_type_for_status(status, category)
    raise error_type(operation, status, status_name, detail, category)


__all__ = [
    "DataFileError",
    "EphemerisError",
    "EphemerisRouteError",
    "EventSearchError",
    "InternalCalculationError",
    "InvalidArgumentError",
    "ObserverError",
    "OutOfMemoryError",
    "RuntimeServiceError",
    "StatusCategory",
    "StatusCode",
    "TimeScaleError",
    "UnknownNativeError",
    "UnsupportedOperationError",
]
