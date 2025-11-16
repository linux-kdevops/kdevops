#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Generate dynamic Kconfig files for DataCrunch cloud provider.

Queries the DataCrunch API to generate Kconfig options for:
- Instance types (with H100 focus)
- Images (with PyTorch focus)
- Locations
"""

import sys
import os
from pathlib import Path

# Import our DataCrunch API library
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datacrunch_api import (
    get_api_key,
    list_instance_types,
    list_images,
    list_locations,
)


def sanitize_kconfig_name(name: str) -> str:
    """Convert instance/image/location name to valid Kconfig symbol name."""
    # Replace special characters with underscores
    name = name.upper()
    name = name.replace("-", "_")
    name = name.replace(".", "_")
    name = name.replace(" ", "_")
    name = name.replace("/", "_")
    return name


def generate_instance_types_kconfig() -> str:
    """Generate Kconfig for DataCrunch instance types, focusing on H100."""
    instance_types = list_instance_types()

    if not instance_types:
        # Fallback if API unavailable
        return """# DataCrunch instance types (API unavailable - using defaults)

choice
\tprompt "DataCrunch instance type"
\tdefault TERRAFORM_DATACRUNCH_INSTANCE_TYPE_1X_H100_PCIE
\thelp
\t  Select the DataCrunch instance type for your deployment.
\t  Note: API is currently unavailable, showing default H100 options.

config TERRAFORM_DATACRUNCH_INSTANCE_TYPE_1X_H100_PCIE
\tbool "1x H100 PCIe (80GB) - Pay-as-you-go"
\thelp
\t  Single NVIDIA H100 PCIe GPU with 80GB HBM3 memory.
\t  Pay-as-you-go pricing, ideal for quick development and testing.

endchoice
"""

    # Filter for H100 instances (pay-as-you-go)
    h100_types = []
    for inst_type in instance_types:
        name = inst_type.get("instance_type", "")
        description = inst_type.get("description", "")
        if "H100" in name or "H100" in description:
            h100_types.append(inst_type)

    if not h100_types:
        # If no H100 found, show all GPU types
        h100_types = [it for it in instance_types if "GPU" in it.get("description", "")]

    # Sort by price (cheapest first)
    h100_types.sort(key=lambda x: float(x.get("price_per_hour", "999") or "999"))

    # Generate Kconfig
    kconfig = "# DataCrunch instance types (dynamically generated)\n\n"
    kconfig += "choice\n"
    kconfig += '\tprompt "DataCrunch instance type"\n'

    # Use first (cheapest) H100 as default
    if h100_types:
        default_name = sanitize_kconfig_name(h100_types[0].get("instance_type", ""))
        kconfig += f"\tdefault TERRAFORM_DATACRUNCH_INSTANCE_TYPE_{default_name}\n"

    kconfig += "\thelp\n"
    kconfig += "\t  Select the DataCrunch instance type for your deployment.\n"
    kconfig += "\t  These options are dynamically generated from the DataCrunch API.\n"
    kconfig += "\t  Focused on H100 GPUs for high-performance computing.\n\n"

    # Add each H100 instance type
    for inst_type in h100_types:
        name = inst_type.get("instance_type", "")
        kconfig_name = sanitize_kconfig_name(name)
        description = inst_type.get("description", name)
        price_raw = inst_type.get("price_per_hour", "0")
        price = float(price_raw) if price_raw else 0.0
        cpu = inst_type.get("cpu", "N/A")
        ram_gb = inst_type.get("ram_gb", "N/A")

        kconfig += f"config TERRAFORM_DATACRUNCH_INSTANCE_TYPE_{kconfig_name}\n"
        kconfig += f'\tbool "{name} - ${price:.2f}/hr"\n'
        kconfig += "\thelp\n"
        kconfig += f"\t  {description}\n"
        kconfig += f"\t  Price: ${price:.2f} per hour (pay-as-you-go)\n"
        kconfig += f"\t  CPU: {cpu}, RAM: {ram_gb} GB\n\n"

    kconfig += "endchoice\n\n"

    # Add string config for the actual instance type value
    kconfig += "config TERRAFORM_DATACRUNCH_INSTANCE_TYPE\n"
    kconfig += '\tstring "DataCrunch instance type value"\n'
    kconfig += "\toutput yaml\n"

    for inst_type in h100_types:
        name = inst_type.get("instance_type", "")
        kconfig_name = sanitize_kconfig_name(name)
        kconfig += (
            f'\tdefault "{name}" if TERRAFORM_DATACRUNCH_INSTANCE_TYPE_{kconfig_name}\n'
        )

    kconfig += "\thelp\n"
    kconfig += "\t  The actual instance type string to use for provisioning.\n\n"

    return kconfig


def generate_images_kconfig() -> str:
    """Generate Kconfig for DataCrunch images, focusing on PyTorch."""
    images = list_images()

    if not images:
        # Fallback if API unavailable
        return """# DataCrunch OS images (API unavailable - using defaults)

