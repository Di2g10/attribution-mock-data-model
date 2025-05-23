"""Snowflake Quickstart module. Shows how to connect to Snowflake and run some SQL."""

import pandas as pd
from snowflake.snowpark import Session

from clevertouch_internal_tools.utils.credentials_manager import SnowflakeCredentials


def connect_to_snowflake() -> Session:
    """Create a Snowflake connection and generate a session."""
    creds = SnowflakeCredentials(keeper_id="EXAMPLE KEEPER ID")
    return creds.connect()


def run_snowflake_query(session: Session, query: str) -> pd.DataFrame:
    """Run a SQL query on Snowflake."""
    return session.sql(query).to_pandas()


if __name__ == "__main__":
    session = connect_to_snowflake()
    df = run_snowflake_query(session, "SELECT * FROM TABLE")
