#!/usr/bin/env python3
# ex: set filetype=python:

"""
Common utilities for OCI Kconfig generation scripts.

This module provides shared functionality used by gen_kconfig_location,
gen_kconfig_shape, and gen_kconfig_image scripts to avoid code duplication.
"""

from __future__ import annotations

import os
import sys
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Optional

import yaml
from jinja2 import Environment, FileSystemLoader


class OciNotConfiguredError(Exception):
    """Raised when OCI configuration is not available."""

    pass


def get_default_region() -> str:
    """
    Get the default OCI region from the ~/.oci/config file.

    Returns:
        str: Default region, or 'us-ashburn-1' if no default is found.
    """
    config_path = os.path.expanduser("~/.oci/config")
    if os.path.exists(config_path):
        try:
            config = ConfigParser()
            config.read(config_path)
            if "DEFAULT" in config:
                return config["DEFAULT"].get("region", "us-ashburn-1")
        except Exception as e:
            print(f"Warning: Error reading OCI config file: {e}", file=sys.stderr)
    return "us-ashburn-1"


def get_default_compartment() -> Optional[str]:
    """
    Get the default compartment OCID from OCI config.

    Returns:
        str: Tenancy OCID (root compartment), or None on error
    """
    try:
        config = get_oci_config()
        return config["tenancy"]
    except Exception as e:
        print(f"Error getting compartment: {e}", file=sys.stderr)
        return None


def get_subscribed_regions(quiet: bool = False) -> list[str]:
    """
    Get all subscribed regions for the tenancy.

    Args:
        quiet (bool): Suppress debug messages

    Returns:
        list: List of subscribed region names
    """
    try:
        config = get_oci_config()
        identity = create_identity_client()

        region_subs = identity.list_region_subscriptions(config["tenancy"]).data
        subscribed = [r.region_name for r in region_subs if r.status == "READY"]

        if not quiet:
            print(
                f"Found {len(subscribed)} subscribed regions: {', '.join(subscribed)}",
                file=sys.stderr,
            )

        return subscribed

    except Exception as e:
        print(f"Error getting subscribed regions: {e}", file=sys.stderr)
        # Fallback to default region
        return [get_default_region()]


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
    region_friendly_names.yml, catalog_shapes.yml, and
    publisher_definitions.yml.

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


def get_oci_config(region: Optional[str] = None) -> dict[str, Any]:
    """
    Get OCI configuration with optional region override.

    This provides a centralized way to load OCI config and optionally
    override the region, with consistent error handling.

    Args:
        region (str): Optional region to override config default

    Returns:
        dict: OCI configuration dictionary

    Raises:
        ConfigFileNotFound: If OCI config file doesn't exist
        Exception: For other configuration errors
    """
    # Lazy import - only load OCI SDK when actually needed
    import oci

    config = oci.config.from_file()
    if region:
        config["region"] = region
    return config


def require_oci_config() -> dict[str, Any]:
    """
    Require OCI configuration, raising an exception if not configured.

    This function should be called early in main() to validate OCI
    configuration. If OCI is not configured, it raises OciNotConfiguredError
    to let the caller decide how to handle it.

    This centralizes the handling of missing OCI configuration and avoids
    TOCTOU race conditions from manual file existence checks.

    Returns:
        dict: OCI configuration dictionary if available

    Raises:
        OciNotConfiguredError: If OCI configuration file is not found
    """
    # Lazy import - only load OCI SDK when actually needed
    import oci
    from oci.exceptions import ConfigFileNotFound

    try:
        return oci.config.from_file()
    except ConfigFileNotFound as e:
        raise OciNotConfiguredError("OCI configuration not found") from e


def create_identity_client(region: Optional[str] = None) -> oci.identity.IdentityClient:
    """
    Create an OCI Identity client with optional region override.

    Args:
        region (str): Optional region to use instead of config default

    Returns:
        oci.identity.IdentityClient: Configured identity client

    Raises:
        ConfigFileNotFound: If OCI config file doesn't exist
        Exception: For other initialization errors
    """
    # Lazy import - only load OCI SDK when actually needed
    import oci

    config = get_oci_config(region)
    return oci.identity.IdentityClient(config)


def create_compute_client(region: Optional[str] = None) -> oci.core.ComputeClient:
    """
    Create an OCI Compute client with optional region override.

    Args:
        region (str): Optional region to use instead of config default

    Returns:
        oci.core.ComputeClient: Configured compute client

    Raises:
        ConfigFileNotFound: If OCI config file doesn't exist
        Exception: For other initialization errors
    """
    # Lazy import - only load OCI SDK when actually needed
    import oci

    config = get_oci_config(region)
    return oci.core.ComputeClient(config)


def get_all_region_keys(quiet: bool = False) -> dict[str, str]:
    """
    Get all OCI regions with their official region keys from the OCI API.

    The region key is the 3-letter code (e.g., 'ORD' for us-chicago-1)
    that OCI uses in its API responses. This is the authoritative source
    for region codes rather than hardcoding a mapping.

    Args:
        quiet (bool): Suppress debug messages

    Returns:
        dict: Dictionary mapping region_name -> region_key (e.g., 'us-chicago-1' -> 'ORD')
    """
    try:
        identity = create_identity_client()

        # Get all regions - this includes their official region keys
        all_regions = identity.list_regions().data

        region_key_map = {}
        for region in all_regions:
            region_key_map[region.name] = region.key

        if not quiet:
            print(
                f"Loaded {len(region_key_map)} region key mappings from OCI API",
                file=sys.stderr,
            )

        return region_key_map

    except Exception as e:
        if not quiet:
            print(
                f"Warning: Could not load region keys from OCI API: {e}",
                file=sys.stderr,
            )
            print("Using fallback region key generation", file=sys.stderr)
        return {}


def get_region_kconfig_name(
    region_name: str, region_key_map: Optional[dict[str, str]] = None
) -> str:
    """
    Convert OCI region name to Kconfig region constant name.

    Uses the official region key from the OCI API when available,
    falling back to a generated name if the API is not accessible.

    Args:
        region_name (str): OCI region name (e.g., 'us-chicago-1')
        region_key_map (dict): Optional mapping from region_name to region_key.
                              If None, generates from region name.

    Returns:
        str: Kconfig constant name (e.g., 'ORD' for us-chicago-1)
    """
    if region_key_map and region_name in region_key_map:
        return region_key_map[region_name]

    # Fallback: generate from region name
    # Take first 3 letters of the location part
    parts = region_name.split("-")
    if len(parts) >= 2:
        return parts[1][:3].upper()
    return region_name[:3].upper()
