import bulk_lead_extract as lead_extract
import access_token as tok

def bulk_lead_extract_to_file(fields,
                              filter_type,
                              filter_value,
                              output_directory,
                              output_filename):
    token = tok.AccessToken()
    token.get_marketo_access_token()
    extract = lead_extract.LeadExtract(access_token=token,
                                       fields=fields,
                                       filter_type=filter_type,
                                       filter_value=filter_value,
                                       output_directory=output_directory,
                                       output_filename=output_filename)
    extract.run_extract()
