"""Who answered a survey (respondents.py) and the Census adults it's compared with (ingest/adult_profile.py)."""

import pandas as pd
import pytest

from congress_congruence import respondents as rp
from congress_congruence.ingest import adult_profile as ap

CES_LABELS = {
    "gender4": {1: "Man", 2: "Woman", 3: "Non-binary", 4: "Other", 8: "skipped"},
    "race": {1: "White", 2: "Black", 3: "Hispanic", 4: "Asian", 5: "Native American", 6: "Middle Eastern",
             7: "Two or more races", 8: "Other"},
    "hispanic": {1: "Yes", 2: "No"},
    "educ": {1: "No HS", 2: "High school graduate", 3: "Some college", 4: "2-year", 5: "4-year", 6: "Post-grad"},
}


def test_groups_from_ces_labels():
    assert [rp.sex_group(CES_LABELS["gender4"][k]) for k in (1, 2, 3, 8)] == ["male", "female", "other", None]
    assert [rp.education_group(CES_LABELS["educ"][k]) for k in range(1, 7)] == \
           ["hs_or_less", "hs_or_less", "some_college", "some_college", "ba_plus", "ba_plus"]
    assert [rp.race_group(CES_LABELS["race"][k]) for k in range(1, 9)] == \
           ["white", "black", "hispanic", "asian", "other", "other", "other", "other"]
    assert [rp.is_hispanic(x) for x in ("Yes", "No", "skipped", None)] == [True, False, None, None]


def test_groups_from_nationscape_labels():
    assert rp.sex_group("Female") == "female" and rp.sex_group("Male") == "male"
    assert [rp.race_group(x) for x in ("White", "Black, or African American", "American Indian or Alaska Native",
                                       "Asian (Asian Indian)", "Asian (Other)", "Pacific Islander (Other)",
                                       "Some other race")] == \
           ["white", "black", "other", "asian", "asian", "other", "other"]
    assert [rp.is_hispanic(x) for x in ("Not Hispanic", "Mexican", "Puerto Rican")] == [False, True, True]
    assert rp.race_group("White/Caucasian") == "white"
    assert [rp.education_group(x) for x in (
        "3rd Grade or less", "Middle School - Grades 4 - 8", "Completed some high school", "High school graduate",
        "Other post high school vocational training", "Completed some college, but no degree", "Associate Degree",
        "College Degree (such as B.A., B.S.)", "Completed some graduate, but no degree", "Masters degree",
        "Doctorate degree")] == ["hs_or_less"] * 5 + ["some_college"] * 2 + ["ba_plus"] * 4


def test_age_groups_and_columns():
    assert [rp.age_group(a) for a in (17, 18, 34.9, 35, 44, 45, 64, 65, 99, 130, None, "x")] == \
           [None, "18_34", "18_34", "35_44", "35_44", "45_64", "45_64", "65_plus", "65_plus", None, None, None]
    cols = rp.pick_columns(["birthyr", "age", "gender", "gender4", "race", "hispanic", "educ", "x"])
    assert cols == {"birth_year": "birthyr", "sex": "gender4", "race": "race", "hispanic": "hispanic", "education": "educ"}
    assert rp.pick_columns(["age", "gender", "race_ethnicity", "education"]) == \
           {"age": "age", "sex": "gender", "race": "race_ethnicity", "education": "education"}
    assert rp.pick_columns(["V208", "gender"], {"sex": "V208"}) == {"sex": "V208"}
    assert rp.dimensions({"sex": "g"}) == ["sex"] and rp.dimensions({}) == []


def test_a_person_who_is_hispanic_counts_as_hispanic_whatever_race_they_chose():
    cols = {"race": "race", "hispanic": "hispanic", "birth_year": "birthyr"}
    labels = {"race": CES_LABELS["race"], "hispanic": CES_LABELS["hispanic"]}
    g = lambda **row: rp.person_groups(row, cols, labels, 2024)   # noqa: E731
    assert g(race=1, hispanic=1, birthyr=1990)["race"] == "hispanic"
    assert g(race=1, hispanic=2, birthyr=1990) == {"race": "white", "age": "18_34"}
    assert g(race=3, hispanic=float("nan"), birthyr=1950) == {"race": "hispanic", "age": "65_plus"}
    assert g(race=2, hispanic=float("nan"), birthyr=2010) == {"race": "black", "age": None}
    # An "age" column whose value is a labelled code isn't read as an age.
    assert rp.person_groups({"age": 99}, {"age": "age"}, {"age": {99: "Refused"}}, 2020) == {"age": None}
    assert rp.person_groups({"age": 40}, {"age": "age"}, {"age": {40: "40"}}, 2020) == {"age": "35_44"}
    # An age column named in the item file wins over the birth year.
    assert rp.pick_columns(["birthyr", "agecol"], {"age": "agecol"}) == {"birth_year": "birthyr", "age": "agecol"}
    assert rp.person_groups({"birthyr": 1950, "agecol": 30}, {"birth_year": "birthyr", "age": "agecol"}, {}, 2020) == \
           {"age": "18_34"}


