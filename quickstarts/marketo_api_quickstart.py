"""Quickstart for creating requests to the Marketo API.

This script creates a Marketo lead with the given email address and uses the credentials
object to manage credentials.
"""

from clevertouch_internal_tools.utils.credentials_manager import MarketoAPICredentials
from clevertouch_internal_tools.apis.marketo_api_tools import marketo_api

if __name__ == "__main__":
    creds = MarketoAPICredentials(keeper_id="EXAMPLE KEEPER ID")

    create_data = [
        {
            "email": "me@example.com",
            "firstName": "Joe",
            "lastName": "Bloggs",
            "company": "Clevertouch",
        }
    ]

    result = marketo_api(
        credentials=creds,
        endpoint="SyncLeads",
        action="createOnly",
        input=create_data,
        lookupField="email",
    )
