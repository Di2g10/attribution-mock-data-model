import pandas as pd
from pathlib import Path, PureWindowsPath
import os
from locations import PROJECT_FOLDER
from dataclasses import dataclass, field
from enum import Enum
import msoffcrypto
import openpyxl
from datetime import *
from dateutil import parser
import io
import numpy as np
import warnings
import re


class Region(Enum):
    EMEA = 'EMEA'
    FNA = 'FNA'


@dataclass
class Upload:
    number: int = None
    name: str = None
    target_date: datetime = None
    region: Region = None
    status: str = None
    source_data_path: str = None
    excel_sheet_name: str = None
    excel_password: str = None
    upload_folder_path: str = None
    data: pd.DataFrame = None
    cleaned_data: pd.DataFrame = None


def read_upload_tracker():
    # Set to ignore user warnings
    warnings.simplefilter("ignore", category=UserWarning)

    # Read the Excel file using pandas
    upload_tracker_df = pd.read_excel(PROJECT_FOLDER / 'Upload Tracker V3.xlsx')
    # Create a list to store the class objects
    uploads_list = []

    # Iterate through each row in the DataFrame and create a class object from the data
    for index, row in upload_tracker_df.iterrows():
        number = row['Upload Number']
        name = row['Upload Name']
        target_date = row['Requested Date for Upload']
        region = row['Region']
        status = row['Status']
        file_path = row['Full File Path for Data']
        excel_sheet_name = row['Excel Sheet Name']
        excel_password = row['Excel Password']

        upload_object = Upload(number, name, target_date.strftime("%Y-%m-%d"), region, status, file_path, excel_sheet_name, excel_password)
        uploads_list.append(upload_object)

    # Reset warning settings
    warnings.resetwarnings()

    return uploads_list


def select_an_upload_to_run(uploads_list):
    user_input = 0

    input_message = "Pick an upload to run:\n"

    for upload in uploads_list:
        if upload.status == 'Requested':
            input_message += str(upload.number) + '  (Upload Name: ' + str(upload.name) + '. Requested for: ' + \
                             str(upload.target_date) + ') \n'

    input_message += 'Select upload number: '

    while int(user_input) not in [upload.number for upload in uploads_list]:
        user_input = input(input_message)

    selected_upload = None

    for upload in uploads_list:
        if int(user_input) == upload.number:
            selected_upload = upload
            break

    print('You picked upload : ' + str(upload.number) + '  (Upload Name: ' + str(upload.name) + ')\n')

    return selected_upload


def validate_selected_upload(upload):
    if not PureWindowsPath(upload.source_data_path).is_absolute():
        print("Error: Invalid source data file path. Please enter a valid file path in the upload tracker.\n")
        exit()
    else:
        if len(upload.source_data_path) == 0:
            print("Error: No data source file path found. Please enter a file path in the upload tracker\n")
            exit()
        else:
            try:
                upload.source_data_path = Path(upload.source_data_path)  # Convert to pathlib.Path object
            except Exception as e:
                print("Error: Unable to convert string to pathlib.Path object.")
                print("Exception message:", e, )
                exit()
            else:
                print("Upload object has been validated\n")


def set_up_upload_folder(upload: object):
    """
    A function that takes an upload and creates a folder for the upload.
    The new folder name will be generated from the upload details.
    :param upload: an object of Upload class.
    :return: raw_data: a pandas dataframe of the data that should be uploaded.
    """

    # Create file from upload number, name, and date
    upload_folder_name = str(upload.number) + '_' + upload.name + '_' + str(upload.target_date)
    folder_path = PureWindowsPath(PROJECT_FOLDER / upload_folder_name)

    # Set the upload folder path on the upload object
    upload.upload_folder_path = folder_path

    # Check if folder exists
    if os.path.exists(folder_path):
        print('Folder has already been created for this upload!!!\n')
    else:
        # Folder does not exist, so create folder and populate it.
        os.makedirs(folder_path)
        # Confirm that folder now exists
        if os.path.exists(folder_path):
            print(f'Folder created: {upload_folder_name}')
        else:
            print(f'Error creating folder: {upload_folder_name}')


