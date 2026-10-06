-- Study cohort: older adults with a new depression diagnosis, built step by step so every exclusion is counted.
--
-- Design
--   Index date:  first depression diagnosis in 2009 (ICD-9 296.2x, 296.3x, 300.4, 311) on an inpatient or
--                outpatient claim
--   Baseline:    the 365 days before the index date (covariates and the new-diagnosis washout)
--   Follow-up:   365 days after the index date, censored at death
--   Outcome:     first inpatient admission after the index date; death is recorded as a secondary outcome
--
-- Each step keeps beneficiaries from the previous step who meet one more criterion.

CREATE OR REPLACE TABLE dep_dx AS
SELECT DISTINCT bene_id, dx_dt
FROM stg_claim_dx
WHERE dx_dt IS NOT NULL AND regexp_matches(icd9, '^(2962|2963|3004|311)');

-- Step 1: everyone with a 2009 beneficiary record
CREATE OR REPLACE TABLE c1_all AS
SELECT bene_id, birth_dt, sex, race_cd, death_dt FROM stg_bene WHERE year = 2009;

-- Step 2: aged 65 or older on January 1, 2009
CREATE OR REPLACE TABLE c2_age AS
SELECT * FROM c1_all WHERE date_diff('day', birth_dt, DATE '2009-01-01') / 365.25 >= 65;

-- Step 3: 12 months of Part A, Part B, and Part D coverage in both 2008 and 2009
CREATE OR REPLACE TABLE c3_enrolled AS
SELECT * FROM c2_age WHERE bene_id IN (
    SELECT bene_id FROM stg_bene
    WHERE year IN (2008, 2009) AND part_a_months = 12 AND part_b_months = 12 AND part_d_months = 12
    GROUP BY bene_id HAVING COUNT(DISTINCT year) = 2);

-- Step 4: no Medicare Advantage (HMO) months in 2008-2009, so fee-for-service claims capture all care
CREATE OR REPLACE TABLE c4_ffs AS
SELECT * FROM c3_enrolled WHERE bene_id IN (
    SELECT bene_id FROM stg_bene WHERE year IN (2008, 2009)
    GROUP BY bene_id HAVING COUNT(DISTINCT year) = 2 AND MAX(hmo_months) = 0);

-- Step 5: a depression diagnosis in 2009; the first one is the index date
CREATE OR REPLACE TABLE c5_depression AS
SELECT c.*, d.index_dt
FROM c4_ffs c
JOIN (SELECT bene_id, MIN(dx_dt) AS index_dt FROM dep_dx WHERE year(dx_dt) = 2009 GROUP BY bene_id) d USING (bene_id);

-- Step 6: new diagnosis: no depression diagnosis in the 365 days before the index date
CREATE OR REPLACE TABLE c6_new_dx AS
SELECT c.* FROM c5_depression c
WHERE NOT EXISTS (SELECT 1 FROM dep_dx d WHERE d.bene_id = c.bene_id
                  AND d.dx_dt >= c.index_dt - INTERVAL 365 DAY AND d.dx_dt < c.index_dt);

-- Step 7: alive on the index date
CREATE OR REPLACE TABLE c7_alive AS
SELECT * FROM c6_new_dx WHERE death_dt IS NULL OR death_dt >= index_dt;

-- Charlson comorbidity index from baseline diagnoses
CREATE OR REPLACE TABLE baseline_conditions AS
SELECT DISTINCT c.bene_id, k.condition, k.weight
FROM c7_alive c
JOIN stg_claim_dx x ON x.bene_id = c.bene_id
     AND x.dx_dt >= c.index_dt - INTERVAL 365 DAY AND x.dx_dt < c.index_dt
JOIN charlson_codes k ON starts_with(x.icd9, k.prefix);

CREATE OR REPLACE TABLE charlson AS
SELECT b.bene_id, SUM(b.weight) AS charlson_index, COUNT(*) AS n_conditions
FROM baseline_conditions b
WHERE NOT EXISTS (  -- drop the milder form when the severe form is also present
    SELECT 1 FROM charlson_hierarchy h JOIN baseline_conditions s
      ON s.bene_id = b.bene_id AND s.condition = h.severe
    WHERE h.milder = b.condition)
GROUP BY b.bene_id;

-- Analysis-ready cohort: one row per beneficiary
CREATE OR REPLACE TABLE cohort AS
WITH admit AS (
    SELECT c.bene_id, MIN(i.from_dt) AS first_admit_dt
    FROM c7_alive c JOIN stg_inpatient i ON i.bene_id = c.bene_id
    WHERE i.from_dt > c.index_dt AND i.from_dt <= c.index_dt + INTERVAL 365 DAY
    GROUP BY c.bene_id
)
SELECT
    c.bene_id, c.index_dt, c.sex, c.race_cd,
    floor(date_diff('day', c.birth_dt, c.index_dt) / 365.25)::INTEGER AS age_at_index,
    COALESCE(ch.charlson_index, 0) AS charlson_index,
    b.cc_depression AS cms_depression_flag_2009,
    a.first_admit_dt IS NOT NULL AS hospitalized_1y,
    (c.death_dt IS NOT NULL AND c.death_dt <= c.index_dt + INTERVAL 365 DAY) AS died_1y,
    -- time to first admission; censored at death or 365 days
    date_diff('day', c.index_dt, LEAST(COALESCE(a.first_admit_dt, DATE '9999-12-31'),
                                      COALESCE(c.death_dt, DATE '9999-12-31'),
                                      CAST(c.index_dt + INTERVAL 365 DAY AS DATE))) AS days_followed
FROM c7_alive c
LEFT JOIN charlson ch USING (bene_id)
LEFT JOIN admit a USING (bene_id)
LEFT JOIN stg_bene b ON b.bene_id = c.bene_id AND b.year = 2009;

CREATE OR REPLACE TABLE attrition AS
SELECT * FROM (VALUES
    (1, 'Beneficiaries with a 2009 record', (SELECT COUNT(*) FROM c1_all)),
    (2, 'Aged 65 or older on Jan 1, 2009', (SELECT COUNT(*) FROM c2_age)),
    (3, 'Continuous Part A, B, and D coverage in 2008-2009', (SELECT COUNT(*) FROM c3_enrolled)),
    (4, 'Fee-for-service only (no HMO months) in 2008-2009', (SELECT COUNT(*) FROM c4_ffs)),
    (5, 'Depression diagnosis in 2009 (index date = first)', (SELECT COUNT(*) FROM c5_depression)),
    (6, 'New diagnosis: none in the prior 365 days', (SELECT COUNT(*) FROM c6_new_dx)),
    (7, 'Alive on the index date', (SELECT COUNT(*) FROM c7_alive))
) t(step, criterion, n_remaining);
