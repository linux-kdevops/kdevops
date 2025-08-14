#!/usr/bin/env python3
# Extract API key from Lambda Labs credentials file
import configparser
import json
import sys
from pathlib import Path


def extract_api_key(creds_file="~/.lambdalabs/credentials"):
    """Extract just the API key value from credentials file."""
    try:
        path = Path(creds_file).expanduser()
        if not path.exists():
            sys.stderr.write(f"Credentials file not found: {path}\n")
            sys.exit(1)

        config = configparser.ConfigParser()
        config.read(path)

        # Try default section first
        if "default" in config and "lambdalabs_api_key" in config["default"]:
            return config["default"]["lambdalabs_api_key"].strip()

        # Try DEFAULT section
        if "DEFAULT" in config and "lambdalabs_api_key" in config["DEFAULT"]:
            return config["DEFAULT"]["lambdalabs_api_key"].strip()

        sys.stderr.write("API key not found in credentials file\n")
        sys.exit(1)

    except Exception as e:
        sys.stderr.write(f"Error reading credentials: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    creds_file = sys.argv[1] if len(sys.argv) > 1 else "~/.lambdalabs/credentials"
    api_key = extract_api_key(creds_file)
    # Output JSON format required by terraform external data source
    print(json.dumps({"api_key": api_key}))
