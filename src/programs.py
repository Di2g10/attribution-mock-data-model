import requests as re
import pandas as pd
import access_token as token
from dataclasses import dataclass
import json
import config as config
from datetime import datetime as dt
import time
from pathlib import Path
import filepaths
import sys
import math
from tqdm import tqdm
import csv


@dataclass
class ProgramMemberUpload:
    access_token: token.AccessToken
    program_id: str = ''
    program_member_status: str = ''

    def add_members_to_programs_batch(self, list_of_lead_ids: list):

        # Check token for each batch
        self.access_token.check_expiry()

        headers = {
            'Authorization': 'Bearer {}'.format(self.access_token.access_token),
            "Content-Type": "application/json"}
        payload = {
            "statusName": self.program_member_status,
            "input": list_of_lead_ids
        }
        response = re.post(self.access_token.rest_url + '/v1/programs/' + str(self.program_id) + '/members/status.json',
                           json=payload,
                           headers=headers)

        print(response.json())

        return response

    def add_members_to_programs(self, list_of_lead_ids: list):
        # Format the Ids for the API request
        ids_for_request = []
        for id in list_of_lead_ids:
            list_item = {'leadId': id}
            ids_for_request.append(list_item)

        print(ids_for_request)

        num_of_additions = len(ids_for_request)
        batch_size = 200
        num_batches = num_of_additions / batch_size
        num_batches = math.ceil(num_batches)

        for batch in range(num_batches):
            # Run upload for each batch
            start_index = batch * batch_size
            end_index = min(start_index + batch_size, num_of_additions)
            batch_data = ids_for_request[start_index:end_index]
            print("Import data from index " + str(start_index) + ' to index ' + str(end_index))

            # Run the API request function
            response = self.add_members_to_programs_batch(list_of_lead_ids=batch_data)

            json_response = response.json()
            # Log the batch
            log_row = [dt.now().strftime("%Y-%m-%d %H:%M:%S"),
                       "Change Program member Status",
                       "Index " + str(start_index) + ' to index ' + str(end_index),
                       json_response['success'],
                       json_response]

            with open(str(filepaths.log_file), mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(log_row)

            # progress_bar.update(1)
            time.sleep(10)


