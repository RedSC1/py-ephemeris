from datetime import datetime, timedelta, timezone
import math

import pytest

import taiyin


def assert_same_julian_date(left: taiyin.JulianDate, right: taiyin.JulianDate) -> None:
    assert left.day_number == right.day_number
    assert left.day_fraction == right.day_fraction


def test_from_timestamp_uses_python_unix_seconds() -> None:
    epoch = taiyin.JulianDate.from_timestamp(0)
    next_day = taiyin.JulianDate.from_timestamp(86400.0)
    previous_day = taiyin.JulianDate.from_timestamp(-86400.0)

    assert (epoch.day_number, epoch.day_fraction) == (2440587, 0.5)
    assert (next_day.day_number, next_day.day_fraction) == (2440588, 0.5)
    assert (previous_day.day_number, previous_day.day_fraction) == (2440586, 0.5)
    assert taiyin.JulianDate.from_timestamp(0.123456).seconds_difference(
        epoch
    ) == pytest.approx(0.123456, abs=1e-11)


def test_from_timestamp_preserves_large_integer_seconds() -> None:
    first = taiyin.JulianDate.from_timestamp(2**53 + 1)
    second = taiyin.JulianDate.from_timestamp(2**53 + 2)

    assert second.seconds_difference(first) == pytest.approx(1.0, abs=1e-11)

    minimum_day = taiyin.JulianDate.from_timestamp(
        (-(2**63) - 2440587) * 86400
    )
    assert (minimum_day.day_number, minimum_day.day_fraction) == (-(2**63), 0.5)


def test_from_timestamp_preserves_float_lower_boundary() -> None:
    minimum_whole_days = float(-(2**63))
    minimum = taiyin.JulianDate.from_timestamp(minimum_whole_days * 86400.0)

    assert (minimum.day_number, minimum.day_fraction) == (
        -(2**63) + 2440587,
        0.5,
    )


def test_from_datetime_uses_the_represented_instant() -> None:
    china_standard_time = timezone(timedelta(hours=8))
    local = datetime(2003, 3, 13, 14, 15, 0, 123456, tzinfo=china_standard_time)
    utc = datetime(2003, 3, 13, 6, 15, 0, 123456, tzinfo=timezone.utc)

    local_jd = taiyin.JulianDate.from_datetime(local)
    utc_jd = taiyin.JulianDate.from_datetime(utc)
    assert_same_julian_date(local_jd, utc_jd)
    assert abs(local_jd.seconds_difference(utc_jd)) < 1e-12


def test_from_datetime_preserves_microseconds_without_float_timestamp() -> None:
    value = datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)
    previous = value - timedelta(microseconds=1)

    difference = taiyin.JulianDate.from_datetime(value).seconds_difference(
        taiyin.JulianDate.from_datetime(previous)
    )
    assert difference == pytest.approx(1e-6, abs=1e-11)


@pytest.mark.parametrize(
    ("value", "utc_reference", "offset_seconds"),
    [
        (
            datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=14))),
            datetime(1, 1, 1, tzinfo=timezone.utc),
            -14 * 3600,
        ),
        (
            datetime(
                9999,
                12,
                31,
                23,
                59,
                59,
                999999,
                tzinfo=timezone(timedelta(hours=-14)),
            ),
            datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc),
            14 * 3600,
        ),
    ],
)
def test_from_datetime_handles_offset_instants_beyond_datetime_utc_range(
    value: datetime,
    utc_reference: datetime,
    offset_seconds: int,
) -> None:
    actual = taiyin.JulianDate.from_datetime(value)
    expected = taiyin.JulianDate.from_datetime(utc_reference).add_seconds(
        offset_seconds
    )

    assert actual.seconds_difference(expected) == pytest.approx(0.0, abs=1e-9)


def test_from_datetime_rejects_naive_values() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        taiyin.JulianDate.from_datetime(datetime(2003, 3, 13, 14, 15))


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_from_timestamp_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        taiyin.JulianDate.from_timestamp(value)


def test_from_timestamp_rejects_values_outside_split_jd_range() -> None:
    with pytest.raises(OverflowError, match="supported Julian-date range"):
        taiyin.JulianDate.from_timestamp(1e30)
