"""Adults (18 and over) in the nation and each state by sex, age, race and ethnicity, and education,
from the Census Bureau's American Community Survey 1-year estimates. Shown beside who answered each
survey (respondents.py), so readers can see how closely the people surveyed matched the people living
there.

    python -m congress_congruence.ingest.adult_profile 2024          # one release
    python -m congress_congruence.ingest.adult_profile 2012 2024     # a range (2020 is skipped: the
                                                                      # Census didn't release it)

Tables (whole groups, read by their labels, so the code doesn't depend on variable numbers):
    B15001   sex by age by educational attainment, population 18 and over: sex, age and education
    B01001H  sex by age, white alone, not Hispanic or Latino
    B01001B  sex by age, Black or African American alone
    B01001D  sex by age, Asian alone
    B01001I  sex by age, Hispanic or Latino (any race)
Adults in the race tables are everyone minus the under-18 age groups. "Other" is all adults minus
those four. The Census's Black and Asian counts include the few people who are also Hispanic, whom
the surveys count as Hispanic, so "other" can come out slightly low (never below zero).

Needs CENSUS_API_KEY in .env, as for population. Re-running a year replaces its rows.
"""

import logging
import sys

from .. import db
from .population import API, FIPS, api_get
from .votes import http_session

log = logging.getLogger(__name__)

EDUCATION_TABLE = "B15001"
RACE_TABLES = {"white": "B01001H", "black": "B01001B", "asian": "B01001D", "hispanic": "B01001I"}
NO_RELEASE = {2020}
MINOR_AGES = ("under 5 years", "5 to 9 years", "10 to 14 years", "15 to 17 years")
AGE = {"18 to 24 years": "18_34", "25 to 34 years": "18_34", "35 to 44 years": "35_44",
       "45 to 64 years": "45_64", "65 years and over": "65_plus"}


def education(label: str) -> str | None:
    t = label.lower()
    if "bachelor" in t or "graduate or professional" in t:
        return "ba_plus"
    if "some college" in t or "associate" in t:
        return "some_college"
    if "less than 9th" in t or "no diploma" in t or "high school graduate" in t:
        return "hs_or_less"
    return None


def parts(label: str) -> list[str]:
    """'Estimate!!Total:!!Male:!!18 to 24 years:' -> ['Total', 'Male', '18 to 24 years'] (older
    releases have no colons)."""
    bits = [p.strip().rstrip(":").strip() for p in label.split("!!")]
    return bits[1:] if bits and bits[0].lower() == "estimate" else bits


def group_labels(year: int, table: str, http=None) -> dict[str, list[str]]:
    """{variable: label parts} for a table's estimates, from the API's own variable list."""
    resp = (http or http_session()).get(f"{API.format(year=year)}/groups/{table}.json", timeout=60)
    resp.raise_for_status()
    found = resp.json().get("variables", {})
    return {v: parts(meta.get("label", "")) for v, meta in found.items() if v.endswith("E") and v.startswith(table + "_")}


def fetch_table(year: int, table: str, http=None) -> list[list[str]]:
    """The whole table for every state and for the nation, as rows with a 'state' column ('US' for the nation)."""
    states = api_get(year, [f"group({table})"], "state:*", None, http)
    nation = api_get(year, [f"group({table})"], "us:1", None, http)
    header = states[0]
    i_state = header.index("state")
    rows = [header] + states[1:]
    n_header = nation[0]
    for r in nation[1:]:
        rec = dict(zip(n_header, r))
        rows.append([rec.get(h, "") if h != "state" else "US" for h in header])
    for r in rows[1:]:
        if r[i_state] != "US":
            r[i_state] = FIPS.get(r[i_state], "")
    return rows


def _value(rec: dict, var: str) -> float | None:
    """A count, or None where the Census gives none (blank, or a negative annotation code such as
    -666666666 for a figure withheld for data quality)."""
    try:
        v = float(rec.get(var))
    except (TypeError, ValueError):
        return None
    return v if v >= 0 else None


