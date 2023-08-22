import requests as re
import pandas as pd
import access_token as token
from dataclasses import dataclass
import json
import config as config
import time
import io
from pathlib import Path


@dataclass
class LeadExtract:
    access_token: token.AccessToken
    fields: list
    filter_type: str
    output_directory: Path
    output_filename: str
    filter_value: str = ''
    date_start_at: str = ''
    date_end_at: str = ''
    export_id: str = ''
    export_status: str = ''

    def _set_filter_type_values(self):
        set_filter_value = ''
        if self.filter_type == 'createdAt':
            set_filter_value = {"startAt": self.date_start_at, "endAt": self.date_end_at}
        if self.filter_type == 'updatedAt':
            set_filter_value = {"startAt": self.date_start_at, "endAt": self.date_end_at}
        if self.filter_type == 'staticListName':
            set_filter_value = self.filter_value
        if self.filter_type == 'staticListId':
            set_filter_value = int(self.filter_value)
        if self.filter_type == 'smartListName':
            set_filter_value = self.filter_value
        if self.filter_type == 'smartListId':
            set_filter_value = int(self.filter_value)
        return set_filter_value

    def _create_extract_job(self):
        endpoint = config.bulk_url + f"/v1/leads/export/create.json"
        self.access_token.check_expiry()
        headers = {'Authorization': 'Bearer {}'.format(self.access_token.access_token),
                   'Accept': 'application/json',
                   'Content-Type': 'application/json'}
        print(self.fields)
        print({self.filter_type: self._set_filter_type_values()})
        data = json.dumps({'fields': self.fields,
                           'format': 'CSV',
                           'filter': {self.filter_type: self._set_filter_type_values()}})
        response = re.post(endpoint, headers=headers, data=data)
        print(response.text)
        self.export_id = json.loads((json.dumps((response.json()['result'])[0])))['exportId']
        print("Export Id Set to: " + self.export_id)
        self.export_status = json.loads((json.dumps((response.json()['result'])[0])))['status']
        print("Export Status set to " + self.export_status)

    def _enqueue_extract_job(self):
        endpoint = config.bulk_url + f"/v1/leads/export/{self.export_id}/enqueue.json"
        self.access_token.check_expiry()
        headers = {'Authorization': 'Bearer {}'.format(self.access_token.access_token),
                   'Accept': 'application/json',
                   'Content-Type': 'application/json'}
        response = re.post(endpoint, headers=headers)
        print(response.text)
        self.export_status = json.loads((json.dumps((response.json()['result'])[0])))['status']
        print("Export Status set to " + self.export_status)

    def _poll_job_status(self):
        endpoint = config.bulk_url + f'/v1/leads/export/{self.export_id}/status.json'
        self.access_token.check_expiry()
        headers = {'Authorization': 'Bearer {}'.format(self.access_token.access_token),
                   'Accept': 'application/json',
                   'Content-Type': 'application/json'}
        response = re.get(endpoint, headers=headers)
        print(response.text)
        self.export_status = json.loads((json.dumps((response.json()['result'])[0])))['status']
        print("Export Status set to " + self.export_status)

    def _retrieve_extract(self):
        endpoint = config.bulk_url + f'/v1/leads/export/{self.export_id}/file.json'
        headers = {'Authorization': 'Bearer {}'.format(self.access_token.access_token),
                   'Accept': 'application/json',
                   'Content-Type': 'application/json'}

        url_data = re.get(endpoint, headers=headers).content
        df_data = pd.read_csv(io.StringIO(url_data.decode('utf-8')))
        print("Extract to Dataframe Complete.")
        df_data.to_csv(self.output_directory / (self.output_filename + ".csv"), index=False)

    def _cancel_job(self):
        endpoint = config.bulk_url + f'/v1/leads/export/{self.export_id}/cancel.json'
        self.access_token.check_expiry()
        headers = {'Authorization': 'Bearer {}'.format(self.access_token.access_token),
                   'Accept': 'application/json',
                   'Content-Type': 'application/json'}
        response = re.post(endpoint, headers=headers)
        print(response.text)

    def run_extract(self):
        self._create_extract_job()
        self._enqueue_extract_job()
        while self.export_status != 'Completed':
            self._poll_job_status()
            time.sleep(config.time_sleep_seconds)
        self._retrieve_extract()
        self._cancel_job()

    def get_extracted_leads_as_dataframe(self):
        file_path = str(self.output_directory.joinpath(self.output_filename)) + '.csv'
        df = pd.read_csv(file_path)

        return df
