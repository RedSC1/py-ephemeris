import taiyin
import taiyin_ziwei
import pytest


def _chart():
    eph = taiyin.Ephemeris()
    context = eph.create_context()
    ziwei = context.ziwei()
    local = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
    instant = local.to_julian_date().add_seconds(-8 * 3600)
    chart, _ = ziwei.create_chart(
        instant, local, gender=taiyin_ziwei.ZiweiGender.male
    )
    return ziwei, chart


def test_default_catalog_produces_a_chart():
    ziwei, chart = _chart()

    assert ziwei.star_count == 159
    assert len(chart.anchors) == 31
    assert chart.summary.bureauId == 1

    star = ziwei.find_star("ziwei")
    assert star is not None
    assert chart.star_position(star) == 4
    assert chart.star_palace(star) is not None
    assert chart.brightness(star) is taiyin_ziwei.ZiweiBrightness.de


def test_ziwei_accepts_an_owned_custom_calendar_only():
    eph = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False)
    context = eph.create_context()
    calendar = context.create_chinese_calendar(
        taiyin.ChineseCalendarConfig.local_astronomical_utc_offset(0)
    )
    ziwei = context.ziwei(calendar=calendar)
    assert ziwei.chinese_calendar is calendar

    foreign_calendar = eph.create_context().create_chinese_calendar()
    with pytest.raises(ValueError, match="belong"):
        context.ziwei(calendar=foreign_calendar)


def test_birth_options_match_the_core_lunar_boundary_defaults():
    options = taiyin_ziwei.ZiweiBirthOptions()
    assert options.wuHuDunYearBoundary is taiyin_ziwei.ZiweiPillarBoundary.lunar
    assert options.sihuaYearBoundary is taiyin_ziwei.ZiweiPillarBoundary.lunar
    assert options.bodyMasterYearBoundary is taiyin_ziwei.ZiweiPillarBoundary.lunar


def test_named_anchors_and_palaces_expose_semantic_chart_view():
    ziwei, chart = _chart()
    anchors = chart.anchors

    assert anchors[taiyin_ziwei.ZiweiAnchorSlot.ziwei] == 4
    assert anchors.ziwei == 4
    assert anchors.bureau is taiyin_ziwei.ZiweiBureau.wood3
    assert chart.summary.bureau is taiyin_ziwei.ZiweiBureau.wood3

    life = chart.palace(taiyin_ziwei.ZiweiPalace.life)
    assert life.branchId == anchors.palace_position(taiyin_ziwei.ZiweiPalace.life)
    assert life.stemId == chart.summary.palaceStems[life.branchId]
    assert len(chart.palaces) == 12
    assert chart.palaces[taiyin_ziwei.ZiweiPalace.life.value] == life
    assert ziwei.find_star("lianzhen") in life.stars


def test_chart_exposes_palace_stars_and_transform_overlay():
    ziwei, chart = _chart()
    star = ziwei.find_star("lianzhen")
    assert star is not None

    life_palace = chart.anchors[19]
    assert star in chart.palace_stars(life_palace)
    assert chart.transform_mask(star) != 0


def test_catalog_selection_context_reuses_loaded_resources():
    catalog = taiyin_ziwei.ZiweiDataCatalog()
    first_generation = catalog.generation
    selection = taiyin_ziwei.ZiweiOptionSelection(placementDefault="option1")
    eph = taiyin.Ephemeris()
    ziwei = eph.create_context().ziwei(catalog, selection)

    assert ziwei.generation == first_generation
    assert ziwei.find_star("ziwei").key == "ziwei"


def test_longevity_option_is_independent_and_changes_earth_bureau_only():
    eph = taiyin.Ephemeris()
    catalog = taiyin_ziwei.ZiweiDataCatalog()
    birth = taiyin.AstroDateTime(2003, 9, 26, 12)

    water_context = eph.create_context().ziwei(catalog)
    fire_context = eph.create_context().ziwei(
        catalog, taiyin_ziwei.ZiweiOptionSelection(longevity="option2")
    )
    water_earth, _ = water_context.calculate_local(
        birth, gender=taiyin_ziwei.ZiweiGender.male
    )
    fire_earth, _ = fire_context.calculate_local(
        birth, gender=taiyin_ziwei.ZiweiGender.male
    )

    changsheng = water_context.find_star("changsheng")
    ziwei = water_context.find_star("ziwei")
    assert changsheng is not None
    assert ziwei is not None
    assert water_earth.summary.bureau is taiyin_ziwei.ZiweiBureau.earth5
    assert fire_earth.summary.bureau is taiyin_ziwei.ZiweiBureau.earth5
    assert water_earth.star_position(changsheng) == 8  # Shen
    assert fire_earth.star_position(changsheng) == 2  # Yin
    assert water_earth.star_position(ziwei) == fire_earth.star_position(ziwei)


