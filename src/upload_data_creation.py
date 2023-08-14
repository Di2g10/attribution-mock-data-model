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
    actc_df = pd.read_excel(fpath.workspace_directory_input/import_file_name,
                            sheet_name=import_sheet_name)
    #print(actc_df)
    return actc_df


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
    df.rename(columns=field_mapping_dict, inplace=True)
    df.drop(columns='Ignore', inplace=True)
    df.to_excel(fpath.workspace_directory_output / 'ACTC_mapping_test.xlsx', index=False)
    return df

def country_field(df: pd.DataFrame,
                  vm_file_name: str,
                  vm_sheet_name: str):
    """Replaces the unwanted Country values with blank values.
    Import the file with the value mapping in from the fpath.workspace_directory_mapping folder.
    df: dataframe with the renamed fields in
    vm_file_name: the name of the value mapping file in the folder (xlsx)
    vm_sheet_name: the name of the sheet in the Excel value mapping file
    """
