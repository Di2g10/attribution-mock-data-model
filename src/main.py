import pandas as pd
import config
from create_credentials import create_credentials
import filepaths as fpath
from datetime import date
from extraction import bulk_lead_extract_to_file
import src
from upload_data_transformation import import_data, rename_fields, field_value_mapping, list_name, obtain_list_prog_ids, \
    fix_dates, existing_records, new_records, post_existing_records
pd.set_option('display.max_columns', None)


# Snapshot saved to C:\Users\AnneYoung\AppData\Local\JetBrains\PyCharm2023.1\snapshots\aveva-marketo-dedupe.pstat
def main():
    # Define possible campaigns
    campaigns = ['ACTC', 'PI', 'Training']
    # Define manual campaign to file mappings
    campaign_to_file_mapping = {"ACTC": 'ACTC Course Registration - July 2022 to March 2023.xlsx',
                                "PI": 'PI Course Registration Information - Dec 2022 to Feb 2023.xlsx',
                                "Training": 'Training Manager_January_2018 to February 2023.xlsx'}
    campaign_to_sheet_mapping = {"ACTC": 'Sheet1',
                                 "PI": 'Summary',
                                 "Training": '2018-2022 Sept'}
    # Create campaign dataframe
    campaign_df = {}
    for campaign in campaigns:
        print(campaign)
        campaign_file_name = campaign_to_file_mapping[campaign]
        campaign_sheet_name = campaign_to_sheet_mapping[campaign]
        df = import_data(import_file_name=campaign_file_name,
                         import_sheet_name=campaign_sheet_name)
        rename_df = rename_fields(df=df, campaign=campaign, fm_file_name='Field Mapping_V7.xlsx',
                                  fm_sheet_name='Field Mapping')
        values_mapped_df = field_value_mapping(df=rename_df, vm_file_name='Field Mapping_V7.xlsx',
                                               columns_to_map_values=['country', 'state', 'pmi_Preferred_Language__c'],
                                               campaign=campaign)
        list_name_df = list_name(df=values_mapped_df, lvc_file_name='Aveva API Import ID_s.xlsx', campaign=campaign)
        obtain_list_prog_ids_df = obtain_list_prog_ids(df=list_name_df, lookup_file_name='Aveva API Import ID_s.xlsx',
                                                       campaign=campaign)
        # Fix date values
        fix_dates_df = fix_dates(obtain_list_prog_ids_df, campaign)
        output_file_name = f'{campaign}_output.xlsx'
        fix_dates_df.to_excel(fpath.workspace_directory_output / output_file_name, index=False)
        fix_dates_df['Campaign'] = campaign
        campaign_df[campaign] = fix_dates_df

    # Combine data for different campaigns
    combined_df = pd.concat([campaign_df['ACTC'], campaign_df['PI'], campaign_df['Training']], ignore_index=True)
    # Below outputs combined file
    output_file_name = 'combined_output.xlsx'
    combined_df.to_excel(fpath.workspace_directory_output / output_file_name, index=False)

    print(str(len(combined_df)) + ' rows in combined_df')
    print(combined_df.head(10).to_markdown())

    # Pull the people from Marketo
    # fields = ['id', 'email']
    marketo_credentials = create_credentials(client_id=config.client_id,
                                             client_secret=config.client_secret,
                                             url=config.url)
    # bulk_lead_extract_to_file(fields=fields,
    #                           filter_type='smartListId',
    #                           filter_value='751814',
    #                           output_directory=fpath.workspace_directory_process,
    #                           output_filename='lead_extract1',
    #                           marketo_credentials=marketo_credentials)

    existing_records_df = existing_records(# df=fix_dates_df,
        df=combined_df,
        marketo_people_filename='lead_extract1.csv')

    print(str(len(existing_records_df)) + ' rows in existing_records_df')
    print(existing_records_df.head(10).to_markdown())

    new_records_df = new_records(#df=fix_dates_df,
                                 df=combined_df,
                                 marketo_people_filename='lead_extract1.csv')
    print(str(len(new_records_df)) + ' rows in new_records_df')
    print(new_records_df.head(10).to_markdown())


if __name__ == '__main__':
    main()

