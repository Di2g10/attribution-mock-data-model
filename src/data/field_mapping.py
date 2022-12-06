from datetime import date
import pandas as pd

import src.data.extract_and_cache_data

pd.options.mode.chained_assignment = None  # default='warn'

import numpy as np
import os
import config
import pathlib
from pathlib import Path

# install Pandas Connector Part
sf_user = config.sf_user
sf_password = config.sf_password
sf_account = config.sf_account
sf_role = config.sf_role
sf_warehouse = config.sf_warehouse
sf_database = config.sf_database
sf_bl_schema = config.sf_bl_schema
sf_fm_schema = config.sf_bl_schema
# this should be the first part of the snowflake URL
# I stuck on this bit for a long time: Snowflake has a good documentation on account name
# https://docs.snowflake.com/en/user-guide/admin-account-identifier.html#where-are-account-identifiers-used
print("User id :" + sf_user)
print("Account :" + sf_account)
print("Role :" + sf_role)
print("Warehouse :" + sf_warehouse)
print("Database :" + sf_database)
print("Schema :" + sf_bl_schema)
print("Schema :" + sf_fm_schema)

def blackline_data():
    hs_deals = "Select * from KAINOS_DB.HUBSPOT_BLACKLINE_PROD.DEAL"
    hs_contacts = "Select * from KAINOS_DB.HUBSPOT_BLACKLINE_PROD.CONTACT"
    deals = src.data.extract_and_cache_data.fetch_object_from_snowflake(hs_deals)
    contacts = src.data.extract_and_cache_data.fetch_object_from_snowflake(hs_contacts)

    print(deals)
    print(contacts)

    return deals, contacts

