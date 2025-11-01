#!/usr/bin/env python3
# ex: set filetype=python:

"""
Common utilities for Azure Kconfig generation scripts.

This module provides shared functionality for Azure-specific Kconfig
generation, including region discovery, default region detection, and
Jinja2 template management.
"""

import os
import sys
import json
from configparser import ConfigParser

from jinja2 import Environment, FileSystemLoader


def get_default_region():
    """
    Get the default Azure region from Azure configuration.

    Returns:
            str: Default region, or 'westus' if no default is found.
    """
    try:
        from azure.common.credentials import get_cli_profile

        # Check if user is authenticated by getting the CLI profile
        # This reuses the 'az login' session without subprocess calls
        profile = get_cli_profile()
        _, _, _ = profile.get_login_credentials(resource="https://management.azure.com")

        # Azure doesn't have a per-account default region like AWS
        # Check environment variable first
        if "AZURE_DEFAULTS_LOCATION" in os.environ:
            return os.environ["AZURE_DEFAULTS_LOCATION"]

        # Try to read from azure config
        config_path = os.path.expanduser("~/.azure/config")
        if os.path.exists(config_path):
            try:
                config = ConfigParser()
                config.read(config_path)
                if "defaults" in config and "location" in config["defaults"]:
                    return config["defaults"]["location"]
            except Exception:
                pass

        # Default fallback
        return "westus"
    except Exception as e:
        print(f"Warning: Error reading Azure config: {e}", file=sys.stderr)
        print("Ensure you are logged in with 'az login'", file=sys.stderr)
        return "westus"


def get_jinja2_environment(template_path=None):
    """
    Create a standardized Jinja2 environment for template rendering.

    Args:
            template_path (str): Path to template directory. If None, uses caller's directory.

    Returns:
            Environment: Configured Jinja2 Environment object
    """
    if template_path is None:
        template_path = sys.path[0]

    return Environment(
        loader=FileSystemLoader(template_path),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def get_all_regions(quiet=False):
    """
    Retrieve the list of all Azure regions using the Azure SDK.

    Returns:
            list: List of region dictionaries with name, displayName, and metadata
    """
    if not quiet:
        print("Querying Azure for available regions...", file=sys.stderr)

    try:
        from azure.common.credentials import get_cli_profile
        from azure.mgmt.resource import SubscriptionClient

        # Get credentials from Azure CLI profile (reuses 'az login' session)
        profile = get_cli_profile()
        credentials, subscription_id, _ = profile.get_login_credentials(
            resource="https://management.azure.com"
        )

        # Query regions using SDK
        subscription_client = SubscriptionClient(credentials)
        locations = subscription_client.subscriptions.list_locations(subscription_id)

        # Convert SDK objects to dict format
        region_list = []
        for location in locations:
            # Skip logical regions (not for general use)
            if location.metadata and location.metadata.region_type == "Logical":
                continue

            # Convert metadata to dict with camelCase keys
            # Only convert the fields we actually use to minimize overhead
            metadata = {}
            if location.metadata:
                meta = location.metadata
                metadata = {
                    "physicalLocation": meta.physical_location,
                    "pairedRegion": meta.paired_region,
                }

            region_list.append(
                {
                    "name": location.name or "",
                    "displayName": location.display_name or "",
                    "regionalDisplayName": location.regional_display_name or "",
                    "metadata": metadata,
                }
            )

        return sorted(region_list, key=lambda x: x["name"])

    except Exception as e:
        if not quiet:
            print(f"Error: Failed to query Azure regions: {e}", file=sys.stderr)
            print("Ensure you are logged in with 'az login'", file=sys.stderr)
        return []


def get_region_kconfig_name(region_name):
    """
    Convert an Azure region name to a Kconfig variable name.

    Args:
            region_name (str): Azure region name (e.g., 'westus', 'eastus2')

    Returns:
            str: Kconfig-safe name (e.g., 'WESTUS', 'EASTUS2')
    """
    return region_name.upper().replace("-", "_")


def exit_on_empty_result(result, context, quiet=False):
    """
    Exit with error if result is empty or None.

    This consolidates the common pattern of checking if an API query
    returned results and exiting with appropriate error messaging if not.

    Args:
            result: Result from API query (list, dict, or other iterable)
            context (str): Description of what operation failed
            quiet (bool): Suppress error messages

    Returns:
            Does not return; exits the process with status 1
    """
    if not result:
        if not quiet:
            print(
                f"Error: Cannot perform {context}. Check Azure authentication status.",
                file=sys.stderr,
            )
            print("Run 'az login' to authenticate with Azure.", file=sys.stderr)
        sys.exit(1)
