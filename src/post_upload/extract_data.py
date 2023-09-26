import os
from pathlib import Path
import pandas as pd
import marketo_api_tools.functions.extraction
import marketo_api_tools.classes.activity_types as act_type
import marketo_api_tools.classes.access_token as atoken
import config as cf
import requests
import json
import tabulate

input_filepath = Path(
    "C:/Users",
    os.getlogin(),
    "Documents",
    "aveva-marketo-dedupe",
    "data",
    "input")

marketo_credentials = marketo_api_tools.functions.extraction.create_credentials(cf.client_id,
                                                          cf.client_secret,
                                                          cf.url)

token = atoken.AccessToken(marketo_credentials)
token.get_marketo_access_token()
activity_id_df = act_type.ActivityTypesExtract(token).get_activity_types()

marketo_api_tools.functions.extraction.bulk_activity_extract_to_file(
    start_at_filter="2023-08-25T00:00:00-00:00",
    end_at_filter="2023-08-26T00:00:00-00:00",
    output_directory=input_filepath,
    output_filename="activity_data_value_change",
    marketo_credentials=marketo_credentials,
    activity_type_ids=[13],

    )


df = pd.read_csv(input_filepath / "activity_data_value_change.csv.csv")
# filter out df based on the primaryAttributeValue, keep rows that primaryAttributeValue equals to: Last Campaign, MEL Campaign, AQL Campaign, AQL Latest Campaign

df = df[df['primaryAttributeValue'].isin(['Last Campaign',
                                          'MEL Campaign',
                                          'AQL Campaign',
                                          'AQL Latest Campaign',
                                          'Preferred Language'])]
print(df.head().to_markdown())

print(df.describe().to_markdown())
# output this to a csv file
df.to_csv(input_filepath / "activity_data_value_change_filtered.csv", index=False)

# break the field "attributes" into multiple columns based on its key value pairs
df = pd.read_csv(input_filepath / "activity_data_value_change_filtered.csv")
df = pd.concat([df.drop(['attributes'], axis=1), df['attributes'].apply(json.loads).apply(pd.Series)], axis=1)
df.to_csv(input_filepath / "activity_data_value_change_filtered_reformatted.csv", index=False)

print(df.head().to_markdown())
