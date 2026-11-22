"""ZIP code areas to congressional districts (Census relationship file) and the contact section."""

import importlib.util
from pathlib import Path

from congress_congruence.ingest import zip_districts as z

HEAD = ("OID_CD119_20|GEOID_CD119_20|NAMELSAD_CD119_20|AREALAND_CD119_20|AREAWATER_CD119_20|MTFCC_CD119_20|"
        "FUNCSTAT_CD119_20|OID_ZCTA5_20|GEOID_ZCTA5_20|NAMELSAD_ZCTA5_20|AREALAND_ZCTA5_20|AREAWATER_ZCTA5_20|"
        "MTFCC_ZCTA5_20|CLASSFP_ZCTA5_20|FUNCSTAT_ZCTA5_20|AREALAND_PART|AREAWATER_PART")


def row(cd, zcta, land):
    return f"1|{cd}|District|0|0|G5200|N|2|{zcta}|ZCTA5 {zcta}|0|0|G6350|B5|S|{land}|0"


def test_parse_shares_land_and_drops_slivers():
    text = "\n".join([HEAD,
                      row("4808", "77378", 600), row("4802", "77378", 395), row("4810", "77378", 5),   # 0.5%: dropped
                      row("0200", "99501", 100),                    # Alaska at-large
                      row("1198", "20001", 100),                    # D.C. delegate
                      row("48ZZ", "77001", 100),                    # water: no district
                      row("4807", "", 50)]) + "\n"                  # part of a district with no ZCTA
    rows = z.parse(text, 119)
    assert (119, "77378", "TX", 8, 0.6) in rows and (119, "77378", "TX", 2, 0.395) in rows
    assert not any(r[1] == "77378" and r[3] == 10 for r in rows)
    assert (119, "99501", "AK", 0, 1.0) in rows and (119, "20001", "DC", 0, 1.0) in rows
    assert {r[1] for r in rows} == {"77378", "99501", "20001"}


def test_member_page_contact_section():
    spec = importlib.util.spec_from_file_location("build_profiles", Path(__file__).parents[1] / "scripts" / "build_profiles.py")
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
    m = {"serving": True, "chamber": "house",
         "contact": {"website": "https://example.house.gov", "phone": "202-225-0000",
                     "address": "1 Longworth House Office Building Washington DC 20515"},
         "offices": [{"city": "Conroe", "state": "TX", "address": "1 Main St.", "zip": "77301", "phone": "936-555-0100"}]}
    html = "\n".join(bp.contact_html(m))
    assert '<h2 id="contact">Contact</h2>' in html and "Tell your representative what you think" in html
    assert 'href="tel:+12022250000"' in html and "Offices in the district (1)" in html and "Conroe" in html
    assert bp.contact_html({**m, "serving": False}) == []
