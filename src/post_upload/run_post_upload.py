import pandas as pd
import config
from create_credentials import create_credentials
from src.upload import lead_upload, add_leads_to_static_list_from_dataframe, add_leads_to_program_from_dataframe


run_type = input("Run sample or full data? (s/f)")
filepath = input("Enter filepath: ")
existing_leads = pd.read_csv(filepath, encoding='utf-8')

if run_type == 'f':
    rollback_for_upload = existing_leads
else:
    rollback_for_upload = existing_leads.head(5)

# Check email is unique
if len(rollback_for_upload) != rollback_for_upload['id'].nunique():
    print("EMAILS NOT UNIQUE")

print("--------------------------------------------------------------------------------------------------")
print("Running existing leads loads")

marketo_credentials = create_credentials(client_id=config.client_id,
                                         client_secret=config.client_secret,
                                         url=config.url)
lead_upload(marketo_credentials=marketo_credentials,
            data_to_upload=rollback_for_upload,
            create_or_update='updateOnly',
            lead_lookup='id',
            batch_size=100
            )

