import pandas as pd
from config import SNOWFLAKE
import snowflake.connector as sf
from src.utils import cache


@cache.permanent_df(cache_days=1)
def query(sql: str) -> pd.DataFrame:
    """
    Queries the kainos area of our snowflake with the input sql query. Includes a caching element.
    :param sql: The Snowflake sql query to run. Expecting a select statement.
    :return: DF with the result of the sql query.
    """
    ctx = sf.connect(user=SNOWFLAKE['USERNAME'],
                     password=SNOWFLAKE['PASSWORD'],
                     account=SNOWFLAKE['ACCOUNT'],
                     # role=config.sf_role,
                     # warehouse=config.sf_warehouse,
                     # database=config.sf_database,
                     # schema=config.sf_schema
                     )
    cs = ctx.cursor()
    cs.execute(sql)
    df = cs.fetch_pandas_all()
    return df

