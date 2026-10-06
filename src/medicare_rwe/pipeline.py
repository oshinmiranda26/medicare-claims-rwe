"""Run the SQL pipeline on the raw CMS DE-SynPUF files with DuckDB.

Run:  python -m medicare_rwe.pipeline --raw-dir data/raw
Creates data/medicare.duckdb and writes the profile, data-quality checks, cohort attrition, and Table 1 to results/.
"""
import argparse
import time
from pathlib import Path

import duckdb
import pandas as pd

from medicare_rwe import charlson

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / "sql"
STEPS = ["01_load_raw.sql", "02_staging.sql", "03_data_quality.sql", "04_cohort.sql"]
RACE = {"1": "White", "2": "Black", "3": "Other", "5": "Hispanic"}


def run_sql_file(con, name, **params):
    sql = (SQL_DIR / name).read_text().format(**params)
    start = time.time()
    con.execute(sql)
    print(f"{name:<24} {time.time() - start:6.1f}s")


def profile(con):
    return con.execute("""
        SELECT 'beneficiary-years' AS item, COUNT(*) AS n FROM stg_bene
        UNION ALL SELECT 'unique beneficiaries', COUNT(DISTINCT bene_id) FROM stg_bene
        UNION ALL SELECT 'inpatient claims', COUNT(*) FROM stg_inpatient
        UNION ALL SELECT 'outpatient claims', COUNT(*) FROM stg_outpatient
        UNION ALL SELECT 'drug events (Part D fills)', COUNT(*) FROM stg_pde
        UNION ALL SELECT 'diagnosis codes (long format)', COUNT(*) FROM stg_claim_dx
        UNION ALL SELECT 'beneficiaries who died 2008-2010', COUNT(DISTINCT bene_id) FROM stg_bene WHERE death_dt IS NOT NULL
    """).df()


def build(con, raw_dir):
    for step in STEPS:
        if step == "04_cohort.sql":
            charlson.create_table(con)  # code lists the cohort step joins against
        run_sql_file(con, step, raw_dir=raw_dir)


def table_one(cohort):
    """Baseline characteristics and one-year outcomes of the cohort."""
    n = len(cohort)
    pct = lambda s: f"{100 * s.mean():.1f}%"
    rows = [("Beneficiaries", f"{n:,}"),
            ("Age at index, mean (SD)", f"{cohort.age_at_index.mean():.1f} ({cohort.age_at_index.std():.1f})"),
            ("Female", pct(cohort.sex == "F"))]
    rows += [(f"Race: {label}", pct(cohort.race_cd == code)) for code, label in RACE.items()]
    rows += [("Charlson index, mean (SD)", f"{cohort.charlson_index.mean():.2f} ({cohort.charlson_index.std():.2f})"),
             ("Charlson index 0", pct(cohort.charlson_index == 0)),
             ("Charlson index 1-2", pct(cohort.charlson_index.between(1, 2))),
             ("Charlson index 3+", pct(cohort.charlson_index >= 3)),
             ("CMS chronic-condition depression flag (2009)", pct(cohort.cms_depression_flag_2009.fillna(False))),
             ("Hospitalized within 1 year", pct(cohort.hospitalized_1y)),
             ("Died within 1 year", pct(cohort.died_1y))]
    return pd.DataFrame(rows, columns=["characteristic", "value"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--db", default="data/medicare.duckdb")
    args = ap.parse_args()
    raw_dir = Path(args.raw_dir).resolve()
    con = duckdb.connect(args.db)
    build(con, raw_dir.as_posix())

    Path("results").mkdir(exist_ok=True)
    prof = profile(con)
    dq = con.execute("SELECT *, ROUND(100.0 * n_flagged / NULLIF(n_records, 0), 3) AS pct_flagged "
                     "FROM dq_checks").df()
    prof.to_csv("results/table_profile.csv", index=False)
    dq.to_csv("results/data_quality.csv", index=False)
    print("\nProfile:\n" + prof.to_string(index=False))
    print("\nData quality:\n" + dq.to_string(index=False))

    attrition = con.execute("SELECT * FROM attrition ORDER BY step").df()
    attrition["excluded"] = (attrition.n_remaining.shift(1) - attrition.n_remaining).fillna(0).astype(int)
    cohort = con.execute("SELECT * FROM cohort").df()
    t1 = table_one(cohort)
    attrition.to_csv("results/attrition.csv", index=False)
    t1.to_csv("results/table1.csv", index=False)
    print("\nCohort attrition:\n" + attrition.to_string(index=False))
    print("\nTable 1:\n" + t1.to_string(index=False))


if __name__ == "__main__":
    main()
