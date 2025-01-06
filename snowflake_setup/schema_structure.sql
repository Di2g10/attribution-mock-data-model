USE ROLE CLIENT_ROLE;

-- replace CLIENT_DB here with the client name
USE DATABASE CLIENT_DB;

-- Base schema for initial filtering on a SINGLE table.
-- E.g. filtering and selecting relevant columns from the Salesforce Contact table
CREATE SCHEMA BASE_DEV;
CREATE SCHEMA BASE_PROD;

-- Intermediate views for creating generic views which could be used across projects
-- E.g. Creating a person view from the Salesforce Lead and Contact tables
CREATE SCHEMA INTERMEDIATE_DEV;
CREATE SCHEMA INTERMEDIATE_PROD;

-- Dashboard views for creating final data products for use in a specific dashboard
CREATE SCHEMA DASHBOARDS_MARKETING_DEV;
CREATE SCHEMA DASHBOARDS_MARKETING_PROD;

-- CREATE SCHEMA DASHBOARDS_OPERATIONS_DEV;
-- CREATE SCHEMA DASHBOARDS_OPERATIONS_PROD;
--
-- CREATE SCHEMA DASHBOARDS_MARKETING_DEV;
-- CREATE SCHEMA DASHBOARDS_MARKETING_PROD;

CREATE SCHEMA STATIC_FILES;
CREATE STAGE STATIC_FILES.STATIC_FILES;