def get_source_data(upload):
    # Change username in filepath
    file_path = str(upload.source_data_path)
    file_path_end = '\CleverTouch' + file_path.split('\CleverTouch')[1]
    file_path_new = 'C:\\Users\\' + os.getlogin() + file_path_end
    # Update the filepath on the upload object
    upload.source_data_path = Path(file_path_new)

    print("Retrieving data from " + str(upload.source_data_path))
    try:
        # Read CSV files
        if upload.source_data_path.suffix.lower() == '.csv':
            upload.data = pd.read_csv(upload.source_data_path, encoding="utf-8")

        # Read password-protected Excel files
        elif not pd.isna(upload.excel_password) and len(str(upload.excel_password)) > 0:

            decrypted_workbook = io.BytesIO()

            # Decrypt workbook and save new version in memory
            with open(upload.source_data_path, 'rb') as file:
                office_file = msoffcrypto.OfficeFile(file)
                office_file.load_key(password=upload.excel_password)
                office_file.decrypt(decrypted_workbook)

            # Read data from decrypted version of workbook
            workbook = openpyxl.load_workbook(filename=decrypted_workbook)
            worksheet = workbook.active
            # get values from worksheet
            data = worksheet.values
            # get column names from worksheet
            columns = next(data)
            upload.data = pd.DataFrame(data, columns=columns)

        # Read standard Excel files
        else:
            upload.data = pd.read_excel(upload.source_data_path, sheet_name=upload.excel_sheet_name)

    # Error handing for the file reading
    except FileNotFoundError:
        print("File not found error: check if the specified file path is correct.\n")
    except ValueError:
        print("Value error: check if the specified sheet name is valid.\n")
    except PermissionError:
        print("Permission error: Either the details provided are incorrect, or the file is read-only. "
              "Check the filepath and sheet name in the upload tracker\n")

    # Save the extracted data as a pre-cleaned back up
    upload.data.to_csv(path_or_buf=str(upload.upload_folder_path) + '/upload ' + str(upload.number) + ' pre-clean.csv')
    print("Pre-cleaning data backup has been saved to upload folder\n")


# Initialise a class of Field
class DataType(Enum):
    Text = "Text"
    Textarea = "TextArea"
    Dropdown = "Dropdown"
    Checkbox = "Checkbox"
    Date = "Date"
    Radio = "Radio"
    Button = "Button"
    Number = "Number"
    MultiSelect = "MultiSelect"


@dataclass
class Field:
    name: str = None
    api_name: str = None
    region: str = None
    data_type: DataType = None
    required_field: bool = False
    picklist_name: str = None
    field_values: pd.Series = None


def get_field_values(list_of_fields: list, upload_object: Upload):
    # Get mapped data from upload object
    dataframe = upload_object.data

    # Get field objects of the right region
    fields_to_use = []
    for field_object in list_of_fields:
        if upload_object.region == field_object.region:
            fields_to_use.append(field_object)

    for field_object in fields_to_use:
        if field_object.api_name in dataframe.columns:
            # print("Data gathered from " + field_object.api_name)
            field_object.field_values = dataframe[field_object.api_name]


def read_fields_dictionary():
    # Read the Excel file using pandas
    fields_df = pd.read_excel(PROJECT_FOLDER / "Mapping Files" / 'Pardot Fields.xlsx')
    # Create a list to store the class objects
    field_list = []

    # Iterate through each row in the DataFrame and create a class object from the data
    for index, row in fields_df.iterrows():
        name = row['field_name']
        api_name = row['api_name']
        region = row['region']
        data_type = row['data_type']
        required_field = row['required_field']
        picklist_name = row['picklist_name']

        try:
            field_object = Field(name, api_name, region, data_type, required_field, picklist_name)
            field_list.append(field_object)
        except ValueError:
            print("Value Error: Check data types match the allowed values in the data type enum!\n")
    return field_list


@dataclass
class FieldMap:
    source_field_name: str = None
    destination_api_name: str = None
    region: str = None


