from concurrent.futures import ThreadPoolExecutor

import pytest
import taiyin
from taiyin_ziwei import (
    ZiweiGender as Gender, ZiweiChartMode as Mode, ZiweiBureau,
    ZiweiPlacementInput as Input, ZiweiPlacementPatch as Patch,
)


@pytest.fixture
def ctx():
    owner = taiyin.Ephemeris().create_context()
    value = owner.ziwei()
    yield value
    value.close()
    owner.close()


def digest(ctx, chart):
    s = chart.summary
    values = [s['bureau'], s['ziwei'], s['tianfu'], s['body_palace']]
    values += s['palace_branches'] + s['palace_stems']
    values += [s['life_master'], s['body_master']]
    values += [s['transforms'][key] for key in ('lu', 'quan', 'ke', 'ji')]
    values += [255 if chart.star_position(i) is None else chart.star_position(i)
               for i in range(ctx.star_count)]
    values += [chart.transform_mask(i) for i in range(ctx.star_count)]
    h = 0x811c9dc5
    for value in values:
        for byte in int(value).to_bytes(4, 'little'):
            h = ((h ^ byte) * 0x01000193) & 0xffffffff
    return h


@pytest.mark.parametrize('gender,mode,expected', [
    (Gender.male, Mode.tianPan, 3769082376),
    (Gender.male, Mode.diPan, 3769082376),
    (Gender.male, Mode.renPan, 1666642794),
    (Gender.female, Mode.tianPan, 962889352),
    (Gender.female, Mode.diPan, 962889352),
    (Gender.female, Mode.renPan, 1680750442),
])
def test_js_oracle_all_positions_and_transforms(ctx, gender, mode, expected):
    chart = ctx.casting_from_index(0, gender=gender, chart_mode=mode)
    assert digest(ctx, chart) == expected
    assert not hasattr(chart, 'set_flow')
    assert chart.summary['input'] == vars(Input())


def test_number_edit_reset_and_random(ctx):
    chart = ctx.casting_from_number('000123456', gender=Gender.male)
    assert chart.summary['index'] == 209225
    assert chart.summary['number'] == '123456'
    original = digest(ctx, chart)
    edited = chart.modify(Patch(month=3, day=30, hour_branch=2, update_bureau=True))
    shifted = edited.shift_life_palace(1)
    assert shifted.summary['input']['month'] == 3
    assert shifted.summary['index'] == 209225
    assert digest(ctx, shifted.reset()) == original
    assert digest(ctx, chart) == original
    for _ in range(12):
        draw = ctx.random_casting_chart(gender=Gender.female)
        i = draw.summary['index']
        assert 0 <= i < 259200
        assert digest(ctx, draw) == digest(ctx, ctx.casting_from_index(i, gender=Gender.female))
        assert draw.reset().summary['index'] == i


def test_manual_fixed_bureau_and_missing_inputs(ctx):
    for bureau in ZiweiBureau:
        chart = ctx.create_casting_chart(Input(year_branch=1), gender=Gender.male, fixed_bureau=bureau)
        assert chart.summary['bureau'] == bureau.value
        assert chart.summary['index'] is None
        assert chart.omitted_placements
        for missing in chart.omitted_placements:
            assert chart.star_position(missing['star_id']) is None
            assert missing['missing_inputs']
        assert chart.modify(Patch(day=15)).summary['bureau'] == bureau.value


@pytest.mark.parametrize('value', [-1, 259200, 2**40])
def test_invalid_index(ctx, value):
    with pytest.raises((ValueError, TypeError, OverflowError, RuntimeError)):
        ctx.casting_from_index(value, gender=Gender.male)


@pytest.mark.parametrize('value', ['', '-1', '1.5', '１２', '12\x0034'])
def test_invalid_number(ctx, value):
    with pytest.raises((ValueError, RuntimeError)):
        ctx.casting_from_number(value, gender=Gender.male)


def test_natal_edits_clear_flows_and_retain_birth(ctx):
    chart, _ = ctx.calculate_local(taiyin.AstroDateTime(2003, 3, 13, 14, 15), gender=Gender.male)
    before = [chart.star_position(i) for i in range(ctx.star_count)]
    edited = chart.modify(Patch(month=3, day=30, update_bureau=True)).shift_life_palace(-1)
    assert edited.flow_layer_count == 0
    assert edited.placement['input']['day'] == 30
    assert [edited.reset().star_position(i) for i in range(ctx.star_count)] == before
    target = taiyin.AstroDateTime(2026, 5, 1, 12)
    edited.set_flow(target.to_julian_date().add_seconds(-8*3600), target)
    assert edited.flow_layer_count > 0
    assert chart.flow_layer_count == 0


def test_parallel_immutable_edits(ctx):
    chart = ctx.casting_from_index(0, gender=Gender.male)
    def run(i):
        return digest(ctx, chart.modify(Patch(day=1+i%30)).shift_life_palace(i).reset())
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert set(pool.map(run, range(32))) == {3769082376}
    ctx.close()
    with pytest.raises(RuntimeError, match='closed'):
        chart.reset()


def test_narrowing_and_invalid_patch(ctx):
    chart = ctx.casting_from_index(0, gender=Gender.male)
    invalid_bool = Patch(update_bureau=7)  # pyright: ignore[reportArgumentType]
    for patch in (Patch(month=2**32+1), Patch(hour_branch=-1), invalid_bool):
        with pytest.raises((ValueError, TypeError)):
            chart.modify(patch)
    with pytest.raises((TypeError, OverflowError)):
        chart.shift_life_palace(2**40)


@pytest.mark.parametrize('kind', ['natal', 'casting'])
@pytest.mark.parametrize('update_bureau', [None, False, True])
def test_placement_overrides_preserve_python_optional_types(ctx, kind, update_bureau):
    if kind == 'natal':
        chart, _ = ctx.calculate_local(
            taiyin.AstroDateTime(2003, 3, 13, 14, 15), gender=Gender.male,
        )
    else:
        chart = ctx.casting_from_index(0, gender=Gender.male)

    def overrides(value):
        snapshot = value.placement if kind == 'natal' else value.summary
        return snapshot['overrides']

    empty = vars(Patch())
    assert overrides(chart) == empty
    patch = Patch(year_stem=0, hour_branch=0, day=15, update_bureau=update_bureau)
    edited = chart.modify(patch)
    result = overrides(edited)
    assert result == vars(patch)
    # Identity catches integer 0/1 masquerading as actual bool values.
    assert result['update_bureau'] is update_bureau
    for name in ('year_stem', 'hour_branch', 'day'):
        assert type(result[name]) is int
    assert result['year_branch'] is None
    assert result['month'] is None

    assert overrides(edited.modify(Patch()))['update_bureau'] is update_bureau
    toggled = edited.modify(Patch(update_bureau=True)).modify(Patch(update_bureau=False))
    assert overrides(toggled)['update_bureau'] is False
    assert overrides(toggled.modify(Patch()))['update_bureau'] is False
    if kind == 'casting':
        assert edited.summary['update_bureau'] is bool(update_bureau)
        assert toggled.summary['update_bureau'] is False
    assert overrides(edited.shift_life_palace(1)) == result
    assert overrides(edited.reset()) == empty
    assert overrides(chart) == empty
    # Returned dictionaries can be fed back into a public patch without
    # leaking native keep/inherit sentinels into validation.
    assert overrides(chart.modify(Patch(**result))) == result
