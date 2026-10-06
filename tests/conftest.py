"""A tiny fake SynPUF-shaped dataset with known problems planted in it, for testing the SQL."""
import csv
from pathlib import Path

import pytest

BENE_COLS = ["DESYNPUF_ID", "BENE_BIRTH_DT", "BENE_DEATH_DT", "BENE_SEX_IDENT_CD", "BENE_RACE_CD", "BENE_ESRD_IND",
             "SP_STATE_CODE", "BENE_COUNTY_CD", "BENE_HI_CVRAGE_TOT_MONS", "BENE_SMI_CVRAGE_TOT_MONS",
             "BENE_HMO_CVRAGE_TOT_MONS", "PLAN_CVRG_MOS_NUM", "SP_ALZHDMTA", "SP_CHF", "SP_CHRNKIDN", "SP_CNCR",
             "SP_COPD", "SP_DEPRESSN", "SP_DIABETES", "SP_ISCHMCHT", "SP_OSTEOPRS", "SP_RA_OA", "SP_STRKETIA"]
CLAIM_COLS = (["DESYNPUF_ID", "CLM_ID", "SEGMENT", "CLM_FROM_DT", "CLM_THRU_DT", "PRVDR_NUM", "CLM_PMT_AMT",
               "CLM_ADMSN_DT", "NCH_BENE_DSCHRG_DT", "CLM_DRG_CD", "ADMTNG_ICD9_DGNS_CD"]
              + [f"ICD9_DGNS_CD_{i}" for i in range(1, 11)])
PDE_COLS = ["DESYNPUF_ID", "PDE_ID", "SRVC_DT", "PROD_SRVC_ID", "QTY_DSPNSD_NUM", "DAYS_SUPLY_NUM", "PTNT_PAY_AMT",
            "TOT_RX_CST_AMT"]


def write(path, cols, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def bene(pid, birth="19400101", death="", a=12, d=12, dep="2"):
    return {"DESYNPUF_ID": pid, "BENE_BIRTH_DT": birth, "BENE_DEATH_DT": death, "BENE_SEX_IDENT_CD": "2",
            "BENE_HI_CVRAGE_TOT_MONS": str(a), "BENE_SMI_CVRAGE_TOT_MONS": "12", "BENE_HMO_CVRAGE_TOT_MONS": "0",
            "PLAN_CVRG_MOS_NUM": str(d), "SP_DEPRESSN": dep}


@pytest.fixture
def raw_dir(tmp_path):
    for year in (2008, 2009, 2010):
        # B dies in 2009 but still has a 2010 record (planted problem); C has no Part A coverage in 2009
        rows = [bene("A"), bene("B", death="20090615" if year == 2009 else ""), bene("C", a=0 if year == 2009 else 12)]
        write(tmp_path / f"DE1_0_{year}_Beneficiary_Summary_File_Sample_1.csv", BENE_COLS, rows)
    ip = [
        {"DESYNPUF_ID": "A", "CLM_ID": "1", "SEGMENT": "1", "CLM_FROM_DT": "20080301", "CLM_THRU_DT": "20080305",
         "ICD9_DGNS_CD_1": "29620", "ICD9_DGNS_CD_2": "4019"},
        {"DESYNPUF_ID": "B", "CLM_ID": "2", "SEGMENT": "1", "CLM_FROM_DT": "20091001", "CLM_THRU_DT": "20090901"},  # end<start, after death
        {"DESYNPUF_ID": "C", "CLM_ID": "3", "SEGMENT": "1", "CLM_FROM_DT": "20090505", "CLM_THRU_DT": "20090506"},  # no Part A
        {"DESYNPUF_ID": "Z", "CLM_ID": "4", "SEGMENT": "1", "CLM_FROM_DT": "2008XXXX", "CLM_THRU_DT": "20080101"},  # unknown bene, bad date
    ]
    write(tmp_path / "DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv", CLAIM_COLS, ip)
    op = [{"DESYNPUF_ID": "A", "CLM_ID": "10", "SEGMENT": "1", "CLM_FROM_DT": "20080401", "CLM_THRU_DT": "20080401",
           "ICD9_DGNS_CD_1": "311"}]
    write(tmp_path / "DE1_0_2008_to_2010_Outpatient_Claims_Sample_1.csv", CLAIM_COLS, op)
    pde = [{"DESYNPUF_ID": "A", "PDE_ID": "p1", "SRVC_DT": "20080110", "PROD_SRVC_ID": "00093", "DAYS_SUPLY_NUM": "30"},
           {"DESYNPUF_ID": "A", "PDE_ID": "p2", "SRVC_DT": "20080210", "PROD_SRVC_ID": "00093", "DAYS_SUPLY_NUM": "0"},
           {"DESYNPUF_ID": "B", "PDE_ID": "p3", "SRVC_DT": "20091110", "PROD_SRVC_ID": "00093", "DAYS_SUPLY_NUM": "30"}]
    write(tmp_path / "DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_1.csv", PDE_COLS, pde)
    return tmp_path
