"""Who answered a survey: its respondents by sex, age, race and ethnicity, and education, counted
once each (raw) and with the survey's own weights, for everyone ('US') and for each state.

Written by the CES and Nationscape loaders, which have each person's answers; shown beside the
same groups among each state's adults from the Census (ingest/adult_profile.py), so readers can see
how far the people who answered differed from the people who live there, and how much the weights
had to correct. Sources that publish only their results (PPC, Texas Politics Project, UNH) have no
respondent file, so they have no profile here; the Sources page links to their own tables.

Groups (the same in the Census tables):
    sex        female, male (and "other" for answers such as non-binary: shown, no Census figure)
    age        18_34, 35_44, 45_64, 65_plus
    race       hispanic (any race), white, black, asian (each not Hispanic), other
    education  hs_or_less, some_college (including associate degrees), ba_plus

Answers are put in groups by their value labels in the data file ("Female", "Some college",
"Hispanic"...), so the same code works across survey years whose answer codes differ. Skipped,
refused and "not asked" answers are left out of that question's shares.
"""

import logging
import re

log = logging.getLogger(__name__)

DIMENSIONS = ("sex", "age", "race", "education")
GROUPS = {
    "sex": ("female", "male", "other"),
    "age": ("18_34", "35_44", "45_64", "65_plus"),
    "race": ("hispanic", "white", "black", "asian", "other"),
    "education": ("hs_or_less", "some_college", "ba_plus"),
}
# Columns to read, first one present wins. An item file can override with `demographics:` (same keys).
DEFAULT_COLUMNS = {
    "birth_year": ["birthyr"],
    "age": ["age"],
    "sex": ["gender4", "gender"],
    "race": ["race", "race_ethnicity"],
    "hispanic": ["hispanic"],
    "education": ["educ", "education"],
}
MIN_STATE_RESPONDENTS = 1     # every state is stored; the page says how many people each table rests on

NO_ANSWER = re.compile(r"skip|refus|not asked|don.?t know|prefer not|missing|no answer|not sure|n/a", re.I)


def pick_columns(available, overrides: dict | None = None) -> dict[str, str]:
    """{role: column} for the demographic columns in a data file (roles as in DEFAULT_COLUMNS)."""
    have = set(available)
    out = {}
    for role, cands in DEFAULT_COLUMNS.items():
        wanted = (overrides or {}).get(role)
        cands = [wanted] if isinstance(wanted, str) else list(wanted or cands)
        found = next((c for c in cands if c in have), None)
        if found:
            out[role] = found
    if "birth_year" in out and not (overrides or {}).get("age"):
        out.pop("age", None)          # birth year is exact; an "age" column may be grouped
    return out


# ---------------------------------------------------------------- one person's groups, from labels

def _label(value, labels: dict | None) -> str | None:
    if value is None or value != value:
        return None
    if not labels:
        return None
    for key in (value, _num(value)):
        if key in labels:
            return str(labels[key]).strip()
    return None


