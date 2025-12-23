#!/usr/bin/env python3
# ex: set filetype=python:

"""
Common utilities for GCE Kconfig generation scripts.

This module provides shared functionality used by gen_kconfig_location
and other gen_kconfig_* scripts to avoid code duplication.

API Approach:
    Unlike the AWS, Azure, and OCI scripts which use their respective
    provider SDKs (boto3, azure-mgmt-*, oci), this module uses the GCE
    REST API directly with google-auth and requests.

    This design choice was made because the google-cloud-compute SDK
    is not widely packaged in Linux distributions:

      - Fedora: Not packaged
      - Debian/Ubuntu: Not packaged (python3-google-compute-engine is
        a different package for running inside GCE VMs)
      - openSUSE/SUSE: Available as python-google-cloud-compute

    In contrast, google-auth and requests are available as distribution
    packages across all major Linux distributions, making this approach
    work out-of-the-box without requiring pip.

    The REST API provides the same functionality and is well-documented:
    https://cloud.google.com/compute/docs/reference/rest/v1
"""

from __future__ import annotations

import os
import sys
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Optional

import yaml
from jinja2 import Environment, FileSystemLoader

import requests
import google.auth
import google.auth.exceptions
import google.auth.transport.requests


class GceNotConfiguredError(Exception):
    """Raised when GCE credentials are not available."""


# GCE Compute API base URL
GCE_COMPUTE_API = "https://compute.googleapis.com/compute/v1"

# Timeout in seconds for GCE API requests to prevent indefinite hangs
GCE_API_TIMEOUT = 30


def get_authenticated_session() -> (
    tuple[google.auth.transport.requests.AuthorizedSession, str]
):
    """
    Create an authenticated requests session for GCE API calls.

    Returns an AuthorizedSession that automatically handles OAuth2 token
    refresh. This allows long-running callers to make API requests without
    worrying about token expiration.

    Returns:
        tuple: (session, project_id) - AuthorizedSession and project ID

    Raises:
        ValueError: If project ID cannot be determined
        google.auth.exceptions.DefaultCredentialsError: If authentication fails
    """
    credentials, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/compute.readonly"]
    )

    if not project:
        # Try environment variables
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get(
            "GCLOUD_PROJECT"
        )

    if not project:
        raise ValueError(
            "Could not determine GCE project. Set GOOGLE_CLOUD_PROJECT "
            "environment variable or configure gcloud default project."
        )

    # Create authenticated session with automatic token refresh
    session = google.auth.transport.requests.AuthorizedSession(credentials)

    return session, project


def get_default_project() -> Optional[str]:
    """
    Get the default GCE project from gcloud configuration.

    Returns:
        str: Default project ID, or None if not found.
    """
    try:
        _, project = google.auth.default()
        if project:
            return project
    except google.auth.exceptions.DefaultCredentialsError:
        pass

    # Try environment variable
    if "GOOGLE_CLOUD_PROJECT" in os.environ:
        return os.environ["GOOGLE_CLOUD_PROJECT"]

    if "GCLOUD_PROJECT" in os.environ:
        return os.environ["GCLOUD_PROJECT"]

    return None


def _get_gcloud_config_value(section: str, key: str) -> Optional[str]:
    """
    Read a value from the gcloud properties file.

    Args:
        section: Config section name (e.g., 'compute')
        key: Config key name (e.g., 'region', 'zone')

    Returns:
        The config value if found, None otherwise.
    """
    config_path = os.path.expanduser("~/.config/gcloud/properties")
    if not os.path.exists(config_path):
        return None

    try:
        config = ConfigParser()
        config.read(config_path)
        if section in config and key in config[section]:
            return config[section][key]
    except Exception as e:
        print(f"Warning: Error reading gcloud config: {e}", file=sys.stderr)

    return None


def get_default_region() -> str:
    """
    Get the default GCE region from gcloud configuration.

    Returns:
        str: Default region, or 'us-west2' if no default is found.
    """
    if "CLOUDSDK_COMPUTE_REGION" in os.environ:
        return os.environ["CLOUDSDK_COMPUTE_REGION"]

    value = _get_gcloud_config_value("compute", "region")
    if value:
        return value

    return "us-west2"


