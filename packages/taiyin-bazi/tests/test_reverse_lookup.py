"""Reverse intervals are verified with the existing forward pillar engine."""
import math
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

import pytest
import taiyin
import taiyin_bazi as b

pytestmark = pytest.mark.skipif(
    not b._native.supports_reverse_lookup,
    reason="the pinned release core predates BaZi reverse lookup",
)


def jd(ctx, y, m, d, h=0, minute=0):
    return ctx.time.julian_day(taiyin.AstroDateTime(y, m, d, h, minute))[0]


def seconds(a, b):
    return b.seconds_difference(a)


def virtual(ctx, instant, clock):
    if clock.mode is b.BaziClockMode.fixedOffset:
        coordinate = instant.add_seconds(ctx.chinese_calendar.config.utcOffsetMinutes * 60)
    else:
        mean = taiyin.LocalMeanSolarTime.from_ut1(instant, longitudeRadians=clock.longitudeRadians)
        coordinate = (ctx.solar_time.mean_to_apparent(mean)[0].coordinate
                      if clock.mode is b.BaziClockMode.apparentSolar else mean.coordinate)
    return ctx.time.reverse_julian_day(coordinate)[0]


@pytest.mark.parametrize("mode", list(b.BaziClockMode))
@pytest.mark.parametrize("rat", list(taiyin.GanzhiRatHourMode))
def test_reverse_roundtrip_clocks_and_rat_modes(mode, rat):
    eph = taiyin.Ephemeris(load_packaged_data=True, load_builtin_eop=False)
    with eph.create_context() as ctx:
        baz = ctx.bazi()
        clock = b.BaziClock(mode, math.radians(118.582))
        for hour in (0, 11, 23):
            instant = jd(ctx, 2003, 3, 13, hour, 30).add_seconds(-28800)
            p = ctx.chinese_calendar.four_pillars(instant, virtual(ctx, instant, clock), rat_hour_mode=rat)[0]
            matches, flags = baz.reverse_lookup_at_ut1(p, instant.add_seconds(-86400),
                instant.add_seconds(86400), clock=clock, rat_hour_mode=rat)
            assert isinstance(flags, taiyin.ResultFlag)
            assert any(seconds(c.startUt1, instant) >= 0 and seconds(instant, c.endUt1) > 0 for c in matches)
            for c in matches:
                assert c.pillars == p
                for fraction in (0.01, 0.5, 0.99):
                    probe = c.startUt1.add_seconds(seconds(c.startUt1, c.endUt1) * fraction)
                    assert ctx.chinese_calendar.four_pillars(probe, virtual(ctx, probe, clock), rat_hour_mode=rat)[0] == p


def test_reverse_unified_zi_clipping_empty_validation_and_closed():
    eph = taiyin.Ephemeris()
    with eph.create_context() as ctx:
        baz = ctx.bazi()
        instant = jd(ctx, 2003, 3, 13, 23, 30).add_seconds(-28800)
        p = ctx.chinese_calendar.four_pillars(instant, taiyin.AstroDateTime(2003,3,13,23,30))[0]
        matches, _ = baz.reverse_lookup_at_ut1(p, instant.add_seconds(-86400), instant.add_seconds(86400))
        assert len(matches) == 1
        assert matches[0].startVirtualTime.hour == 23
        assert matches[0].endVirtualTime.hour == 1
        assert baz.reverse_lookup_at_ut1(p, instant, instant)[0] == ()
        clipped, _ = baz.reverse_lookup_at_ut1(p, instant, instant.add_seconds(100))
        assert seconds(clipped[0].startUt1, instant) == 0
        assert seconds(clipped[0].startUt1, clipped[0].endUt1) == pytest.approx(100)
        with pytest.raises(taiyin.InvalidArgumentError):
            baz.reverse_lookup_at_ut1(p, instant.add_seconds(1), instant)
        with pytest.raises(TypeError):
            baz.reverse_lookup_at_ut1(p, instant, instant, rat_hour_mode=cast(Any, 99))
        baz.close()
        with pytest.raises(RuntimeError):
            baz.reverse_lookup_at_ut1(p, instant, instant)


def test_reverse_contexts_can_run_concurrently():
    eph = taiyin.Ephemeris()
    with ExitStack() as stack:
        contexts = [stack.enter_context(eph.create_context(chinese_calendar_config=
                    taiyin.ChineseCalendarConfig.local_astronomical_utc_offset(offset)))
                    for offset in (0, 420, 480)]
        def calculate(ctx):
            instant = jd(ctx, 2003,3,13,14,15).add_seconds(-ctx.chinese_calendar.config.utcOffsetMinutes * 60)
            p = ctx.chinese_calendar.four_pillars(instant, taiyin.AstroDateTime(2003,3,13,14,15))[0]
            return ctx.bazi().reverse_lookup_at_ut1(p, instant.add_seconds(-86400), instant.add_seconds(86400))[0]
        serial = [calculate(ctx) for ctx in contexts]
        with ThreadPoolExecutor(max_workers=3) as pool:
            parallel = list(pool.map(calculate, contexts))
        assert [[(c.startUt1.day_number,c.startUt1.day_fraction) for c in x] for x in parallel] == [
            [(c.startUt1.day_number,c.startUt1.day_fraction) for c in x] for x in serial]


