"""Charlson comorbidity index from ICD-9-CM codes (Quan et al., 2005 coding algorithm; original Charlson weights).

Codes in the CMS files have no decimal point (428.0 -> "4280"), so each condition is defined by code prefixes.
Ranges like 430.x-438.x are expanded to prefixes 430, 431, ..., 438.
"""
import pandas as pd


def rng(a, b):
    """Integer-like prefix range, keeping zero padding: rng('140', '172') -> ['140', ..., '172']."""
    width = len(a)
    return [str(i).zfill(width) for i in range(int(a), int(b) + 1)]


CHARLSON = {  # condition: (weight, prefixes)
    "myocardial_infarction": (1, ["410", "412"]),
    "congestive_heart_failure": (1, ["39891", "40201", "40211", "40291", "40401", "40403", "40411", "40413",
                                     "40491", "40493", *rng("4254", "4259"), "428"]),
    "peripheral_vascular": (1, ["0930", "4373", "440", "441", *rng("4431", "4439"), "4471", "5571", "5579", "V434"]),
    "cerebrovascular": (1, ["36234", *rng("430", "438")]),
    "dementia": (1, ["290", "2941", "3312"]),
    "chronic_pulmonary": (1, ["4168", "4169", *rng("490", "505"), "5064", "5081", "5088"]),
    "rheumatic": (1, ["4465", *rng("7100", "7104"), *rng("7140", "7142"), "7148", "725"]),
    "peptic_ulcer": (1, rng("531", "534")),
    "mild_liver": (1, ["07022", "07023", "07032", "07033", "07044", "07054", "0706", "0709", "570", "571",
                       "5733", "5734", "5738", "5739", "V427"]),
    "diabetes_uncomplicated": (1, [*rng("2500", "2503"), "2508", "2509"]),
    "diabetes_complicated": (2, rng("2504", "2507")),
    "hemiplegia_paraplegia": (2, ["3341", "342", "343", *rng("3440", "3446"), "3449"]),
    "renal": (2, ["40301", "40311", "40391", "40402", "40403", "40412", "40413", "40492", "40493", "582",
                  *rng("5830", "5837"), "585", "586", "5880", "V420", "V451", "V56"]),
    "malignancy": (2, [*rng("140", "172"), *rng("174", "194"), *rng("1950", "1958"), *rng("200", "208"), "2386"]),
    "severe_liver": (3, [*rng("4560", "4562"), *rng("5722", "5728")]),
    "metastatic_tumor": (6, rng("196", "199")),
    "hiv_aids": (6, rng("042", "044")),
}
# When both a milder and a more severe form are present, only the more severe one counts
HIERARCHY = {"mild_liver": "severe_liver", "diabetes_uncomplicated": "diabetes_complicated",
             "malignancy": "metastatic_tumor"}


def codes_frame():
    return pd.DataFrame([{"condition": c, "weight": w, "prefix": p}
                         for c, (w, prefixes) in CHARLSON.items() for p in prefixes])


def create_table(con):
    con.register("charlson_df", codes_frame())
    con.execute("CREATE OR REPLACE TABLE charlson_codes AS SELECT * FROM charlson_df")
    con.unregister("charlson_df")
    con.execute("CREATE OR REPLACE TABLE charlson_hierarchy AS SELECT * FROM (VALUES "
                + ", ".join(f"('{m}', '{s}')" for m, s in HIERARCHY.items()) + ") t(milder, severe)")
