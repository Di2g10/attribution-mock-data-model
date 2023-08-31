import pandas as pd
import filepaths as fpath
# Script to read api logs recorded during main run and produce summary of loaded data


# Read api logs (api_upload_log.csv)

log_file_name = 'api_upload_log.csv'
log_df = pd.read_csv(fpath.workspace_directory_output / log_file_name, encoding='utf-8')

# Select rows 113 onwards (rows that were part of the main run)
log_df = log_df.loc[113:]
print(log_df.head(10).to_markdown())

