"""Set the keyring from environment variables. For use on GitLab."""

import keyring
import os
import re


def set_keyring() -> None:
    """Set keyrings values from environment variables set in GitLab.

    The format of the GitLab variable is as follows: KEYRING_{PLATFORM}_{SECRET}
    """
    # get keyring groups - groups of credentials for the same keeper id
    pattern = re.compile("KEYRING_(.*)_KEEPER")
    keeper_groups = [pattern.search(value) for value in list(os.environ) if pattern.search(value)]
    keeper_groups_values = [value.group(1) for value in keeper_groups if value is not None]

    for platform in keeper_groups_values:
        # run through platforms (groups of creds)
        secret_id = os.environ[f"KEYRING_{platform}_KEEPER"]

        # get the different credentials
        secret_pattern = re.compile(f"KEYRING_{platform}_(.*)")
        keeper_secrets = [
            secret_pattern.search(value)
            for value in list(os.environ)
            if secret_pattern.search(value)
        ]
        keeper_secret_values = [value.group(1) for value in keeper_secrets if value is not None]

        # set the credentials
        for secret_value in keeper_secret_values:
            if secret_value != "KEEPER":
                keyring.set_password(
                    secret_id, f"{secret_value}", os.environ[f"KEYRING_{platform}_{secret_value}"]
                )


if __name__ == "__main__":
    set_keyring()
