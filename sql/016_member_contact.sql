-- How to reach serving members, and which congressional district each ZIP code is in.
--
-- member_contact: the official website, contact form, Washington office phone and address of each
--   serving member, from the latest term in congress-legislators (legislators-current.yaml).
--   Replaced in full by every members run.
-- member_office: their state and district offices (legislators-district-offices.yaml). Replaced too.
-- zip_district: ZIP Code Tabulation Areas (the Census Bureau's version of ZIP codes) and the
--   congressional districts they fall in, with the share of the ZCTA's land in each, from the Census
--   relationship file for one Congress (ingest/zip_districts.py). The site turns this into a static
--   file, so a reader's ZIP code is looked up in their own browser and never sent to the server.

create table core.member_contact (
    bioguide_id  text primary key references core.member on delete cascade,
    website      text,
    contact_form text,
    phone        text,
    address      text
);

create table core.member_office (
    bioguide_id text not null references core.member on delete cascade,
    office_id   text not null,
    city        text,
    state       text,
    address     text,
    suite       text,
    building    text,
    zip         text,
    phone       text,
    primary key (bioguide_id, office_id)
);

create table core.zip_district (
    congress  smallint not null,
    zcta      text not null check (zcta ~ '^[0-9]{5}$'),
    state     text not null,
    district  smallint not null,          -- 0 = at-large (and delegates' seats)
    land_share real not null,             -- share of the ZCTA's land in this district, 0 to 1
    primary key (congress, zcta, state, district)
);

do $$
begin
    if exists (select 1 from pg_roles where rolname = 'ccapi') then
        grant select on core.member_contact, core.member_office, core.zip_district to ccapi;
    end if;
end $$;
