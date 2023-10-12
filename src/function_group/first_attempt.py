import pandas as pd
pd.set_option('display.max_columns', None)
import filepaths as fpath
from datetime import date
from extraction import bulk_lead_extract_to_file

def main():
    fields = ['id', 'email', 'pmi_MCL_Date__c']
    bulk_lead_extract_to_file(fields=fields,
                              filter_type='smartListId',
                              filter_value='751814',
                              output_directory=fpath.workspace_directory_process,
                              output_filename='date_format_find')

if __name__ == '__main__':
    main()



# import pandas as pd
# import filepaths as fpath
# pd.set_option('display.max_columns', None)

# df = pd.read_excel(fpath.workspace_directory_input / 'Training Manager_January_2018 to February 2023.xlsx',
#                    sheet_name='2018-2022 Sept')
#
# # start_index = 63000
# # end_index = 65000
# #
# # df_sample = df.iloc[start_index:end_index]
#
# df_sample = df[df['E-mail'] == 'andrew.j.ramsden@sellafieldsites.com']
# df_sample = df_sample[df_sample['Course Name'] =='AVEVA E3D 2.1 User Overview & Admin']
# print(df_sample)
# output_file_name = 'Taining_sample.xlsx'
# df_sample.to_excel(fpath.workspace_directory_output / output_file_name, index=False)





