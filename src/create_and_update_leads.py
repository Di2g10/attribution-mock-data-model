import requests as re
import pandas as pd
import access_token as token
from dataclasses import dataclass
import json
import config as config
import time
from datetime import datetime as dt
from pathlib import Path
import access_token as token
import filepaths
import sys
import math
from tqdm import tqdm
import datetime
import csv



@dataclass
class LeadUpload:
    access_token: token.AccessToken
    # createOrUpdate or create or update
    create_or_update: str = 'createOrUpdate'
    lead_lookup: str = 'id'
    batch_size: int = 200

    def upload_leads_batch(self, data_to_upload: list):

        # Check token for each batch
        self.access_token.check_expiry()

        headers = {
            'Authorization': 'Bearer {}'.format(self.access_token.access_token),
            "Content-Type": "application/json"}
        payload = {
            "input": data_to_upload,
            "action": self.create_or_update,
            "lookupField": self.lead_lookup
        }
        response = re.post(self.access_token.rest_url + '/v1/leads.json', json=payload, headers=headers)

        return response

    def upload_leads_in_batches(self, data_for_upload: pd.DataFrame):
        # Convert into list of dictionaries
        data_change_dicts = data_for_upload.to_dict(orient='records')
        filtered_data_change_dicts = []
        for d in data_change_dicts:
            filtered_dict = {key: value for key, value in d.items() if
                             (isinstance(value, str) or not math.isnan(value))}
            filtered_data_change_dicts.append(filtered_dict)

        # Read logged changes
        prev_log_df = pd.read_csv(str(filepaths.log_file))

        # Get rows from log where type = 'Upload Value'
        log_rows = prev_log_df[prev_log_df['type'] == 'Upload Value']

        # Extract IDs from logs
        # Function to extract 'id' values from a JSON string
        def extract_ids_from_json(json_str):
            json_str = json_str.replace(", \"success\": True", "")
            print(json_str)
            data = json.loads(json_str)
            return [item['id'] for item in data['result']]

        # Create a list to store all the 'id' values
        logged_ids = []
        # Iterate over the 'full_response' column and extract 'id' values from each JSON
        for json_str in log_rows['full_response']:
            json_str = json_str.replace("'", "\"")
            if json_str[45:50] == True:
                ids = extract_ids_from_json(json_str)
                logged_ids.extend(ids)

        # Remove dictionaries that only have an id key and no data changes
        # Remove dictionaries with only one key
        data_to_upload = [d for d in filtered_data_change_dicts if len(d) > 1]

        # Remove dictionaries where record ID has already been logged
        print('Previously logged IDs: ' + str(len(logged_ids)))
        if len(logged_ids) != 0:
            filtered_data_to_upload = [item for item in data_to_upload if item['Id'] not in logged_ids]
        else:
            filtered_data_to_upload = data_to_upload

        # Apply upload_leads_batch function using batches
        num_value_changes = len(filtered_data_to_upload)
        num_batches = (num_value_changes // self.batch_size) + 1

        # Stop the script if all data has already been uploaded
        if num_value_changes < 1:
            print('No more values to upload. Check logs.')
            sys.exit()

        print('Function will execute ' + str(num_value_changes) + ' value changes, across ' + str(
            num_batches) + ' batches')
        total_iterations = num_batches
        progress_bar = tqdm(total=total_iterations)

        for batch in range(num_batches):
            # Run upload for each batch
            start_index = batch * self.batch_size
            end_index = min(start_index + self.batch_size, num_value_changes)
            batch_data = filtered_data_to_upload[start_index:end_index]
            print("Import data from index " + str(start_index) + ' to index ' + str(end_index))
            # print(batch_data[0])
            batch_response = self.upload_leads_batch(batch_data)
            batch_response = batch_response.json()
            print(batch_response)

            # Log the batch
            log_row = [dt.now().strftime("%Y-%m-%d %H:%M:%S"),
                       "Upload Value",
                       "Index " + str(start_index) + ' to index ' + str(end_index),
                       batch_response['success'],
                       batch_response]

            with open(str(filepaths.log_file), mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(log_row)

            progress_bar.update(1)
            time.sleep(120)