def get_default_zone() -> str:
    """
    Get the default GCE zone from gcloud configuration.

    Returns:
        str: Default zone, or 'us-west2-a' if no default is found.
    """
    if "CLOUDSDK_COMPUTE_ZONE" in os.environ:
        return os.environ["CLOUDSDK_COMPUTE_ZONE"]

    value = _get_gcloud_config_value("compute", "zone")
    if value:
        return value

    return "us-west2-a"


def get_jinja2_environment(template_path: Optional[str] = None) -> Environment:
    """
    Create a standardized Jinja2 environment for template rendering.

    Args:
        template_path (str): Path to template directory. If None, uses caller's directory.

    Returns:
        Environment: Configured Jinja2 Environment object
    """
    if template_path is None:
        template_path = Path(__file__).parent

    return Environment(
        loader=FileSystemLoader(template_path),
        trim_blocks=True,
        lstrip_blocks=True,
        extensions=["jinja2.ext.loopcontrols"],
    )


def load_yaml_config(
    filename: str, quiet: bool = False, default: Optional[Any] = None
) -> Any:
    """
    Load a YAML configuration file with consistent error handling.

    This function provides standardized YAML loading used across all
    gen_kconfig_* scripts for loading configuration files like
    region_friendly_names.yml.

    Args:
        filename (str): Name of YAML file (not full path - will be looked up
                       in script directory)
        quiet (bool): Suppress warning messages to stderr
        default: Default value to return on error (default: empty dict)

    Returns:
        Data loaded from YAML file, or default value on error
    """
    if default is None:
        default = {}

    yaml_path = Path(__file__).parent / filename

    try:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
            return data if data else default
    except FileNotFoundError:
        if not quiet:
            print(f"Warning: {yaml_path} not found. Using defaults.", file=sys.stderr)
        return default
    except yaml.YAMLError as e:
        if not quiet:
            print(
                f"Warning: Error parsing {yaml_path}: {e}. Using defaults.",
                file=sys.stderr,
            )
        return default


def get_region_kconfig_name(region_name: str) -> str:
    """
    Convert GCE region name to Kconfig region constant name.

    Args:
        region_name (str): GCE region name (e.g., 'us-west2', 'asia-south1')

    Returns:
        str: Kconfig constant name (e.g., 'US_WEST2', 'ASIA_SOUTH1')
    """
    return region_name.upper().replace("-", "_")


def get_zone_kconfig_name(zone_name: str) -> str:
    """
    Convert GCE zone name to Kconfig zone constant name.

    Args:
        zone_name (str): GCE zone name (e.g., 'us-west2-a', 'asia-south1-b')

    Returns:
        str: Kconfig constant name (e.g., 'US_WEST2_A', 'ASIA_SOUTH1_B')
    """
    return zone_name.upper().replace("-", "_")


def list_regions(session: requests.Session, project: str) -> list[dict]:
    """
    List all GCE regions using the REST API.

    Args:
        session: Authenticated requests session
        project: GCE project ID

    Returns:
        list: List of region dictionaries from the API
    """
    url = f"{GCE_COMPUTE_API}/projects/{project}/regions"
    # Request only needed fields to reduce response size and latency
    params = {"fields": "items(name,status,zones)"}
    response = session.get(url, params=params, timeout=GCE_API_TIMEOUT)
    response.raise_for_status()

    data = response.json()
    return data.get("items", [])


def list_zones(session: requests.Session, project: str) -> list[dict]:
    """
    List all GCE zones using the REST API.

    Args:
        session: Authenticated requests session
        project: GCE project ID

    Returns:
        list: List of zone dictionaries from the API
    """
    url = f"{GCE_COMPUTE_API}/projects/{project}/zones"
    # Request only needed fields to reduce response size and latency
    params = {"fields": "items(name,status)"}
    response = session.get(url, params=params, timeout=GCE_API_TIMEOUT)
    response.raise_for_status()

    data = response.json()
    return data.get("items", [])


