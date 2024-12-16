CREATE OR REPLACE VIEW AVIS_DB.INTERMEDIATE_DEV.PERSON_WITH_CONVERSION_DETAILS AS
-- this is a replica of the report that Rob is currently using in Salesforce
SELECT
    -- LEAD FIELDS
    LEAD.ID                                           AS LEAD_ID,
    LEAD.RECORD_TYPE_ID,
    LEAD.AE_CAMPAIGN,
    LEAD.AE_FIRST_REFERRER_TYPE,
    LEAD.OWNER_ID,
    LEAD.FIRST_NAME,
    LEAD.LAST_NAME,
    LEAD.COMPANY,
    LEAD.COUNTRY,

    LEAD.LEAD_SOURCE,
    LEAD.STATUS,
    LEAD.CREATED_DATE,
    LEAD.LAST_MODIFIED_DATE,
    LEAD.CONVERTED_DATE,

    -- LEAD CALCULATED FIELDS
    OPP.STAGE_NAME,
    OPP.TOTAL_POTENTIAL_REVENUE_PER_YEAR,

    -- OPP FIELDS
    OPP.CLOSE_DATE,
    COALESCE(CMAP.COUNTRY_OUTPUT, 'Unmapped Country') AS MAPPED_COUNTRY,
    CASE
        WHEN REGEXP_LIKE(LEAD.AE_CAMPAIGN, '^(CLA-Facebook).*') THEN 'Social - Cold Leads'
        WHEN REGEXP_LIKE(LEAD.AE_CAMPAIGN, '^(CLA-Vans).*') THEN 'Social - Cold Leads'
        WHEN LEAD.AE_CAMPAIGN = 'Stations Lead Form' THEN 'Stations Lead Form - Warm Leads'
        --         WHEN REGEXP_LIKE(LEAD.AE_CAMPAIGN, '(Lead Form Extensions)') THEN 'Pardot Landing Pages'
        WHEN REGEXP_LIKE(LEAD.AE_CAMPAIGN, '.*(Google Ads).*') THEN 'PPC - Cold Leads'
        WHEN
            REGEXP_LIKE(LEAD.AE_CAMPAIGN, '.*(Website Tracking).*') AND LEAD.AE_CAMPAIGN != 'Lease.com Website Tracking'
            THEN 'Organic Web Leads - Warm Leads'
        WHEN LEAD.AE_CAMPAIGN IN (
                'UK Vans Form Enquiries',
                'Avis Finland Website Leads'
            ) THEN 'Organic Web Leads - Warm Leads'
        WHEN LEAD.AE_CAMPAIGN = 'Avis Website iFramed forms' THEN 'Pardot Landing Pages'
        ELSE 'Ungrouped'
    END                                               AS GROUPED_CAMPAIGN

-- OPP FIELDS - REQUIRE ACCOUNT OBJECT
-- these are not currently needed and the account object is not being synced

--     OPP.ACTUAL_FULL_YEAR_PY_REVENUE,
--     OPP.ACTUAL_YTD_PY_REVENUE,
--     OPP.ACTUAL_YT_CY_REVENUE,

-- ACCOUNT FIELDS
-- these are not currently needed and the account object is not being synced

--     ACCOUNT.AWD_NUMBER,
--     ACCOUNT.AVIS_FLEX_AWD,
--     ACCOUNT.VANS_AWD

FROM AVIS_DB.BASE_DEV.SALESFORCE_LEAD_ALL AS LEAD
LEFT JOIN AVIS_DB.BASE_DEV.SALESFORCE_OPPORTUNITY AS OPP
    ON LEAD.CONVERTED_OPPORTUNITY_ID = OPP.ID
LEFT JOIN AVIS_DB.STATIC_FILES.COUNTRY_MAPPING AS CMAP
    -- merge on the lowercase country names as this is how mapping is set up
    ON COALESCE(LOWER(LEAD.COUNTRY), 'Missing Country') = COALESCE(CMAP.COUNTRY_INPUT, 'Missing Country');