def test_profile_counts_raw_and_weighted_shares_for_the_nation_and_each_state():
    df = pd.DataFrame({
        "gender4": [1, 2, 2, 2, 8],
        "educ":    [6, 2, 2, 5, 2],
        "w":       [3.0, 1.0, 1.0, 1.0, 1.0],
    })
    cols = {"sex": "gender4", "education": "educ"}
    rows = rp.profile(df, cols, rp.read_labels(CES_LABELS, cols), "w", ["TX", "TX", "TX", "OK", None], 2024)
    by = {(r["area"], r["dimension"], r["grp"]): r for r in rows}
    # Nation: 4 with a known sex (the skipped answer is left out); 5 with a known education.
    assert by[("US", "sex", "male")]["respondents"] == 1 and by[("US", "sex", "male")]["raw_share"] == 0.25
    assert by[("US", "sex", "male")]["weighted_share"] == 0.5          # 3 of 6
    assert by[("US", "education", "hs_or_less")]["raw_share"] == 0.6
    assert by[("US", "education", "some_college")]["respondents"] == 0  # every group listed, even empty ones
    assert ("US", "sex", "other") not in by                            # "other" sex only when someone gave it
    assert by[("TX", "sex", "female")]["raw_share"] == round(2 / 3, 4)
    assert by[("OK", "education", "ba_plus")]["weighted_share"] == 1.0
    assert {r["area"] for r in rows} == {"US", "TX", "OK"}
    dc = rp.profile(df, cols, rp.read_labels(CES_LABELS, cols), "w", ["DC"] * 5, 2024)
    assert {r["area"] for r in dc} == {"US"}                         # DC counts nationwide only
    assert rp.profile(df, {}, {}, "w", [None] * 5, 2024) == []


def test_nearest_census_year():
    assert rp.nearest_year(2024, [2019, 2023, 2024]) == 2024
    assert rp.nearest_year(2025, [2019, 2023, 2024]) == 2024    # next year's release isn't out yet
    assert rp.nearest_year(2020, [2019, 2021]) == 2019          # no 2020 release
    assert rp.nearest_year(2006, [2012, 2024]) == 2012
    assert rp.nearest_year(2024, []) is None


# ---------------------------------------------------------------- Census tables

def census_labels(table: str, leaves: list[list[str]]) -> dict[str, list[str]]:
    out = {f"{table}_001E": ["Total"]}
    for i, p in enumerate(leaves, start=2):
        out[f"{table}_{i:03d}E"] = ["Total", *p]
    return out


EDU_LEAVES = [[sex, age, edu] for sex in ("Male", "Female")
              for age in ("18 to 24 years", "25 to 34 years", "35 to 44 years", "45 to 64 years", "65 years and over")
              for edu in ("Less than 9th grade", "9th to 12th grade, no diploma", "High school graduate (includes equivalency)",
                          "Some college, no degree", "Associate's degree", "Bachelor's degree",
                          "Graduate or professional degree")]
RACE_LEAVES = [[sex, age] for sex in ("Male", "Female")
               for age in ("Under 5 years", "5 to 9 years", "10 to 14 years", "15 to 17 years", "18 and 19 years",
                           "20 to 24 years", "65 to 74 years")]


def test_label_parts_old_and_new_style():
    assert ap.parts("Estimate!!Total:!!Male:!!18 to 24 years:") == ["Total", "Male", "18 to 24 years"]
    assert ap.parts("Estimate!!Total!!Female!!65 years and over!!Bachelor's degree") == \
           ["Total", "Female", "65 years and over", "Bachelor's degree"]


def test_parse_census_tables_into_shares():
    labels = census_labels("B15001", EDU_LEAVES)
    # Every leaf cell is 10 adults: 70 education cells per sex -> 700 adults; one bad value is read as 0.
    header = ["NAME", *labels, "state"]
    values = {v: "10" for v in labels}
    values["B15001_001E"] = "700"
    us = [values.get(h, "United States") if h != "state" else "US" for h in header]
    tx = [values.get(h, "Texas") if h != "state" else "TX" for h in header]
    tx[header.index("B15001_002E")] = "-666666666"
    edu = ap.parse_education([header, us, tx], labels)
    assert edu["US"]["total"] == 700 and edu["US"]["sex"] == {"male": 350, "female": 350}
    assert edu["TX"]["sex"] == {} and edu["TX"]["total"] == 700  # a withheld cell: no sex, age or education rows
    assert edu["US"]["age"]["18_34"] == 280 and edu["US"]["age"]["65_plus"] == 140
    assert edu["US"]["education"] == {"hs_or_less": 300, "some_college": 200, "ba_plus": 200}

    rl = census_labels("B01001H", RACE_LEAVES)
    rh = ["NAME", *rl, "state"]
    rrow = [("5" if h in rl else "US") if h != "state" else "US" for h in rh]
    adults = ap.parse_adults([rh, rrow], rl)
    assert adults == {"US": 30}                                   # 3 adult ages x 2 sexes x 5; the total cell is skipped
    rrow[rh.index("B01001H_006E")] = ""                           # an adult cell (male, 18 and 19) left blank
    assert ap.parse_adults([rh, rrow], rl) == {"US": None}
    races = {"white": {"US": 300, "TX": None}, "black": {"US": 100}, "asian": {"US": 50}, "hispanic": {"US": 200}}
    tx_rows = ap.rows_for(2024, {"TX": {**edu["US"], "total": 700}}, races)
    assert tx_rows and not any(r[2] == "race" for r in tx_rows)  # a missing race table: no race rows at all
    rows = ap.rows_for(2024, {"US": edu["US"]}, races)
    by = {(r[2], r[3]): r for r in rows}
    assert by[("race", "other")][4] == 50 and by[("race", "white")][5] == round(300 / 700, 4)
    assert by[("sex", "female")][6] == "ACS 2024 1-year estimates"
    assert sum(r[5] for r in rows if r[2] == "education") == pytest.approx(1, abs=1e-3)


def test_unexpected_census_labels_stop_the_load():
    labels = census_labels("B15001", [["Male", "16 to 17 years", "Bachelor's degree"]])
    header = ["NAME", *labels, "state"]
    with pytest.raises(ValueError, match="unexpected label"):
        ap.parse_education([header, ["x", "1", "1", "US"]], labels)
