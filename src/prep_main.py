import pandas as pd
pd.set_option('display.max_columns', None)
import filepaths as fpath
from datetime import date
from upload_data_creation import import_data, rename_fields, field_value_mapping, list_name


def main():
    campaigns = ['ACTC', 'PI', 'Training']
    #campaigns = ['Training']
    campaign_to_file_mapping = {"ACTC": 'ACTC Course Registration - July 2022 to March 2023.xlsx',
                                "PI": 'PI Course Registration Information - Dec 2022 to Feb 2023.xlsx',
                                "Training": 'Training Manager_January_2018 to February 2023.xlsx'}
    campaign_to_sheet_mapping = {"ACTC": 'Sheet1',
                                 "PI": 'Summary',
                                 "Training": '2018-2022 Sept'}
    for campaign in campaigns:
        print(campaign)
        campaign_file_name = campaign_to_file_mapping[campaign]
        campaign_sheet_name = campaign_to_sheet_mapping[campaign]
        df = import_data(import_file_name=campaign_file_name,
                         import_sheet_name=campaign_sheet_name)
        rename_df = rename_fields(df=df, campaign=campaign, fm_file_name='Field Mapping_20231408_test.xlsx', fm_sheet_name='Field Mapping')
        values_mapped_df = field_value_mapping(df=rename_df, vm_file_name='Field Mapping_20231408_test.xlsx', columns_to_map_values=['country', 'state', 'pmi_Preferred_Language__c'], campaign=campaign)
        list_name_df = list_name(df=values_mapped_df, lvc_file_name='Aveva API Import ID_s.xlsx', campaign=campaign)
        output_file_name = f'{campaign}_output.xlsx'
        list_name_df.to_excel(fpath.workspace_directory_output / output_file_name, index=False)

# Manipulate for upload
if __name__ == '__main__':
    main()

