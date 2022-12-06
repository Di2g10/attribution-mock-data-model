import src
from src.connectors.snowflake import query


def blackline_data():
    hs_deals = "Select * from KAINOS_DB.HUBSPOT_BLACKLINE_PROD.DEAL"
    hs_contacts = "Select * from KAINOS_DB.HUBSPOT_BLACKLINE_PROD.CONTACT"
    deals = src.connectors.snowflake.query(hs_deals)
    contacts = src.connectors.snowflake.query(hs_contacts)

    print(deals)
    print(contacts)

    return deals, contacts


def formulate_data():
    hs_deals = "Select * from KAINOS_DB.HUBSPOT_FORMULATE_PROD.DEAL"
    hs_contacts = "Select * from KAINOS_DB.HUBSPOT_FORMULATE_PROD.CONTACT"
    deals = src.connectors.snowflake.query(hs_deals)
    contacts = src.connectors.snowflake.query(hs_contacts)

    print(deals)
    print(contacts)

    return deals, contacts