def _num(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return value
    return int(f) if f == int(f) else f


def sex_group(label: str | None) -> str | None:
    if not label or NO_ANSWER.search(label):
        return None
    t = label.lower()
    if re.search(r"\b(female|woman|women)\b", t):
        return "female"
    if re.search(r"\b(male|man|men)\b", t):
        return "male"
    return "other"


def is_hispanic(label: str | None) -> bool | None:
    """From a separate Hispanic-origin question: 'Yes' or an origin ('Mexican') -> True; 'No' or
    'Not Hispanic' -> False; skipped -> None."""
    if not label or NO_ANSWER.search(label):
        return None
    t = label.lower()
    if re.match(r"no\b", t) or re.search(r"\bnot\b.*(hispanic|latino|spanish)", t):
        return False
    return True


def race_group(label: str | None) -> str | None:
    if not label or NO_ANSWER.search(label):
        return None
    t = label.lower()
    if re.search(r"hispanic|latin", t):
        return "hispanic"
    if re.search(r"american indian|alaska|native american", t):
        return "other"
    if re.search(r"\basian\b|chinese|japanese|korean|filipino|vietnamese|\bindian\b", t):
        return "asian"
    if re.search(r"pacific|hawaiian|two or more|mixed|middle eastern|other", t):
        return "other"
    if re.search(r"\bwhite\b", t):
        return "white"
    if re.search(r"\bblack\b|african", t):
        return "black"
    return "other"


def education_group(label: str | None) -> str | None:
    if not label or NO_ANSWER.search(label):
        return None
    t = label.lower()
    if re.search(r"post-?grad|master|doctor|professional|some graduate|4-year|four-year|bachelor|college degree|b\.a\.", t):
        return "ba_plus"
    if re.search(r"some college|2-year|two-year|associate", t):
        return "some_college"
    if re.search(r"high school|\bhs\b|grade|less than|vocational|no schooling|none", t):
        return "hs_or_less"
    return None


def age_group(age) -> str | None:
    try:
        a = float(age)
    except (TypeError, ValueError):
        return None
    if a != a or a < 18 or a > 115:
        return None
    return "18_34" if a < 35 else "35_44" if a < 45 else "45_64" if a < 65 else "65_plus"


def person_groups(row: dict, cols: dict[str, str], labels: dict[str, dict], year: int) -> dict[str, str | None]:
    """{dimension: group or None} for one respondent (row: column -> raw value)."""
    out = {}
    if "birth_year" in cols and "age" not in cols:
        by = row.get(cols["birth_year"])
        try:
            out["age"] = age_group(year - float(by))
        except (TypeError, ValueError):
            out["age"] = None
    elif "age" in cols:
        value = row.get(cols["age"])          # a value labelled with words ("Refused") is a code, not an age
        label = _label(value, labels.get(cols["age"]))
        out["age"] = None if label and not re.fullmatch(r"\d+(\.0+)?", label) else age_group(value)
    if "sex" in cols:
        out["sex"] = sex_group(_label(row.get(cols["sex"]), labels.get(cols["sex"])))
    if "education" in cols:
        out["education"] = education_group(_label(row.get(cols["education"]), labels.get(cols["education"])))
    if "race" in cols or "hispanic" in cols:
        hisp = is_hispanic(_label(row.get(cols["hispanic"]), labels.get(cols["hispanic"]))) if "hispanic" in cols else None
        race = race_group(_label(row.get(cols["race"]), labels.get(cols["race"]))) if "race" in cols else None
        out["race"] = "hispanic" if hisp or race == "hispanic" else race
    return out


# ---------------------------------------------------------------- tables for the nation and each state

def profile(df, cols: dict[str, str], labels: dict[str, dict], weight_col: str, states, year: int) -> list[dict]:
    """Rows for survey_respondent_profile (without survey and census_year): for 'US' and each state
    in `states` (a sequence of state codes or None, one per row of df), each dimension's groups with
    the count of respondents, their share, and their weighted share."""
    if not cols:
        return []
    dims = dimensions(cols)
    use = list(dict.fromkeys(cols.values()))
    totals: dict[tuple, list[float]] = {}               # (area, dim, group) -> [count, weight]
    for rec, st, w in zip(df[use].to_dict("records"), states, df[weight_col]):
        try:
            w = float(w)
        except (TypeError, ValueError):
            continue
        if w != w or w <= 0:
            continue
        groups = person_groups(rec, cols, labels, year)
        for d in dims:
            g = groups.get(d)
            if not g:
                continue
            for area in ("US", st) if st and st != "DC" else ("US",):   # DC has no senators
                t = totals.setdefault((area, d, g), [0, 0.0])
                t[0] += 1
                t[1] += w
    out = []
    areas = sorted({a for a, _, _ in totals}, key=lambda a: (a != "US", a))
    for area in areas:
        for d in dims:
            n = sum(totals.get((area, d, g), [0, 0])[0] for g in GROUPS[d])
            wt = sum(totals.get((area, d, g), [0, 0.0])[1] for g in GROUPS[d])
            if n < MIN_STATE_RESPONDENTS:
                continue
            for g in GROUPS[d]:
                c, w = totals.get((area, d, g), [0, 0.0])
                if g == "other" and d == "sex" and not c:
                    continue
                out.append({"area": area, "dimension": d, "grp": g, "respondents": c,
                            "raw_share": round(c / n, 4), "weighted_share": round(w / wt, 4) if wt else None})
    return out


def dimensions(cols: dict[str, str]) -> list[str]:
    """The dimensions a set of columns can show."""
    have = {"age": "birth_year" in cols or "age" in cols, "sex": "sex" in cols,
            "race": "race" in cols or "hispanic" in cols, "education": "education" in cols}
    return [d for d in DIMENSIONS if have[d]]


def read_labels(value_labels: dict, cols: dict[str, str]) -> dict[str, dict]:
    return {c: (value_labels or {}).get(c) or {} for c in cols.values()}


def report_missing(survey: str, cols: dict[str, str], value_labels: dict | None = None) -> None:
    """Log the groups a survey can't show: no column found, or (given value_labels) a column whose
    answers have no labels to sort them by (e.g. a CSV file rather than Stata)."""
    if value_labels is not None:
        bare = [r for r, c in cols.items() if r not in ("birth_year", "age") and not value_labels.get(c)]
        if bare:
            log.warning("%s: no answer labels for %s, so who answered isn't shown by those (read the Stata "
                        "file, which has the labels)", survey, ", ".join(cols[r] for r in bare))
    gone = [d for d in DIMENSIONS if d not in dimensions(cols)]
    if gone:
        log.warning("%s: no column found for %s, so who answered isn't shown by %s (set `demographics:` "
                    "in the item file to name the columns)", survey, ", ".join(gone), ", ".join(gone))


def save(cur, survey: str, rows: list[dict], census_year: int) -> int:
    cur.execute("delete from core.survey_respondent_profile where survey = %s", (survey,))
    cur.executemany(
        """insert into core.survey_respondent_profile (survey, area, dimension, grp, respondents, raw_share,
               weighted_share, census_year)
           values (%(survey)s, %(area)s, %(dimension)s, %(grp)s, %(respondents)s, %(raw_share)s,
                   %(weighted_share)s, %(census_year)s)""",
        [{**r, "survey": survey, "census_year": census_year} for r in rows])
    return len(rows)


def nearest_year(wanted: int, loaded: list[int]) -> int | None:
    """The Census year to compare a survey with: the latest loaded year not after the survey's, else
    the earliest loaded (the ACS 1-year release for a year comes out the following September)."""
    if not loaded:
        return None
    before = [y for y in loaded if y <= wanted]
    return max(before) if before else min(loaded)
