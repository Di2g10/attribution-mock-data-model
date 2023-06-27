# Fujitsu Pardot Upload Tool
This tool currently handles the folder organisation, data preparation, and checks required by the Fujitsu upload process.

This tool does not upload the data to Pardot. This step is currently still a manual step.

## This tool will:
- Read the Fujitsu upload tracker (https://clevertouch.sharepoint.com/:x:/s/Fujitsu/EXtoYvpDa3ZOq6dooBzYzq0BqP0u91p9jdBT3Ld7vrVtwg?e=CzU79U).
- Validate whether the upload tracker has been filled in correctly.
- Create a folder for the upload. This folder will store the raw data, any mid-steps and the prepared data that is ready for upload.
- Map fields from the raw data to those in the relevant Fujitsu Pardot instance.
- Map any values in picklist fields to the accepted values.
- Check the formatting of date and number values.
- Check that records have the required fields populated.
- Check whether opted in records have an opt-in date and an opt-in source.

## How to run the process:
The aim of this tool is to provide enough prompts and error messaging that it can be run without detailed context of the process.
If any part of the process is unclear, please reach out to Jake Campling.

1. Click "Run"
2. You will be shown the details of all uploads in the upload tracker that have a status of "Requested". Type the number of the upload you want to run.
3. If prompted to do so; map any unmapped fields in this spreadsheet: https://clevertouch.sharepoint.com/:x:/s/Fujitsu/EUrrWT8bPX5CloNezPxJdyIBecFWZzbO0iB4YEPud86Xow?e=yYZ2pW
   1. If you want a fields in the data to be ignored, just map it to "IGNORE".
4. Once all fields in the data have a mapping, you will be prompted to "Please review the mappings above."
5. Once you are happy with the field mappings show, type "y" and hit enter.
6. If prompted to do so; map any unmapped picklist values.
   1. The values you need to map will be found in the upload folder in a csv ending in "picklist_values_to_map"
   2. Add the values to the picklist mapping spreadsheet: https://clevertouch.sharepoint.com/:x:/s/Fujitsu/EdGNXy_vUf1Flvz1FHZAHUIBlHNDKIZeBuEpGEN2y6YspA?e=zXCSa2
   3. Values can be mapped to an empty string if there is no valid match.
7. Once all picklist values in the data have a mapping, you will be prompted check whether you are happy with the resulting values from the mapping.
8. Once you are happy with the resulting picklist values, type "y" and hit enter.
9. The tool will then print the details of any date or number formatting that has occurred. Check whether any data has been lost (same number of nulls before formatting as after formatting). 
   1. Example message here:
      ```
      Date formatting completed for: Email Opt In Date 
      Nulls before: 0-> Null count after: 0
      ```
10. The tool will print the number of opted in rows with valid source and date values
11. The tool will check whether the records have the required fields populated. It will either print "All records had required fields populated", or it will print the number of records that have been dropped due to insufficient data.
12. The tool will print "File is ready for upload!", followed by the file path of your cleaned and prepared data.
13. Upload your data to Pardot and marvel at the lack of upload or sync errors.