def test_catalog_reload_keeps_existing_context_snapshot_usable():
    catalog = taiyin_ziwei.ZiweiDataCatalog()
    eph = taiyin.Ephemeris()
    first = eph.create_context().ziwei(catalog)
    old_generation = first.generation
    catalog.reload()
    second = eph.create_context().ziwei(catalog)

    assert first.generation == old_generation
    assert second.generation > old_generation
    assert first.find_star("ziwei").key == "ziwei"
    assert second.find_star("ziwei").key == "ziwei"


def test_complete_flow_stack_uses_base_calendar_context():
    ziwei, chart = _chart()
    target_local = taiyin.AstroDateTime(2025, 3, 13, 14, 15)
    target = target_local.to_julian_date().add_seconds(-8 * 3600)

    result, result_flags = chart.set_flow(target, target_local)

    assert result_flags == taiyin.ResultFlag.none
    assert chart.flow_layer_count == 5
    assert result.decade.startYear == 2025
    assert chart.flow_layer_summary(taiyin_ziwei.ZiweiFlowLevel.year)["level"] == 1
    assert chart.flow_star_position(
        taiyin_ziwei.ZiweiFlowLevel.year, ziwei.find_star("flow_lucun")
    ) is not None


def test_lunar_flow_uses_calendar_month_building_for_leap_eleven():
    ziwei, chart = _chart()
    # 2033 has a leap eleventh month.  Both regular and leap 11 retain the Zi
    # month building; inferring it from a simple ordinal would incorrectly
    # advance the leap month to Chou.
    target_local = taiyin.AstroDateTime(2033, 12, 22, 12)
    target = target_local.to_julian_date().add_seconds(-8 * 3600)

    resolution, resolution_flags = chart.set_flow(target, target_local)

    assert resolution_flags == taiyin.ResultFlag.none
    assert (
        resolution.targetMonth,
        resolution.targetEffectiveMonth,
        resolution.targetMonthSequence,
        resolution.targetMonthIsLeap,
        resolution.targetMonthBuildingBranch,
        resolution.targetPalaceMonthIndex,
    ) == (11, 11, 12, True, 0, 12)

    effective_resolution, _ = chart.set_flow(
        target, target_local,
        options=taiyin_ziwei.ZiweiFlowOptions(
            flowMonthPalaceStrategy=(
                taiyin_ziwei.ZiweiFlowMonthPalaceStrategy.effectiveMonth
            )
        ),
    )
    assert effective_resolution.targetPalaceMonthIndex == 11

    # The normal twelfth month after that early leap month is the thirteenth
    # physical month of lunar year 2033.  It is not the synthetic leap-twelfth
    # fallback reserved for historical fourteenth-month reform years.
    regular_twelfth_local = taiyin.AstroDateTime(2034, 1, 20, 12)
    regular_twelfth = regular_twelfth_local.to_julian_date().add_seconds(-8 * 3600)
    resolution, _ = chart.set_flow(
        regular_twelfth, regular_twelfth_local
    )

    assert (
        resolution.targetMonth,
        resolution.targetEffectiveMonth,
        resolution.targetMonthSequence,
        resolution.targetMonthIsLeap,
        resolution.targetMonthBuildingBranch,
        resolution.targetPalaceMonthIndex,
    ) == (12, 12, 13, False, 1, 13)


def test_lunar_flow_uses_calendar_month_building_for_historical_reforms():
    eph = taiyin.Ephemeris()
    ziwei = eph.create_context(
        chinese_calendar_config=taiyin.ChineseCalendarConfig.historical_china()
    ).ziwei()
    birth = taiyin.AstroDateTime(1, 1, 1, 12)
    chart, _ = ziwei.calculate_local(
        birth, gender=taiyin_ziwei.ZiweiGender.male
    )
    # Xin's alternate written twelfth month is physically Jian-Zi.  Its
    # written month number must not be used as the month-building branch.
    target_local = taiyin.AstroDateTime(23, 12, 2, 12)
    target = target_local.to_julian_date().add_seconds(-8 * 3600)

    resolution, resolution_flags = chart.set_flow(target, target_local)

    assert resolution_flags & taiyin.ResultFlag.historicalCalendarRulesApplied
    assert (
        resolution.effectiveTargetYear,
        resolution.targetMonth,
        resolution.targetMonthBuildingBranch,
    ) == (23, 12, 0)


