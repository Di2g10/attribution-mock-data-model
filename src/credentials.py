"""Define the credentials class for Marketo API"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Credentials:
    client_id: str
    client_secret: str
    url: str
    """
    Contains required credentials to request an access token for a Marketo Instance.
    All attributes are required.
    :param client_id: str This is Client ID value of the LaunchPoint Service being used for the API call.
    :param client_secret: str This is the Client Secret value of the LaunchPoint Service being used for the API call.
    :param url: str This is the url of the marketo instance. For example: 'https://XXX-XXX-XXX.mktorest.com'
    """

    @property
    def identity_url(self):
        return f"{self.url}/identity"

    @property
    def rest_url(self):
        return f"{self.url}/rest"

    @property
    def bulk_url(self):
        return f"{self.url}/bulk"
