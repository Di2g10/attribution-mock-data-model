import pandas as pd
from tqdm import tqdm

import create_and_update_leads as lead_upload_py
import access_token as tok
import static_lists as static_list_py
import programs as programs_py
import credentials as Credentials
import config as config
from create_credentials import create_credentials


def lead_upload(marketo_credentials: Credentials, data_to_upload: pd.DataFrame, create_or_update: str,
                lead_lookup: str, batch_size: int):
    """
    Allows for creating or updating leads (or both).
    data_to_upload: A dataframe of lead to upload.
    create_or_update: create, update or createOrUpdate.
    lead_lookup: either id or email (id is better if you are just running an update).
    batch_size: Size of each upload. An integer between 1 and 200.
    """
    # Get initial access token
    token = tok.AccessToken(credentials=marketo_credentials)
    token.get_marketo_access_token()
    # Create instance of the LeadUpload object
    lead_upload_object = lead_upload_py.LeadUpload(access_token=token,
                                                   create_or_update=create_or_update,
                                                   lead_lookup=lead_lookup,
                                                   batch_size=batch_size)
    lead_upload_object.upload_leads_in_batches(data_to_upload)


def add_leads_to_static_list(marketo_credentials: Credentials, static_list_id: str, lead_ids_to_add: list):
    # Get initial access token
    token = tok.AccessToken(credentials=marketo_credentials)
    token.get_marketo_access_token()
    # Create an instance of the ListUpload object
    list_upload = static_list_py.ListUpload(access_token=token,
                                            list_id=static_list_id)
    # Run the add to list function
    list_upload.add_leads_to_static_list(list_of_lead_ids=lead_ids_to_add)


def add_leads_to_static_list_from_dataframe(marketo_credentials: Credentials,
                                            dataframe_for_upload: pd.DataFrame,
                                            lead_id_column_name: str,
                                            list_id_column_name: str):

    # Convert into a lists of lead_ids within a dictionary. Each item is  a list.
    static_list_dict = dataframe_for_upload.groupby(list_id_column_name)[lead_id_column_name].apply(list).to_dict()

    total_iterations = len(static_list_dict)
    progress_bar = tqdm(total=total_iterations)

    for key, value in static_list_dict.items():
        add_leads_to_static_list(marketo_credentials=marketo_credentials,
                                 static_list_id=key,
                                 lead_ids_to_add=value)
        progress_bar.update(1)


def add_leads_to_program(marketo_credentials: Credentials, program_id: str, lead_ids_to_add: list, member_status: str):
    # Get initial access token
    token = tok.AccessToken(credentials=marketo_credentials)
    token.get_marketo_access_token()
    # Create an instance of the ListUpload object
    program_mem_upload = programs_py.ProgramMemberUpload(access_token=token,
                                                         program_id=program_id,
                                                         program_member_status=member_status)
    # Run the add to list function
    program_mem_upload.add_members_to_programs(list_of_lead_ids=lead_ids_to_add)


def add_leads_to_program_from_dataframe(marketo_credentials: Credentials,
                                        dataframe_for_upload: pd.DataFrame,
                                        lead_id_column_name: str,
                                        program_id_column_name: str,
                                        member_status_column_name: str):

    # Convert into a lists of lead_ids for each group
    grouped = dataframe_for_upload.groupby([program_id_column_name, member_status_column_name])[lead_id_column_name].\
        apply(list).reset_index()

    total_iterations = grouped.ngroups
    progress_bar = tqdm(total=total_iterations)

    # Apply function to each group
    for _, group in grouped.iterrows():
        add_leads_to_program(marketo_credentials=marketo_credentials,
                             program_id=group[program_id_column_name],
                             member_status=group[member_status_column_name],
                             lead_ids_to_add=group[lead_id_column_name])

        progress_bar.update(1)

