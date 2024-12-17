USE ROLE CLIENT_DB;

-- create a view which references the country mapping csv file

CREATE OR REPLACE VIEW CLIENT_DB.STATIC_FILES.COUNTRY_MAPPING AS
SELECT
    $1 AS COUNTRY_OUTPUT,
    $2 AS COUNTRY_CODE_OUTPUT,
    $3 AS COUNTRY_INPUT
FROM
    '@STATIC_FILES/Country_Mapping/Country Mapping_v4.csv'
    -- no qa is due to SQLFluff not understanding that this as the file format exists in a different file.
    (FILE_FORMAT => CLIENT_DB.STATIC_FILES.COUNTRY_MAPPING_CSV);  -- noqa: RF01