def read_field_mapping_dictionary():
    # Read the Excel file using pandas
    field_mapping_df = pd.read_excel(PROJECT_FOLDER / "Mapping Files" / 'Fujitsu Pardot Field Mapping.xlsx')
    # Create a list to store the class objects
    field_mapping_list = []

    # Iterate through each row in the DataFrame and create a class object from the data
    for index, row in field_mapping_df.iterrows():
        source_field_name = row['source_field_name']
        destination_api_name = row['destination_api_name']
        region = row['region']

        field_mapping_object = FieldMap(source_field_name, destination_api_name, region)
        field_mapping_list.append(field_mapping_object)

    return field_mapping_list


def apply_field_mapping_to_upload(upload_object: Upload, field_mapping_list: list):
    print("")
    # Read source dataframe from the Upload object
    source_df = upload_object.data

    # Select field mappings where their region matches the upload object
    field_mapping_to_apply = []

    for field_map in field_mapping_list:
        if field_map.region == upload_object.region:
            field_mapping_to_apply.append(field_map)

    unmatched_columns = []
    destination_names = []

    # Rename dataframe column names using the field_map objects
    for column_name in source_df.columns:
        matched = False
        for field_map in field_mapping_to_apply:
            if str.lower(column_name).strip() == str.lower(field_map.source_field_name):
                if field_map.destination_api_name != "IGNORE" and field_map.destination_api_name in destination_names:
                    # destination name already exists, handle error
                    raise ValueError("Please adjust mappings! Two fields have been mapped to the same "
                                     "destination field: {}".format(field_map.destination_api_name))
                source_df = source_df.rename(columns={column_name: field_map.destination_api_name})
                destination_names.append(field_map.destination_api_name)
                matched = True
                print(str(column_name) + " -> " + str(field_map.destination_api_name))
                break
        if not matched:
            unmatched_columns.append(column_name)

    # Drop columns marked as "IGNORE"
    source_df = source_df.drop([col for col in source_df.columns if col == "IGNORE"], axis=1)

    # If there are unmapped columns, return the unmapped columns and stop the script
    if len(unmatched_columns) > 0:
        print("")
        print("Fields need mapping:")
        print(unmatched_columns)
        quit()
    else:
        upload_object.data = source_df
        print("All fields have been mapped successfully! Please review the mappings above.\n")

        proceed = input("Are you happy with the above field mappings? (y/n)  ")

        if proceed == 'y':
            print("")
        else:
            print("Please change the field mappings in the field mapping doc.")
            quit()

    return upload_object


# ----------------------------------------------Data Cleaning Functions ----------------------------------------------

def clean_number_values(value) -> int:
    """
    Take values and ensure they are int values
    :param value:
    :return: An int value
    """
    try:
        if type(value) == int or type(value) == float:
            cleaned_value = value
        else:
            # Check if string is a range
            pattern = r'\d+-\d+'
            match = re.search(pattern, value)
            if match:
                # Remove all punctuation
                nums_from_range = str.split(value, "-")
                first_in_range = nums_from_range[0]
                cleaned_value = re.sub(r'\D', '', first_in_range)
            elif str.isnumeric(value):
                cleaned_value = value
            else:
                cleaned_value = re.sub(r'\D', '', value)

    except ValueError:
        cleaned_value = np.nan
    return cleaned_value


def clean_date_values(value, date_format_string):
    """
    Take values and ensure they are datetime values
    :param date_format_string: The incoming date format. Such as: '%d-%m-%Y'
    :param value: The incoming data value.
    :return: A datetime value.
    """
    try:
        # Check whether value is a timestamp
        if isinstance(value, int):
            if value < 0 or value > 2147483647:
                raise ValueError("Invalid Unix timestamp value")
            else:
                cleaned_value = datetime.datetime.fromtimestamp(value)

        # Value is already a datetime object, no need to convert
        elif isinstance(value, datetime):
            cleaned_value = value

        # If value is a string, check it contains a date and then parse
        elif type(value) == str:
            if "-" not in value and "/" not in value:
                raise ValueError("Invalid date string value")
                cleaned_value = pd.NaT
            else:
                cleaned_value = datetime.strptime(value, date_format_string)

    # If standard parsing does not work, use the more general parser that will attempt to derive the datetime format.
    # More prone to incorrectly parse non-date data
    except ValueError:
        try:
            cleaned_value = parser.parse(value)
        except ValueError:
            cleaned_value = pd.NaT

    except TypeError:
        cleaned_value = pd.NaT

    return cleaned_value


