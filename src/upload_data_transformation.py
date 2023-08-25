import pandas as pd

pd.set_option('display.max_columns', None)
import filepaths as fpath
import re
from datetime import date
from pathlib import Path


def import_data(import_file_name: str,
                import_sheet_name: str):
    """
    Import the file with the data in for upload from fpath.workspace_directory_input folder
    import_file_name: the name of the import file in the folder (xlsx)
    import_sheet_name: the name of the sheet in the Excel import file
    """
    df = pd.read_excel(fpath.workspace_directory_input / import_file_name,
                       sheet_name=import_sheet_name)
    return df


def rename_fields(df: pd.DataFrame,
                  campaign: str,
                  fm_file_name: str,
                  fm_sheet_name: str):
    """
    Import the file with the field mapping in for upload from fpath.workspace_directory_mapping folder.
    Rename the majority of fields in the dataframe to match Marketo API nad keep only required fields.
    The 'program name', 'list name' and 'address' fields are carried out in a different function.
    df: dataframe imported from client event with leads in, which are to be created/updated in Marketo
    campaign: client campaign. Choice of 'ACTC', 'PI' or 'Training'
    fm_file_name: the name of the field mapping file in the folder (xlsx)
    fm_sheet_name: the name of the sheet in the Excel field mapping file
    """
    field_mapping_df = pd.read_excel(fpath.workspace_directory_mapping / fm_file_name,
                                     sheet_name=fm_sheet_name)
    field_mapping_df = field_mapping_df[field_mapping_df['Campaign File'] == campaign]
    field_mapping_dict = {}
    for index, row in field_mapping_df.iterrows():
        old_name = row['Field in Upload File']
        new_name = row['REST API Name']
        field_mapping_dict[old_name] = new_name
    df = df.rename(columns=field_mapping_dict)
    df = df.drop(columns='Ignore')
    if campaign == 'Training':
        df = df.assign(address=lambda x: x.apply(
            lambda row: (str(row['address1']).strip() + ' ' + str(row['address2']).strip()) if not pd.isna(
                row['address1']) and not pd.isna(row['address2']) else str(row['address1']).strip() if not pd.isna(
                row['address1']) else str(row['address2']).strip(), axis=1))
        df.loc[df['address'] == 'nan', 'address'] = ''
        print(df)
        df = df.drop(columns=['address1', 'address2'])
    return df


def field_value_mapping(df: pd.DataFrame,
                        vm_file_name: str,
                        columns_to_map_values: list,
                        campaign: str):
    """
    Replaces the unwanted Country, State and Language values with blank values and maps to the wanted values.
    Import the file with the value mapping in from the fpath.workspace_directory_mapping folder.
    Create mapping and applies it
    df: dataframe with the renamed fields in
    vm_file_name: the name of the value mapping file in the folder (xlsx)
    columns_to_map_values: a list of the columns you'd like to map values from.
    This will be the name of the field in the dataset and the name of the sheet with the mapping values in.
    campaign: the name of the campaign
    """
    for column in columns_to_map_values:
        if column not in df.columns:
            continue

        value_mapping_df = pd.read_excel(fpath.workspace_directory_mapping / vm_file_name,
                                         sheet_name=column)
        value_mapping_dict = {}
        for index, row in value_mapping_df.iterrows():
            old_name = row['Value in File']
            new_name = row['Upload Value']
            value_mapping_dict[old_name] = new_name

        df[column] = df[column].replace(value_mapping_dict)
        output_file_name = f'{campaign}_{column}_mapping_test.xlsx'
        df.to_excel(fpath.workspace_directory_output / output_file_name, index=False)
        print(f"Values in '{column}' column for {campaign} have been mapped and written to '{output_file_name}'.")
    return df

def custom_parse(date_str):
    """
    Feeds into the fix_dates function below
    """
    # Define a list of regular expressions for different formats
    formats = [
         r'\d{2}-\d{2}-\d{4}',  # dd-mm-yyyy
         r'\d{2}/\d{2}/\d{4}',  # dd/mm/yyyy
    ]

    # Try each regular expression to match the format
    for fmt in formats:
        match = re.match(fmt, date_str)
        if match:
            return match.group(0)
    return None


