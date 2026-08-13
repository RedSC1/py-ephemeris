import math, os
from pathlib import Path
import pytest, taiyin

@pytest.fixture()
def star_env():
    root=os.environ.get("TAIYIN_SOURCE_DIR")
    if not root: pytest.skip("set TAIYIN_SOURCE_DIR")
    root=Path(root); source=root/"data/ephemerides/opm2/major-bodies/600y"; catalog=root/"data/stars/catalogs/stars-fixed-traditional.tsc1"
    engine=taiyin.Ephemeris(source_paths=[str(source)],load_packaged_data=False); engine.star_catalog.clear(); engine.star_catalog.add_tsc1(str(catalog))
    context=engine.create_context(); context.configuration.set_geocentric_observer(observer_id=399,center_id=399); context.configuration.set_route_rule(taiyin.RouteRule.opm2)
    yield engine,context,catalog
    engine.star_catalog.clear(); context.close()

def test_catalog_file_bytes_alias_and_magnitude(star_env):
    engine,_,catalog=star_env
    assert engine.star_catalog.count==1
    assert engine.star_catalog.magnitude_of("spica")==pytest.approx(0.98,abs=1e-6)
    assert engine.star_catalog.magnitude_of("Spica")==pytest.approx(0.98,abs=1e-6)
    data=catalog.read_bytes(); engine.star_catalog.clear(); engine.star_catalog.add_tsc1_bytes(data)
    assert engine.star_catalog.count==1 and engine.star_catalog.magnitude_of("spica")==pytest.approx(0.98,abs=1e-6)

def test_editable_tsf1_catalog(star_env,tmp_path):
    engine,_,_=star_env; path=tmp_path/"custom.tsf1"
    path.write_text("""TSF1
version=1
star_count=1

star.0.id=custom_star
star.0.name=Custom Star
star.0.aliases=custom-star-alias
star.0.ra_deg=180
star.0.dec_deg=45
star.0.pm_ra_mas_yr=1
star.0.pm_dec_mas_yr=-2
star.0.parallax_mas=0
star.0.radial_velocity_km_s=0
star.0.reference_epoch=2000
star.0.magnitude=5.5
""")
    engine.star_catalog.clear(); engine.star_catalog.add_tsf1(str(path))
    assert engine.star_catalog.magnitude_of("Custom Star")==5.5
    assert engine.star_catalog.magnitude_of("custom-star-alias")==5.5

def test_all_single_and_batch_time_routes(star_env):
    _,ctx,_=star_env; jd=taiyin.JulianDate.from_double(2460409.0); flags=(taiyin.PositionFlag.xyz,taiyin.PositionFlag.speed,taiyin.PositionFlag.truepos)
    singles=(ctx.stars.at_tdb("spica",jd,jd,flags),ctx.stars.at_tt("spica",jd,flags),ctx.stars.at_ut1("spica",jd,flags),ctx.stars.at_ut1_with_delta_t("spica",jd,69.184,flags))
    for result in singles:
        assert result.is_cartesian and all(math.isfinite(v) for v in result.values)
    assert ctx.last_status==0
    keys=["spica","antares"]
    batches=(ctx.stars.batch_at_tdb(keys,jd,jd,flags),ctx.stars.batch_at_tt(keys,jd,flags),ctx.stars.batch_at_ut1(keys,jd,flags),ctx.stars.batch_at_ut1_with_delta_t(keys,jd,69.184,flags))
    assert all([row.starKey for row in batch]==keys for batch in batches)
    mixed=ctx.stars.batch_at_tt(["spica","missing-star"],jd,flags)
    assert all(math.isfinite(v) for v in mixed[0].values)
    assert all(math.isnan(v) for v in mixed[1].values)
    assert ctx.last_status==0

def test_observed_single_batch_and_validation(star_env):
    _,ctx,_=star_env; jd=taiyin.JulianDate.from_double(2460409.0)
    ctx.configuration.set_observer_location(taiyin.ObserverLocation(116.391,39.907,50)); ctx.configuration.set_standard_atmosphere()
    flags=(taiyin.ObservedFlag.speed,taiyin.ObservedFlag.topocentric,taiyin.ObservedFlag.horizontal,taiyin.ObservedFlag.refraction,taiyin.ObservedFlag.truePosition)
    single=ctx.stars.observed_at_ut1("spica",jd,flags); batch=ctx.stars.observed_batch_at_ut1(["spica","antares"],jd,flags)
    assert single.status==0 and single.horizontal is not None and single.refractedHorizontalRates is not None
    assert len(batch)==2 and all(row.diagnostic.status==0 for row in batch)
    assert ctx.stars.batch_at_tt([],jd)==[] and ctx.stars.observed_batch_at_ut1([],jd)==[]
    with pytest.raises(ValueError): ctx.stars.at_tt("",jd)
    with pytest.raises(ValueError): ctx.stars.observed_at_ut1("spica",jd,(taiyin.ObservedFlag.horizontal,))
    with pytest.raises(ValueError): ctx.stars.at_ut1_with_delta_t("spica",jd,math.nan)
