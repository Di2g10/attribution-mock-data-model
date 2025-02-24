"""Snowflake Quickstart module. Shows how to connect to Snowflake and run some SQL."""

from clevertouch_internal_tools.utils.credentials_manager import SnowflakeCredentials

creds = SnowflakeCredentials(keeper_id="EXAMPLE KEEPER ID")

session = creds.connect()

data = session.sql("SELECT * FROM TABLE").to_pandas()