choice
\tprompt "DataCrunch OS image"
\tdefault TERRAFORM_DATACRUNCH_IMAGE_PYTORCH
\thelp
\t  Select the operating system image for your instances.
\t  Note: API is currently unavailable, showing default PyTorch option.

config TERRAFORM_DATACRUNCH_IMAGE_PYTORCH
\tbool "PyTorch (Ubuntu 22.04 with PyTorch pre-installed)"
\thelp
\t  Ubuntu 22.04 LTS with PyTorch and CUDA drivers pre-installed.
\t  Ready for machine learning workloads.

endchoice
"""

    # Filter for PyTorch images first, then Ubuntu/Linux
    pytorch_images = [img for img in images if "pytorch" in img.get("name", "").lower()]
    ubuntu_images = [img for img in images if "ubuntu" in img.get("name", "").lower()]

    # Prefer PyTorch, fallback to Ubuntu
    preferred_images = pytorch_images if pytorch_images else ubuntu_images
    if not preferred_images:
        preferred_images = images[:5]  # Show first 5 if nothing matches

    # Generate Kconfig
    kconfig = "# DataCrunch OS images (dynamically generated)\n\n"
    kconfig += "choice\n"
    kconfig += '\tprompt "DataCrunch OS image"\n'

    # Use first PyTorch image as default
    if preferred_images:
        default_name = sanitize_kconfig_name(preferred_images[0].get("image_type", ""))
        kconfig += f"\tdefault TERRAFORM_DATACRUNCH_IMAGE_{default_name}\n"

    kconfig += "\thelp\n"
    kconfig += "\t  Select the operating system image for your instances.\n"
    kconfig += "\t  These options are dynamically generated from the DataCrunch API.\n"
    kconfig += "\t  PyTorch images are recommended for ML workloads.\n\n"

    # Add each image
    for img in preferred_images:
        image_type = img.get("image_type", "")
        kconfig_name = sanitize_kconfig_name(image_type)
        name = img.get("name", image_type)
        description = name  # Use name as description

        kconfig += f"config TERRAFORM_DATACRUNCH_IMAGE_{kconfig_name}\n"
        kconfig += f'\tbool "{name}"\n'
        kconfig += "\thelp\n"
        kconfig += f"\t  {description}\n\n"

    kconfig += "endchoice\n\n"

    # Add string config for the actual image ID
    kconfig += "config TERRAFORM_DATACRUNCH_IMAGE\n"
    kconfig += '\tstring "DataCrunch image ID"\n'
    kconfig += "\toutput yaml\n"

    for img in preferred_images:
        image_type = img.get("image_type", "")
        kconfig_name = sanitize_kconfig_name(image_type)
        kconfig += (
            f'\tdefault "{image_type}" if TERRAFORM_DATACRUNCH_IMAGE_{kconfig_name}\n'
        )

    kconfig += "\thelp\n"
    kconfig += "\t  The actual image ID to use for instance provisioning.\n\n"

    return kconfig


def generate_locations_kconfig() -> str:
    """Generate Kconfig for DataCrunch locations."""
    locations = list_locations()

    if not locations:
        # Fallback if API unavailable
        return """# DataCrunch locations (API unavailable - using defaults)

