from pathlib import Path
import os
import pandas as pd
import filepaths
from src.post_upload.file_location import input_filepath, mid_filepath, output_filepath

def split_df(request: str):
    if request=='activity_data_value_change':
        df = pd.read_csv(input_filepath / "activity_data_value_change_filtered_reformatted.csv")
        # break df based on the primaryAttributeValue column
        df_last_campaign = df[df['primaryAttributeValue'].isin(['Last Campaign'])]
        print('df_last_campaign shape: ', df_last_campaign.shape)
        df_aql_campaign = df[df['primaryAttributeValue'].isin(['AQL Campaign'])]
        print('df_aql_campaign shape: ', df_aql_campaign.shape)
        df_mel_campaign = df[df['primaryAttributeValue'].isin(['MEL Campaign'])]
        print('df_mel_campaign shape: ', df_mel_campaign.shape)
        df_aql_latest_campaign = df[df['primaryAttributeValue'].isin(['AQL Latest Campaign'])]
        print('df_aql_latest_campaign shape: ', df_aql_latest_campaign.shape)
        df_preferred_language = df[df['primaryAttributeValue'].isin(['Preferred Language'])]
        print('df_preferred_language shape: ', df_preferred_language.shape)
        return df_last_campaign, df_aql_campaign, df_mel_campaign, df_aql_latest_campaign, df_preferred_language
    elif request=='mcl_campaign_data_value_change':
        df_mcl_campaign = pd.read_csv(input_filepath / "activity_data_value_change_filtered_mcl.csv")
        print('df_mcl_campaign shape: ', df_mcl_campaign.shape)
        return df_mcl_campaign


def keep_training_status(df):
    field_name = str(df['primaryAttributeValue'].unique())
    print('the shape of the dataframe before keeping only the training status: ', df.shape[0])
    # keep rows that the field New Value is not null
    # keep rows that the field New Value starts with 'TR'
    df = df[df['New Value'].str.startswith('TR') & df['New Value'].notna()]
    print('the shape of the dataframe after keeping only the training status: ', df.shape[0])
    # do a check to see if there are duplicated ids
    print('the number of duplicated ids: ', df['leadId'].duplicated().sum())

    # remove rows that are not duplicated
    df_dup = df[df['leadId'].duplicated()]
    print('the unique number of ids in the duplicated records: ', df_dup['leadId'].nunique())
    # df_dup.to_csv(mid_filepath / f"{field_name}_dup.csv", index=False)

    df = df.sort_values(by=['activityDate'])
    # dedup the dataframe based on the field leadId, keep the first record - earliest date
    df = df.drop_duplicates(subset=['leadId'], keep='first')
    print('the shape of the dataframe after deduplication: ', df.shape[0])
    return df


def keep_all_status(df):
    field_name = str(df['primaryAttributeValue'].unique())
    print('the shape of the dataframe: ', df.shape[0])
    # keep rows that the field New Value is not null
    # keep rows that the field New Value starts with 'TR'
    # do a check to see if there are duplicated ids
    print('the number of duplicated ids: ', df['leadId'].duplicated().sum())

    # remove rows that are not duplicated
    df_dup = df[df['leadId'].duplicated()]
    print('the unique number of ids in the duplicated records: ', df_dup['leadId'].nunique())
    # df_dup.to_csv(mid_filepath / f"{field_name}_dup.csv", index=False)

    df = df.sort_values(by=['activityDate'])
    # dedup the dataframe based on the field leadId, keep the first record - earliest date
    df = df.drop_duplicates(subset=['leadId'], keep='first')
    print('the shape of the dataframe after deduplication: ', df.shape[0])
    return df



def format_df_for_upload(df, field_api_name: str):
    fields_keep = ['leadId', 'activityDate', 'Old Value', 'New Value']
    df = df[fields_keep]
    df = df.rename(columns={'leadId': 'id',
                            'Old Value': field_api_name,
                            'New Value': f'current_{field_api_name}'})
    # remove pmi_ and __c from the field_api_name and save it as file_name
    file_name = field_api_name[4:-3]

    df.to_csv(output_filepath / f"{file_name}_to_upload.csv", index=False)
    return df


def main():
    df_last_campaign, \
        df_aql_campaign, \
        df_mel_campaign, \
        df_aql_latest_campaign, \
        df_preferred_language = split_df(request='activity_data_value_change')
    df_list = [df_last_campaign, df_aql_campaign, df_mel_campaign, df_aql_latest_campaign]
    file_names = ['pmi_Last_campaign__c', 'pmi_AQL_campaign__c',
                  'pmi_MEL_campaign__c', 'pmi_AQL_Latest_campaign__c']
    for df, file_name in zip(df_list, file_names):
        df = keep_training_status(df)
        df = format_df_for_upload(df, file_name)


def mcl_campaign_main():
    df_mcl_campaign = split_df(request='mcl_campaign_data_value_change')
    df_mcl_campaign = keep_all_status(df_mcl_campaign)
    df_mcl_campaign = format_df_for_upload(df_mcl_campaign, 'pmi_MCL_campaign__c')
    df_existing = pd.read_csv(filepaths.workspace_directory_output / "Post_existing_upload.csv")
    df_new = pd.read_csv(filepaths.workspace_directory_output / "New_upload.csv")

    df_mcl_campaign = pd.merge(df_mcl_campaign, df_existing, on='id', how='left', indicator=True)
    print(df_mcl_campaign['_merge'].value_counts())
    print(df_mcl_campaign.head(10).to_markdown())
    # output
    # df_mcl_campaign.to_csv(output_filepath / f"MCL_campaign_full_to_upload_v2.csv", index=False)
    # df_preferred_language = df_preferred_language[df_preferred_language['New Value'] == 'English']

    # df_preferred_language = format_df_for_upload(df_preferred_language, 'pmi_Preferred_Language__c')
    # keep df_preferred_language rows that the field New Value is English



if __name__ == '__main__':
    mcl_campaign_main()