# """Jake's instructions taken from task in WF."""
#
#
# # #Jake's instructions:
# # set "Non-Marketable" to True
# # Dynamic Lead Source - AVEVA Virtual Event
# # Lead Source -  AVEVA Virtual Event
# # Dynamic Detailed Lead Source - {{Program Name}}.{{List Name}}
# # Detailed Lead Source - {{Program Name}}.{{List Name}}
# # Original Campaign Source - Training
# # Campaign Source - Training
# # MCL Campaign - {{Program Name}}.{{List Name}} (Earliest available) from the sheet with the associated earliest registration date
# # MCL Date - Earliest Registered Date as taken from the sheet
#
#
# import pandas as pd
#
# pd.set_option('display.max_columns', None)
# import filepaths as fpath
# from datetime import date
# from pathlib import Path
#
#
# def import_data():
#     """
#     Import the three upload files
#     """
#     workspace_directory = fpath.workspace_directory_input
#     actc_df = pd.read_excel(workspace_directory / 'ACTC Course Registration - July 2022 to March 2023.xlsx',
#                             sheet_name='Sheet1')
#     actc_df['Campaign'] = 'ACTC'
#
#     pi_df = pd.read_excel(workspace_directory / 'PI Course Registration Information - Dec 2022 to Feb 2023.xlsx',
#                           sheet_name='Summary')
#     pi_df['Campaign'] = 'PI'
#     training_df = pd.read_excel(fpath.workspace_directory / 'Training Manager_January_2018 to February 2023.xlsx',
#                                 sheet_name='2018-2022 Sept')
#     training_df['Campaign'] = 'Training'
#
#
# def import_data_general(workspace_directory,
#                         file_name,
#                         sheet_name,
#                         campaign_name):
#
#
# def import_pl_mapping_file(campaign: str):
#     """
#     Import mapping file for the program/list name based on campaign and the field mapping based on campaign
#     campaign: client campaign. Choice of 'ACTC', 'PI' or 'Training'
#     """
#     file_name = 'Aveva API Import ID_s.xlsx'
#     if campaign == 'ACTC':
#         prog_list_df = pd.read_excel(fpath.workspace_directory / file_name,
#                                      sheet_name='ALL IDs CT')
#         print('ACTC "prog_list_df" created')
#         return prog_list_df
#     elif campaign == 'PI':
#         prog_list_df = pd.read_excel(fpath.workspace_directory / file_name,
#                                      sheet_name='ALL IDs PI')
#         print('PI "prog_list_df" created')
#         return prog_list_df
#     elif campaign == 'Training':
#         prog_list_df = pd.read_excel(fpath.workspace_directory / file_name,
#                                      sheet_name='ALL IDs TM')
#         return prog_list_df
#     else:
#         print('Campaign unsupported')
#
#
# def import_field_mapping_file(campaign: str):
#     """
#     Import mapping file for the field names to be changed to align to Marketo, based on campaign.
#     campaign: client campaign. Choice of 'ACTC', 'PI' or 'Training'
#     """
#     workspace_directory = fpath.workspace_directory_mapping
#     file_name = 'Field Mapping_V3.xlsx'
#     if campaign == 'ACTC':
#         field_mapping_df = pd.read_excel(workspace_directory / file_name,
#                                          sheet_name='ALL IDs CT')
#         # Select rows where Campaign File = ACTC
#         print('ACTC "prog_list_df" created')
#         return field_mapping_df
#     elif campaign == 'PI':
#         field_mapping_df = pd.read_excel(workspace_directory / file_name,
#                                          sheet_name='ALL IDs PI')
#         print('PI "prog_list_df" created')
#         return field_mapping_df
#     elif campaign == 'Training':
#         field_mapping_df = pd.read_excel(workspace_directory / file_name,
#                                          sheet_name='ALL IDs TM')
#         print('Training "prog_list_df" created')
#         return field_mapping_df
#     else:
#         print('Campaign unsupported')
#
#
# def rename_fields(actc_df: pd.DataFrame,
#                   pi_df: pd.DataFrame,
#                   training_df: pd.DataFrame,
#                   field_mapping_doc: Path,
#                   sheet_name: str):
#     """
#     Rename fields in the dataframe to match Marketo API, apart from the list name which is carried out in a different function
#
#     ENSURE THAT THE PROGRAM AND LIST FIELDS ARE NAMED CORRECTLY HERE FOR THE PROGRAM_VALID FUNCTION
#
#     actc_df: the acta campaign dataframe
#     pi_df: the pi campaign dataframe
#     training_df: the training campaign dataframe
#     field_mapping_doc: the path where the field mapping document is, with the 'Field in Upload File' and 'REST API Name' name
#     sheet_name: sheet name to be imported of the field mapping doc
#     """
#
#     field_mapping = pd.read_excel(field_mapping_doc,
#                                   sheet_name=sheet_name)
#     campaigns = ['ACTC', 'PI', 'Training']
#
#     for campaign in campaigns:
#         campaign_mapping = field_mapping[field_mapping['Campaign Field'] == campaign]
#
#     field_mapping_dict = {}
#     for index, row in campaign_mapping.iterrows():
#         old_name = row['Field in Upload File']
#         new_name = row['REST API Name']
#         dict_item = {old_name, new_name}
#         field_mapping_dict.update(dict_item)
#     df.rename(columns=field_mapping_dict)
#     return df
#
#
# def fix_date(df: pd.DataFrame,
#              desired_format: date):
#     """
#     Fix the date field
#     df: dataframe with leads in with the fields named to match Marketo API
#     desired_format: The format that the date is supposed to be in
#
#     CHECK DATE FORMAT FOR MARKETO
#
#     """
#     df['pmi_MCL_Date__c'] = pd.to_datetime(df['pmi_MCL_Date__c'], format=desired_format, errors='coerce')
#     return df
#
#
# def select_records(df: pd.DataFrame):
#     """
#     Selects records that are required for upload, one record per email address with the first enrollment date (now called pmi_MCL_Date__c) taken.
#     This should be run after rename_fields as the Marketo API fields names are used
#     df: File from client event with leads in, which are to be created/updated in Marketo
#     """
#     idx = df.groupby('email')['pmi_MCL_Date__c'].idxmin()
#     df = df.loc[idx]
#
#     # # Take the first enrolled date for each email and list name
#     # idx = df.groupby(['email', 'List Name part one', 'List Name part two'])['Enrolled date'].idxmin()
#     return (df)
#
#
# def program_valid(df: pd.DataFrame,
#                   campaign: str,
#                   prog_list_df: pd.DataFrame):
#     """
#     Ensures the program names are valid; that they're programs in Marketo
#     df: dataframe with leads in with the fields renamed
#     campaign: The campaign name as called by the client. One of three: 'ACTC', 'PI' or 'Training'
#     prog_list_df: the valid program and list values.
#
#     PROG_LIST_DF SHOULD REFER TO THE DF RETURNED FROM THE import_pl_mapping_file FUNCTION
#
#     """
#
#     # Remove TM superscript
#     search_symbol = '\u2122'
#     df['List Name part two'] = df['List Name part two'].str.replace(search_symbol, '')
#
#     return df
#
# def program_name(df: pd.DataFrame,
#               pvc_file_name: str,
#               campaign: str):
#     """
#     Does a program value check against valid values. Alterations are scripted to ensure they are all correct.
#     Import the file with the valid program values in from the fpath.workspace_directory_mapping folder.
#     Alters the values in the Program Name field and prints if there are still invalid values.
#     df: dataframe with the renamed fields in
#     pvc_file_name: the name of the program value check file, containing valid values (xlsx)
#     campaign: the name of the campaign, which is used to determine the sheet in the Excel program value check file
#     """
#     campaign_to_sheet_mapping = {"ACTC": "ALL ID's CT",
#                                  "PI": "ALL ID's PI",
#                                  "Training": "ALL ID's TM"}
#     pvc_sheet_name = campaign_to_sheet_mapping[campaign]
#     program_value_df = pd.read_excel(fpath.workspace_directory_mapping / pvc_file_name,
#                                  sheet_name=pvc_sheet_name)
#     df['Program Name'] = df['Program Name'].str.strip()
#     search_tm_symbol = '\u2122'
#     df['Program Name'] = df['Program Name'].str.replace(search_tm_symbol, '')
#     df['Program Name'] = 'TR-CORP-CT-' + df['Program Name']
#     df['Program Name'] = df['Program Name'].str.replace('&', 'and')
#     df['Program Name'] = df['Program Name'].str.replace('AVEVA E3D Design, AVEVA Administration', 'AVEVA E3D Design')
#     df['Program Name'] = df['Program Name'].str.replace('AVEVA Engineering, AVEVA E3D Design', 'AVEVA Schematics and Engineering')
#
#     # # Used to check values. Not needed when actually creating upload file
#     valid_program_names = program_value_df['Program Name'].unique()
#     # valid_program_names_df = pd.DataFrame({'Program Name': valid_program_names})
#     # valid_program_names_df.to_excel(fpath.workspace_directory_output / 'ACTC_valid_prog_names.xlsx', index=False)
#     # current_program_names = df['Program Name'].unique()
#     # current_program_names_df = pd.DataFrame({'Program Name': current_program_names})
#     # current_program_names_df.to_excel(fpath.workspace_directory_output / 'ACTC_current_prog_names.xlsx', index=False)
#     invalid_programs_df = df[~df['Program Name'].isin(valid_program_names)]
#     # print("Possible valid values: ", len(valid_program_names))
#     # print("Unique program values in data: ", len(current_program_names))
#     # print("Invalid records in data: ", len(invalid_programs_df))
#     invalid_program_names_list = invalid_programs_df['Program Name'].unique()
#     number_invalid_program_names_df = pd.DataFrame({'Program Name': invalid_program_names_list})
#     #print("Number of invalid Program Names:", len(number_invalid_program_names_df))
#     #print(invalid_program_names_list)
#     # df.to_excel(fpath.workspace_directory_output / 'ACTC_program_test.xlsx', index=False)
#     return df
#
#
# def create_additional_fields(df: pd.DataFrame, program_name: str):
#     """
#     Creating additional fields required for the Marketo upload
#     df: dataframe of records to be created/updated with all other transformation carried out
#     program_name: The name of the Program in Marketo
#     """
#     df['ChannelProgramName'] = program_name  # Check correct Marketo field
#     df['nonmarketable'] = 'True'
#     df['Dynamic_Lead_Source__c'] = 'AVEVA Virtual Event'
#     df['pmi_Original_Lead_Source__c'] = 'AVEVA Virtual Event'  # Check correct Marketo field
#
#
#
#
#
#