def test_reverse_solar_clock_keeps_the_physical_lichun_boundary():
    eph = taiyin.Ephemeris()
    with eph.create_context() as ctx:
        baz = ctx.bazi()
        term, _ = ctx.chinese_calendar.get_specific_jie_qi_ut(2026, 21)
        boundary = cast(Any, term.jdUt)
        clock = b.BaziClock(b.BaziClockMode.apparentSolar, 1.0)
        for side in (-30, 30):
            probe = boundary.add_seconds(side)
            p = ctx.chinese_calendar.four_pillars(probe, virtual(ctx, probe, clock))[0]
            matches, _ = baz.reverse_lookup_at_ut1(p, boundary.add_seconds(-60),
                                                  boundary.add_seconds(60), clock=clock)
            assert len(matches) == 1
            edge = matches[0].endUt1 if side < 0 else matches[0].startUt1
            assert abs(seconds(edge, boundary)) < 1e-5


def test_reverse_accepts_equivalent_noncanonical_split_dates():
    eph = taiyin.Ephemeris()
    with eph.create_context() as ctx:
        baz = ctx.bazi()
        instant = jd(ctx, 2003, 3, 13, 14, 15).add_seconds(-28800)
        p = ctx.chinese_calendar.four_pillars(instant, taiyin.AstroDateTime(2003,3,13,14,15))[0]
        start, end = instant.add_seconds(-86400), instant.add_seconds(86400)
        expected = baz.reverse_lookup_at_ut1(p, start, end)[0]
        equivalent_start = taiyin.JulianDate(start.day_number+1, start.day_fraction-1)
        equivalent_end = taiyin.JulianDate(end.day_number-1, end.day_fraction+1)
        actual = baz.reverse_lookup_at_ut1(p, equivalent_start, equivalent_end)[0]
        assert [(c.startUt1.day_number,c.startUt1.day_fraction,c.endUt1.day_number,c.endUt1.day_fraction)
                for c in actual] == [(c.startUt1.day_number,c.startUt1.day_fraction,c.endUt1.day_number,c.endUt1.day_fraction)
                                     for c in expected]


def test_reverse_uses_forward_root_equality_window():
    eph = taiyin.Ephemeris()
    with eph.create_context(chinese_calendar_config=
                            taiyin.ChineseCalendarConfig.china_standard_astronomical()) as ctx:
        baz = ctx.bazi()
        term, _ = ctx.chinese_calendar.get_specific_jie_qi_ut(2026, 21)
        root = cast(Any, term.jdUt)
        epsilon_seconds = 1e-10 * 86400
        start, end = root.add_seconds(-2*epsilon_seconds), root.add_seconds(0.5*epsilon_seconds)
        clock = b.BaziClock()
        for side in (-3, 3):
            probe = root.add_seconds(side*epsilon_seconds)
            pillars = ctx.chinese_calendar.four_pillars(probe, virtual(ctx, probe, clock))[0]
            matches, _ = baz.reverse_lookup_at_ut1(pillars, start, end)
            assert len(matches) == 1
            edge = matches[0].endUt1 if side < 0 else matches[0].startUt1
            assert abs(seconds(edge, root.add_seconds(-epsilon_seconds))) < epsilon_seconds/4


def test_reverse_uses_assigned_historical_midnight():
    eph = taiyin.Ephemeris()
    with eph.create_context() as ctx:
        baz = ctx.bazi()
        term, _ = ctx.chinese_calendar.get_specific_jie_qi_ut(500, 5)
        boundary = taiyin.JulianDate(term.civilDayNumber-1, 0.5-480/1440)
        assert seconds(boundary, term.jdUt) > 86400
        clock = b.BaziClock(b.BaziClockMode.meanSolar, 1.0)
        for side in (-30,30):
            probe = boundary.add_seconds(side)
            pillars = ctx.chinese_calendar.four_pillars(probe, virtual(ctx, probe, clock))[0]
            matches, flags = baz.reverse_lookup_at_ut1(pillars, boundary.add_seconds(-60),
                                                       boundary.add_seconds(60), clock=clock)
            assert flags & taiyin.ResultFlag.historicalPillarTermsApplied
            assert len(matches) == 1
            edge = matches[0].endUt1 if side < 0 else matches[0].startUt1
            assert seconds(edge, boundary) == 0
