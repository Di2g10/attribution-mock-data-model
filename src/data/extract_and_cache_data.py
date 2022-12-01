import os
import config
import snowflake.connector as sf
import hashlib
import functools
from datetime import date
import pandas as pd
from pathlib import Path



# data_storage_path =

# Importing

def hard_cache_df(cache_days):
    def hard_cache_df_limit(func):
        @functools.wraps(func)
        def wrapper_hard_cache_df_limit(*args, **kwargs):
            args_str = ''.join(args)
            csv_filename = hashlib.md5(args_str.encode('utf-8')).hexdigest() + ".csv"
            csv_file_location = Path(os.getcwd(), "data" ,"cache", csv_filename)
            print(csv_filename)

            if not os.path.exists(Path(os.getcwd(), "data", "cache")):
                os.mkdir(Path(os.getcwd(),"data","cache"))

            try:
                file_stats_obj = os.stat(csv_file_location)
                modification_time = date.fromtimestamp(os.path.getmtime(csv_file_location))
                today = date.today()
                date_diff = today - modification_time
                if date_diff.days <= cache_days:
                    df = pd.read_csv(csv_file_location, low_memory=False)
                    print("Retrieved Cached File")
                    return df
            # Handles where cache tracker doesn't exist
            except IOError:
                pass
            # print("Fail")
            df = func(*args, **kwargs)
            df.to_csv(csv_file_location)
            print("Retrieved File from server")
            return df
        return wrapper_hard_cache_df_limit
    return hard_cache_df_limit

# To acquire live data: use -1

@hard_cache_df(cache_days=60)
def query_sf(sql):
    ctx = sf.connect(user=config.sf_user,
                     password=config.sf_password,
                     account=config.sf_account,
                     # role=config.sf_role,
                     # warehouse=config.sf_warehouse,
                     # database=config.sf_database,
                     # schema=config.sf_schema
                     )

    cs = ctx.cursor()
    cs.execute(sql)
    df = cs.fetch_pandas_all()
    return df

# Function 1: Fetch the account object from Snowflake

def fetch_object_from_snowflake(get_all_object_sql):
    df_object = query_sf(get_all_object_sql)
    return df_object



