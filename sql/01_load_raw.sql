-- Load the raw CMS DE-SynPUF CSV files exactly as delivered (every column as text).
-- Typing and cleaning happen in the next step, so nothing is silently coerced at load time.

CREATE OR REPLACE TABLE raw_bene AS
SELECT *, 2008 AS file_year FROM read_csv('{raw_dir}/DE1_0_2008_Beneficiary_Summary_File_Sample_1.csv', all_varchar = true, header = true)
UNION ALL BY NAME
SELECT *, 2009 AS file_year FROM read_csv('{raw_dir}/DE1_0_2009_Beneficiary_Summary_File_Sample_1.csv', all_varchar = true, header = true)
UNION ALL BY NAME
SELECT *, 2010 AS file_year FROM read_csv('{raw_dir}/DE1_0_2010_Beneficiary_Summary_File_Sample_1.csv', all_varchar = true, header = true);

CREATE OR REPLACE TABLE raw_inpatient AS
SELECT * FROM read_csv('{raw_dir}/DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv', all_varchar = true, header = true);

CREATE OR REPLACE TABLE raw_outpatient AS
SELECT * FROM read_csv('{raw_dir}/DE1_0_2008_to_2010_Outpatient_Claims_Sample_1.csv', all_varchar = true, header = true);

CREATE OR REPLACE TABLE raw_pde AS
SELECT * FROM read_csv('{raw_dir}/DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_1.csv', all_varchar = true, header = true);
