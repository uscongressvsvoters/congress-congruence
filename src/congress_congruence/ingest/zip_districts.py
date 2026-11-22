"""Which congressional district each ZIP code is in, for the site's "Find your members by ZIP code".

    python -m congress_congruence.ingest.zip_districts            # load the current and next Congress if
                                                                  # published and not loaded yet (weekly job)
    python -m congress_congruence.ingest.zip_districts 120        # load (or reload) one Congress's file

Source: the Census Bureau's relationship file between congressional districts and 2020 ZIP Code
Tabulation Areas (ZCTAs), https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/ (file
tab20_cd<congress>20_zcta520_natl.txt). A ZCTA is the Census Bureau's area version of a ZIP code: close to
the Postal Service's ZIP codes for where people live, but not identical, and some ZIP codes (P.O. boxes,
single buildings) have none. Many ZIP codes cross district lines, so each ZCTA keeps every district that
holds at least 1% of its land (or its largest one), with that share.

The site turns the table into one static file (zip-districts.json, written by scripts/build_profiles.py):
a reader's ZIP code is looked up in their own browser and is never sent to the server.

District lines change when a new Congress begins (January 3 after an election): for every state after
each census (the next in 2033), and in between wherever courts or legislatures redraw (as several states
did for the 120th Congress, January 2027). The Census Bureau publishes a file for each new Congress,
usually months ahead. The weekly job (scripts/run_job.sh zip-districts) loads it as soon as it appears;
the API serves a Congress's lines from the day it begins, and the weekly page rebuild publishes them.
"""

import csv
import io
import logging
import sys
from datetime import date

import requests

from .. import db
from .population import FIPS
from .votes import http_session

log = logging.getLogger(__name__)

URL = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_cd{c}20_zcta520_natl.txt"
TERRITORIES = {"60": "AS", "66": "GU", "69": "MP", "78": "VI"}
MIN_SHARE = 0.01


def parse(text: str, congress: int) -> list[tuple]:
    """(congress, zcta, state, district, land share) rows from the relationship file."""
    first = text.split("\n", 1)[0]
    delim = "|" if "|" in first else ","
    rows = csv.DictReader(io.StringIO(text), delimiter=delim)
    cd_col = next(c for c in rows.fieldnames if c.startswith("GEOID_CD"))
    parts: dict[str, dict] = {}
    for r in rows:
        cd, zcta = (r.get(cd_col) or "").strip(), (r.get("GEOID_ZCTA5_20") or "").strip()
        if len(zcta) != 5 or len(cd) != 4 or not cd[2:].isdigit():
            continue                     # parts of a district with no ZCTA, or of the water ("ZZ")
        state = FIPS.get(cd[:2]) or TERRITORIES.get(cd[:2])
        if not state:
            continue
        district = int(cd[2:])
        district = 0 if district in (0, 98) else district      # at-large seats and delegates
        land = int(r.get("AREALAND_PART") or 0)
        key = (state, district)
        parts.setdefault(zcta, {})[key] = parts.get(zcta, {}).get(key, 0) + land
    out = []
    for zcta, by_cd in parts.items():
        total = sum(by_cd.values())
        shares = {k: (v / total if total else 1 / len(by_cd)) for k, v in by_cd.items()}
        biggest = max(shares, key=shares.get)
        for (state, district), share in shares.items():
            if share >= MIN_SHARE or (state, district) == biggest:
                out.append((congress, zcta, state, district, round(share, 4)))
    return out


def run(congress: int = 119, conn=None, http=None) -> int:
    url = URL.format(c=congress)
    resp = (http or http_session()).get(url, timeout=120)
    resp.raise_for_status()
    rows = parse(resp.content.decode("utf-8-sig"), congress)
    if len(rows) < 30000:
        raise RuntimeError(f"Only {len(rows)} rows from {url}: expected about 40,000. Nothing was changed.")
    own = conn is None
    conn = conn or db.connect()
    try:
        with conn.transaction(), conn.cursor() as cur:
            cur.execute("delete from core.zip_district where congress = %s", (congress,))
            with cur.copy("copy core.zip_district (congress, zcta, state, district, land_share) from stdin") as cp:
                for r in rows:
                    cp.write_row(r)
    finally:
        if own:
            conn.close()
    zctas = len({r[1] for r in rows})
    log.info("Loaded %d ZIP code areas (%d ZIP-district pairs) for the %dth Congress", zctas, len(rows), congress)
    return zctas


def current_congress(day: date) -> int:
    """The Congress in session on a day (each begins January 3 of an odd year: 2 * n + 1787)."""
    year = day.year if (day.month, day.day) >= (1, 3) else day.year - 1
    return (year - 1787) // 2


def refresh(today: date | None = None, conn=None, http=None) -> list[int]:
    """Load the current and the next Congress's files, if published and not loaded yet."""
    today = today or date.today()
    own = conn is None
    conn = conn or db.connect()
    loaded = []
    try:
        for congress in (current_congress(today), current_congress(today) + 1):
            with conn.cursor() as cur:
                cur.execute("select 1 from core.zip_district where congress = %s limit 1", (congress,))
                if cur.fetchone():
                    continue
            try:
                run(congress, conn=conn, http=http)
                loaded.append(congress)
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 404:
                    log.info("The %dth Congress's ZIP code file isn't published yet", congress)
                    continue
                raise
    finally:
        if own:
            conn.close()
    if not loaded:
        log.info("ZIP code districts are up to date")
    return loaded


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = argv[1:]
    if len(args) > 1 or (args and not args[0].isdigit()):
        print(__doc__)
        return 2
    if args:
        run(int(args[0]))
    else:
        refresh()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
