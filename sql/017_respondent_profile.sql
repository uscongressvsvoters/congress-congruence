-- Who answered each survey, and who lives in each state, so readers can compare the two.
--
-- survey_respondent_profile: a survey's respondents by sex, age, race and ethnicity, and education,
-- for everyone ('US') and each state. Written when the survey is loaded, from its respondent file
-- (CES and Nationscape; sources that publish only results have none). raw_share counts each person
-- once; weighted_share uses the survey's own weights, i.e. what its published figures rest on.
-- census_year is the American Community Survey year to compare with (the survey's year; the page
-- uses the nearest year loaded in adult_profile).
create table core.survey_respondent_profile (
    survey          text not null,
    area            char(2) not null,       -- a state code, or 'US' for every respondent
    dimension       text not null check (dimension in ('sex', 'age', 'race', 'education')),
    grp             text not null,          -- e.g. 'female', '18_34', 'hispanic', 'ba_plus'
    respondents     integer not null,       -- people in the group (unweighted count)
    raw_share       real not null,          -- respondents / everyone with a known answer, 0..1
    weighted_share  real,                   -- the same with the survey's weights, 0..1
    census_year     smallint not null,
    primary key (survey, area, dimension, grp)
);

-- Adults (18 and over) by the same groups, from the Census Bureau's American Community Survey 1-year
-- estimates (tables B15001 for sex, age and education; B01001B, D, H and I for race and ethnicity).
create table core.adult_profile (
    acs_year   smallint not null,
    area       char(2) not null,           -- a state code, or 'US'
    dimension  text not null check (dimension in ('sex', 'age', 'race', 'education')),
    grp        text not null,
    adults     integer not null,
    share      real not null,              -- of all adults in the area, 0..1
    source     text not null,
    loaded_at  timestamptz not null default now(),
    primary key (acs_year, area, dimension, grp)
);
