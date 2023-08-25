import pandas as pd
import config
from create_credentials import create_credentials
from extraction import bulk_lead_extract_to_file
from upload import lead_upload, add_leads_to_static_list_from_dataframe, add_leads_to_program_from_dataframe
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


# Check email is unique
if len(existing_leads_for_upload) != existing_leads_for_upload['id'].nunique():
    print("EMAILS NOT UNIQUE")


# Run the upload
marketo_credentials = create_credentials(client_id=config.client_id,
                                         client_secret=config.client_secret,
                                         url=config.url)

lead_upload(marketo_credentials=marketo_credentials,
            data_to_upload=existing_leads_for_upload,
            create_or_update='updateOnly',
            lead_lookup='id',
            batch_size=100
            )


# Upload new records
print("Uploading new leads")
output_file_name = 'New_upload.csv'
new_leads = pd.read_csv(fpath.workspace_directory_output / output_file_name, encoding='utf-8')

if run_type == 'f':
    new_leads_for_upload = new_leads
else:
    new_leads_for_upload = new_leads.head(3)

if len(new_leads_for_upload) != new_leads_for_upload['email'].nunique():
    print("EMAILS NOT UNIQUE")

# # Run the upload
marketo_credentials = create_credentials(client_id=config.client_id,
                                         client_secret=config.client_secret,
                                         url=config.url)

lead_upload(marketo_credentials=marketo_credentials,
            data_to_upload=new_leads_for_upload,
            create_or_update='createOnly',
            lead_lookup='email',
            batch_size=100
            )



# Pull the people from Marketo - Round 2
fields = ['id', 'email', 'Unsubscribed']
marketo_credentials = create_credentials(client_id=config.client_id,
                                         client_secret=config.client_secret,
                                         url=config.url)
bulk_lead_extract_to_file(fields=fields,
                          filter_type='smartListId',
                          filter_value='751814',
                          output_directory=fpath.workspace_directory_process,
                          output_filename='lead_extract2',
                          marketo_credentials=marketo_credentials)



# Obtain people ids for email addresses
# Get list and programs Ids from combined data
output_file_name = 'combined_output.xlsx'
combined_df = pd.read_excel(fpath.workspace_directory_output / output_file_name)
combined_df = combined_df[['email', 'Program ID', 'List ID']]
print(combined_df.head(3).to_markdown())


current_leads_df = pd.read_csv(fpath.workspace_directory_process / 'lead_extract2.csv')

current_leads_df_filtered = current_leads_df[current_leads_df['Unsubscribed'] != True]
email_and_ids_df = current_leads_df[['id', 'email']]

leads_for_programs = combined_df.merge(email_and_ids_df, on='email', how='inner')

print(leads_for_programs.head(3).to_markdown())

# upload to lists
marketo_credentials = create_credentials(client_id=config.client_id,
                                         client_secret=config.client_secret,
                                         url=config.url)
add_leads_to_static_list_from_dataframe(marketo_credentials=marketo_credentials,
                                        dataframe_for_upload=leads_for_programs,
                                        lead_id_column_name='id',
                                        list_id_column_name='List ID')


# ToDo: Add column for program member status
leads_for_programs['memer_status'] = 'Registered'

# upload to programs
add_leads_to_program_from_dataframe(marketo_credentials=marketo_credentials,
                                    dataframe_for_upload=leads_for_programs,
                                    lead_id_column_name='id',
                                    program_id_column_name='Program ID',
                                    member_status_column_name='memer_status')
