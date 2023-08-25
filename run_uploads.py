import pandas as pd

import config
from create_credentials import create_credentials
from extraction import bulk_lead_extract_to_file
from upload import lead_upload
import filepaths as fpath
from tqdm import tqdm

run_type = input("Run sample or full data? (s/f)")

# Upload existing data
print("Uploading existing leads")
output_file_name = 'Existing_upload.csv'
existing_leads = pd.read_csv(fpath.workspace_directory_output / output_file_name, encoding='utf-8')

if run_type == 'f':
    existing_leads_for_upload = existing_leads
else:
    existing_leads_for_upload = existing_leads.head(3)

# Run the upload
# marketo_credentials = create_credentials(client_id=config.client_id,
#                                          client_secret=config.client_secret,
#                                          url=config.url)
#
# lead_upload(marketo_credentials=marketo_credentials,
#             data_to_upload=existing_leads_for_upload,
#             create_or_update='updateOnly',
#             lead_lookup='id',
#             batch_size=100
#             )


# Upload new records
print("Uploading new leads")
output_file_name = 'New_upload.csv'
new_leads = pd.read_csv(fpath.workspace_directory_output / output_file_name, encoding='utf-8')


if run_type == 'f':
    new_leads_for_upload = new_leads
else:
    new_leads_for_upload = new_leads.head(3)

# # Run the upload
# marketo_credentials = create_credentials(client_id=config.client_id,
#                                          client_secret=config.client_secret,
#                                          url=config.url)
#
# lead_upload(marketo_credentials=marketo_credentials,
#             data_to_upload=new_leads_for_upload,
#             create_or_update='createOnly',
#             lead_lookup='email',
#             batch_size=100
#             )



# Pull the people from Marketo - Round 2
# fields = ['id', 'email', 'Unsubscribed']
# marketo_credentials = create_credentials(client_id=config.client_id,
#                                          client_secret=config.client_secret,
#                                          url=config.url)
# bulk_lead_extract_to_file(fields=fields,
#                           filter_type='smartListId',
#                           filter_value='751814',
#                           output_directory=fpath.workspace_directory_process,
#                           output_filename='lead_extract2',
#                           marketo_credentials=marketo_credentials)



# Obtain people ids for email addresses

current_leads_df = pd.read_csv(fpath.workspace_directory_process / 'lead_extract2.csv')

current_leads_df_filtered = current_leads_df[current_leads_df['Unsubscribed'] != True]
email_and_ids_df = current_leads_df[['id', 'email']]

# Create a dictionary from the selected columns
# email_and_ids_dict = email_and_ids_df.to_dict(orient='records')
email_and_ids_list = email_and_ids_df.to_dict(orient='records')

# Convert the list of dictionaries into a single dictionary
email_and_ids_dict = {entry['email']: entry['id'] for entry in email_and_ids_list}

# Add Id for new records
new_leads_for_upload['id'] = new_leads_for_upload['email'].map(email_and_ids_dict)

# Remove records with no id
new_leads_for_programs = new_leads_for_upload[new_leads_for_upload['id'].notna()]

print(str(len(new_leads_for_programs)) + ' new leads to be added to programs and lists')
print(new_leads_for_programs.head(10).to_markdown())


# ToDo: Check all existing records have an Id in the non_unsubscribed Id and email dict


# ToDo: Concat new and existing leads ready for list uploads

# upload to lists

# upload to programs


