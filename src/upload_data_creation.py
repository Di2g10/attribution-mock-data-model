import pandas as pd
pd.set_option('display.max_columns', None)
import filepaths as fpath
from datetime import date
from pathlib import Path


def import_upload_data():
    """
    Import the three upload files
    """
    actc_df = pd.read_excel(fpath.workspace_directory / 'ACTC Course Registration - July 2022 to March 2023.xlsx',
                            sheet_name='Sheet1')
    pi_df = pd.read_excel(fpath.workspace_directory / 'PI Course Registration Information - Dec 2022 to Feb 2023.xlsx',
                          sheet_name='Summary')
    training_df = pd.read_excel(fpath.workspace_directory / 'Training Manager_January_2018 to February 2023.xlsx',
                                sheet_name='2018-2022 Sept')

def import_pl_mapping_file(campaign: str):
    """
    Import mapping file for the program/list name based on campaign and the field mapping based on campaign
    """
    file_name = 'Aveva API Import ID_s.xlsx'
    if campaign=='ACTC':
        prog_list_df = pd.read_excel(fpath.workspace_directory / file_name,
                                     sheet_name='ALL IDs CT')
        print('ACTC "prog_list_df" created')
    elif campaign=='PI':
        prog_list_df = pd.read_excel(fpath.workspace_directory / file_name,
                                     sheet_name='ALL IDs PI')
        print('PI "prog_list_df" created')
    elif campaign=='Training':
        prog_list_df = pd.read_excel(fpath.workspace_directory / file_name,
                                     sheet_name='ALL IDs TM')
    elif print('Campaign unsupported'):

    return prog_list_df


def import_field_mapping_file(campaign: str):
    """
    Import mapping file for the field names to be changed to align to Marketo, based on campaign.
    campaign: client campaign. Choice of 'ACTC', 'PI' or 'Training'
    """
    file_name = 'Field Mapping_V1.xlsx'
    if campaign=='ACTC':
        field_mapping_df = pd.read_excel(fpath.workspace_directory / file_name,
                                     sheet_name='ALL IDs CT')
        # Select rows where Campaign File = ACTC
        print('ACTC "prog_list_df" created')
    elif campaign=='PI':
        field_mapping_df = pd.read_excel(fpath.workspace_directory / file_name,
                                     sheet_name='ALL IDs PI')
        print('PI "prog_list_df" created')
    elif campaign=='Training':
        field_mapping_df = pd.read_excel(fpath.workspace_directory / file_name,
                                     sheet_name='ALL IDs TM')
        print('Training "prog_list_df" created')
    elif print('Campaign unsupported'):

    return field_mapping_df


def rename_fields(df: pd.DataFrame,
                  campaign: str,
                  field_mapping_doc: Path,
                  sheet_name:str):
    """
    Rename fields in the dataframe to match Marketo API, apart from the list name which is carried out in a different function

    ENSURE THAT THE PROGRAM AND LIST FIELDS ARE NAMED CORRECTLY HERE FOR THE PROGRAM_VALID FUNCTION

    df: File from client event with leads in, which are to be created/updated in Marketo
    campaign: client campaign. Choice of 'ACTC', 'PI' or 'Training'
    field_mapping_doc: the path where the field mapping document in, with the 'Field in Upload File' and 'REST API Name' name
    sheet_name: sheet name to be imported of the field mapping doc
    """
    field_mapping = pd.read_excel(field_mapping_doc,
                                  sheet_name=sheet_name)
    field_mapping = field_mapping[field_mapping['Campaign Field'] == campaign]
    field_mapping_dict = {}
    for index, row in field_mapping.iterrows():
        old_name = row['Field in Upload File']
        new_name = row['REST API Name']
        dict_item = {old_name, new_name}
        field_mapping_dict.update(dict_item)
    df.rename(columns=field_mapping_dict)
    return df


def fix_date(df: pd.DataFrame,
             desired_format: date):
    """
    Fix the date field
    df: dataframe with leads in with the fields named to match Marketo API
    desired_format: The format that the date is supposed to be in

    CHECK DATE FORMAT FOR MARKETO

    """
    df['pmi_MCL_Date__c'] = pd.to_datetime(df['pmi_MCL_Date__c'], format=desired_format, errors='coerce')
    return df


def select_records(df: pd.DataFrame):
    """
    Selects records that are required for upload, one record per email address with the first enrollment date (now called pmi_MCL_Date__c) taken.
    This should be run after rename_fields as the Marketo API fields names are used
    df: File from client event with leads in, which are to be created/updated in Marketo
    """
    idx = df.groupby('email')['pmi_MCL_Date__c'].idxmin()
    df = df.loc[idx]

    # # Take the first enrolled date for each email and list name
    # idx = df.groupby(['email', 'List Name part one', 'List Name part two'])['Enrolled date'].idxmin()
    return(df)


def program_valid(df: pd.DataFrame,
                  campaign: str,
                  prog_list_df: pd.DataFrame):
    """
    Ensures the program names are valid; that they're programs in Marketo
    df: dataframe with leads in with the fields renamed
    campaign: The campaign name as called by the client. One of three: 'ACTC', 'PI' or 'Training'
    prog_list_df: the valid program and list values.

    PROG_LIST_DF SHOULD REFER TO THE DF RETURNED FROM THE import_pl_mapping_file FUNCTION

    """

    # Remove TM superscript
    search_symbol = '\u2122'
    df['List Name part two'] = df['List Name part two'].str.replace(search_symbol, '')


    return df


def create_additional_fields(df: pd.DataFrame, program_name: str):
    """
    Creating additional fields required for the Marketo upload
    df: dataframe of records to be created/updated with all other transformation carried out
    program_name: The name of the Program in Marketo
    """
    df['ChannelProgramName'] = program_name # Check correct Marketo field
    df['nonmarketable'] = 'True'
    df['Dynamic_Lead_Source__c'] = 'AVEVA Virtual Event'
    df['pmi_Original_Lead_Source__c'] = 'AVEVA Virtual Event' # Check correct Marketo field





