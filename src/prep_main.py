import pandas as pd
pd.set_option('display.max_columns', None)
import filepaths as fpath
from datetime import date
from upload_data_creation import import_data, rename_fields

# Manipulate for upload
if __name__ == '__main__':
    actc_df = import_data(import_file_name='ACTC Course Registration - July 2022 to March 2023.xlsx', import_sheet_name='Sheet1')
    #import_field_mapping(fm_file_name='Field Mapping_V3.xlsx', fm_sheet_name='Field Mapping')
    rename_fields(df=actc_df, campaign='ACTC', fm_file_name='Field Mapping_20231408_test.xlsx', fm_sheet_name='Field Mapping')
