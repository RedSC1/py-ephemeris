import math,os
from pathlib import Path
import pytest,taiyin
@pytest.fixture()
def ctx():
    root=os.environ.get("TAIYIN_SOURCE_DIR")
    if not root:pytest.skip("set TAIYIN_SOURCE_DIR")
    root=Path(root);e=taiyin.Ephemeris(source_paths=[str(root/"data/ephemerides/opm2/major-bodies/600y")],load_packaged_data=False);e.star_catalog.clear();e.star_catalog.add_tsc1(str(root/"data/stars/catalogs/stars-fixed-traditional.tsc1"))
    c=e.create_context();c.configuration.set_geocentric_observer(observer_id=399,center_id=399);c.configuration.set_observer_location(taiyin.ObserverLocation(0,0));c.configuration.set_atmosphere_policy((taiyin.AtmospherePolicyFlag.allowStandardFallback,));c.configuration.set_heliacal_visibility_model(taiyin.HeliacalVisibilityModel.schaefer1993);c.configuration.set_route_rule(taiyin.RouteRule.opm2)
    yield c;e.star_catalog.clear();c.close()
def test_body_and_star_visibility(ctx):
    jd=taiyin.JulianDate.from_double(2460408.5);conditions=taiyin.HeliacalVisibilityConditions(extinctionMagnitudePerAirmass=.5,skyBrightnessNanolambert=1234)
    body=ctx.heliacal.body_at_ut1(taiyin.Body.venus,jd,position_flags=(taiyin.PositionFlag.truepos,),conditions=conditions);star=ctx.heliacal.star_at_ut1("spica",jd)
    assert ctx.last_status==0 and body.modelId==1
    assert body.extinctionMagnitudePerAirmass==.5 and body.skyBrightnessNanolambert==1234
    assert math.isfinite(star.targetMagnitude)
def test_body_and_star_event_searches(ctx):
    body=ctx.heliacal.next_body_event_at_ut1(taiyin.Body.venus,taiyin.JulianDate.from_double(2460428.731063851),event=taiyin.HeliacalEventKind.morningLast,max_search_days=5,conditions=taiyin.HeliacalVisibilityConditions(extinctionMagnitudePerAirmass=.25))
    star=ctx.heliacal.next_star_event_at_ut1("spica",taiyin.JulianDate.from_double(2460310.5),event=taiyin.HeliacalEventKind.morningFirst,max_search_days=366)
    for result in (body,star):
        assert result.visibility.visible
        assert result.windowStart.to_double()<result.coordinate.to_double()<result.windowEnd.to_double()
    assert ctx.last_status==0
def test_validation(ctx):
    jd=taiyin.JulianDate.from_double(2460408.5)
    with pytest.raises(ValueError):ctx.heliacal.body_at_ut1(taiyin.Body.sun,jd)
    with pytest.raises(ValueError):ctx.heliacal.body_at_ut1(taiyin.Body.venus,jd,position_flags=(taiyin.PositionFlag.speed,))
    with pytest.raises(ValueError):ctx.heliacal.next_body_event_at_ut1(taiyin.Body.venus,jd,event=taiyin.HeliacalEventKind.morningFirst,max_search_days=0)
