# Import functions from function.py
from functions import *


def main():
    # Read the upload tracker and create instances of the Upload object.
    uploads_list = read_upload_tracker()

    # Select an upload to run
    upload_to_run = select_an_upload_to_run(uploads_list)

    # Validate that the upload has all the required in the upload tracker
    validate_selected_upload(upload_to_run)

    # Set up a folder for the upload
    set_up_upload_folder(upload_to_run)

    # Get the data for the upload and add it to the upload object
    get_source_data(upload_to_run)

    # Field mapping
    field_mapping_list = read_field_mapping_dictionary()
    apply_field_mapping_to_upload(upload_to_run, field_mapping_list)

    # Create list of field objects
    field_object_list = read_fields_dictionary()

    # Field data formatting
    get_field_values(field_object_list, upload_to_run)

    # Make a list of the fields in the data
    fields_in_data = get_list_of_fields_in_data(field_object_list)

    # fields_in_data = []
    # for field in field_list:
    #     if field.field_values is not None:
    #         fields_in_data.append(field)

    # Picklist mapping
    picklist_list = read_picklists()

    apply_picklist_mapping(upload_to_run, fields_in_data, picklist_list)

    # Clean and format values
    clean_field_values(fields_in_data, '%Y-%m-%d')

    # Bring cleaned data into a single dataframe
    collate_cleaned_data(upload_to_run, fields_in_data)

    # Validate permission field values
    validate_permission_values(upload_to_run)

    # Select valid records from the cleaned data
    select_valid_records(upload_to_run)

    # Write cleaned data to csv
    write_data_to_csv(upload_to_run)


# Run main
if __name__ == '__main__':
    main()


