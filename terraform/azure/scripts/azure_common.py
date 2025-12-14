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


class AzureNotConfiguredError(Exception):
    """Raised when Azure credentials are not available."""

    pass


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


def get_compute_client():
    """
    Get an authenticated Azure Compute Management client.

    Returns:
            tuple: (ComputeManagementClient, subscription_id)

    Raises:
            Exception: If authentication fails or SDK is not available
    """
    from azure.common.credentials import get_cli_profile
    from azure.mgmt.compute import ComputeManagementClient

    # Get credentials from Azure CLI profile (reuses 'az login' session)
    profile = get_cli_profile()
    credentials, subscription_id, _ = profile.get_login_credentials(
        resource="https://management.azure.com"
    )

    client = ComputeManagementClient(credentials, subscription_id)
    return client, subscription_id


def get_vm_sizes_and_skus(region, quiet=False):
    """
    Get all VM sizes and capabilities for a region using a single Azure SDK call.

    This function uses the resource SKUs API which provides all the information
    from both VM sizes and SKU capabilities in a single efficient API call.

    Args:
            region (str): Azure region name
            quiet (bool): Suppress debug messages

    Returns:
            tuple: (sizes_list, capabilities_dict) where:
                - sizes_list: List of VM size dictionaries in CLI-compatible format
                - capabilities_dict: Dict mapping VM size names to their capabilities
    """
    if not quiet:
        print(f"Fetching VM sizes and capabilities from {region}...", file=sys.stderr)

    try:
        client, _ = get_compute_client()

        # Query resource SKUs using SDK with location filter
        # This single API call provides all information we need
        skus = list(client.resource_skus.list(filter=f"location eq '{region}'"))

        # Filter to VM SKUs only
        vm_skus = [s for s in skus if s.resource_type == "virtualMachines"]

        # Build both data structures
        size_list = []
        sku_capabilities = {}

        for sku in vm_skus:
            if not sku.capabilities:
                continue

            # Convert capabilities list to dictionary for easy lookup
            caps = {cap.name: cap.value for cap in sku.capabilities}

            # Extract size information from capabilities
            # The resource SKUs API provides the same data as the VM sizes API
            try:
                cores = int(caps.get("vCPUs", 0))
                memory_mb = int(float(caps.get("MemoryGB", 0)) * 1024)
                max_disks = int(caps.get("MaxDataDiskCount", 0))
                resource_disk_mb = int(caps.get("MaxResourceVolumeMB", 0))
                os_disk_mb = int(caps.get("OSVhdSizeMB", 0))

                # Build VM size dict in CLI-compatible format
                size_list.append(
                    {
                        "name": sku.name,
                        "numberOfCores": cores,
                        "memoryInMB": memory_mb,
                        "maxDataDiskCount": max_disks,
                        "resourceDiskSizeInMB": resource_disk_mb,
                        "osDiskSizeInMB": os_disk_mb,
                    }
                )

                # Store capabilities for this size
                sku_capabilities[sku.name] = caps

            except (ValueError, TypeError) as e:
                if not quiet:
                    print(
                        f"Warning: Could not parse capabilities for {sku.name}: {e}",
                        file=sys.stderr,
                    )
                continue

        if not quiet:
            print(f"  Found {len(size_list)} VM sizes in {region}", file=sys.stderr)

        return size_list, sku_capabilities

    except Exception as e:
        if not quiet:
            print(f"Error: Failed to query VM sizes and SKUs: {e}", file=sys.stderr)
            print("Ensure you are logged in with 'az login'", file=sys.stderr)
        return [], {}


def get_all_offers_and_skus(publisher_id, region, quiet=False, max_workers=10):
    """
    Get all offers and SKUs for a publisher using Azure SDK with parallel execution.

    This function uses parallel SKU fetching for optimal performance with
    publishers that have many offers. The parallelization is safe because
    each SKU query is independent and the Azure API supports concurrent requests.

    Args:
            publisher_id (str): Azure publisher identifier (e.g., "Debian", "RedHat")
            region (str): Azure region name
            quiet (bool): Suppress debug messages
            max_workers (int): Maximum concurrent workers for parallel SKU fetching

    Returns:
            dict: Dictionary mapping offer names to lists of SKU names
                  Example: {"debian-12": ["12", "12-arm64"], ...}
    """
    from concurrent.futures import ThreadPoolExecutor

    if not quiet:
        print(f"Querying offers for {publisher_id} in {region}...", file=sys.stderr)

    try:
        client, _ = get_compute_client()

        # Get all offers (single fast API call)
        offers = list(client.virtual_machine_images.list_offers(region, publisher_id))

        if not offers:
            return {}

        if not quiet:
            print(
                f"  Found {len(offers)} offers, fetching SKUs in parallel...",
                file=sys.stderr,
            )

        def fetch_skus_for_offer(offer):
            """Helper function to fetch SKUs for a single offer."""
            offer_name = offer.name

            # Skip test offers and other non-production offers
            offer_lower = offer_name.lower()
            if any(
                skip in offer_lower
                for skip in ["test", "preview", "experimental", "-dev", "staging"]
            ):
                return (offer_name, [])

            try:
                skus = list(
                    client.virtual_machine_images.list_skus(
                        region, publisher_id, offer_name
                    )
                )
                sku_names = [sku.name for sku in skus if sku.name]
                return (offer_name, sku_names)
            except Exception as e:
                if not quiet:
                    print(
                        f"    Warning: Failed to get SKUs for {offer_name}: {e}",
                        file=sys.stderr,
                    )
                return (offer_name, [])

        # Fetch SKUs for all offers in parallel
        offers_dict = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = executor.map(fetch_skus_for_offer, offers)

            for offer_name, sku_names in results:
                if sku_names:
                    offers_dict[offer_name] = sku_names

        if not quiet:
            print(
                f"  Found {len(offers_dict)} offers with available SKUs",
                file=sys.stderr,
            )

        return offers_dict

    except Exception as e:
        if not quiet:
            print(
                f"Error: Failed to query offers and SKUs for {publisher_id}: {e}",
                file=sys.stderr,
            )
            print("Ensure you are logged in with 'az login'", file=sys.stderr)
        return {}


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


def require_azure_credentials():
    """
    Require Azure credentials, raising an exception if not configured.

    This function should be called early in main() to validate Azure
    credentials. If Azure is not configured, it raises AzureNotConfiguredError
    to let the caller decide how to handle it.

    This centralizes the handling of missing Azure credentials and avoids
    TOCTOU race conditions from manual file existence checks.

    Returns:
        str: Subscription ID if credentials are valid

    Raises:
        AzureNotConfiguredError: If Azure credentials are not found
    """
    try:
        from azure.common.credentials import get_cli_profile

        profile = get_cli_profile()
        credentials, subscription_id, _ = profile.get_login_credentials(
            resource="https://management.azure.com"
        )
        return subscription_id
    except ImportError as e:
        raise AzureNotConfiguredError("Azure SDK not installed") from e
    except Exception as e:
        # Only treat as "not configured" if it looks like an auth/login issue
        error_msg = str(e).lower()
        auth_indicators = [
            "login",
            "logged in",
            "authenticate",
            "credential",
            "az login",
        ]
        if any(phrase in error_msg for phrase in auth_indicators):
            raise AzureNotConfiguredError("Azure credentials not found") from e
        raise
