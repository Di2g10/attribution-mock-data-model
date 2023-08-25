import datetime
from dataclasses import dataclass

import requests as re
import config as config
from credentials import Credentials


@dataclass
class AccessToken:
    credentials: Credentials
    expires_datetime: datetime.datetime = datetime.datetime.now()
    wait_time = 30
    access_token: str = ''
    expires_in: int = 0
    scope: str = ''
    token_type: str = ''
    bulk_url: str = ''
    rest_url: str = ''

    def get_marketo_access_token(self):
        endpoint = self.credentials.identity_url + '/oauth/token'
        data = {'client_id': self.credentials.client_id,
                'client_secret': self.credentials.client_secret,
                'grant_type': 'client_credentials'}
        response = re.get(endpoint, data)
        print(response.text)
        self.access_token = response.json()['access_token']
        self.token_type = response.json()['token_type']
        self.scope = response.json()['scope']
        self.expires_in = response.json()['expires_in']
        self.expires_datetime = datetime.datetime.now() + datetime.timedelta(0, self.expires_in)
        self.bulk_url = self.credentials.bulk_url
        self.rest_url = self.credentials.rest_url
        print(f"Access Token: {self.access_token}"
              f"Token Type: {self.token_type}"
              f"Scope: {self.scope}"
              f"Expires In: {self.expires_in}"
              f"Expires Datetime: {self.expires_datetime}")

    def check_expiry(self):
        if self.expires_datetime < datetime.datetime.now():
            print("Token expired. Requesting new access token.")
            self.get_marketo_access_token()
        else:
            print("Token remains valid. Continuing request.")




if __name__ == '__main__':
    token = AccessToken()
    token.get_marketo_access_token()