def clean_field_values(list_of_field_objects: list, date_format_string):
    """
    A function runs several data cleaning functions.
    The datatype of the field object determines which cleaning function will run.
    :param list_of_field_objects:
    :param date_format_string: The incoming date format. Such as: '%d-%m-%Y'
    :return:
    """
    for field_object in list_of_field_objects:
        if field_object.data_type == "Date":

            null_count_before = field_object.field_values.isnull().sum()

            field_object.field_values = field_object.field_values.apply(clean_date_values,
                                                                        date_format_string=date_format_string)
            print("\nDate formatting completed for: " + field_object.name)

            null_count_after = field_object.field_values.isnull().sum()

            # Check if the number of null values has increased
            print("Nulls before: " + str(null_count_before) + "-> Null count after: " + str(null_count_after))
            if null_count_after > null_count_before:
                raise ValueError("The number of null values has increased in " + field_object.name)

        elif field_object.data_type == "Number":

            null_count_before = field_object.field_values.isnull().sum()

            field_object.field_values = field_object.field_values.apply(clean_number_values)
            print("\nNumber formatting completed for: " + field_object.name)

            null_count_after = field_object.field_values.isnull().sum()

            # Check if the number of null values has increased
            print("Nulls before: " + str(null_count_before) + "-> Null count after: " + str(null_count_after))
            if null_count_after > null_count_before:
                raise ValueError("The number of null values has increased in " + field_object.name)


@dataclass
class Picklist:
    name: str = None
    region: str = None
    value_mappings: dict = None


def read_picklists() -> list[Picklist]:
    """

    :return: A list of Picklist objects
    """
    # Read the Excel file using pandas
    picklist_df = pd.read_excel(PROJECT_FOLDER / "Mapping Files" / 'Pardot Picklist Mapping.xlsx')
    # Create a list to store the class objects
    groups = picklist_df.groupby(['picklist_name', 'region'])

    picklist_list = []

    for (name, region), group in groups:
        # Create a dictionary of the value mappings. Converts all keys and values are strings.
        value_mappings = dict(zip(map(str, group['data_value']), map(str, group['picklist_value'])))
        picklist = Picklist(name=name, region=region, value_mappings=value_mappings)
        picklist_list.append(picklist)

    return picklist_list


def apply_picklist_mapping(upload_object: Upload, list_of_field_objects: list, list_of_picklist_maps: list):
    print("\nPicklist mapping commencing:\n")

    # Create an empty dataframe to store unmatched data_values
    all_unmatched_values_df = pd.DataFrame(columns=['region', 'picklist_name', 'data_value'])

    for field in list_of_field_objects:
        for picklist in list_of_picklist_maps:
            if field.region == picklist.region and field.picklist_name == picklist.name:

                # DATA PREP
                # Lowercase all the keys before mapping
                lower_picklist_map = {key.lower(): value for key, value in picklist.value_mappings.items()}

                # Lowercase all the series values
                def lower_str(val):
                    if isinstance(val, str):
                        return val.lower().strip()
                    else:
                        return val

                # apply the custom function to each element of the Series
                lowercase_field_values = field.field_values.astype(str)
                lowercase_field_values = lowercase_field_values.apply(lower_str)

                # MAPPING
                # Map the values in the Series using the lower_picklist_map dictionary
                mapped_field_values = lowercase_field_values.map(lower_picklist_map)
                mapped_field_values[mapped_field_values == "nan"] = np.nan
                values_from_mapping = pd.Series(mapped_field_values.unique())
                print("Values from picklist mapping for " + field.name)
                print(values_from_mapping.values)
                print("\n")

                # Get the unmatched values from the Series
                unmatched_values = lowercase_field_values[~lowercase_field_values.isin(lower_picklist_map.keys())]
                unique_unmatched_values = pd.Series(unmatched_values.unique())
                # Add into a dataframe with region and picklist name
                unique_unmatched_values = unique_unmatched_values[unique_unmatched_values != "nan"]
                unique_unmatched_values.name = 'data_value'
                unmatched_value_df = pd.DataFrame(unique_unmatched_values)
                unmatched_value_df.insert(0, 'region', field.region)
                unmatched_value_df.insert(1, 'picklist_name', field.picklist_name)
                # append the new unmatched values to the main dataframe
                unmatched_value_df = unmatched_value_df[unmatched_value_df['data_value'].notnull()]
                all_unmatched_values_df = pd.concat([all_unmatched_values_df, unmatched_value_df])

                # Add matched values back onto the field object
                field.field_values = mapped_field_values

    if len(all_unmatched_values_df) > 0:
        print("\nPlease map these picklist values in the picklist mapping spreadsheet: ")
        print(all_unmatched_values_df.to_markdown())
        all_unmatched_values_df.to_csv(path_or_buf=str(upload_object.upload_folder_path) + '/upload ' +
                                                   str(upload_object.number) + ' picklist_values_to_map.csv')
        print("\nPicklist values to map saved here: " + str(upload_object.upload_folder_path) + '/upload ' +
              str(upload_object.number) + ' picklist_values_to_map.csv')
        quit()
    else:
        print("Picklist mapping completed successfully")

        proceed = input("Are you happy with the resulting picklist values? (y/n)  ")

        if proceed == 'y':
            print("")
        else:
            print("Please change the field mappings in the field mapping doc.")
            quit()


