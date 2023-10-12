"""Arya's script from Beamery: https://git.clever-touch.com/data-and-insights/client/beamery/beamery-data-remediation/-/blob/dev_shared_marketo_api_tool/src/shared_functions/marketo_lead_update.py."""


#Arya's script below

### get access token
class AccessToken:
    access_token: str = ""
    expires_in: int = 0
    expires_datetime: datetime
    scope: str = ""
    token_type: str = ""

    def get_marketo_access_token(self):
        endpoint = config.identity_url + "/oauth/token"
        data = {
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "grant_type": "client_credentials",
        }
        response = re.get(endpoint, data)
        print(response.text)
        self.access_token = response.json()["access_token"]
        self.token_type = response.json()["token_type"]
        self.scope = response.json()["scope"]
        self.expires_in = response.json()["expires_in"]
        self.expires_datetime = datetime.now() + timedelta(0, self.expires_in)
        print(
            f"Access Token: {self.access_token}"
            f"Token Type: {self.token_type}"
            f"Scope: {self.scope}"
            f"Expires In: {self.expires_in}"
            f"Expires Datetime: {self.expires_datetime}"
        )

    def check_expiry(self):
        if self.expires_datetime < datetime.now():
            print("Token expired. Requesting new access token.")
            self.get_marketo_access_token()
        else:
            print("Token remains valid. Continuing request.")


def upload_leads_batch(data_to_upload, request_token: AccessToken):
    headers = {
        "Authorization": "Bearer {}".format(request_token.access_token),
        "Content-Type": "application/json",
    }
    payload = {"input": data_to_upload, "action": "createOrUpdate", "lookupField": "id"}
    response = re.post(config.rest_url + "/v1/leads.json", json=payload, headers=headers)

    return response


def upload_value_changes(upload_file_path, batch_size: int):
    # Convert dataframe to a list of dictionaries
    data_change_df = pd.read_csv(upload_file_path, low_memory=False)

    # Convert into list of dictionaries
    data_change_dicts = data_change_df.to_dict(orient="records")
    filtered_data_change_dicts = []
    for d in data_change_dicts:
        filtered_dict = {
            key: value
            for key, value in d.items()
            if (isinstance(value, str) or not math.isnan(value))
        }
        filtered_data_change_dicts.append(filtered_dict)

    # Remove dictionaries that only have an id key and no data changes
    # Remove dictionaries with only one key
    data_to_upload = [d for d in filtered_data_change_dicts if len(d) > 1]

    # Printing list of dicts to aid dev
    print(len(data_to_upload))
    print(data_to_upload[0])
    print(data_to_upload[1])
    print(data_to_upload[2])

    # Apply upload_leads_batch function using batches
    num_value_changes = len(data_to_upload)
    num_batches = (num_value_changes // batch_size) + 1

    print(
        "Function will execute "
        + str(num_value_changes)
        + " value changes, across "
        + str(num_batches)
        + " batches"
    )

    for batch in range(num_batches):
        # Get a new token for each batch
        token = AccessToken()
        token.get_marketo_access_token()

        # Run upload for each batch
        start_index = batch * batch_size
        end_index = min(start_index + batch_size, num_value_changes)
        batch_data = data_to_upload[start_index:end_index]
        print("Import data from index " + str(start_index) + " to index " + str(end_index))
        print(batch_data[0])
        batch_response = upload_leads_batch(batch_data, token)
        batch_response = batch_response.json()
        print(batch_response)

        # Log the batch
        log_row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Upload Value" "Index " + str(start_index) + " to index " + str(end_index),
            batch_response["success"],
            batch_response,
        ]

        with Path.open(
            r"C:\Users\AryaZhao\CleverTouch\Beamery - Documents"
            r"\74615_Beamery_Data Audit\Data Remediations\Outputs\Value Upload Log v2.csv",
            mode="a",
            newline="",
        ) as file:
            writer = csv.writer(file)
            writer.writerow(log_row)


def upload_blank_values(upload_file_path, batch_size: int):
    # Convert dataframe to a list of dictionaries
    data_change_df = pd.read_csv(upload_file_path, low_memory=False)

    # Drop unnamed column
    data_change_df = data_change_df.dropna(axis=1, how="all")

    print(data_change_df.head(10).to_markdown())

    # Convert into list of dictionaries
    data_change_dicts = data_change_df.to_dict(orient="records")
    filtered_data_change_dicts = []
    for d in data_change_dicts:
        filtered_dict = {
            key: value
            for key, value in d.items()
            if (isinstance(value, str) or not math.isnan(value))
        }
        filtered_data_change_dicts.append(filtered_dict)

    # Remove dictionaries that only have an id key and no data changes
    # Remove dictionaries with only one key
    data_to_upload = [d for d in filtered_data_change_dicts if len(d) > 1]

    for d in data_to_upload:
        for key, value in d.items():
            if key != "Id":
                d[key] = ""

    print(len(data_to_upload))
    print(data_to_upload[0])
    print(data_to_upload[1])
    print(data_to_upload[2])

    # Apply upload_leads_batch function using batches
    num_value_changes = len(data_to_upload)
    num_batches = (num_value_changes // batch_size) + 1

    print(
        "Function will execute "
        + str(num_value_changes)
        + " value changes, across "
        + str(num_batches)
        + " batches"
    )

    for batch in range(num_batches):
        # Get a new token for each batch
        token = AccessToken()
        token.get_marketo_access_token()

        # Run upload for each batch
        start_index = batch * batch_size
        end_index = min(start_index + batch_size, num_value_changes)
        batch_data = data_to_upload[start_index:end_index]
        print("Import data from index " + str(start_index) + " to index " + str(end_index))
        print(batch_data[0])
        batch_response = upload_leads_batch(batch_data, token)
        batch_response = batch_response.json()
        print(batch_response)

        # Log the batch
        log_row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Upload Blank",
            "Index " + str(start_index) + " to index " + str(end_index),
            batch_response["success"],
            batch_response,
        ]

        with Path.open(
            r"C:\Users\JakeCampling\CleverTouch\
            Education Software Solutions (ESS) - Documents\63001_ESS_Data "
            r"Remediation 2022\Upload Logging\Value Upload Log.csv",
            mode="a",
            newline="",
        ) as file:
            writer = csv.writer(file)
            writer.writerow(log_row)


def run_data_changes():
    # get the access tokens
    token = AccessToken()
    token.get_marketo_access_token()

    run_value_upload = input("Do you want to run the value upload? (y/n) ")
    if run_value_upload.lower() == "y":
        upload_value_changes(
            filepath.output_directory / "marketo_mapping_api_postupload_130723.csv", 100
        )


run_data_changes()
