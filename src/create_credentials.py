import credentials as Credentials

def create_credentials(client_id: str,
                       client_secret: str,
                       url: str):
    marketo_credentials = Credentials.Credentials(client_id=client_id,
                                                  client_secret=client_secret,
                                                  url=url)
    return marketo_credentials