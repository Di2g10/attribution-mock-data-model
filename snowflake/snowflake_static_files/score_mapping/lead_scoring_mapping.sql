CREATE OR REPLACE TABLE CLIENT_DB.STATIC_FILES.LEAD_SCORE_MAPPING AS
WITH RAW_MAPPING AS (
    SELECT
        $1               AS TYPE,  -- noqa: RF04
        $3               AS ACTIVITY_NAME,
        $4               AS SCORE,
        COALESCE($2, '') AS TYPE_NAME
    FROM
        '@CLIENT_DB.STATIC_FILES.STATIC_FILES/Lead_Scoring_Mapping/lead_scoring_mapping_v1.csv'
        -- no qa is due to SQLFluff not understanding that this as the file format exists in a different file.
        (FILE_FORMAT => CLIENT_DB.STATIC_FILES.CSV_FORMAT) -- noqa: RF01
)

SELECT
    TYPE,
    TYPE_NAME,
    ACTIVITY_NAME,
    SCORE,
    TYPE || TYPE_NAME AS ID
FROM RAW_MAPPING;