def collate_cleaned_data(upload_object: Upload, list_of_field_objects: list):
    # Create empty dataframe
    df = pd.DataFrame()
    for field_object in list_of_field_objects:
        df[field_object.name] = field_object.field_values

    # Write the cleaned data back onto the upload object
    upload_object.cleaned_data = df


def validate_permission_values(upload_object: Upload):
    df = upload_object.cleaned_data
    print("")
    invalid_rows = pd.DataFrame()

    if upload_object.region == 'EMEA':
        opt_in_field = 'Email Opt In'
        opt_in_source_field = 'Email Opt In Source'
        opt_in_date_field = 'Email Opt In Date'
        double_opt_in_field = 'Email Double Opt In'
        double_opt_in_source_field = 'Email Double Opt In Date'
        double_opt_in_date_field = 'Email Double Opt In Source'
    else:
        opt_in_field = 'Marketing Opt In'
        opt_in_source_field = 'Marketing Opt In Date'
        opt_in_date_field = 'Marketing Opt In Source'

    # Select records with aligned permissions fields
    if opt_in_field in df.columns:
        if opt_in_source_field in df.columns and opt_in_date_field in df.columns:
            invalid_rows = df[
                (df[opt_in_field] == '1') & ((df[opt_in_date_field].isnull()) | (df[opt_in_source_field].isnull()))]
            invalid_rows = invalid_rows[['Email', opt_in_field, opt_in_date_field, opt_in_source_field]]
        else:
            print("Opt In field found, but a Source or Date field is missing.")
            print(invalid_rows.to_markdown())
            quit()
    else:
        print("No Opt In field found.")

    # TODO: Add checks for double opt ins

    if len(invalid_rows) > 0:
        print(str(len(invalid_rows)) + " Opted In Records found missing source or date:")
        print(invalid_rows.to_markdown())
        quit()
    else:
        print(str(len(df[df[opt_in_field] == '1'])) + " opted in rows with valid source and date values")


def select_valid_records(upload_object: Upload):
    df = upload_object.cleaned_data
    records_at_start = len(df)

    # Select records with required fields populated
    df = df[df['Country'].notnull() & df['Email'].notnull() & df['Company'].notnull()]
    upload_object.cleaned_data = df

    if records_at_start > len(df):
        dropped_records = records_at_start - len(df)
        print('\n' + str(dropped_records) + ' records were dropped. These records were missing required values.')
    else:
        print('\nAll records had required fields populated\n')


def write_data_to_csv(upload_object: Upload):
    ready_to_upload_filepath = upload_object.upload_folder_path / 'ready_for_upload.csv'
    upload_object.cleaned_data.to_csv(ready_to_upload_filepath, index=False, encoding='utf-8', date_format='%Y-%m-%d')
    print("\nFile is ready for upload!\nFile saved here: " + str(ready_to_upload_filepath))


def get_list_of_fields_in_data(field_list):
    fields_in_data = []
    for field in field_list:
        if field.field_values is not None:
            fields_in_data.append(field)

    return fields_in_data