def test_flow_target_navigation_preserves_split_rat_transitions():
    eph = taiyin.Ephemeris()
    ziwei = eph.create_context().ziwei()
    clock = taiyin.AstroDateTime(2024, 5, 20, 22, 30)
    instant = clock.to_julian_date().add_seconds(-8 * 3600)

    late = ziwei.next_flow_hour_target(
        instant, clock, rat_hour_mode=taiyin.GanzhiRatHourMode.todayGan
    )
    assert (late.virtualTime.day, late.virtualTime.hour, late.virtualTime.minute) == (20, 23, 30)
    assert late.ratHourSegment is taiyin_ziwei.ZiweiRatHourSegment.late

    early = ziwei.next_flow_hour_target(
        late.instantUtc, late.virtualTime, rat_hour_mode=taiyin.GanzhiRatHourMode.todayGan
    )
    assert (early.virtualTime.day, early.virtualTime.hour, early.virtualTime.minute) == (21, 0, 30)
    assert early.ratHourSegment is taiyin_ziwei.ZiweiRatHourSegment.early

    chou = ziwei.next_flow_hour_target(
        early.instantUtc, early.virtualTime, rat_hour_mode=taiyin.GanzhiRatHourMode.todayGan
    )
    assert (chou.virtualTime.day, chou.virtualTime.hour, chou.virtualTime.minute) == (21, 2, 0)
    returned = ziwei.previous_flow_hour_target(
        chou.instantUtc, chou.virtualTime, rat_hour_mode=taiyin.GanzhiRatHourMode.todayGan
    )
    assert (
        returned.virtualTime.year, returned.virtualTime.month, returned.virtualTime.day,
        returned.virtualTime.hour, returned.virtualTime.minute, returned.virtualTime.second,
    ) == (
        early.virtualTime.year, early.virtualTime.month, early.virtualTime.day,
        early.virtualTime.hour, early.virtualTime.minute, early.virtualTime.second,
    )
    assert returned.instantUtc.seconds_difference(early.instantUtc) == 0.0

    next_day = ziwei.next_flow_day_target(instant, clock)
    assert (next_day.virtualTime.day, next_day.virtualTime.hour, next_day.virtualTime.minute) == (21, 22, 30)
    assert next_day.instantUtc.seconds_difference(instant) == 86400.0


def test_tier1_reverse_lookup_matches_a_forward_chart_slot():
    ziwei, chart = _chart()
    local = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
    instant = local.to_julian_date().add_seconds(-8 * 3600)
    query = taiyin_ziwei.ZiweiTier1ReverseQuery(
        lucunBranch=chart.star_position(ziwei.find_star("lucun")),
        hongluanBranch=chart.star_position(ziwei.find_star("hongluan")),
        wenchangBranch=chart.star_position(ziwei.find_star("wenchang")),
        santaiBranch=chart.star_position(ziwei.find_star("santai")),
        ziweiBranch=chart.star_position(ziwei.find_star("ziwei")),
    )

    candidates, candidate_flags = ziwei.reverse_lookup_tier1(
        instant, instant, local, gender=taiyin_ziwei.ZiweiGender.male, query=query
    )
    assert candidate_flags == taiyin.ResultFlag.none
    assert len(candidates) == 1
    assert candidates[0].instantUtc == instant
    assert candidates[0].virtualTime == local
    assert candidates[0].hourBranch == 7


def test_tier1_reverse_lookup_requires_a_real_constraint():
    ziwei, _ = _chart()
    local = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
    instant = local.to_julian_date().add_seconds(-8 * 3600)

    try:
        ziwei.reverse_lookup_tier1(
            instant, instant, local, gender=taiyin_ziwei.ZiweiGender.male,
            query=taiyin_ziwei.ZiweiTier1ReverseQuery(),
        )
    except ValueError as error:
        assert "at least one" in str(error)
    else:
        raise AssertionError("an empty reverse query must be rejected")


def test_all_rat_hour_modes_and_historical_calendar_boundary_are_chartable():
    eph = taiyin.Ephemeris()
    modern = eph.create_context().ziwei()
    local = taiyin.AstroDateTime(2024, 5, 20, 23, 30)
    instant = local.to_julian_date().add_seconds(-8 * 3600)
    for mode in taiyin.GanzhiRatHourMode:
        chart, _ = modern.create_chart(
            instant, local, gender=taiyin_ziwei.ZiweiGender.male,
            options=taiyin_ziwei.ZiweiBirthOptions(ratHourMode=mode),
        )
        assert len(chart.anchors) == 31

    historical_context = eph.create_context(
        chinese_calendar_config=taiyin.ChineseCalendarConfig.historical_china()
    )
    historical = historical_context.ziwei()
    ancient_local = taiyin.AstroDateTime(237, 4, 11, 12)
    ancient_instant = ancient_local.to_julian_date().add_seconds(-8 * 3600)
    ancient_chart, _ = historical.calculate_local(
        ancient_local, gender=taiyin_ziwei.ZiweiGender.male
    )

    assert len(ancient_chart.anchors) == 31
    historical_lunar, _ = historical.chinese_calendar.from_instant_ut(
        ancient_instant
    )
    assert (historical_lunar.year, historical_lunar.month, historical_lunar.day) == (237, 2, 28)
