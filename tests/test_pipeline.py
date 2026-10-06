import duckdb

from medicare_rwe import pipeline
from medicare_rwe.pipeline import profile


def build(raw_dir):
    con = duckdb.connect()
    pipeline.build(con, raw_dir.as_posix())
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


def test_cohort_criteria_and_attrition(cohort_raw_dir):
    con = build(cohort_raw_dir)
    att = dict(con.execute("SELECT step, n_remaining FROM attrition").fetchall())
    assert att == {1: 6, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1, 7: 1}
    rows = con.execute("SELECT bene_id, index_dt::VARCHAR, charlson_index, hospitalized_1y, days_followed "
                       "FROM cohort").fetchall()
    # D: index 2009-03-01; baseline CHF (1) + complicated diabetes (2, replaces uncomplicated) = 3;
    # admitted 2009-06-01 -> event after 92 days. The index-day inpatient claim does not count as the outcome.
    assert rows == [("D", "2009-03-01", 3, True, 92)]


def test_charlson_prefixes():
    from medicare_rwe.charlson import codes_frame
    df = codes_frame()
    chf = df[df.condition == "congestive_heart_failure"].prefix
    assert "428" in set(chf) and "4254" in set(chf) and "4253" not in set(chf)
    assert "042" in set(df[df.condition == "hiv_aids"].prefix)