choice
\tprompt "DataCrunch datacenter location"
\tdefault TERRAFORM_DATACRUNCH_LOCATION_FIN_01
\thelp
\t  Select the datacenter location for your deployment.

config TERRAFORM_DATACRUNCH_LOCATION_FIN_01
\tbool "FIN-01 - Finland"
\thelp
\t  DataCrunch datacenter in Finland.

endchoice
"""

    # Generate Kconfig
    kconfig = "# DataCrunch locations (dynamically generated)\n\n"
    kconfig += "choice\n"
    kconfig += '\tprompt "DataCrunch datacenter location"\n'

    # Use first location as default
    if locations:
        default_code = sanitize_kconfig_name(locations[0].get("code", ""))
        kconfig += f"\tdefault TERRAFORM_DATACRUNCH_LOCATION_{default_code}\n"

    kconfig += "\thelp\n"
    kconfig += "\t  Select the datacenter location for your deployment.\n"
    kconfig += (
        "\t  These options are dynamically generated from the DataCrunch API.\n\n"
    )

    # Add each location
    for loc in locations:
        code = loc.get("code", "")
        kconfig_name = sanitize_kconfig_name(code)
        name = loc.get("name", code)
        country = loc.get("country", "")

        kconfig += f"config TERRAFORM_DATACRUNCH_LOCATION_{kconfig_name}\n"
        kconfig += f'\tbool "{code} - {name}, {country}"\n'
        kconfig += "\thelp\n"
        kconfig += f"\t  DataCrunch datacenter in {name}, {country}.\n\n"

    kconfig += "endchoice\n\n"

    # Add string config for the actual location code
    kconfig += "config TERRAFORM_DATACRUNCH_LOCATION\n"
    kconfig += '\tstring "DataCrunch location code"\n'
    kconfig += "\toutput yaml\n"

    for loc in locations:
        code = loc.get("code", "")
        kconfig_name = sanitize_kconfig_name(code)
        kconfig += (
            f'\tdefault "{code}" if TERRAFORM_DATACRUNCH_LOCATION_{kconfig_name}\n'
        )

    kconfig += "\thelp\n"
    kconfig += "\t  The actual location code to use for provisioning.\n\n"

    return kconfig


def main():
    """Generate all DataCrunch Kconfig files."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate DataCrunch Kconfig files")
    parser.add_argument(
        "--output-dir",
        default="terraform/datacrunch/kconfigs",
        help="Output directory for generated Kconfig files",
    )
    parser.add_argument(
        "--type",
        choices=["all", "instances", "images", "locations"],
        default="all",
        help="Which Kconfig files to generate",
    )
    args = parser.parse_args()

    # Check API key
    api_key = get_api_key()
    if not api_key:
        print("Warning: No DataCrunch API key found", file=sys.stderr)
        print("Using fallback default configurations", file=sys.stderr)
        print(
            "Run: python3 scripts/datacrunch_credentials.py set <api_key>",
            file=sys.stderr,
        )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.type in ["all", "instances"]:
        print("Generating instance types Kconfig...")
        kconfig = generate_instance_types_kconfig()
        output_file = output_dir / "Kconfig.compute.generated"
        output_file.write_text(kconfig)
        print(f"  → {output_file}")

    if args.type in ["all", "images"]:
        print("Generating images Kconfig...")
        kconfig = generate_images_kconfig()
        output_file = output_dir / "Kconfig.images.generated"
        output_file.write_text(kconfig)
        print(f"  → {output_file}")

    if args.type in ["all", "locations"]:
        print("Generating locations Kconfig...")
        kconfig = generate_locations_kconfig()
        output_file = output_dir / "Kconfig.location.generated"
        output_file.write_text(kconfig)
        print(f"  → {output_file}")

    print("\nDataCrunch Kconfig generation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
