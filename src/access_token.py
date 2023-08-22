import datetime
import requests as re
import config as config

class AccessToken:
    access_token: str = ''
    expires_in: int = 0
    expires_datetime: datetime.datetime
    scope: str = ''
    token_type: str = ''

    def get_marketo_access_token(self):
        endpoint = config.identity_url + '/oauth/token'
        data = {'client_id': config.client_id,
                'client_secret': config.client_secret,
                'grant_type': 'client_credentials'}
        response = re.get(endpoint, data)
        print(response.text)
        self.access_token = response.json()['access_token']
        self.token_type = response.json()['token_type']
        self.scope = response.json()['scope']
        self.expires_in = response.json()['expires_in']
        self.expires_datetime = datetime.datetime.now() + datetime.timedelta(0, self.expires_in)
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
