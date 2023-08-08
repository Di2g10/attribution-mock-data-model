import pandas as pd
pd.set_option('display.max_columns', None)
import filepaths as fpath
from datetime import date
from upload_data_creation import rename_fields, fix_date, select_records, remove_tm,create_additional_fields

# Manipulate for upload
if __name__ == '__main__':
    renamed_actc_df = rename_fields(actc_df)
    fixed_actc_df = fix_date(renamed_actc_df, "%d-%m-%Y")
    records_actc_df = select_records(fixed_actc_df)
    removed_tm_actc_df = remove_tm(records_actc_df)
