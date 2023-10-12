import marketo_api_tools.functions.upload
import marketo_api_tools.classes.access_token as atoken
import config as cf
import credentials as Credentials
import pandas as pd

def create_credentials(client_id: str,
                       client_secret: str,
                       url: str):
    marketo_credentials = Credentials.Credentials(client_id=client_id,
                                                  client_secret=client_secret,
                                                  url=url)
    return marketo_credentials

marketo_credentials = create_credentials(cf.client_id, cf.client_secret, cf.url)

token = atoken.AccessToken(marketo_credentials)
token.get_marketo_access_token()

df = pd.read_csv('C:/Users/AryaZhao/Documents/aveva-marketo-dedupe/data/output/AQL_campaign_to_upload.csv')
marketo_api_tools.functions.upload.lead_upload(
    marketo_credentials=marketo_credentials,
    data_to_upload=df,
    create_or_update='updateOnly',
    lead_lookup='id',
    batch_size=5,
)