def exit_on_empty_result(result, context: str, quiet: bool = False) -> None:
    """
    Exit with error if result is empty or None.

    This consolidates the common pattern of checking if an API query
    returned results and exiting with appropriate error messaging if not.

    Args:
        result: Result from API query (list, dict, or other iterable)
        context (str): Description of what operation failed
        quiet (bool): Suppress error messages
    """
    if not result:
        if not quiet:
            print(
                f"Error: Cannot perform {context}. Check GCE authentication status.",
                file=sys.stderr,
            )
            print(
                "Run 'gcloud auth application-default login' to authenticate.",
                file=sys.stderr,
            )
        sys.exit(1)


def require_gce_credentials():
    """
    Require GCE credentials, raising an exception if not configured.

    This function should be called early in main() to validate GCE
    credentials. If GCE is not configured, it raises GceNotConfiguredError
    to let the caller decide how to handle it.

    This centralizes the handling of missing GCE credentials and avoids
    TOCTOU race conditions from manual file existence checks.

    Returns:
        tuple: (session, project_id) if credentials are valid

    Raises:
        GceNotConfiguredError: If GCE credentials are not found
    """
    try:
        return get_authenticated_session()
    except ValueError as e:
        raise GceNotConfiguredError(str(e)) from e
    except google.auth.exceptions.DefaultCredentialsError as e:
        raise GceNotConfiguredError("GCE credentials not found") from e


# Fields needed for machine type Kconfig generation
MACHINE_TYPE_FIELDS = (
    "name,guestCpus,memoryMb,isSharedCpu,description,"
    "maximumPersistentDisks,maximumPersistentDisksSizeGb"
)


def list_machine_types(
    session: requests.Session, project: str, zone: str
) -> list[dict]:
    """
    List all GCE machine types for a specific zone using the REST API.

    Args:
        session: Authenticated requests session
        project: GCE project ID
        zone: GCE zone name (e.g., 'us-west2-a')

    Returns:
        list: List of machine type dictionaries from the API
    """
    url = f"{GCE_COMPUTE_API}/projects/{project}/zones/{zone}/machineTypes"
    # Request only needed fields to reduce response size and latency
    params = {"fields": f"items({MACHINE_TYPE_FIELDS})"}
    response = session.get(url, params=params, timeout=GCE_API_TIMEOUT)
    response.raise_for_status()

    data = response.json()
    return data.get("items", [])


