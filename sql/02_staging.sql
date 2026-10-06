-- Typed, cleaned staging tables. Dates arrive as YYYYMMDD text; TRY_STRPTIME returns NULL for
-- unparseable values instead of failing, and the data-quality step counts those NULLs.

CREATE OR REPLACE TABLE stg_bene AS
SELECT
    DESYNPUF_ID                                              AS bene_id,
    file_year                                                AS year,
    TRY_STRPTIME(BENE_BIRTH_DT, '%Y%m%d')::DATE              AS birth_dt,
    TRY_STRPTIME(NULLIF(BENE_DEATH_DT, ''), '%Y%m%d')::DATE  AS death_dt,
    CASE BENE_SEX_IDENT_CD WHEN '1' THEN 'M' WHEN '2' THEN 'F' END AS sex,
    BENE_RACE_CD                                             AS race_cd,
    SP_STATE_CODE                                            AS state_cd,
    TRY_CAST(BENE_HI_CVRAGE_TOT_MONS AS INTEGER)             AS part_a_months,
    TRY_CAST(BENE_SMI_CVRAGE_TOT_MONS AS INTEGER)            AS part_b_months,
    TRY_CAST(BENE_HMO_CVRAGE_TOT_MONS AS INTEGER)            AS hmo_months,
    TRY_CAST(PLAN_CVRG_MOS_NUM AS INTEGER)                   AS part_d_months,
    SP_DEPRESSN = '1'                                        AS cc_depression,
    SP_DIABETES = '1'                                        AS cc_diabetes,
    SP_CHF = '1'                                             AS cc_chf,
    SP_COPD = '1'                                            AS cc_copd,
    SP_ALZHDMTA = '1'                                        AS cc_alzheimers
FROM raw_bene;

CREATE OR REPLACE TABLE stg_inpatient AS
SELECT
    DESYNPUF_ID AS bene_id, CLM_ID AS clm_id, SEGMENT AS segment,
    TRY_STRPTIME(CLM_FROM_DT, '%Y%m%d')::DATE         AS from_dt,
    TRY_STRPTIME(CLM_THRU_DT, '%Y%m%d')::DATE         AS thru_dt,
    TRY_STRPTIME(CLM_ADMSN_DT, '%Y%m%d')::DATE        AS admit_dt,
    TRY_STRPTIME(NCH_BENE_DSCHRG_DT, '%Y%m%d')::DATE  AS discharge_dt,
    TRY_CAST(CLM_PMT_AMT AS DOUBLE)                   AS payment,
    CLM_DRG_CD                                        AS drg
FROM raw_inpatient;

CREATE OR REPLACE TABLE stg_outpatient AS
SELECT
    DESYNPUF_ID AS bene_id, CLM_ID AS clm_id, SEGMENT AS segment,
    TRY_STRPTIME(CLM_FROM_DT, '%Y%m%d')::DATE AS from_dt,
    TRY_STRPTIME(CLM_THRU_DT, '%Y%m%d')::DATE AS thru_dt,
    TRY_CAST(CLM_PMT_AMT AS DOUBLE)           AS payment
FROM raw_outpatient;

CREATE OR REPLACE TABLE stg_pde AS
SELECT
    DESYNPUF_ID AS bene_id, PDE_ID AS pde_id,
    TRY_STRPTIME(SRVC_DT, '%Y%m%d')::DATE   AS fill_dt,
    PROD_SRVC_ID                            AS ndc,
    TRY_CAST(QTY_DSPNSD_NUM AS DOUBLE)      AS quantity,
    TRY_CAST(DAYS_SUPLY_NUM AS INTEGER)     AS days_supply,
    TRY_CAST(TOT_RX_CST_AMT AS DOUBLE)      AS total_cost
FROM raw_pde;

-- Long-format diagnosis table: one row per claim x diagnosis position (wide ICD9_DGNS_CD_1..10 -> rows)
CREATE OR REPLACE TABLE stg_claim_dx AS
WITH ip AS (
    UNPIVOT (SELECT DESYNPUF_ID, CLM_ID, CLM_FROM_DT, COLUMNS('^ICD9_DGNS_CD_[0-9]+$') FROM raw_inpatient)
    ON COLUMNS('^ICD9_DGNS_CD_[0-9]+$') INTO NAME dx_position VALUE icd9
), op AS (
    UNPIVOT (SELECT DESYNPUF_ID, CLM_ID, CLM_FROM_DT, COLUMNS('^ICD9_DGNS_CD_[0-9]+$') FROM raw_outpatient)
    ON COLUMNS('^ICD9_DGNS_CD_[0-9]+$') INTO NAME dx_position VALUE icd9
)
SELECT DESYNPUF_ID AS bene_id, CLM_ID AS clm_id, 'inpatient' AS setting,
       TRY_STRPTIME(CLM_FROM_DT, '%Y%m%d')::DATE AS dx_dt,
       CAST(regexp_extract(dx_position, '[0-9]+$') AS INTEGER) AS dx_position, icd9
FROM ip WHERE icd9 IS NOT NULL AND icd9 <> ''
UNION ALL
SELECT DESYNPUF_ID, CLM_ID, 'outpatient', TRY_STRPTIME(CLM_FROM_DT, '%Y%m%d')::DATE,
       CAST(regexp_extract(dx_position, '[0-9]+$') AS INTEGER), icd9
FROM op WHERE icd9 IS NOT NULL AND icd9 <> '';
