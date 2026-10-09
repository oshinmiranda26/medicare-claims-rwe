# Medicare Claims RWE: From Raw Files to an Analysis-Ready Cohort

An end-to-end real-world evidence pipeline built from **raw** Medicare claims files: loading, typing, data-quality
checks, enrollment logic, a new-diagnosis cohort with a washout period, outcomes, and a Charlson comorbidity index
computed from raw ICD-9 codes. Written mostly in SQL (DuckDB), with tests that plant known data problems and check
that the pipeline catches them.

> **Why this project:** analyzing claims data that someone else has already cleaned is a different skill from
> building a cohort from raw files. This repository shows the second: every step from the CMS files to Table 1 is
> visible, documented, and reproducible.

## Data

CMS 2008-2010 Data Entrepreneurs' Synthetic Public Use File (DE-SynPUF), Sample 1, available on CMS.gov under
Medicare Claims Synthetic Public Use Files: beneficiary summary files (2008, 2009, 2010), inpatient, outpatient, and
Part D prescription drug event files. The DE-SynPUF mirrors the structure of CMS Limited Data Sets, so code built on
it is designed to run on real Medicare claims. CMS notes that, because of the synthetic process used to protect
privacy, it has very limited inferential value: **this project demonstrates the pipeline, not clinical findings.**
Data files are not included; download them from CMS into `data/raw/`.

| Raw data loaded | Count |
|---|---|
| Unique beneficiaries | 116,352 |
| Beneficiary-years | 343,644 |
| Inpatient claims | 66,773 |
| Outpatient claims | 790,790 |
| Part D prescription fills | 5,552,421 |
| Diagnosis codes (reshaped to one row per claim and code) | 2,611,067 |

## Pipeline

```
sql/01_load_raw.sql        load every raw file exactly as delivered, all columns as text
sql/02_staging.sql         typed, cleaned staging tables; wide diagnosis columns reshaped to long format
sql/03_data_quality.sql    17 data-quality rules
sql/04_cohort.sql          step-by-step cohort with attrition counts, Charlson index, and outcomes
```

Loading raw files as text means nothing is silently coerced or dropped at load time; malformed values become
explicit nulls in staging, where the data-quality step counts them.

## Data quality

| Check | Flagged | % |
|---|---|---|
| Prescription fills with days supply missing, zero, or over 365 | 117,726 | 2.1 |
| Outpatient claims with no usable start date | 11,253 | 1.4 |
| Inpatient claims in a year without Part A coverage | 479 | 0.7 |
| Prescription fills in a year without Part D coverage | 23,088 | 0.4 |
| Inpatient claims with no usable start date | 68 | 0.1 |
| Duplicate claims, impossible ages, claims or fills after death | 0 | 0 |

Handling decisions: claims without usable dates are excluded from time-based analyses; fills with invalid days
supply are excluded from exposure calculations; continuous-enrollment requirements remove claims that fall outside
coverage. The full table is in `results/data_quality.csv`.

## Cohort: older adults with a new depression diagnosis

| Design element | Definition |
|---|---|
| Index date | First depression diagnosis in 2009 (ICD-9 296.2x, 296.3x, 300.4, 311) on an inpatient or outpatient claim |
| Baseline | 365 days before the index date |
| Washout | No depression diagnosis during the baseline, so the diagnosis is new |
| Follow-up | 365 days after the index date, censored at death |
| Outcome | First inpatient admission after the index date (an admission on the index date is the reason for entry, not an outcome); death as a secondary outcome |

**Attrition**

| Step | Remaining | Excluded |
|---|---|---|
| Beneficiaries with a 2009 record | 114,538 | |
| Aged 65 or older on January 1, 2009 | 95,730 | 18,808 |
| Continuous Part A, B, and D coverage in 2008-2009 | 46,374 | 49,356 |
| Fee-for-service only (no Medicare Advantage months) | 27,935 | 18,439 |
| Depression diagnosis in 2009 | 1,878 | 26,057 |
| No depression diagnosis in the prior 365 days | **1,681** | 197 |

Requiring continuous Part D coverage removed more than half of the aged population, so any drug-exposure analysis
on this cohort generalizes only to beneficiaries with stable drug coverage. Fee-for-service restriction is standard
because Medicare Advantage care is largely absent from fee-for-service claims.

**Table 1**

| Characteristic | Value |
|---|---|
| Age at index, mean (SD) | 77.8 (8.6) |
| Female | 62.6% |
| Charlson index, mean (SD) | 3.11 (3.06) |
| Charlson index 0 / 1-2 / 3+ | 25.5% / 25.8% / 48.7% |
| CMS chronic-condition depression flag (2009) | 99.6% |
| Hospitalized within 1 year | 27.7% |
| Died within 1 year | 1.0% |

The Charlson index uses the Quan et al. (2005) ICD-9-CM coding algorithm with original Charlson weights,
including the hierarchy rules (complicated diabetes, severe liver disease, and metastatic cancer replace their milder
forms).

## Interpreting the results critically

Two results do not match clinical expectations, and both have explanations worth stating:

- **Only 197 patients (about 10%) failed the new-diagnosis washout.** Carrier (physician) claims were not loaded,
  and much depression is diagnosed in physician offices, so some patients classified as newly diagnosed are likely
  prevalent cases. The 99.6% agreement with CMS's chronic-condition flag confirms these patients have depression,
  not that the diagnosis is new, because CMS builds that flag from all claim types over a lookback window.
- **One-year mortality of 1.0% is implausibly low** for 78-year-olds with this comorbidity burden. CMS documents
  attrition and disclosure treatment in the synthetic 2010 data, which is the likely cause.

## How to run

```bash
pip install -r requirements.txt
pip install -e .
pytest                                              # tests plant data problems and check they are caught
python -m medicare_rwe.pipeline --raw-dir data/raw  # about 10 seconds on a laptop
```

Results are written to `results/` (profile, data quality, attrition, Table 1).

## Limitations

- Synthetic data with scrambled clinical relationships; results demonstrate the pipeline, not clinical evidence.
- Carrier claims not included, which undercounts diagnoses and weakens the new-diagnosis definition.
- The DE-SynPUF provides yearly counts of covered months rather than month-by-month enrollment flags, so
  continuous enrollment is defined as 12 covered months per year, coarser than with real Medicare files.

## Next steps

- Add carrier claims and compare the new-diagnosis definition with and without them.
- Antidepressant exposure from raw Part D codes, a new-user design, and propensity-score weighting.

## Author

**Oshin Miranda, PhD** | [LinkedIn](https://www.linkedin.com/in/oshin-miranda-ph-d-9551781b5/) | [GitHub](https://github.com/oshinmiranda26)
