#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1
# Extract API key from DataCrunch credentials file
import configparser
import json
import sys
from pathlib import Path


def extract_credentials(creds_file="~/.datacrunch/credentials"):
    """Extract client credentials from credentials file."""
    try:
        path = Path(creds_file).expanduser()
        if not path.exists():
            sys.stderr.write(f"Credentials file not found: {path}\n")
            sys.exit(1)

        config = configparser.ConfigParser()
        config.read(path)

        result = {}

        # Try default section first
        section = (
            "default"
            if "default" in config
            else "DEFAULT" if "DEFAULT" in config else None
        )

        if section is None:
            sys.stderr.write("No default section found in credentials file\n")
            sys.exit(1)

        # Extract client_id
        for key_name in ["client_id"]:
            if key_name in config[section]:
                result["client_id"] = config[section][key_name].strip()
                break

        # Extract client_secret (also try legacy api_key names)
        for key_name in ["client_secret", "datacrunch_api_key", "api_key"]:
            if key_name in config[section]:
                result["client_secret"] = config[section][key_name].strip()
                break

        if "client_id" not in result or "client_secret" not in result:
            sys.stderr.write(
                "client_id and client_secret not found in credentials file\n"
            )
            sys.exit(1)

        return result

    except Exception as e:
        sys.stderr.write(f"Error reading credentials: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    creds_file = sys.argv[1] if len(sys.argv) > 1 else "~/.datacrunch/credentials"
    credentials = extract_credentials(creds_file)
    # Output JSON format required by terraform external data source
    print(json.dumps(credentials))
