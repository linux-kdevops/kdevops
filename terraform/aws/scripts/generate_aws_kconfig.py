#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
AWS Kconfig generator using Chuck's ec2_instance_info.py with JSON caching.

This script orchestrates the generation of Kconfig files for AWS EC2 instances
using Chuck's existing scripts with added caching and parallelization.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

# Cache configuration
CACHE_DIR = Path.home() / ".cache" / "kdevops" / "aws"
CACHE_TTL = 24 * 3600  # 24 hours in seconds

# Scripts directory
SCRIPTS_DIR = Path(__file__).parent
EC2_INFO_SCRIPT = SCRIPTS_DIR / "ec2_instance_info.py"
AMI_INFO_SCRIPT = SCRIPTS_DIR / "aws_ami_info.py"
REGIONS_INFO_SCRIPT = SCRIPTS_DIR / "aws_regions_info.py"

# Output directories
KCONFIG_DIR = SCRIPTS_DIR.parent / "kconfigs"
INSTANCE_TYPES_DIR = KCONFIG_DIR / "instance-types"


def ensure_cache_dir():
    """Create cache directory if it doesn't exist."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_file(cache_key: str) -> Path:
    """Get cache file path for a given key."""
    return CACHE_DIR / f"{cache_key}.json"


def is_cache_valid(cache_file: Path) -> bool:
    """Check if cache file exists and is still valid."""
    if not cache_file.exists():
        return False

    age = time.time() - cache_file.stat().st_mtime
    return age < CACHE_TTL


def load_from_cache(cache_key: str) -> Optional[Any]:
    """Load data from cache if valid."""
    cache_file = get_cache_file(cache_key)

    if is_cache_valid(cache_file):
        try:
            with cache_file.open('r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    return None


def save_to_cache(cache_key: str, data: Any):
    """Save data to cache."""
    cache_file = get_cache_file(cache_key)

    try:
        with cache_file.open('w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"Warning: Failed to save cache: {e}", file=sys.stderr)


def run_chuck_script(script: Path, args: List[str]) -> Optional[Any]:
    """Run one of Chuck's scripts and return JSON output."""
    cmd = [sys.executable, str(script)] + args + ["--format", "json", "--quiet"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "AWS_DEFAULT_REGION": os.environ.get("AWS_DEFAULT_REGION", "us-east-1")}
        )

        if result.stdout:
            return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script.name}: {e}", file=sys.stderr)
        if e.stderr:
            print(f"stderr: {e.stderr}", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from {script.name}: {e}", file=sys.stderr)

    return None


def fetch_all_families() -> Optional[List[Dict[str, Any]]]:
    """Fetch all instance families."""
    cache_key = "aws_families"

    # Check cache first
    cached = load_from_cache(cache_key)
    if cached:
        print("Using cached AWS families data", file=sys.stderr)
        return cached

    print("Fetching AWS instance families...", file=sys.stderr)
    families = run_chuck_script(EC2_INFO_SCRIPT, ["--families"])

    if families:
        save_to_cache(cache_key, families)

    return families


def fetch_family_instances(family_name: str) -> Optional[List[Dict]]:
    """Fetch instances for a specific family."""
    cache_key = f"aws_family_{family_name}"

    # Check cache first
    cached = load_from_cache(cache_key)
    if cached:
        return cached

    instances = run_chuck_script(EC2_INFO_SCRIPT, [family_name])

    if instances:
        save_to_cache(cache_key, instances)

    return instances


def fetch_all_instances() -> Dict[str, List[Dict]]:
    """Fetch all instances for all families with parallel processing."""
    families = fetch_all_families()
    if not families:
        print("Error: Could not fetch AWS families", file=sys.stderr)
        return {}

    # Check if we have a complete cache
    cache_key = "aws_all_instances"
    cached = load_from_cache(cache_key)
    if cached:
        print("Using cached complete AWS instance data", file=sys.stderr)
        return cached

    print(f"Fetching instance data for {len(families)} families...", file=sys.stderr)
    all_instances = {}

    # Extract family names from the list of family dicts
    family_names = [f['family_name'] for f in families if 'family_name' in f]

    # Use parallel processing to fetch instance data
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_family = {
            executor.submit(fetch_family_instances, family): family
            for family in family_names
        }

        for future in as_completed(future_to_family):
            family = future_to_family[future]
            try:
                instances = future.result()
                if instances:
                    all_instances[family] = instances
                    print(f"  Fetched {family}: {len(instances)} instances", file=sys.stderr)
            except Exception as e:
                print(f"  Error fetching {family}: {e}", file=sys.stderr)

    # Save complete dataset to cache
    if all_instances:
        save_to_cache(cache_key, all_instances)

    return all_instances


def fetch_regions() -> Optional[List[Dict]]:
    """Fetch AWS regions."""
    cache_key = "aws_regions"

    cached = load_from_cache(cache_key)
    if cached:
        print("Using cached AWS regions data", file=sys.stderr)
        return cached

    print("Fetching AWS regions...", file=sys.stderr)
    regions = run_chuck_script(REGIONS_INFO_SCRIPT, ["--regions"])

    if regions:
        save_to_cache(cache_key, regions)

    return regions


def fetch_gpu_amis() -> Optional[Dict]:
    """Fetch GPU AMI information."""
    cache_key = "aws_gpu_amis"

    cached = load_from_cache(cache_key)
    if cached:
        print("Using cached AWS GPU AMI data", file=sys.stderr)
        return cached

    print("Fetching AWS GPU AMIs...", file=sys.stderr)
    amis = run_chuck_script(AMI_INFO_SCRIPT, ["--gpu"])

    if amis:
        save_to_cache(cache_key, amis)

    return amis


def generate_family_kconfig(family: str, instances: List[Dict]) -> str:
    """Generate Kconfig content for a single family."""
    content = [f"# AWS {family.upper()} instance sizes (dynamically generated)", ""]

    # Filter instances to only include the exact family (not related families)
    # e.g., for "r8g" family, exclude "r8gd" and "r8gn" instances
    filtered_instances = [
        inst for inst in instances
        if inst['instance_type'].split('.')[0] == family
    ]

    if not filtered_instances:
        # If no exact matches, use all instances (backward compatibility)
        filtered_instances = instances

    # Sort instances by a logical order
    sorted_instances = sorted(filtered_instances, key=lambda x: (
        'metal' not in x['instance_type'],  # metal instances last
        x.get('vcpus', 0),  # then by vCPUs
        x.get('memory_gb', 0)  # then by memory
    ))

    # Determine default instance (usually the first non-nano/micro)
    default = sorted_instances[0]['instance_type']
    for inst in sorted_instances:
        if not any(size in inst['instance_type'] for size in ['.nano', '.micro']):
            default = inst['instance_type']
            break

    # Generate choice block
    content.append("choice")
    content.append(f'\tprompt "Instance size for {family.upper()} family"')
    content.append(f'\tdefault TERRAFORM_AWS_INSTANCE_{default.replace(".", "_").replace("-", "_").upper()}')
    content.append("\thelp")
    content.append(f"\t  Select the specific instance size within the {family.upper()} family.")
    content.append("")

    # Generate config entries
    for inst in sorted_instances:
        # Replace both dots and dashes with underscores for valid Kconfig symbols
        type_upper = inst['instance_type'].replace('.', '_').replace('-', '_').upper()
        content.append(f"config TERRAFORM_AWS_INSTANCE_{type_upper}")
        content.append(f'\tbool "{inst["instance_type"]}"')
        content.append("\thelp")
        content.append(f"\t  vCPUs: {inst.get('vcpus', 'N/A')}")
        content.append(f"\t  Memory: {inst.get('memory_gb', 'N/A')} GB")
        content.append(f"\t  Network: {inst.get('network_performance', 'N/A')}")
        content.append("")

    content.append("endchoice")
    content.append("")

    # Generate string config
    content.append(f"config TERRAFORM_AWS_{family.upper()}_SIZE")
    content.append("\tstring")

    for inst in sorted_instances:
        type_upper = inst['instance_type'].replace('.', '_').replace('-', '_').upper()
        content.append(f'\tdefault "{inst["instance_type"]}" if TERRAFORM_AWS_INSTANCE_{type_upper}')

    content.append(f'\tdefault "{default}"')
    content.append("")

    return '\n'.join(content)


def generate_compute_kconfig(families: Dict[str, Any]) -> str:
    """Generate main compute Kconfig."""
    content = ["# AWS EC2 Instance Types (dynamically generated)", ""]

    # Sort families for consistent output
    sorted_families = sorted(families.keys())

    content.append("choice")
    content.append('\tprompt "EC2 instance family"')
    content.append("\tdefault TERRAFORM_AWS_INSTANCE_FAMILY_M5")
    content.append("\thelp")
    content.append("\t  Select the EC2 instance family to use.")
    content.append("")

    for family in sorted_families:
        family_upper = family.upper()
        family_desc = families[family].get('description', f'{family_upper} instances')

        content.append(f"config TERRAFORM_AWS_INSTANCE_FAMILY_{family_upper}")
        content.append(f'\tbool "{family_upper} - {family_desc}"')
        content.append("\thelp")
        content.append(f"\t  {family_desc}")
        content.append(f"\t  Available instances: {families[family].get('count', 0)}")
        content.append("")

    content.append("endchoice")
    content.append("")

    # Generate family name config
    content.append("config TERRAFORM_AWS_INSTANCE_FAMILY")
    content.append("\tstring")

    for family in sorted_families:
        family_upper = family.upper()
        content.append(f'\tdefault "{family}" if TERRAFORM_AWS_INSTANCE_FAMILY_{family_upper}')

    content.append('\tdefault "m5"')
    content.append("")

    # Include family-specific files
    for family in sorted_families:
        content.append(f'if TERRAFORM_AWS_INSTANCE_FAMILY_{family.upper()}')
        content.append(f'source "terraform/aws/kconfigs/instance-types/Kconfig.{family}.generated"')
        content.append("endif")
        content.append("")

    return '\n'.join(content)


def generate_location_kconfig(regions: List[Dict]) -> str:
    """Generate location Kconfig."""
    content = ["# AWS Regions (dynamically generated)", ""]

    content.append("choice")
    content.append('\tprompt "AWS region"')
    content.append("\tdefault TERRAFORM_AWS_REGION_US_EAST_1")
    content.append("\thelp")
    content.append("\t  Select the AWS region for your infrastructure.")
    content.append("")

    for region in regions:
        region_upper = region['region_name'].replace('-', '_').upper()
        content.append(f"config TERRAFORM_AWS_REGION_{region_upper}")
        content.append(f'\tbool "{region["region_name"]} - {region.get("location", "")}"')
        content.append("")

    content.append("endchoice")
    content.append("")

    # Generate region string config
    content.append("config TERRAFORM_AWS_REGION")
    content.append("\tstring")

    for region in regions:
        region_upper = region['region_name'].replace('-', '_').upper()
        content.append(f'\tdefault "{region["region_name"]}" if TERRAFORM_AWS_REGION_{region_upper}')

    content.append('\tdefault "us-east-1"')
    content.append("")

    return '\n'.join(content)


def write_kconfig_file(filepath: Path, content: str):
    """Write Kconfig content to file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content)


def clear_cache():
    """Clear all cached data."""
    if CACHE_DIR.exists():
        for cache_file in CACHE_DIR.glob("*.json"):
            cache_file.unlink()
        print("Cache cleared", file=sys.stderr)


def main():
    """Main function."""
    # Handle cache clearing
    if len(sys.argv) > 1 and sys.argv[1] == "clear-cache":
        clear_cache()
        return

    start_time = time.time()

    # Ensure AWS region is set
    if "AWS_DEFAULT_REGION" not in os.environ:
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        print(f"Set AWS_DEFAULT_REGION to us-east-1", file=sys.stderr)

    ensure_cache_dir()

    # Fetch all data (uses cache if available)
    print("Generating AWS Kconfig files...", file=sys.stderr)

    # Fetch regions
    regions = fetch_regions()
    if not regions:
        print("Warning: Could not fetch regions", file=sys.stderr)
        regions = []

    # Fetch all instance data
    all_instances = fetch_all_instances()
    if not all_instances:
        print("Error: Could not fetch instance data", file=sys.stderr)
        sys.exit(1)

    # Prepare families info for compute Kconfig
    families_info = {}
    for family, instances in all_instances.items():
        families_info[family] = {
            'count': len(instances),
            'description': f'{family.upper()} instances'
        }

    print(f"\nGenerating Kconfig files for {len(all_instances)} families...", file=sys.stderr)

    # Generate files in parallel
    tasks = []

    # Family-specific Kconfig files
    for family, instances in all_instances.items():
        filepath = INSTANCE_TYPES_DIR / f"Kconfig.{family}.generated"
        content = generate_family_kconfig(family, instances)
        tasks.append((filepath, content))

    # Main Kconfig files
    tasks.append((KCONFIG_DIR / "Kconfig.compute.generated",
                  generate_compute_kconfig(families_info)))

    if regions:
        tasks.append((KCONFIG_DIR / "Kconfig.location.generated",
                      generate_location_kconfig(regions)))

    # GPU AMIs (stub for now)
    tasks.append((KCONFIG_DIR / "Kconfig.gpu-amis.generated",
                  "# AWS GPU AMIs (placeholder)\n"))

    # Write files in parallel
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for filepath, content in tasks:
            future = executor.submit(write_kconfig_file, filepath, content)
            futures.append((future, filepath))

        for future, filepath in futures:
            try:
                future.result()
                print(f"  Generated: {filepath.name}", file=sys.stderr)
            except Exception as e:
                print(f"  Error writing {filepath}: {e}", file=sys.stderr)

    elapsed = time.time() - start_time

    # Summary
    print(f"\n✓ Generated {len(tasks)} Kconfig files in {elapsed:.2f} seconds", file=sys.stderr)
    print(f"  • {len(all_instances)} instance families", file=sys.stderr)
    print(f"  • {sum(len(instances) for instances in all_instances.values())} total instance types", file=sys.stderr)
    print(f"  • {len(regions)} regions", file=sys.stderr)

    if elapsed < 1:
        print(f"  • Using cached data (cache valid for 24 hours)", file=sys.stderr)
    else:
        print(f"  • Fresh data fetched from AWS", file=sys.stderr)


if __name__ == "__main__":
    main()