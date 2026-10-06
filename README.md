# Medicare Claims RWE: From Raw Files to an Analysis-Ready Cohort

An end-to-end real-world evidence pipeline built from **raw** Medicare claims files: loading, typing, data-quality
checks, enrollment logic, a new-user drug cohort, outcomes, comorbidity scoring, and a comparative analysis,
written mostly in SQL (DuckDB).

**Status:** in progress. Raw-file loading, typed staging tables, a long-format diagnosis table, and data-quality
checks are complete; cohort construction and analysis are next.

## Data

CMS 2008-2010 Data Entrepreneurs' Synthetic Public Use File (DE-SynPUF), available on CMS.gov under Medicare Claims Synthetic Public Use Files,
Sample 1: beneficiary summary files (2008, 2009, 2010), inpatient, outpatient, and Part D prescription drug event
files. The DE-SynPUF mirrors the structure of CMS Limited Data Sets, so code built on it is designed to run on
real Medicare claims. Because of the synthetic process used to protect privacy, CMS notes it has very limited
inferential value: this project demonstrates the pipeline, not clinical findings. Data files are not included;
download them from CMS into `data/raw/`.

## Quick start
```bash
pip install -r requirements.txt
pip install -e .
pytest
python -m medicare_rwe.pipeline --raw-dir data/raw
```
