CREATE OR REPLACE TABLE CLIENT_DB.STATIC_FILES.VISITOR_ACTIVITY_TYPE_MAPPING AS
WITH RAW_MAPPING AS (
    SELECT
        $1               AS TYPE, -- noqa: RF04
        COALESCE($2, '') AS TYPE_NAME,
        $3               AS ACTIVITY_NAME
    FROM
        '@CLIENT_DB.STATIC_FILES.STATIC_FILES/Pardot_Visitor_Activity_Type/pardot_visitor_activity_type_mapping_v1.csv'
        -- no qa is due to SQLFluff not understanding that this as the file format exists in a different file.
        (FILE_FORMAT => CLIENT_DB.STATIC_FILES.CSV_FORMAT)-- noqa: RF01
)

SELECT
    TYPE,
    TYPE_NAME,
    ACTIVITY_NAME,
    TYPE || TYPE_NAME AS ID
FROM RAW_MAPPING;
