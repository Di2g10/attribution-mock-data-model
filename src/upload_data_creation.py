import pandas as pd

pd.set_option('display.max_columns', None)
import filepaths as fpath
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
    # if campaign == 'Training':
    #     df['address1'] = df['address1'].to_string(index=False)
    #     df['address'] = df['address1']+' '+df['address2']
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
    selected_records = df[df['List_Name_Part_One'] == '0']
    print(selected_records)
    df['List_Name_Part_One'] = df['List_Name_Part_One'].fillna('#N/A') # Fill na with #NA value
    df['List_Name_Part_One'] = df['List_Name_Part_One'].str.strip() # trim
    list_value_df['List Name Part One'] = list_value_df['List Name'].str.split(' -').str[0] # select part one of list from lookup df
    valid_list_po_names = list_value_df['List Name Part One'].unique() # list of valid names
    print("Possible valid values: ", len(valid_list_po_names))
    current_list_po_names = df['List_Name_Part_One'].unique() # list of current names in dataset
    print("Unique list values in data: ", len(current_list_po_names))
    invalid_lists_po_df = df[~df['List_Name_Part_One'].isin(valid_list_po_names)] # dataframe of records where list name not in valid list
    print("Invalid records in data: ", len(invalid_lists_po_df))
    invalid_list_names_po_list = invalid_lists_po_df['List_Name_Part_One'].unique() # list of invalid names in dataset
    number_invalid_list_names_po_df = pd.DataFrame({'List_Name_Part_One': invalid_list_names_po_list}) # dataframe of invalid names in dataset
    print("Number of invalid List Names:", len(number_invalid_list_names_po_df))
    print(invalid_list_names_po_list)
    output_file_name = f'{campaign}_invalid_lists_output.xlsx'
    number_invalid_list_names_po_df.to_excel(fpath.workspace_directory_output_invalid_lists / output_file_name, index=False)
    return df
