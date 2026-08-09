import pytest
import taiyin
import taiyin_bazi


def test_bazi_pure_rules_are_created_from_ephemeris():
    eph=taiyin.Ephemeris(load_packaged_data=False,load_builtin_eop=False)
    bazi=eph.create_bazi()
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
