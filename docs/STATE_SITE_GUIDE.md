# Building the sister site for state legislatures

This guide is for a future developer or AI session asked to build a **state legislature** version of
US Congress vs Voters: the same idea (how elected members voted, compared with what people where they
live told independent surveys), the same rules, and the same look, for state legislators instead of
members of Congress.

Status: **planned, not started.** The maintainer decided on November 23, 2026 that this site stays
Congress-only (PROJECT_NOTES.md, "Decisions that stand") and that state legislatures get a **separate
site**, on its own domain and possibly its own server. Nothing in this repository should grow to cover
states; build the new site in its own repository.

The goal for readers: moving between the two sites should feel like moving between two sections of one
project. Same layout, typeface, colors, words for the same things, rules and privacy promises, with
clear links across at the points where a reader needs the other one.

Read AGENTS.md first. Its rules apply to the new site unchanged, and the sections below say where the
new site differs.

## 1. Decisions the maintainer makes first

Ask about these before building; don't guess. Each becomes a row in the new repository's
`docs/system_info.xlsx` and a line in its `docs/DECISIONS.md`.

| Decision | Notes |
| --- | --- |
| Name and domain | Should read as a sibling: "<Something> vs Voters". Check the domain is free; the maintainer buys it. |
| Which states first | Recommended: **Texas** only, to start. The Texas Politics Project polls already used here ask Texans about state issues, so there is survey data to match. Add a state only when there's a survey source for it. |
| Server | Same VPS as this site (cheapest; one more nginx site and database) or a new one (isolation; this site's outage on Nov 19, 2026 would then not take both down). |
| Repository | A new public repository in the **uscongressvsvoters** GitHub organization, AGPL like this one. Start it as a copy of this repository's site layer (section 3), not as a fork with all of Congress's code. |
| Contact address | A new mailbox on the new domain, or `contact@` here. Never publish or name the private admin address. |

## 2. Rules that carry over unchanged

These are the founding rules (AGENTS.md, "The site's rules"). They apply as written:

- **Neutral.** Same methods, wording and design for every legislator and party. Never mention or link
  to a party, campaign or advocacy group. Votes are told apart by **shape, not party color**.
- **Survey sources are never blended.** Each source is shown on its own line.
- **Like for like.** Only a recorded vote on the same proposal a survey asked about is counted.
  Close-but-different votes are shown as "related" and never counted. **The maintainer approves every
  survey-to-vote match** before it goes live.
- **Visible data, not verdicts.** No rankings, grades, or trend analysis of our own.
- **No data about visitors.** No accounts, cookies, analytics or outside requests from pages. The
  typeface is self-hosted. ZIP codes are looked up in the reader's own browser.
- **Every figure links to its source.** Wrong published figures go in the corrections log.
- **Change log.** Every change a reader could notice gets a dated line on What's new.
- **No newspaper or TV polls**; academic and nonpartisan university surveys only. Keep all adults in
  survey data, with a "who was asked" line on each source.
- **Respect data providers' terms.** Ask permission where terms require it, download in bulk rather
  than scraping, and send one request at a time with pauses between them.

Differences to state on the new site's Methods page:

- **Recorded votes only.** Many state bills pass by voice vote, which records no names. Say so, and
  never infer a legislator's position from a voice vote.
- **Committees matter more** in many legislatures, and committee votes are often unpublished or
  inconsistent. Leave them out unless a state publishes them as records.
- **Sessions differ.** Texas meets in regular session in odd years only, plus special sessions. Show
  dates per state; don't assume Congress's two-year rhythm.

## 3. Same look and feel: what to copy

Copy these files from this repository as the starting point, then change only what's listed. Keep a
note in the new repository's README saying which files came from here, so later design changes can be
copied across.

| File here | What it is | Change for the state site |
| --- | --- | --- |
| `site/frame.html` | Every page's header, footer, link previews, the "Hide party labels" switch | Brand name; the header buttons (keep **Start here** as the one filled button); the footer's source list; add the cross-site link (section 4) |
| `site/site.css` | The whole design | Nothing at first. Keep the color tokens (below) identical so the sites match |
| `site/site.js` | The party switch, the installed app's Back button and install prompt, email links | Nothing, except the storage key prefix (below) |
| `site/cards.js` | Survey-question cards, vote shapes, poll grouping | Replace Congress terms ("Representative", "Senator") with the legislature's chamber names per state |
| `site/zip-finder.js` | ZIP code finder, looked up in the browser | Read state legislative districts instead (section 5); keep the privacy wording word for word |
| `site/static/fonts/` | Public Sans, self-hosted, with its license (OFL.txt) | Nothing |
| `site/static/sw.js`, `offline.html`, `site.webmanifest`, icons | Installable app and offline copies | New app name, icons and shortcuts. Change the cache prefix from `cc-` |
| `scripts/build_site.py` | Builds pages from Markdown and HTML, What's new feed, sitemap | NAV list; the feed title |
| `site/pages/privacy.md`, `methods.md`, `sources.md`, `faq.md`, `glossary.md`, `start.md`, `install.md`, `whats-new.md`, `corrections.md`, `about.md`, `contact.md` | Reference pages | Rewrite for state legislatures; keep the structure, headings and tone |

**Design tokens** (from `site/site.css`; copy exactly):

| Token | Light | Dark | Used for |
| --- | --- | --- | --- |
| `--ink` | `#1d2733` | `#e6ebef` | Text |
| `--ink-soft` | `#55616e` | `#a3afba` | Secondary text |
| `--rule` | `#d7dde3` | `#34404b` | Lines and borders |
| `--page` | `#e9eef1` | `#10161c` | Page background |
| `--surface` | `#ffffff` | `#182028` | Header and cards |
| `--mark` | `#2f6f66` | `#7cc2b5` | The accent: links, buttons, "with voters" |
| `--mark-soft` | `#cfe3de` | `#1f3b37` | Accent backgrounds |
| `--against` | `#b45309` | `#f0a35e` | "Against voters" |
| `--against-soft` | `#f6dfc6` | `#3d2a17` | Its background |
| `--unclear` | `#8a96a3` | `#8f9aa6` | Unclear or no data |

- **Typeface:** Public Sans at 400, 600 and 700, falling back to the system font. **Line height:** 1.55.
- **Brand:** the brand text has "vs" in `--mark` (`US Congress <span>vs</span> Voters`). The new site
  uses the same pattern.
- **Theme color** for the installed app and browser bar: `#2f6f66`, with `#e9eef1` as the background.
- **Vote shapes** (`mark()` in `web/cc-member-panel.js`): a filled dot for Yea, a ring for Nay, a square
  for Present, a dash for Did not vote. Never party colors.
- **Dark mode** follows the reader's device setting. There is no switch.

**Party-blind setting.** This site keeps "Hide party labels" only in the reader's browser
(`localStorage` key `cc-party-blind`). Browsers keep storage separate for each domain, so the setting
can't be shared directly. Both sites accept `?parties=hidden` or `?parties=shown` in a link and
remember it. Cross-site links (section 4) add `?parties=hidden` when the reader has labels hidden, so
the choice carries across. Use a different key prefix on the new site (for example `sv-`) so the two
are never confused.

## 4. Moving between the two sites

Links across should appear where a reader needs the other site, and nowhere else. Each site describes
the other in one plain sentence, so nobody mistakes one for the other.

- **Footer of both sites:** "A sister site, <Name>, does the same for state legislatures" (and the
  reverse).
- **Start here on this site:** the "Is it a federal issue?" paragraph in the `#contact` section points
  to USA.gov today. Once the state site covers a reader's state, link to it there too. Keep USA.gov for
  the states it doesn't cover.
- **ZIP finder:** after showing a reader's members of Congress, add "Your state legislators: <link>",
  passing the ZIP code **in the URL fragment** (`#zip=77378`), which browsers never send to a server.
  The state site does the same in reverse. The privacy promise holds on both sites.
- **State pages:** this site's Texas page (`states/texas/`) links to the state site's Texas page, and the
  reverse.
- **Same words for the same things:** "Surveyed votes", "Related", "With voters" and "Against voters",
  "Who was asked", "What's new" and "Corrections" mean the same on both sites. Copy the definitions from
  this site's `glossary.md`.
- **One app or two:** they are two installable apps (an app belongs to one domain). Each Install page
  mentions the other app.

Making these changes on this site is a normal change here: add a What's new line, and use the commit
rules in AGENTS.md.

## 5. Data

### Legislators, bills and votes: Open States

[Open States](https://open.pluralpolicy.com/data/) (now run by Plural) publishes data for all 50 state
legislatures, under a public domain dedication:

- **Legislators:** a YAML repository (on GitHub, in the `openstates/people` repository) and CSV files,
  with district, chamber, party and contact details including district offices. The person ID
  (`ocd-person/...`) plays the role Bioguide IDs play here.
- **Bills and votes:** CSV or JSON archives for each session, updated monthly. Votes include each
  legislator's position.
- **An API** with a free key, for checking recent changes between monthly archives. Keep the key in
  `.env`, never in the repository.

Load the monthly archives on a schedule, as this site loads House votes (a loader per source that
checks counts against the totals and logs each download). Cross-check a sample of votes against the
legislature's own journal before launch, and say on Sources how often the data is refreshed. Archives
are monthly, so the site can be a few weeks behind; say so plainly.

**Texas:** official records are on Texas Legislature Online (capitol.texas.gov) and in the House and
Senate journals, where record votes are published. Use them to check figures, and link to them as the
official record. Read the legislature's terms before downloading anything from it directly.

### ZIP code to state legislative districts: Census Bureau

The same Census Bureau folder this site uses for congressional districts
(`www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/`) also relates **state legislative
districts** to ZIP code areas:

- Lower chamber (Texas House): `tab20_sldl<year>20_zcta520_natl.txt`
- Upper chamber (Texas Senate): `tab20_sldu<year>20_zcta520_natl.txt`

`<year>` is the state legislative session year (2022 and 2024 so far). The fields match the
congressional file's (`GEOID_SLDL…` or `GEOID_SLDU…`, `GEOID_ZCTA5_20`, `AREALAND_PART`), so
`src/congress_congruence/ingest/zip_districts.py` can be adapted almost line for line.
Note that it must **commit its load** even when it checks for loaded data first (see its comment,
and the fix of November 22, 2026). State districts are smaller, so more ZIP codes cross their lines.
Show the land shares and the link to the state's address lookup, as this site's finder does.

### Surveys

The hard part. A vote can only be compared when a survey asked about the same proposal.

- **Texas Politics Project** (University of Texas): already used here (`config/tpp_items.yaml`,
  `src/congress_congruence/ingest/tpp.py`). Its polls ask Texans about state issues. Check its terms
  for the new use, and ask the project if they're unclear.
- **Other university polls** in each state, by the same rules as `statepolls.py` here: university and
  nonpartisan sources only, no newspaper or TV polls, each source shown separately.
- Statewide figures only, unless a source gives district-level estimates with margins of error.
- Each match goes in a YAML file per source, as here, with `match: same` or `match: related`, and
  waits for the maintainer's approval.

Never use AP VoteCast or Yale Climate Opinion Maps data without the written permission those sources
require. Both requests were pending when this guide was written; see PROJECT_NOTES.md.

## 6. Code to reuse

The new repository can start with copies of these, adapted:

| Here | Reuse for |
| --- | --- |
| `src/congress_congruence/db.py` and the numbered `sql/` files | The migration runner and the habit of one new numbered file per database change. Write a new schema; legislators and terms per state replace members |
| `src/congress_congruence/api/` (FastAPI) | Same read-only data service pattern behind nginx `/api/` |
| `scripts/build_profiles.py` | Legislator and state pages, link-preview images, the sitemap, the ZIP lookup file (`.json` and `.json.gz`) |
| `scripts/run_job.sh`, `scripts/crontab.txt` | Scheduled jobs that ping healthchecks.io (`HEALTHCHECK_<JOB>` in `.env`) |
| `scripts/backup_db.sh`, `scripts/send_latest_backup.sh`, `deploy/windows/download_backup.bat` | Nightly backups, plus off-server copies to the maintainer's OneDrive |
| `scripts/publish_web.sh`, `scripts/check_published.sh` | Publishing to dev and live, and the check that the live site matches the code on GitHub |
| `src/congress_congruence/vote_watch.py`, `reminders.py` | Emails about new votes that may affect a match, and dated reminders |
| `deploy/` | nginx, the systemd service and server setup notes. Add a new nginx site; don't edit this site's |
| `tests/` | The test layout. Keep the rule: commit only when all tests pass |

What not to copy: the Congress loaders (`ingest/votes.py`, `voteview.py`, `members.py`, `history.py`,
`bills.py`), the 1789 historical record, and Congress-specific survey files.

## 7. Server and accounts

- Follow `deploy/README.md` and `docs/HANDOVER.md` as templates. Every new account (domain, mailbox,
  Open States key, healthchecks.io checks) goes in the new repository's HANDOVER.
- If it shares this site's VPS: a separate database, a separate system user or at least a separate
  service, its own nginx site and certificate, and its own log and backup files. A failed state job
  must not affect this site.
- The security rules here apply: the maintainer types every password and key on the server; secrets
  live only in `.env`, which is never committed; two-factor stays on; one SSH key per machine; no
  GitHub Actions; no analytics, including Microsoft Clarity.

## 8. Suggested order of work

1. Settle section 1's decisions with the maintainer.
2. New repository: copy the site layer (section 3), set the name, and build an empty site that
   matches this one page for page. Show it to the maintainer on a dev address before anything else.
3. Database and loaders: legislators, then bills and votes for the first state, checked against the
   official journals.
4. ZIP finder for state districts.
5. Survey matches for the first state, each approved by the maintainer.
6. Reference pages: Start here, Methods, Sources, Privacy, FAQ, Glossary.
7. Cross-site links (section 4), on both sites, in the same week.
8. Go live, with a What's new entry on both sites.
