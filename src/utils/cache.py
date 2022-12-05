import functools
import hashlib
from pathlib import Path
import os
from datetime import date
import pandas as pd
from typing import Callable


def permanent_df(cache_days: int) -> Callable:
    """
    Wrapper function. Takes an existing function and adds a caching element to it. Specifically it takes a hash of the
    function arguments checks if a file with that hash already exists. if so loads that file as the dataframe, If not
    then the original function is called and dataframe is created.
    :param cache_days: Age the cached local file can be to still be called. Files older than this day many days are regenerated
    :return: Original Function amended with the above caching behavoir
    """
    def permanent_df_limit(func):
        @functools.wraps(func)
        def wrapper_permanent_df_limit(*args, **kwargs):
            # makes a directory if it doesn't exist
            directory = Path(os.getcwd(), "cached_files")
            if not os.path.exists(directory):
                os.mkdir(directory)

            args_str = ''.join(args)
            csv_filename = hashlib.md5(args_str.encode('utf-8')).hexdigest() + ".csv"
            csv_file_location = Path(directory, csv_filename)
            print(csv_filename)

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
            df = func(*args, **kwargs)
            df.to_csv(csv_file_location)
            print("Retrieved File from server")
            return df
        return wrapper_permanent_df_limit
    return permanent_df_limit
