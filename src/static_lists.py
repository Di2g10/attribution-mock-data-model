import requests as re
import pandas as pd
from dataclasses import dataclass
import json
import config as config
from datetime import datetime as dt
from pathlib import Path
import access_token as token
import filepaths
import sys
import math
from tqdm import tqdm
import csv
import time


@dataclass
class ListUpload:
    access_token: token.AccessToken
    list_id: str = ''

    def add_leads_to_static_list_batch(self, list_of_lead_ids: list):

        # Check token for each batch
        self.access_token.check_expiry()

        headers = {
            'Authorization': 'Bearer {}'.format(self.access_token.access_token),
            "Content-Type": "application/json"}
        payload = {
            "input": list_of_lead_ids
        }
        response = re.post(self.access_token.rest_url + '/v1/lists/' + str(self.list_id) + '/leads.json',
                           json=payload,
                           headers=headers)

        print(response.json())

        return response

    def add_leads_to_static_list(self, list_of_lead_ids: list):
        # Format the Ids for the API request
        ids_for_request = []
        for id in list_of_lead_ids:
            list_item = {"id": id}
            ids_for_request.append(list_item)

        print(ids_for_request)

        num_of_additions = len(ids_for_request)
        batch_size = 200
        num_batches = num_of_additions / batch_size
        num_batches = math.ceil(num_batches)

        print('Function will execute ' + str(num_of_additions) + ' value changes, across ' + str(
            num_batches) + ' batches')
        total_iterations = num_batches
        progress_bar = tqdm(total=total_iterations)

        for batch in range(num_batches):
            # Run upload for each batch
            start_index = batch * batch_size
            end_index = min(start_index + batch_size, num_of_additions)
            batch_data = ids_for_request[start_index:end_index]
            print("Import data from index " + str(start_index) + ' to index ' + str(end_index))

            # Run the API request function
            response = self.add_leads_to_static_list_batch(list_of_lead_ids=batch_data)

            json_response = response.json()
            # Log the batch
            log_row = [dt.now().strftime("%Y-%m-%d %H:%M:%S"),
                       "Add to Static List",
                       "Index " + str(start_index) + ' to index ' + str(end_index),
                       json_response['success'],
                       json_response]

            with open(str(filepaths.log_file), mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(log_row)

            progress_bar.update(1)
            time.sleep(30)
