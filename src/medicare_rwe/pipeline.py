"""Run the SQL pipeline on the raw CMS DE-SynPUF files with DuckDB.

Run:  python -m medicare_rwe.pipeline --raw-dir data/raw
Creates data/medicare.duckdb and writes results/table_profile.csv and results/data_quality.csv.
"""
import argparse
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / "sql"
STEPS = ["01_load_raw.sql", "02_staging.sql", "03_data_quality.sql"]


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--db", default="data/medicare.duckdb")
    args = ap.parse_args()
    raw_dir = Path(args.raw_dir).resolve()
    con = duckdb.connect(args.db)
    for step in STEPS:
        run_sql_file(con, step, raw_dir=raw_dir.as_posix())

    Path("results").mkdir(exist_ok=True)
    prof = profile(con)
    dq = con.execute("SELECT *, ROUND(100.0 * n_flagged / NULLIF(n_records, 0), 3) AS pct_flagged "
                     "FROM dq_checks").df()
    prof.to_csv("results/table_profile.csv", index=False)
    dq.to_csv("results/data_quality.csv", index=False)
    print("\nProfile:\n" + prof.to_string(index=False))
    print("\nData quality:\n" + dq.to_string(index=False))


if __name__ == "__main__":
    main()
