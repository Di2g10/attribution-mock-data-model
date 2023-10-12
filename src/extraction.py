import bulk_lead_extract as lead_extract
import access_token as tok
from credentials import Credentials


def bulk_lead_extract_to_file(fields,
                              filter_type,
                              filter_value,
                              output_directory,
                              output_filename,
                              marketo_credentials: Credentials):

    token = tok.AccessToken(credentials=marketo_credentials)
    token.get_marketo_access_token()
    extract = lead_extract.LeadExtract(access_token=token,
                                       fields=fields,
                                       filter_type=filter_type,
                                       filter_value=filter_value,
                                       output_directory=output_directory,
                                       output_filename=output_filename)
    extract.run_extract()
