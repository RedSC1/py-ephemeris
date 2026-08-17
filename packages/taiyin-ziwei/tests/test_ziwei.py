import taiyin
import taiyin_ziwei


def _chart():
    eph = taiyin.Ephemeris()
    context = eph.create_context()
    ziwei = context.ziwei()
    local = taiyin.AstroDateTime(2003, 3, 13, 14, 15)
    instant = local.to_julian_date().add_seconds(-8 * 3600)
    return ziwei, ziwei.create_chart(
        instant, local, gender=taiyin_ziwei.ZiweiGender.male
    )


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


def test_complete_flow_stack_uses_base_calendar_context():
    ziwei, chart = _chart()
    target_local = taiyin.AstroDateTime(2025, 3, 13, 14, 15)
    target = target_local.to_julian_date().add_seconds(-8 * 3600)

    result = chart.set_flow(target, target_local)

    assert chart.flow_layer_count == 5
    assert result.decade.startYear == 2025
    assert chart.flow_layer_summary(taiyin_ziwei.ZiweiFlowLevel.year)["level"] == 1
    assert chart.flow_star_position(
        taiyin_ziwei.ZiweiFlowLevel.year, ziwei.find_star("flow_lucun")
    ) is not None
