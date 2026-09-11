import gc
import weakref
from concurrent.futures import ThreadPoolExecutor

import pytest
import taiyin
import taiyin_bazi as b


@pytest.fixture
def chart():
    ctx = taiyin.Ephemeris(load_packaged_data=False, load_builtin_eop=False).create_context()
    calculator = ctx.bazi()
    gz = taiyin.Ganzhi(0, 0)
    yield calculator.calc_chart(taiyin.GanzhiFourPillars(gz, gz, gz, gz))
    calculator.close()
    ctx.close()


def evaluate(ctx, chart):
    return ctx.evaluate(chart, taiyin.Ganzhi(0, 0), b.BaziShenShaTargetKind.year)


def test_snapshots_and_callbacks(chart):
    seen = []
    base = b.BaziShenShaCatalog()
    added = base.add_module(b.BaziShenShaModule('school', [
        b.BaziShenShaRule('custom', 'Custom', lambda value: seen.append(value) is None)]))
    snapshot = added.create_context()
    removed = added.remove_module('school').create_context()
    disabled = added.create_context(disabled_ids=['school:custom'])
    with pytest.raises(ValueError):
        added.add_module(b.BaziShenShaModule('school', [b.BaziShenShaRule('x', 'x', lambda _: True)]))
    with pytest.raises(ValueError):
        base.remove_module('builtin')
    del base, added
    gc.collect()
    assert any(m.id == 'school:custom' and m.builtin_id is None for m in evaluate(snapshot, chart))
    assert len(seen) == 1
    assert seen[0].gender is None
    assert not any(m.id == 'school:custom' for m in evaluate(removed, chart))
    assert not any(m.id == 'school:custom' for m in evaluate(disabled, chart))
    assert len(seen) == 1


def test_exceptions_and_return_type(chart):
    def broken(_):
        raise LookupError('callback failed')
    for callback, error in [(broken, LookupError), (lambda _: 1, TypeError)]:
        ctx = b.BaziShenShaCatalog().add_module(b.BaziShenShaModule('school', [
            b.BaziShenShaRule('x', 'x', callback)])).create_context()
        with pytest.raises(error):
            evaluate(ctx, chart)


def test_shared_snapshot_threads(chart):
    ctx = b.BaziShenShaCatalog().add_module(b.BaziShenShaModule('school', [
        b.BaziShenShaRule('x', 'x', lambda value: value.target == 0)])).create_context()
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: evaluate(ctx, chart), range(40)))
    assert all(result == results[0] for result in results)


def test_close_breaks_bound_method_cycle(chart):
    class Owner:
        def test(self, _):
            return True

    owner = Owner()
    with b.BaziShenShaCatalog() as base:
        owner.catalog = base.add_module(b.BaziShenShaModule('school', [
            b.BaziShenShaRule('x', 'x', owner.test)]))
        owner.ctx = owner.catalog.create_context()
    reference = weakref.ref(owner)
    ctx = owner.ctx
    catalog = owner.catalog
    del owner
    gc.collect()
    assert reference() is not None
    catalog.close()
    assert any(m.id == 'school:x' for m in evaluate(ctx, chart))
    ctx.close()
    gc.collect()
    assert reference() is None
    ctx.close()
    assert ctx.is_closed and catalog.is_closed
    with pytest.raises(RuntimeError, match='closed'):
        evaluate(ctx, chart)
    with pytest.raises(RuntimeError, match='closed'):
        catalog.create_context()
    with pytest.raises(RuntimeError, match='closed'):
        catalog.remove_module('school')


def test_context_manager_and_close_from_callback(chart):
    def predicate(_):
        ctx.close()
        return True

    with b.BaziShenShaCatalog() as base:
        with base.add_module(b.BaziShenShaModule('school', [
                b.BaziShenShaRule('x', 'x', predicate)])) as catalog:
            with catalog.create_context() as ctx:
                assert any(m.id == 'school:x' for m in evaluate(ctx, chart))
                with pytest.raises(RuntimeError, match='closed'):
                    evaluate(ctx, chart)
    assert base.is_closed and catalog.is_closed and ctx.is_closed
