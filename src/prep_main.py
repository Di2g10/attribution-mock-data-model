import pandas as pd
pd.set_option('display.max_columns', None)
import filepaths as fpath
from datetime import date
from upload_data_creation import rename_fields_actc, fix_date, select_records, remove_tm,create_additional_fields

# Read in data
actc_df = pd.read_excel(fpath.workspace_directory / 'ACTC Course Registration - July 2022 to March 2023.xlsx', sheet_name='Sheet1')

# Manipulate it for upload
renamed_actc_df = rename_fields_actc(actc_df)
fixed_actc_df = fix_date(renamed_actc_df,"%d-%m-%Y")
records_actc_df = select_records(fixed_actc_df)
removed_tm_actc_df = remove_tm(records_actc_df)
