import duckdb

from medicare_rwe.pipeline import STEPS, profile, run_sql_file


def build(raw_dir):
    con = duckdb.connect()
    for step in STEPS:
        run_sql_file(con, step, raw_dir=raw_dir.as_posix())
    return con


def checks(con):
    return dict(con.execute("SELECT check_name, n_flagged FROM dq_checks").fetchall())


def test_staging_types_and_counts(raw_dir):
    con = build(raw_dir)
    p = dict(profile(con).values.tolist())
    assert p["unique beneficiaries"] == 3 and p["inpatient claims"] == 4 and p["drug events (Part D fills)"] == 3
    assert con.execute("SELECT typeof(birth_dt) FROM stg_bene LIMIT 1").fetchone()[0] == "DATE"


def test_long_diagnosis_table(raw_dir):
    con = build(raw_dir)
    rows = con.execute("SELECT setting, dx_position, icd9 FROM stg_claim_dx ORDER BY setting, dx_position").fetchall()
    assert rows == [("inpatient", 1, "29620"), ("inpatient", 2, "4019"), ("outpatient", 1, "311")]


def test_planted_quality_problems_are_caught(raw_dir):
    c = checks(build(raw_dir))
    assert c["bene: record in a year after death"] == 1
    assert c["inpatient: claim end before start"] == 1
    assert c["inpatient: claim after beneficiary death"] == 1
    assert c["inpatient: beneficiary missing from summary file"] == 1
    assert c["inpatient: claim year without Part A coverage"] == 1
    assert c["inpatient: missing or unparseable claim start date"] == 1
    assert c["pde: days supply missing, zero, or > 365"] == 1
    assert c["pde: fill after beneficiary death"] == 1
    assert c["bene: implausible age (<0 or >110 on Jan 1 of file year)"] == 0
