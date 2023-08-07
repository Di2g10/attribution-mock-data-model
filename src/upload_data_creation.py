import pandas as pd
pd.set_option('display.max_columns', None)
import filepaths as fpath
from datetime import date


def rename_fields_actc(df: pd.DataFrame):
    """
    Rename fields in the ACTC file to match Marketo API, apart from the list name which is carried out in a different function
    df: File from client event with leads in, which are to be created/updated in Marketo
    CHECK WHICH FIELDS ARE GOING INTO MARKETO
    """
    df = df.rename(columns={'EMAIL Address ': 'email',
                            'FirstName': 'firstName',
                            'LastName': 'lastName',
                            'institution': 'Institution', #Check field in Marketo
                            'city': 'city', #Check field in Marketo, city or City__c
                            'country': 'country code', #Check field in Marketo, this is meant to be Country Code
                            'Country Name': 'country', #Check field in Marketo, country or Country__c or LL_Country__c
                            'category': 'Category', #Check field in Marketo
                            'department': 'department', #Check field in Marketo, department or engagio__Department__c
                            'Parent ID': 'Parent_Acct__c.', #Check field in Marketo
                            'Part Number': 'List Name part one',
                            'Course': 'List Name part two',
                            'Product': 'product',
                            'New Product Name': 'New Product Name', #Check field in Marketo
                            'Course Category': 'Course Category', #Check field in Marketo
                            'Solution': 'Solution', #Check field in Marketo
                            'enrolled': 'pmi_MCL_Date__c'})
    #print(df.info())
    return df


def fix_date(df: pd.DataFrame, desired_format: date):
    """
    Fix the date field
    df: dataframe with leads in with the fields named to match Marketo API
    desired_format: The format that the date is supposed to be in
    CHECK DATE FORMAT FOR MARKETO
    """
    df['pmi_MCL_Date__c'] = pd.to_datetime(df['pmi_MCL_Date__c'], format=desired_format, errors='coerce')
    return(df)


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


def program_valid(df: pd.DataFrame, client_campaign_name: str):
    """
    Ensures the program names are valid; that they're programs in Marketo
    df: dataframe with leads in with the fields renamed
    client_campaign_name: The campaign name as called by the client. One of three:
    """
    #print('original',df)
    #WHEN FOLDER NAME = ACTC
    program_list_df = pd.read_excel(fpath.workspace_directory / 'Aveva API Import ID_s.xlsx',
                            sheet_name='ALL IDs CT')
    # Remove TM superscript
    search_symbol = '\u2122'
    df['List Name part two'] = df['List Name part two'].str.replace(search_symbol, '')
    #print('fixed',df)
    return(df)


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
    df['Dynamic_Detailed_Lead_Source__c'] = ''