def parse_education(table: list[list[str]], labels: dict[str, list[str]]) -> dict[str, dict]:
    """{area: {'total': adults, 'sex': {...}, 'age': {...}, 'education': {...}}} from B15001."""
    header, out = table[0], {}
    for r in table[1:]:
        rec = dict(zip(header, r))
        area = rec.get("state")
        if not area or area == "PR":
            continue
        a = {"total": 0.0, "sex": {}, "age": {}, "education": {}}
        complete = True
        for var, p in labels.items():
            if len(p) == 1 and p[0].lower() == "total":
                a["total"] = _value(rec, var) or 0.0
            if len(p) != 4:                      # Total, sex, age, education: the leaf cells
                continue
            sex, age, edu = p[1].lower(), AGE.get(p[2].lower()), education(p[3])
            if sex not in ("male", "female") or not age or not edu:
                raise ValueError(f"{EDUCATION_TABLE}: unexpected label {' / '.join(p)}; check the table's layout")
            v = _value(rec, var)
            if v is None:
                complete = False
                continue
            for dim, g in (("sex", sex), ("age", age), ("education", edu)):
                a[dim][g] = a[dim].get(g, 0.0) + v
        if not complete:                         # a withheld cell would understate its groups
            log.warning("%s: %s has cells the Census didn't publish; its sex, age and education rows are left out",
                        EDUCATION_TABLE, area)
            a.update(sex={}, age={}, education={})
        out[area] = a
    return out


def parse_adults(table: list[list[str]], labels: dict[str, list[str]]) -> dict[str, float | None]:
    """{area: adults} from a B01001 race table: the sum of every age cell 18 and over; None for an area
    where any of those cells wasn't published (the group would otherwise land in "other")."""
    header, out = table[0], {}
    for r in table[1:]:
        rec = dict(zip(header, r))
        area = rec.get("state")
        if not area or area == "PR":
            continue
        cells = [_value(rec, var) for var, p in labels.items() if len(p) == 3 and p[2].lower() not in MINOR_AGES]
        out[area] = None if any(v is None for v in cells) else sum(cells)
    return out


def rows_for(year: int, edu: dict[str, dict], races: dict[str, dict[str, float]]) -> list[tuple]:
    """(acs_year, area, dimension, group, adults, share, source) rows."""
    source = f"ACS {year} 1-year estimates"
    out = []
    for area, a in sorted(edu.items()):
        total = a["total"] or sum(a["sex"].values())
        if not total:
            continue
        for dim in ("sex", "age", "education"):
            for g, v in sorted(a[dim].items()):
                out.append((year, area, dim, g, round(v), round(v / total, 4), source))
        known = {g: races[g].get(area) for g in RACE_TABLES}
        if any(v is None for v in known.values()):
            log.warning("ACS %s: %s has a race table the Census didn't publish in full; no race rows", year, area)
            continue
        known["other"] = max(0.0, total - sum(known.values()))
        for g, v in known.items():
            out.append((year, area, "race", g, round(v), round(v / total, 4), source))
    return out


def load(conn, year: int, http=None) -> dict:
    edu = parse_education(fetch_table(year, EDUCATION_TABLE, http), group_labels(year, EDUCATION_TABLE, http))
    races = {g: parse_adults(fetch_table(year, t, http), group_labels(year, t, http)) for g, t in RACE_TABLES.items()}
    rows = rows_for(year, edu, races)
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("delete from core.adult_profile where acs_year = %s", (year,))
        cur.executemany("insert into core.adult_profile (acs_year, area, dimension, grp, adults, share, source) "
                        "values (%s, %s, %s, %s, %s, %s, %s)", rows)
    us = edu.get("US", {}).get("total")
    return {"year": year, "areas": len({r[1] for r in rows}), "rows": len(rows),
            "adults_nationwide": round(us) if us else None}


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    nums = sorted(int(a) for a in argv[1:] if a.isdigit())
    if not 1 <= len(nums) <= 2 or len(nums) != len(argv) - 1:
        print(__doc__)
        return 2
    from .votes import record_run
    failed = 0
    with db.connect() as conn:
        for y in [y for y in range(nums[0], nums[-1] + 1) if y not in NO_RELEASE]:
            try:
                print(y, record_run(conn, f"adult_profile_{y}", lambda: load(conn, y)))
            except Exception as e:                        # report and carry on with the other years
                log.error("ACS %s: %s", y, e)
                failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
