"""Which congressional district each ZIP code is in, for the site's "Find your members by ZIP code".

    python -m congress_congruence.ingest.zip_districts            # the current Congress's districts (119th)
    python -m congress_congruence.ingest.zip_districts 120        # once the Census publishes the 120th's

Source: the Census Bureau's relationship file between congressional districts and 2020 ZIP Code
Tabulation Areas (ZCTAs), https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/ (file
tab20_cd<congress>20_zcta520_natl.txt). A ZCTA is the Census Bureau's area version of a ZIP code: close to
the Postal Service's ZIP codes for where people live, but not identical, and some ZIP codes (P.O. boxes,
single buildings) have none. Many ZIP codes cross district lines, so each ZCTA keeps every district that
holds at least 1% of its land (or its largest one), with that share.

The site turns the table into one static file (zip-districts.json, written by scripts/build_profiles.py):
a reader's ZIP code is looked up in their own browser and is never sent to the server.

Run it again for each new Congress whose district lines changed: the next is the 120th (January 2027),
for the states that redrew their districts for the 2026 elections.
"""

import csv
import io
import logging
import sys

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


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = argv[1:]
    if len(args) > 1 or (args and not args[0].isdigit()):
        print(__doc__)
        return 2
    run(int(args[0]) if args else 119)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
