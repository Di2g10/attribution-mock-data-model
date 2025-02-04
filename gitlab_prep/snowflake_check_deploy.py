"""Move scripts from dev->main when a merge request is completed.

Run when merging from dev into main.
"""

import json
import re

from pathlib import Path
from collections import defaultdict, deque
from typing import List, Dict, Tuple, Union, Any
from clevertouch_internal_tools.utils.credentials_manager import SnowflakeCredentials

from set_keyring_from_env import set_keyring


def read_setup() -> Tuple[str, Dict[str, str], Dict[str, str]]:
    """Read Snowflake Schema Setup file."""
    with Path("./gitlab_prep/snowflake_schema_setup.json").open("r") as raw_json:
        raw_config = json.load(raw_json)

    keeper_id: str = raw_config["keeper_id"]

    mapping = {
        stage["dev_schema"]: stage["prod_schema"] for _, stage in raw_config["stages"].items()
    }

    snowflake_config = {
        "role": raw_config["snowflake_role"],
        "database": raw_config["snowflake_database"],
    }

    return keeper_id, mapping, snowflake_config


def topological_sort(views_dir: Path) -> List[Union[Any, Path]]:
    """Topological sort of views in directory graph."""
    # Pattern to match references like EXAMPLE_DB.EXAMPLE_DEV.EXAMPLE_VIEW in the view query
    # excludes when it is preceded by 'view' - so we don't include the view reference
    fully_qualified_pattern = re.compile(
        r"(?<!VIEW\s)\b([A-Z_]+\.[A-Z_]+_DEV\.[A-Za-z0-9_]+)\b", re.IGNORECASE
    )

    # Pattern to get view names from files
    view_names_pattern = re.compile(
        r"VIEW\s\b([A-Z_]+\.[A-Z_]+_DEV\.[A-Za-z0-9_]+)\b", re.IGNORECASE
    )

    # Collect all view SQL files
    view_files = [f for f in views_dir.rglob("*.sql")]

    # Map of VIEW_NAME (uppercased) to file Path
    view_names_mapping = {}

    for file in view_files:
        with file.open("r") as f:
            sql_content = f.read()

        # Find references
        refs = view_names_pattern.findall(sql_content)

        if len(refs) > 1:
            raise ValueError(
                "Multiple views found in the same file. Please put views in separate files."
            )
        view_names_mapping[refs[0]] = file

    # Dependency graph: For each view, which views does it depend on?
    dependency_graph = defaultdict(set)
    reverse_dependency_graph = defaultdict(set)

    for view_name, file_path in view_names_mapping.items():
        with file_path.open("r") as f:
            sql_content = f.read()

        # Find references
        refs = fully_qualified_pattern.findall(sql_content)

        # Add edges to the graph
        for ref in refs:
            # take first match as this is fully qualified name
            ref_upper = ref.upper()
            if ref_upper in view_names_mapping and ref_upper != view_name:
                # view_name depends on ref_upper
                dependency_graph[view_name].add(ref_upper)
                reverse_dependency_graph[ref_upper].add(view_name)

    in_degree = {v: 0 for v in view_names_mapping}
    for v, deps in dependency_graph.items():
        for _ in deps:
            in_degree[v] += 1

    queue = deque([v for v in in_degree if in_degree[v] == 0])
    ordered_views = []

    while queue:
        current = queue.popleft()
        ordered_views.append(current)
        for dependent in reverse_dependency_graph[current]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    # Check if topological sort includes all views (no cycles)
    if len(ordered_views) != len(view_names_mapping):
        raise Exception("Cycle detected in view dependencies!")

    return [(view, view_names_mapping[view]) for view in ordered_views]


def determine_deploy_order() -> List[Union[Any, Path]]:
    """Deploy the views from dev -> prod on Snowflake."""
    stage_path = Path("./snowflake_views")
    return topological_sort(stage_path)


def create_snowflake_connection(keeper_id: str) -> SnowflakeCredentials:
    """Test the CI variables are set up correctly to allow a connection to Snowflake."""
    # set variables in keyring based off CI variables
    set_keyring()

    # create a SnowflakeCreds class which tests the credentials authenticate
    return SnowflakeCredentials(keeper_id, keyring_preset=True)


if __name__ == "__main__":
    # check that there are no loops and the deployment can happen successfully
    keeper_id, mapping, snowflake_config = read_setup()
    print(f"Push Order: {determine_deploy_order()}")

    create_snowflake_connection(keeper_id)
    print("Connection Successful")