def list_machine_types_aggregated(
    session: requests.Session, project: str
) -> dict[str, list[dict]]:
    """
    List all GCE machine types across all zones using the aggregated API.

    This is more efficient than querying each zone separately when we need
    machine type information across multiple zones.

    Args:
        session: Authenticated requests session
        project: GCE project ID

    Returns:
        dict: Dictionary mapping zone names to lists of machine type dicts
    """
    url = f"{GCE_COMPUTE_API}/projects/{project}/aggregated/machineTypes"
    # Request only needed fields to reduce response size and latency
    params = {"fields": f"items/*/machineTypes({MACHINE_TYPE_FIELDS}),nextPageToken"}
    all_machine_types = {}

    while True:
        response = session.get(url, params=params, timeout=GCE_API_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        for zone_key, zone_data in data.get("items", {}).items():
            # zone_key is like "zones/us-west2-a"
            if zone_key.startswith("zones/"):
                zone_name = zone_key.split("/")[1]
                machine_types = zone_data.get("machineTypes", [])
                if machine_types:
                    all_machine_types[zone_name] = machine_types

        # Handle pagination
        next_page = data.get("nextPageToken")
        if not next_page:
            break
        params["pageToken"] = next_page

    return all_machine_types


def get_machine_type_kconfig_name(machine_type: str) -> str:
    """
    Convert GCE machine type name to Kconfig constant name.

    Args:
        machine_type (str): GCE machine type (e.g., 'n2-standard-4', 'e2-micro')

    Returns:
        str: Kconfig constant name (e.g., 'N2_STANDARD_4', 'E2_MICRO')
    """
    return machine_type.upper().replace("-", "_")


def list_images(
    session: requests.Session, image_project: str, quiet: bool = False
) -> list[dict]:
    """
    List all images from a GCE image project using the REST API.

    GCE public images are organized by project. Each Linux distribution
    has its own image project (e.g., 'debian-cloud', 'ubuntu-os-cloud').

    Args:
        session: Authenticated requests session
        image_project: GCE image project (e.g., 'debian-cloud')
        quiet: Suppress debug messages

    Returns:
        list: List of image dictionaries from the API
    """
    url = f"{GCE_COMPUTE_API}/projects/{image_project}/global/images"
    # Request only fields needed for Kconfig generation to reduce network traffic
    params = {
        "fields": "items(name,family,architecture,deprecated,creationTimestamp),"
        "nextPageToken"
    }
    all_images = []

    while True:
        response = session.get(url, params=params, timeout=GCE_API_TIMEOUT)
        if response.status_code == 403:
            if not quiet:
                print(
                    f"  Warning: Access denied for project {image_project}",
                    file=sys.stderr,
                )
            return []
        elif response.status_code == 404:
            if not quiet:
                print(
                    f"  Warning: Project {image_project} not found",
                    file=sys.stderr,
                )
            return []
        response.raise_for_status()

        data = response.json()
        all_images.extend(data.get("items", []))

        # Handle pagination
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break
        params["pageToken"] = next_page_token

    return all_images


def get_image_families(
    session: requests.Session, image_project: str, quiet: bool = False
) -> dict[str, dict]:
    """
    Get image families from a GCE image project.

    Image families group related images together. The latest non-deprecated
    image in a family is used when specifying a family instead of a specific
    image. This function returns information about each family including
    the latest image details.

    Args:
        session: Authenticated requests session
        image_project: GCE image project (e.g., 'debian-cloud')
        quiet: Suppress debug messages

    Returns:
        dict: Dictionary mapping family names to family information:
              {
                  'family_name': {
                      'latest_image': str,  # Name of latest image
                      'architecture': str,  # 'X86_64' or 'ARM64'
                      'deprecated': bool,   # True if family is deprecated
                      'creation_timestamp': str,
                  }
              }
    """
    images = list_images(session, image_project, quiet)

    # Group images by family and find the latest non-deprecated image
    families = {}

    for image in images:
        family = image.get("family")
        if not family:
            continue

        # Check if this image is deprecated
        deprecated_state = image.get("deprecated", {})
        is_deprecated = deprecated_state.get("state") == "DEPRECATED"

        # Get architecture (default to X86_64 if not specified)
        arch = image.get("architecture", "X86_64")

        creation_timestamp = image.get("creationTimestamp", "")

        # Track family information
        if family not in families:
            families[family] = {
                "latest_image": image.get("name"),
                "architecture": arch,
                "deprecated": is_deprecated,
                "creation_timestamp": creation_timestamp,
            }
        else:
            # Update if this image is better: prefer non-deprecated, then newer
            existing = families[family]
            existing_deprecated = existing["deprecated"]

            # Determine if we should replace the existing entry:
            # 1. Current is non-deprecated, existing is deprecated -> replace
            # 2. Both have same deprecation status -> replace if newer
            # 3. Current is deprecated, existing is non-deprecated -> keep existing
            should_replace = False
            if not is_deprecated and existing_deprecated:
                # Non-deprecated beats deprecated regardless of timestamp
                should_replace = True
            elif is_deprecated == existing_deprecated:
                # Same deprecation status: compare timestamps.
                # ISO 8601 timestamps from GCE sort correctly as strings.
                if creation_timestamp > existing["creation_timestamp"]:
                    should_replace = True
            # else: current is deprecated, existing is not -> keep existing

            if should_replace:
                families[family] = {
                    "latest_image": image.get("name"),
                    "architecture": arch,
                    "deprecated": is_deprecated,
                    "creation_timestamp": creation_timestamp,
                }

    return families
