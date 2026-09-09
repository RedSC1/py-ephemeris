import math

import pytest
import taiyin
import taiyin_ziwei as zw


@pytest.fixture
def ziwei():
    eph = taiyin.Ephemeris()
    ctx = eph.create_context()
    yield ctx.ziwei()
    ctx.close()


@pytest.mark.parametrize("mode", list(zw.ZiweiClockMode))
def test_clock_roundtrip_navigation_and_flow(ziwei, mode):
    clock = zw.ZiweiClock(mode, math.radians(118.582))
    wall = taiyin.AstroDateTime(2003, 3, 13, 22)
    instant, _ = ziwei.chart_time_to_ut1(wall, clock=clock)
    mapped, _ = ziwei.chart_time_from_ut1(instant, clock=clock)
    assert (mapped.year, mapped.month, mapped.day, mapped.hour, mapped.minute) == (2003, 3, 13, 22, 0)
    assert abs(mapped.second) < 1e-4
    chart, _ = ziwei.create_chart_at_ut1(instant, clock=clock, gender=zw.ZiweiGender.male)
    assert chart.summary.bureauId in range(5)
    for rat in taiyin.GanzhiRatHourMode:
        target, _ = ziwei.step_flow_hour_at_ut1(instant, clock=clock, rat_hour_mode=rat)
        expected = 0 if rat is taiyin.GanzhiRatHourMode.noSplit else 23
        assert target.virtualTime.hour == expected
        assert target.virtualTime.minute == 0
        again, _ = ziwei.chart_time_from_ut1(target.instantUt1, clock=clock)
        assert again.hour == expected
        result, _ = chart.set_flow_at_ut1(target.instantUt1, clock=clock,
            options=zw.ZiweiFlowOptions(ratHourMode=rat))
        assert result.targetHourIndex == 0
    tomorrow, _ = ziwei.step_flow_day_at_ut1(instant, clock=clock)
    assert (tomorrow.virtualTime.day, tomorrow.virtualTime.hour) == (14, 22)
    if mode is zw.ZiweiClockMode.apparentSolar:
        assert abs(tomorrow.instantUt1.seconds_difference(instant) - 86400) > 0.01


@pytest.mark.parametrize("mode", list(zw.ZiweiClockMode))
def test_reverse_actual_hour_start(ziwei, mode):
    clock = zw.ZiweiClock(mode, math.radians(118.582))
    instant, _ = ziwei.chart_time_to_ut1(taiyin.AstroDateTime(2003, 3, 13, 14, 15), clock=clock)
    chart, _ = ziwei.create_chart_at_ut1(instant, gender=zw.ZiweiGender.male, clock=clock)
    start, _ = ziwei.chart_time_to_ut1(taiyin.AstroDateTime(2003, 3, 13, 12), clock=clock)
    end, _ = ziwei.chart_time_to_ut1(taiyin.AstroDateTime(2003, 3, 13, 15), clock=clock)
    candidates, _ = ziwei.reverse_lookup_tier1_at_ut1(start, end,
        gender=zw.ZiweiGender.male, clock=clock,
        query=zw.ZiweiTier1ReverseQuery(ziweiBranch=chart.star_position(ziwei.find_star("ziwei"))))
    candidate = next(c for c in candidates if c.virtualTime.hour == 13)
    expected, _ = ziwei.chart_time_to_ut1(taiyin.AstroDateTime(2003, 3, 13, 13), clock=clock)
    assert abs(candidate.instantUt1.seconds_difference(expected)) < 1e-4


def test_invalid_clock_and_closed_context(ziwei):
    with pytest.raises(ValueError):
        zw.ZiweiClock(zw.ZiweiClockMode.meanSolar, float("nan"))
    with pytest.raises(TypeError):
        zw.ZiweiClock(99)  # pyright: ignore[reportArgumentType]
    wall = taiyin.AstroDateTime(2003, 3, 13)
    ziwei.chart_time_to_ut1(wall, clock=zw.ZiweiClock(longitudeRadians=float("nan")))
    ziwei.close()
    with pytest.raises(RuntimeError):
        ziwei.chart_time_to_ut1(wall)


@pytest.mark.parametrize("rat", list(taiyin.GanzhiRatHourMode))
def test_jie_is_mapped_at_its_own_instant(ziwei, rat):
    # Put the previous Jie just after apparent-solar midnight, where using
    # today's equation of time for the Jie would change the day count.
    start = taiyin.AstroDateTime(2026, 9, 1, 12).to_julian_date()
    jie, _ = ziwei.chinese_calendar._native_context._next_pillar_jie(start)
    greenwich, _ = ziwei.chart_time_from_ut1(jie,
        clock=zw.ZiweiClock(zw.ZiweiClockMode.apparentSolar, 0))
    seconds = greenwich.hour * 3600 + greenwich.minute * 60 + greenwich.second
    longitude = (1 - seconds) / 86400 * 2 * math.pi
    if longitude < -math.pi:
        longitude += 2 * math.pi
    clock = zw.ZiweiClock(zw.ZiweiClockMode.apparentSolar, longitude)
    target = jie.add_seconds(10 * 86400)
    wall, _ = ziwei.chart_time_from_ut1(target, clock=clock)
    term_wall, _ = ziwei.chart_time_from_ut1(jie, clock=clock)
    def day(t):
        return zw.taiyin_day_number(t) + int(rat is taiyin.GanzhiRatHourMode.noSplit and t.hour >= 23)
    expected = day(wall) - day(term_wall) + 1
    chart, _ = ziwei.create_chart_at_ut1(target, clock=clock, gender=zw.ZiweiGender.male,
        options=zw.ZiweiBirthOptions(ratHourMode=rat))
    flow, _ = chart.set_flow_at_ut1(target, clock=clock,
        options=zw.ZiweiFlowOptions(boundary=zw.ZiweiPillarBoundary.solarTerm, ratHourMode=rat))
    assert flow.targetDay == expected


def test_solar_month_policy_does_not_change_with_lunar_palace_option(ziwei):
    instant, _ = ziwei.chart_time_to_ut1(taiyin.AstroDateTime(2003, 3, 13, 14, 15))
    chart, _ = ziwei.create_chart_at_ut1(instant, gender=zw.ZiweiGender.male)
    results = []
    for strategy in zw.ZiweiFlowMonthPalaceStrategy:
        flow, _ = chart.set_flow_at_ut1(instant,
            options=zw.ZiweiFlowOptions(boundary=zw.ZiweiPillarBoundary.solarTerm,
                flowMonthPalaceStrategy=strategy))
        results.append((flow, chart.flow_layer_summary(zw.ZiweiFlowLevel.month)))
    assert results[0] == results[1]


@pytest.mark.parametrize("year,month,day,expected", [
    (1984, 2, 29, (1984, 3, 1)), (2026, 12, 31, (2027, 1, 1)),
    (1582, 10, 4, (1582, 10, 15)),
])
def test_integer_midnight_carry(ziwei, year, month, day, expected):
    instant, _ = ziwei.chart_time_to_ut1(taiyin.AstroDateTime(year, month, day, 23))
    target, _ = ziwei.step_flow_hour_at_ut1(instant, rat_hour_mode=taiyin.GanzhiRatHourMode.todayGan)
    t = target.virtualTime
    assert (t.year, t.month, t.day) == expected
    assert (t.hour, t.minute) == (0, 0)
