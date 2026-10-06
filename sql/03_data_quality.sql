-- Data-quality checks: each row reports how many records fail a rule.
-- These are the questions to answer before trusting any claims analysis.

CREATE OR REPLACE TABLE dq_checks AS
WITH bene_last AS (  -- one row per beneficiary: most recent record, used for birth and death dates
    SELECT * FROM stg_bene QUALIFY ROW_NUMBER() OVER (PARTITION BY bene_id ORDER BY year DESC) = 1
),
death AS (SELECT bene_id, MIN(death_dt) AS death_dt FROM stg_bene WHERE death_dt IS NOT NULL GROUP BY bene_id)
SELECT 'bene: duplicate beneficiary-year rows' AS check_name,
       (SELECT COUNT(*) - COUNT(DISTINCT (bene_id, year)) FROM stg_bene) AS n_flagged,
       (SELECT COUNT(*) FROM stg_bene) AS n_records
UNION ALL SELECT 'bene: unparseable or missing birth date',
       (SELECT COUNT(*) FROM stg_bene WHERE birth_dt IS NULL), (SELECT COUNT(*) FROM stg_bene)
UNION ALL SELECT 'bene: implausible age (<0 or >110 on Jan 1 of file year)',
       (SELECT COUNT(*) FROM stg_bene WHERE date_diff('year', birth_dt, make_date(year, 1, 1)) NOT BETWEEN 0 AND 110),
       (SELECT COUNT(*) FROM stg_bene)
UNION ALL SELECT 'bene: coverage months outside 0-12',
       (SELECT COUNT(*) FROM stg_bene WHERE part_a_months NOT BETWEEN 0 AND 12 OR part_d_months NOT BETWEEN 0 AND 12),
       (SELECT COUNT(*) FROM stg_bene)
UNION ALL SELECT 'bene: record in a year after death',
       (SELECT COUNT(*) FROM stg_bene b JOIN death d USING (bene_id) WHERE b.year > year(d.death_dt)),
       (SELECT COUNT(*) FROM stg_bene)
UNION ALL SELECT 'inpatient: duplicate claim id + segment',
       (SELECT COUNT(*) - COUNT(DISTINCT (clm_id, segment)) FROM stg_inpatient), (SELECT COUNT(*) FROM stg_inpatient)
UNION ALL SELECT 'inpatient: missing or unparseable claim start date',
       (SELECT COUNT(*) FROM stg_inpatient WHERE from_dt IS NULL), (SELECT COUNT(*) FROM stg_inpatient)
UNION ALL SELECT 'inpatient: claim end before start',
       (SELECT COUNT(*) FROM stg_inpatient WHERE thru_dt < from_dt), (SELECT COUNT(*) FROM stg_inpatient)
UNION ALL SELECT 'inpatient: claim after beneficiary death',
       (SELECT COUNT(*) FROM stg_inpatient i JOIN death d USING (bene_id) WHERE i.from_dt > d.death_dt),
       (SELECT COUNT(*) FROM stg_inpatient)
UNION ALL SELECT 'inpatient: beneficiary missing from summary file',
       (SELECT COUNT(*) FROM stg_inpatient i ANTI JOIN bene_last USING (bene_id)), (SELECT COUNT(*) FROM stg_inpatient)
UNION ALL SELECT 'inpatient: claim year without Part A coverage',
       (SELECT COUNT(*) FROM stg_inpatient i JOIN stg_bene b ON i.bene_id = b.bene_id AND year(i.from_dt) = b.year
        WHERE b.part_a_months = 0), (SELECT COUNT(*) FROM stg_inpatient)
UNION ALL SELECT 'outpatient: missing or unparseable claim start date',
       (SELECT COUNT(*) FROM stg_outpatient WHERE from_dt IS NULL), (SELECT COUNT(*) FROM stg_outpatient)
UNION ALL SELECT 'outpatient: claim end before start',
       (SELECT COUNT(*) FROM stg_outpatient WHERE thru_dt < from_dt), (SELECT COUNT(*) FROM stg_outpatient)
UNION ALL SELECT 'pde: missing or unparseable fill date',
       (SELECT COUNT(*) FROM stg_pde WHERE fill_dt IS NULL), (SELECT COUNT(*) FROM stg_pde)
UNION ALL SELECT 'pde: days supply missing, zero, or > 365',
       (SELECT COUNT(*) FROM stg_pde WHERE days_supply IS NULL OR days_supply <= 0 OR days_supply > 365),
       (SELECT COUNT(*) FROM stg_pde)
UNION ALL SELECT 'pde: fill after beneficiary death',
       (SELECT COUNT(*) FROM stg_pde p JOIN death d USING (bene_id) WHERE p.fill_dt > d.death_dt),
       (SELECT COUNT(*) FROM stg_pde)
UNION ALL SELECT 'pde: fill in a year without Part D coverage',
       (SELECT COUNT(*) FROM stg_pde p JOIN stg_bene b ON p.bene_id = b.bene_id AND year(p.fill_dt) = b.year
        WHERE b.part_d_months = 0), (SELECT COUNT(*) FROM stg_pde);
