import pandas as pd
import create_and_update_leads as lead_upload_py
import access_token as tok
#import marketo_api_tools.classes.static_lists as static_list_py
#import marketo_api_tools.classes.programs as programs_py
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

