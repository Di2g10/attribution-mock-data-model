import os
import pathlib
from pathlib import Path
from datetime import date
'''
Contain all Global Path variables
'''


# C:\Users\AntonyThornton\CleverTouch\Kainos - Kainos_Acquisitions Migration project

#
PROJECT_FILE_PATH = \
    Path("C:/Users",
         os.getlogin(), # relative path
         "CleverTouch",
         "Kainos - Kainos_Acquisitions Migration project",
         )

# File contains the value mapping from SFDC to Dynamics
# URL: https://clevertouch.sharepoint.com/:x:/s/Kainos/ERIHliiaYjNCup3mLrxMT9sB319MSSPPF6ICKeiUBhYuVQ?e=yFa6sl
FIELD_VALUE_MAPPING_FILEPATH = PROJECT_FILE_PATH / "07 - Migration Mapping Documents/Mapping Document Template.xlsx"


