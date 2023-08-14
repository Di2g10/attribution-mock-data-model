import pandas as pd
import filepaths as fpath

# Get all Country values
all_people_country = pd.read_csv(fpath.workspace_directory_general/'All_people.csv', usecols=['Country'])
grouped_country = all_people_country.groupby('Country')
grouped_country.size().to_frame('Count').reset_index().to_csv(fpath.workspace_directory_mapping/'marketo_country_values.csv', index=False)

# Get all State values
all_people_state = pd.read_csv(fpath.workspace_directory_general/'All_people.csv', usecols=['State'])
grouped_state = all_people_state.groupby('State')
grouped_state.size().to_frame('Count').reset_index().to_csv(fpath.workspace_directory_mapping/'marketo_state_values.csv', index=False)
