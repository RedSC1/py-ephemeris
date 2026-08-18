"""Portable copies of the lightweight C++ Dart-oracle corpus tests.

The records are generated from the author's MIT-licensed ``ziwei_core 0.13.0``
default-rule oracle and are intentionally only 23 natal/flow cases.  The much
larger 520,000-chart differential sweep remains a manual C++ slow test rather
than a Python CI requirement.
"""

# pyright: reportMissingImports=false

from __future__ import annotations

import csv
from pathlib import Path

import taiyin
import taiyin_ziwei
from taiyin_ziwei import _ziwei_native


_DATA = Path(__file__).parent / "data"
_INSTANT = taiyin.JulianDate.from_double(2451545.0)
_CLOCK = taiyin.AstroDateTime(2000, 1, 1, 12)
_NATAL_STAR_COUNT = 115


def _rows(filename: str, expected_columns: int) -> tuple[tuple[int, ...], ...]:
    with (_DATA / filename).open(newline="") as source:
        result = tuple(
            tuple(int(value) for value in row)
            for row in csv.reader(line for line in source if not line.startswith("#"))
            if row
        )
    assert all(len(row) == expected_columns for row in result)
    assert len(result) == 23
    return result


def _packed(stem: int, branch: int) -> int:
    return (stem << 4) | branch


def _birth_facts(values: tuple[int, ...]) -> dict:
    return {
        "lunar_year": values[1],
        "lunar_month": values[2],
        "lunar_day": values[3],
        "lunar_is_leap": bool(values[4]),
        "lunar_month_name": 0,
        "effective_lunar_year": values[5],
        "effective_lunar_month": values[6],
        "solar_pillars": [
            _packed(values[index], values[index + 1])
            for index in range(8, 16, 2)
        ],
        "lunar_pillars": [
            _packed(values[index], values[index + 1])
            for index in range(16, 24, 2)
        ],
        "solar_day_from_previous_jie": values[7],
        "lunar_month_sequence": values[6],
    }


def _target_facts(values: tuple[int, ...]) -> dict:
    # C++ ``test_limit_oracle`` calls individual limit primitives.  The Python
    # facade instead exposes the complete stack, so build the smallest valid
    # target facts that encode exactly the oracle's target coordinates.
    day_stem = values[19]
    hour_branch = values[22]
    hour_stem = values[23]
    return {
        "lunar_year": values[2],
        "lunar_month": values[13],
        "lunar_day": values[18],
        "lunar_is_leap": bool(values[15]),
        "lunar_month_name": 0,
        "solar_pillars": [
            _packed(0, 0), _packed(0, 0),
            _packed(day_stem, day_stem & 1),
            _packed(hour_stem, hour_branch),
        ],
        "solar_day_from_previous_jie": 1,
        "lunar_month_sequence": values[14],
    }


def _native_context():
    catalog = taiyin_ziwei.ZiweiDataCatalog()
    context = _ziwei_native.NativeZiweiContext(
        catalog._native._core_context_capsule(),
        taiyin_ziwei.ZiweiOptionSelection()._native_value(),
    )
    return catalog, context


def _native_chart(context, values: tuple[int, ...]):
    return context.create_chart(_birth_facts(values), _INSTANT, _CLOCK, values[0])


def test_dart_natal_oracle_corpus_matches_all_23_records():
    natal_rows = _rows("ziwei_core_0_13_0_natal.csv", 142)
    _, context = _native_context()
    assert context.star_count == 159

    for record, values in enumerate(natal_rows):
        chart = _native_chart(context, values)
        anchors = chart.anchors()
        summary = chart.summary()
        assert anchors[19] == values[24], record
        assert summary["body_palace"] == values[25], record
        assert summary["bureau"] == values[26], record
        for star_id, expected in enumerate(values[27:27 + _NATAL_STAR_COUNT]):
            assert chart.star_position(star_id) == expected, (record, star_id)
        for star_id in range(_NATAL_STAR_COUNT, context.star_count):
            assert chart.star_position(star_id) == -1, (record, star_id)


def test_dart_flow_limit_oracle_corpus_matches_all_23_records():
    natal_rows = _rows("ziwei_core_0_13_0_natal.csv", 142)
    limit_rows = _rows("ziwei_core_0_13_0_limits.csv", 25)
    _, context = _native_context()

    for record, (natal, expected) in enumerate(zip(natal_rows, limit_rows)):
        assert expected[0] == record
        chart = _native_chart(context, natal)
        resolution = chart.set_flow(
            _target_facts(expected), _INSTANT, _CLOCK,
            boundary=taiyin_ziwei.ZiweiPillarBoundary.lunar.value,
            deepest_level=taiyin_ziwei.ZiweiFlowLevel.hour.value,
        )
        assert resolution["effective_birth_year"] == expected[1], record
        assert resolution["effective_target_year"] == expected[2], record
        assert resolution["target_month"] == expected[13], record
        assert resolution["target_month_sequence"] == expected[14], record
        assert resolution["target_month_is_leap"] == bool(expected[15]), record
        assert resolution["target_day"] == expected[18], record
        assert resolution["target_hour_index"] == expected[22], record
        assert resolution["decade"]["index"] == expected[3], record
        assert resolution["decade"]["start_age"] == expected[4], record
        assert resolution["decade"]["end_age"] == expected[5], record
        assert resolution["small_limit"]["virtual_age"] == expected[8], record
        assert resolution["small_limit"]["stem"] == expected[9], record
        assert resolution["small_limit"]["branch"] == expected[10], record

        expected_coordinates = (
            (expected[6], expected[7]),
            (expected[11], expected[12]),
            (expected[16], expected[17]),
            (expected[20], expected[21]),
            (expected[23], expected[24]),
        )
        for level, coordinate in enumerate(expected_coordinates):
            summary = chart.flow_layer_summary(level)
            assert (summary["coordinate_stem"], summary["coordinate_branch"]) == coordinate, (
                record, level,
            )
