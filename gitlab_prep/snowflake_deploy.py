"""Deploy SQL scripts to Prod in Snowflake."""

from typing import List, Dict, Tuple
from pathlib import Path

from snowflake.snowpark import Session
from snowflake_check_deploy import create_deploy_order, read_setup, create_snowflake_connection


def clear_old_views(
    session: Session, dev_views: List[str], database: str, mapping: Dict[str, str]
) -> None:
    """Remove any views which no longer exist in DEV but previous existed in PROD."""
    # get all prod views in the database where the schema is in the dev-prod mapping
    prod_views = [
        f"{row.database_name}.{row.schema_name}.{row.name}"
        for row in session.sql(f"SHOW VIEWS IN DATABASE {database}").collect()
        if row.schema_name in mapping.values()
    ]

    dev_views_mapped = [
        dev_view.replace(dev_schema, prod_schema)  # replace _DEV with _PROD
        for (dev_schema, prod_schema) in mapping.items()  # try all mappings
        for dev_view in dev_views  # for all dev views
        if dev_schema
        in dev_view  # if the dev schema is present in the view - ensures no duplicates
    ]

    prod_views_to_remove = [
        prod_view for prod_view in prod_views if prod_view not in dev_views_mapped
    ]

    for prod_view in prod_views_to_remove:
        print(f"Dropping view {prod_view}")
        session.sql(f"DROP VIEW {prod_view}").collect()


def push_to_snowflake(
    ordered_paths: List[Tuple[str, Path]],
    keeper_id: str,
    mapping: Dict[str, str],
    snowflake_config: Dict[str, str],
) -> None:
    """Push the views to the Snowflake Prod Schemas."""
    creds = create_snowflake_connection(keeper_id)

    if isinstance(mapping, dict):
        dev_prod_mapping: Dict[str, str] = mapping
    else:
        raise ValueError("Expected 'mapping' to be a dictionary.")

    session = creds.connect()
    session.use_role(snowflake_config["role"])

    print(f"Ordered Paths: {ordered_paths}")

    dev_views = [ordered_path[0] for ordered_path in ordered_paths]
    clear_old_views(session, dev_views, snowflake_config["database"], mapping)

    for view_name, file_path in ordered_paths:
        with file_path.open("r", encoding="utf-8") as f:
            dev_sql = f.read()

        prod_sql = dev_sql
        for dev, prod in dev_prod_mapping.items():
            prod_sql = prod_sql.replace(dev, prod)

        with session.connection.cursor() as cur:
            print(f"Pushing SQL File: {file_path} into Dev.")
            cur.execute(dev_sql)  # update DEV to match Prod

        with session.connection.cursor() as cur:
            print(f"Pushing SQL File: {file_path} into Prod.")
            cur.execute(prod_sql)  # update PROD

    session.close()


if __name__ == "__main__":
    keeper_id, mapping, snowflake_config = read_setup()
    ordered_paths = create_deploy_order()
    push_to_snowflake(ordered_paths, keeper_id, mapping, snowflake_config)
