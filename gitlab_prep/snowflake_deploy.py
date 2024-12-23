"""Deploy SQL scripts to Prod in Snowflake."""

from typing import List, Dict, Tuple
from pathlib import Path
import json

import snowflake

from set_keyring_from_env import set_keyring
from snowflake_check_deploy import determine_deploy_order
from credentials_manager import SnowflakeCredentials


def read_setup() -> Tuple[str, Dict[str, str]]:
    """Read Snowflake Schema Setup file."""
    with Path("./gitlab_prep/snowflake_schema_setup.json").open("r") as raw_json:
        raw_config = json.load(raw_json)

    keeper_id: str = raw_config["keeper_id"]

    mapping = {
        stage["dev_schema"]: stage["prod_schema"] for _, stage in raw_config["stages"].items()
    }

    return keeper_id, mapping


def push_to_snowflake(ordered_paths: List[Path], keeper_id: str, mapping: Dict[str, str]) -> None:
    """Push the views to the Snowflake Prod Schemas."""
    set_keyring()
    creds = SnowflakeCredentials(keeper_id)

    if isinstance(mapping, dict):
        dev_prod_mapping: Dict[str, str] = mapping
    else:
        raise ValueError("Expected 'mapping' to be a dictionary.")

    ctx = snowflake.connector.connect(
        user=creds.username, password=creds.password, account=creds.account
    )

    print(f"Ordered Paths: {ordered_paths}")

    for file_path in ordered_paths:
        with file_path.open("r", encoding="utf-8") as f:
            prod_sql = f.read()
        print(f"Pushing SQL File: {file_path} into Prod.")
        for dev, prod in dev_prod_mapping.items():
            prod_sql = prod_sql.replace(dev, prod)
        with ctx.cursor() as cur:
            cur.execute(prod_sql)

    ctx.close()


if __name__ == "__main__":
    keeper_id, mapping = read_setup()
    ordered_paths = determine_deploy_order()
    push_to_snowflake(ordered_paths, keeper_id, mapping)