def fix_dates(df: pd.DataFrame, campaign: str):
    """
    Puts the date into the correct format for the upload
    df: dataframe with the correct field mapping in.
    campaign: campaign file to be uploaded.
    """
    if campaign == 'ACTC':
        df['pmi_MCL_Date__c'] = pd.to_datetime(df['pmi_MCL_Date__c'], format="mixed", dayfirst=True)
    campaign_to_dateformat_mapping = {"ACTC": "%d/%m/%Y %H:%M:%S",
                                      "PI": "%m/%d/%Y %H:%M:%S",
                                      "Training": "%m/%d/%Y"}
    format=campaign_to_dateformat_mapping[campaign]
    df['pmi_MCL_Date__c'] = pd.to_datetime(df['pmi_MCL_Date__c'], format=format, errors='coerce')
    df['pmi_MCL_Date__c'] = df['pmi_MCL_Date__c'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Change invalid dates
    condition = df['pmi_MCL_Date__c'] == '1970-01-01T00:00:00Z'
    # Set the new value for the selected rows
    df.loc[condition, 'pmi_MCL_Date__c'] = '2022-01-31T00:00:00Z'

    # test for invalid dates
    invalid_dates = df[df['pmi_MCL_Date__c'] == '1970-01-01T00:00:00Z']
    if len(invalid_dates) > 0:
        print("Invalid dates found")
        print(invalid_dates.to_markdown())

    return df


def list_name(df: pd.DataFrame,
              lvc_file_name: str,
              campaign: str):
    """
    Does a list value check against valid values. Uses the first part of the list name only.
    Import the file with the valid list values in from the fpath.workspace_directory_mapping folder.
    Alters the values in the list name field and prints if there are still invalid values.
    df: dataframe with the renamed fields in
    lvc_file_name: the name of the list value check file, containing valid values (xlsx)
    campaign: the name of the campaign, which is used to determine the sheet in the Excel program value check file
    """
    campaign_to_sheet_mapping = {"ACTC": "ALL ID's CT",
                                 "PI": "ALL ID's PI",
                                 "Training": "ALL ID's TM"}
    lvc_sheet_name = campaign_to_sheet_mapping[campaign]
    list_value_df = pd.read_excel(fpath.workspace_directory_mapping / lvc_file_name,
                                  sheet_name=lvc_sheet_name)
    df['List_Name_Part_One'] = df['List_Name_Part_One'].fillna('#N/A') #Fill na with #NA value
    df['List_Name_Part_One'] = df['List_Name_Part_One'].apply(lambda x: str(x).strip() if isinstance(x, str) else str(x)) #trim if string
    list_value_df['List Name Part One'] = list_value_df['List Name'].str.split(' -').str[0] #select part one of list from lookup df
    df['List_Name_Part_One'] = df['List_Name_Part_One'].str.split(' -').str[0] #ensure same part is brought back for campaign data
    valid_list_po_names = list_value_df['List Name Part One'].unique()#list of valid names
    valid_list_po_names = [str(name) for name in valid_list_po_names] #converts to string
    # target_value = 'CITEL409105'
    # for name in valid_list_po_names:
    #     if name == target_value:
    #         print('valid_target_value:', name)
    valid_list_df = pd.DataFrame(valid_list_po_names, columns=['Valid List Names'])
    valid_list_df.to_excel(fpath.workspace_directory_output / 'valid_list_names.xlsx', index=False)
    print("Possible valid values:", valid_list_df)
    print("Number of possible valid values: ", len(valid_list_po_names))
    current_list_po_names = df['List_Name_Part_One'].unique() # list of current names in dataset
    current_list_po_names = [str(name) for name in current_list_po_names] #converts to string
    # for name in current_list_po_names:
    #     if name == target_value:
    #         print('valid_current_value:', name)
    print("Unique list values in data: ", len(current_list_po_names))
    invalid_lists_po_df = df[~df['List_Name_Part_One'].isin(valid_list_po_names)] # dataframe of records where list name not in valid list
    print("Invalid records in data: ", len(invalid_lists_po_df))
    invalid_list_names_po_list = invalid_lists_po_df['List_Name_Part_One'].unique() # list of invalid names in dataset
    number_invalid_list_names_po_df = pd.DataFrame({'List_Name_Part_One': invalid_list_names_po_list}) # dataframe of invalid names in dataset
    print("Number of invalid List Names:", len(number_invalid_list_names_po_df))
    print(invalid_list_names_po_list)
    output_file_name = f'{campaign}_invalid_lists_output.xlsx'
    number_invalid_list_names_po_df.to_excel(fpath.workspace_directory_output_invalid_lists / output_file_name,
                                             index=False)
    return df


def obtain_list_prog_ids(df: pd.DataFrame,
              lookup_file_name: str,
              campaign: str):
    """
    Obtains the list and program ids from the lookup file
    df: dataframe with the renamed fields in
    lookup_file_name: the name of the lookup file, containing valid values of lists and programs (xlsx)
    campaign: the name of the campaign, which is used to determine the sheet in the Excel program value check file
    """
    campaign_to_sheet_mapping = {"ACTC": "ALL ID's CT",
                                 "PI": "ALL ID's PI",
                                 "Training": "ALL ID's TM"}
    lvc_sheet_name = campaign_to_sheet_mapping[campaign]
    list_value_df = pd.read_excel(fpath.workspace_directory_mapping / lookup_file_name,
                                  sheet_name=lvc_sheet_name,
                                  usecols=['Program Name', 'List Name', 'Program ID', 'List ID'])
    # select part one of list from lookup df
    list_value_df['List_Name_Part_One'] = list_value_df['List Name'].str.split(' -').str[0]
    # ensure same part is brought back for campaign data
    df['List_Name_Part_One'] = df['List_Name_Part_One'].str.split(' -').str[0]
    df = pd.merge(df, list_value_df, how='left', on='List_Name_Part_One')
    df['Program ID'] = df['Program ID'].astype(str)
    df['Program ID'] = df['Program ID'].str.replace('.0', '')
    df['List ID'] = df['List ID'].astype(str)
    df['List ID'] = df['List ID'].str.replace('.0', '')
    return df


def existing_records(df: pd.DataFrame,
                     marketo_people_filename: str):
    """
    Creates a file to upload to Marketo that will update fields specified, for the exisiting records only.
    df: dataframe with leads in with the fields names to match Marketo API
    marketo_people_filename: filename of all marketo people to check against in csv format. Will be pulled
    from fpath.workspace_directory_process.
    """

    # Convert the 'pmi_MCL_Date__c_date' column to datetime type
    df['pmi_MCL_Date__c_date'] = pd.to_datetime(df['pmi_MCL_Date__c'])

    # Sort the DataFrame by email and date in descending order
    df_sorted = df.sort_values(by=['email', 'pmi_MCL_Date__c_date'], ascending=[True, False])

    # Use groupby to get the most recent date for each email
    df_latest_all_fields = df_sorted.groupby('email').first().reset_index()

    df = df_latest_all_fields.drop_duplicates(subset=['email'])
    marketo_df = pd.read_csv(fpath.workspace_directory_process / marketo_people_filename)
    df = df[df['email'].isin(marketo_df['email'])]
    print("existing_records_df", df)
    df = df[['pmi_Preferred_Language__c', 'email']]
    df = pd.merge(df, marketo_df, how='left', on='email')
    df = df.drop(columns='email')
    df['nonmarketable'] = 'False'
    output_file_name = 'Existing_upload.csv'
    df.to_csv(fpath.workspace_directory_output / output_file_name, index=False)
    return df


def new_records(df: pd.DataFrame, marketo_people_filename: str):
    """
    Creates a file to upload to Marketo with the fields required for new people
    df: dataframe with leads in with the fields names to match Marketo API
    marketo_people_filename: filename of all marketo people to check against in csv format.
    Will be pulled from fpath.workspace_directory_process.
    """
    # Convert the 'pmi_MCL_Date__c_date' column to datetime type
    df['pmi_MCL_Date__c_date'] = pd.to_datetime(df['pmi_MCL_Date__c'])

    # Sort the DataFrame by email and date in descending order
    df_sorted = df.sort_values(by=['email', 'pmi_MCL_Date__c_date'], ascending=[True, False])

    # Use groupby to get the first date for each email
    df_earliest_all_fields = df_sorted.groupby('email').last().reset_index()

    df = df_earliest_all_fields.drop_duplicates(subset=['email'])
    df['Detailed_Lead_Source__c'] = df['Program Name'] + '.' + df['List Name']
    df['pmi_MCL_Campaign__c'] = df['Program Name'] + '.' + df['List Name']
    latest_indices = df.groupby('email')['pmi_MCL_Date__c_date'].idxmax()
    df_latest = df.loc[latest_indices]
    df_latest = df_latest[['email']]
    df_latest['Dynamic_Detailed_Lead_Source__c'] = df['Program Name']+'.'+df['List Name']
    df = pd.merge(df, df_latest, on='email', how='inner')

    # Read current marketo data
    marketo_df = pd.read_csv(fpath.workspace_directory_process/marketo_people_filename)
    # Take records not in current marketo data
    df = df[~df['email'].isin(marketo_df['email'])]

    # Set manual values
    df['Dynamic_Lead_Source__c'] = 'AVEVA Virtual Event'
    df['leadSource'] = 'AVEVA Virtual Event'
    df['pmi_Original_Campaign_Source__c'] = 'Training'
    df['pmi_Campaign_Source__c'] = 'Training'
    df['nonmarketable'] = 'True'
    output_file_name = 'New_upload.csv'
    df.to_csv(fpath.workspace_directory_output / output_file_name, index=False, encoding='utf-8')

    return df







