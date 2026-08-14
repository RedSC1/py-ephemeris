import pytest
import taiyin
import taiyin_bazi
import os
from pathlib import Path


def test_bazi_pure_rules_are_created_from_ephemeris():
    eph=taiyin.Ephemeris(load_packaged_data=False,load_builtin_eop=False)
    bazi=eph.create_context().bazi()
    assert bazi.get_kong_wang(taiyin.Ganzhi(0,0))==(taiyin.EarthlyBranch.xu,taiyin.EarthlyBranch.hai)
    assert bazi.get_ten_god(0,3) is taiyin_bazi.BaziTenGod.shangGuan
    stems,count=bazi.get_hidden_stems(4)
    assert count==len(stems) and all(0<=stem<=9 for stem in stems)
    stem=bazi.calc_stem_relation(0,5)
    assert taiyin_bazi.BaziStemRelationFlags.combination in stem.flags
    assert stem.combinedElementId is taiyin.GanzhiWuxing.earth
    branch=bazi.calc_branch_relation(0,1)
    assert taiyin_bazi.BaziBranchRelationFlags.combination in branch.flags
    assert bazi.calc_liunian(2024)==taiyin.Ganzhi(0,4)
    assert bazi.calc_liuri(taiyin.AstroDateTime(2024,2,10))==taiyin.Ganzhi(0,4)
    assert bazi.calc_liushi(taiyin.Ganzhi(0,4),0)==taiyin.Ganzhi(0,0)
    assert 0<=bazi.get_life_stage(0,0)<=11
    bazi.close()
    with pytest.raises(RuntimeError): bazi.calc_liunian(2025)


def test_bazi_calendar_utc_offset_is_configurable():
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    calendar_config = taiyin.ChineseCalendarConfig.historical_china(-5 * 60)
    context = eph.create_context(chinese_calendar_config=calendar_config)
    bazi = context.bazi()
    assert bazi.chinese_calendar.config is calendar_config
    assert bazi.chinese_calendar.config.utcOffsetMinutes == -5 * 60
    bazi.close()


def test_bazi_reuses_owning_context_calendar():
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    context = eph.create_context()
    bazi = context.bazi()
    assert bazi.chinese_calendar is context.chinese_calendar
    bazi.close()


def _bazi_chart_with_data():
    source_root = os.environ.get("TAIYIN_SOURCE_DIR")
    if source_root is None:
        pytest.skip("set TAIYIN_SOURCE_DIR to run BaZi integration tests")
    source_path = (
        Path(source_root)
        / "data"
        / "ephemerides"
        / "opm2"
        / "major-bodies"
        / "600y"
    )
    eph = taiyin.Ephemeris(
        source_paths=[str(source_path)],
        load_packaged_data=False,
        load_builtin_eop=False,
    )
    birth = taiyin.AstroDateTime(2024, 2, 10, 12)
    instant = birth.to_julian_date().add_seconds(-8 * 3600)
    context = eph.create_context()
    bazi = context.bazi()
    pillars = bazi.chinese_calendar.four_pillars(instant, birth)
    return eph, bazi, instant, birth, bazi.calc_chart(pillars)


def test_bazi_chart_xiaoyun_relations_and_shen_sha():
    eph, bazi, instant, birth, chart = _bazi_chart_with_data()
    assert chart.yearPillar == taiyin.Ganzhi(0, 4)
    assert len(chart.hiddenStems) == 4
    assert len(chart.hiddenTenGods) == 4
    assert len(chart.visibleTenGods) == 4
    assert len(chart.lifeStages) == 4
    assert len(chart.nayinIds) == 4

    first = bazi.calc_xiaoyun(chart, 1, 1)
    entries = bazi.fill_xiaoyun(chart, 1, 1, 5)
    assert len(entries) == 5
    assert entries[0].ganzhi == first
    assert tuple(item.age for item in entries) == (1, 2, 3, 4, 5)

    relations = bazi.collect_chart_relations(chart)
    assert relations
    assert all(item.pillarMask for item in relations)
    shen_sha = bazi.collect_target_shen_sha(
        chart,
        chart.yearPillar,
        taiyin_bazi.BaziShenShaTargetKind.year,
        taiyin_bazi.BaziGender.male,
    )
    assert all(isinstance(item, taiyin_bazi.BaziShenShaId) for item in shen_sha)
    bazi.close()


@pytest.mark.parametrize(
    "gender,expected_direction",
    [
        (taiyin_bazi.BaziGender.male, 1),
        (taiyin_bazi.BaziGender.female, -1),
    ],
)
def test_bazi_qiyun_dayun_and_renyuan_use_ephemeris_data(
    gender, expected_direction
):
    eph, bazi, instant, birth, chart = _bazi_chart_with_data()
    qiyun = bazi.calc_qiyun(instant, birth, chart, gender)
    assert bazi._owner.last_status == 0
    assert qiyun.direction == expected_direction
    assert qiyun.startAgeYears > 0
    dayun = bazi.fill_dayun(birth, chart, qiyun, 5)
    assert len(dayun) == 5
    assert tuple(item.index for item in dayun) == (1, 2, 3, 4, 5)

    renyuan = bazi.calc_renyuan_siling(
        instant,
        chart,
        taiyin_bazi.BaziRenyuanSilingTableModel.common,
        taiyin_bazi.BaziRenyuanSilingTimeModel.elapsed24Hours,
    )
    assert bazi._owner.last_status == 0
    assert 0 <= renyuan.stemId <= 9
    segments = bazi.get_renyuan_siling_segments(
        chart.monthPillar.branch_id,
        taiyin_bazi.BaziRenyuanSilingTableModel.common,
    )
    assert 1 <= len(segments) <= 3
    assert segments[0].startDay == 0.0
    bazi.close()


@pytest.mark.parametrize(
    "gender,expected_direction",
    [
        (taiyin_bazi.BaziGender.male, 1),
        (taiyin_bazi.BaziGender.female, -1),
    ],
)
def test_bazi_calculate_is_complete_high_level_entrypoint(
    gender, expected_direction
):
    eph, bazi, instant, birth, expected_chart = _bazi_chart_with_data()
    result = bazi.calculate_instant(instant, gender=gender)
    assert isinstance(result, taiyin_bazi.BaziResult)
    assert result.chart == expected_chart
    assert result.qiyun.direction == expected_direction
    assert result.qiyun.startAgeYears > 0
    assert result.localTime.year == birth.year
    assert result.localTime.month == birth.month
    assert result.localTime.day == birth.day
    assert result.localTime.hour == birth.hour

    local_result = bazi.calculate_local(birth, gender=gender)
    assert abs(
        local_result.instantUtc.seconds_difference(instant)
    ) < 1e-6
    assert local_result.chart == result.chart
