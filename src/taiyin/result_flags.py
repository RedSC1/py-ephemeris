"""Execution facts reported by successful native calculations."""

from enum import IntFlag


class ResultFlag(IntFlag):
    """Non-fatal execution facts attached to ephemeris-backed results.

    These bits describe how a calculation was performed, rather than requested
    input semantics. They intentionally mirror the native ``taiyin::ResultFlag``
    values and retain future unknown bits when constructed from an integer.
    """

    none = 0
    fallbackOccurred = 1 << 0
    numericalDerivative = 1 << 1
    barycenterApprox = 1 << 2
    timeScaleFallback = 1 << 3
    historicalEventAssignmentApplied = 1 << 4
    historicalCalendarRulesApplied = 1 << 5
    historicalPillarTermsApplied = 1 << 6
