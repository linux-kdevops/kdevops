#!/usr/bin/python3
# SPDX-License-Identifier: copyleft-next-0.3.1

# Takes as input the output of $(lspci -Dvmmm) and then creates a kconfig
# file you can use. One use case is pci-passthrough.

import argparse
import os
import sys
import re

dynpci_kconfig_ansible_python_dir = os.path.dirname(os.path.abspath(__file__))
passthrough_prefix = "KDEVOPS_DYNAMIC_PCIE_PASSTHROUGH"
sys_bus_prefix = "/sys/bus/pci/devices/"

debug = 0


def get_first_dir(path):
    if len(os.listdir(path)) > 0:
        return os.listdir(path)[0]
    return None


def get_sysname(sys_path, entry):
    sys_entry_path = sys_path + entry
    if not os.path.isfile(sys_entry_path):
        return None
    entry_fd = open(sys_entry_path, "r")
    line = entry_fd.readlines()[0]
    line = line.strip()
    entry_fd.close()
    return line


# kconfig does not like some characters
def strip_kconfig_name(name):
    fixed_name = name.replace('"', "")
    fixed_name = fixed_name.replace("'", "")
    return fixed_name


def get_special_device_nvme(pci_id, IOMMUGroup):
    pci_id_name = strip_kconfig_name(pci_id)
    sys_path = sys_bus_prefix + pci_id + "/nvme/"
    if not os.path.isdir(sys_path):
        return None
    block_device_name = get_first_dir(sys_path)
    if not block_device_name:
        return None
    block_sys_path = sys_path + block_device_name + "/"
    model = get_sysname(block_sys_path, "model")
    if not model:
        return None
    fw = get_sysname(block_sys_path, "firmware_rev")
    if not fw:
        return None
    return "%s IOMMU group %s - /dev/%s - %s with FW %s" % (
        pci_id_name,
        IOMMUGroup,
        block_device_name,
        model,
        fw,
    )


def get_gpu_memory_info(pci_id):
    """Try to get GPU memory information from sysfs."""
    # Try to get memory info from various possible locations
    mem_paths = [
        sys_bus_prefix + pci_id + "/mem_info_vram_total",
        sys_bus_prefix + pci_id + "/drm/card0/mem_info_vram_total",
    ]

    for mem_path in mem_paths:
        if os.path.isfile(mem_path):
            try:
                with open(mem_path, "r") as f:
                    mem_bytes = int(f.read().strip())
                    mem_gb = mem_bytes / (1024 * 1024 * 1024)
                    return f"{mem_gb:.0f}GB"
            except:
                pass

    # Try to get memory from resource file size (less accurate)
    resource_path = sys_bus_prefix + pci_id + "/resource0"
    if os.path.isfile(resource_path):
        try:
            size = os.path.getsize(resource_path)
            if size > 0:
                size_gb = size / (1024 * 1024 * 1024)
                if size_gb >= 1:
                    return f"{size_gb:.0f}GB"
        except:
            pass

    return None


def get_special_device_gpu(pci_id, device_name, IOMMUGroup):
    """Generate a nice display name for GPU devices."""
    pci_id_name = strip_kconfig_name(pci_id)

    # Clean up the device name to extract the GPU model
    gpu_model = device_name

    # Common GPU name patterns to clean up
    replacements = [
        ("[AMD/ATI]", "AMD"),
        ("Advanced Micro Devices, Inc.", "AMD"),
        ("NVIDIA Corporation", "NVIDIA"),
        ("Intel Corporation", "Intel"),
    ]

    for old, new in replacements:
        gpu_model = gpu_model.replace(old, new).strip()

    # Try to extract specific GPU model from brackets
    import re

    bracket_match = re.search(r"\[([^\]]+)\]", gpu_model)
    if bracket_match:
        model_name = bracket_match.group(1)
        # Keep the vendor prefix if it's a clean model name
        if "Radeon" in model_name or "GeForce" in model_name or "Intel" in model_name:
            gpu_model = model_name
        else:
            # Prepend vendor if needed
            if "AMD" in gpu_model and "Radeon" not in model_name:
                gpu_model = f"AMD {model_name}"
            elif (
                "NVIDIA" in gpu_model
                and "GeForce" not in model_name
                and "Quadro" not in model_name
            ):
                gpu_model = f"NVIDIA {model_name}"
            else:
                gpu_model = model_name

    # Remove any existing memory info from the model name (e.g., "32GB" at the end)
    gpu_model = re.sub(r"\s+\d+GB\s*$", "", gpu_model)

    # Try to get memory info
    mem_info = get_gpu_memory_info(pci_id)

    # Build the display name
    if mem_info:
        display_name = (
            f"{pci_id_name} IOMMU group {IOMMUGroup} - GPU - {gpu_model} {mem_info}"
        )
    else:
        display_name = f"{pci_id_name} IOMMU group {IOMMUGroup} - GPU - {gpu_model}"

    return display_name


def is_gpu_device(device_name):
    """Check if a device is a GPU based on its name."""
    gpu_keywords = [
        # AMD/ATI
        "Radeon",
        "Vega",
        "Navi",
        "RDNA",
        "GCN",
        "Polaris",
        "Fiji",
        "Instinct",
        "FirePro",
        "FireGL",
        "RX",
        "AMD.*GPU",
        # NVIDIA
        "GeForce",
        "Quadro",
        "Tesla",
        "NVIDIA.*GPU",
        "GTX",
        "RTX",
        "Titan",
        "NVS",
        "GRID",
        # Intel
        "Intel.*Graphics",
        "UHD Graphics",
        "HD Graphics",
        "Iris",
        "Arc",
        "Xe Graphics",
        # Generic
        "VGA compatible controller",
        "Display controller",
        "3D controller",
        "Graphics",
    ]

    device_lower = device_name.lower()
    for keyword in gpu_keywords:
        if keyword.lower() in device_lower:
            return True
    return False


def get_kconfig_device_name(
    pci_id, sdevice, IOMMUGroup, vendor_name=None, device_name=None
):
    default_name = "%s IOMMU group %s - %s" % (pci_id, IOMMUGroup, sdevice)
    special_name = None

    # Check for NVMe devices
    if os.path.isdir(sys_bus_prefix + pci_id + "/nvme"):
        special_name = get_special_device_nvme(pci_id, IOMMUGroup)
    # Check for GPU devices
    elif device_name and is_gpu_device(device_name):
        special_name = get_special_device_gpu(pci_id, device_name, IOMMUGroup)

    if not special_name:
        return strip_kconfig_name(default_name)
    return strip_kconfig_name(special_name)


def add_pcie_kconfig_string(prefix, val, name):
    config_name = prefix + "_" + name.upper()
    sys.stdout.write("config %s\n" % (config_name))
    sys.stdout.write("\tstring\n")
    sys.stdout.write('\tdefault "%s"\n' % (strip_kconfig_name(str(val))))
    sys.stdout.write("\n")


def add_pcie_kconfig_name(config_name, sdevice):
    sys.stdout.write("config %s\n" % (config_name))
    sys.stdout.write('\tbool "%s"\n' % (sdevice))
    sys.stdout.write("\tdefault n\n")
    sys.stdout.write("\thelp\n")
    sys.stdout.write("\t  Enabling this will PCI-E passthrough this device onto the\n")
    sys.stdout.write("\t  target guest.\n")
    sys.stdout.write("\n")


def add_pcie_kconfig_target(config_name, sdevice):
    sys.stdout.write("config %s_TARGET_GUEST\n" % (config_name))
    sys.stdout.write(
        '\tstring  "Target guest to offload %s"\n' % (strip_kconfig_name(sdevice))
    )
    sys.stdout.write("\tdefault KDEVOPS_HOSTS_PREFIX\n")
    sys.stdout.write("\tdepends on %s\n" % config_name)
    sys.stdout.write("\tdepends on KDEVOPS_LIBVIRT_PCIE_PASSTHROUGH_TYPE_EACH\n")
    sys.stdout.write("\thelp\n")
    sys.stdout.write("\t  Enabling this will PCI-E passthrough this device onto the\n")
    sys.stdout.write("\t  target guest.\n")
    sys.stdout.write("\n")


def add_pcie_kconfig_entry(
    pci_id,
    sdevice,
    domain,
    bus,
    slot,
    function,
    IOMMUGroup,
    config_id,
    vendor_name=None,
    device_name=None,
):
    prefix = passthrough_prefix + "_%04d" % config_id
    name = get_kconfig_device_name(
        pci_id, sdevice, IOMMUGroup, vendor_name, device_name
    )
    add_pcie_kconfig_name(prefix, name)
    add_pcie_kconfig_target(prefix, sdevice)
    add_pcie_kconfig_string(prefix, pci_id, "pci_id")
    add_pcie_kconfig_string(prefix, sdevice, "sdevice")
    add_pcie_kconfig_string(prefix, name, "name")
    add_pcie_kconfig_string(prefix, IOMMUGroup, "IOMMUGroup")
    add_pcie_kconfig_string(prefix, domain, "domain")
    add_pcie_kconfig_string(prefix, bus, "bus")
    add_pcie_kconfig_string(prefix, slot, "slot")
    add_pcie_kconfig_string(prefix, function, "function")


def add_new_device(
    slot, sdevice, IOMMUGroup, possible_id, vendor_name=None, device_name=None
):
    # Example expeced format 0000:2d:00.0
    m = re.match(
        r"^(?P<DOMAIN>\w+):" "(?P<BUS>\w+):" "(?P<MSLOT>\w+)\." "(?P<FUNCTION>\w+)$",
        slot,
    )
    if not m:
        return possible_id

    possible_id += 1

    slot_dict = m.groupdict()
    domain = "0x" + slot_dict["DOMAIN"]
    bus = "0x" + slot_dict["BUS"]
    mslot = "0x" + slot_dict["MSLOT"]
    function = "0x" + slot_dict["FUNCTION"]

    if debug:
        sys.stdout.write("\tslot: %s\n" % (slot))
        sys.stdout.write("\tdomain: %s\n" % (domain))
        sys.stdout.write("\tbus: %s\n" % (bus))
        sys.stdout.write("\tslot: %s\n" % (mslot))
        sys.stdout.write("\tfunction: %s\n" % (function))
        sys.stdout.write("\tIOMMUGroup: %s\n" % (IOMMUGroup))

    if possible_id == 1:
        sys.stdout.write(
            "# Automatically generated PCI-E passthrough Kconfig by kdevops\n\n"
        )

    add_pcie_kconfig_entry(
        slot,
        sdevice,
        domain,
        bus,
        mslot,
        function,
        IOMMUGroup,
        possible_id,
        vendor_name,
        device_name,
    )

    return possible_id


def main():
    num_candidate_devices = 0
    parser = argparse.ArgumentParser(description="Creates a Kconfig file lspci output")
    parser.add_argument(
        "input",
        metavar="<input file with lspci -Dvmmm output>",
        type=str,
        help="input file wth lspci -Dvmmm output",
    )
    args = parser.parse_args()

    lspci_output = args.input

    if not os.path.isfile(lspci_output):
        sys.stdout.write("input file did not exist: %s\n" % (lspci_output))
        sys.exit(1)

    lspci = open(lspci_output, "r")
    all_lines = lspci.readlines()
    lspci.close()

    slot = -1
    sdevice = None
    IOMMUGroup = None
    vendor_name = None
    device_name = None

    for line in all_lines:
        line = line.strip()
        m = re.match(r"^(?P<TAG>\w+):" "(?P<STRING>.*)$", line)
        if not m:
            continue
        eval_line = m.groupdict()
        tag = eval_line["TAG"]
        data = eval_line["STRING"]
        data = data.strip()
        if tag == "Slot":
            if sdevice:
                num_candidate_devices = add_new_device(
                    slot,
                    sdevice,
                    IOMMUGroup,
                    num_candidate_devices,
                    vendor_name,
                    device_name,
                )
            slot = data
            sdevice = None
            IOMMUGroup = None
            vendor_name = None
            device_name = None
        elif tag == "SDevice":
            sdevice = data
        elif tag == "IOMMUGroup":
            IOMMUGroup = data
        elif tag == "Vendor":
            vendor_name = data
        elif tag == "Device":
            device_name = data

    # Handle the last device
    if sdevice and slot:
        num_candidate_devices = add_new_device(
            slot, sdevice, IOMMUGroup, num_candidate_devices, vendor_name, device_name
        )

    add_pcie_kconfig_string(passthrough_prefix, num_candidate_devices, "NUM_DEVICES")
    os.unlink(lspci_output)


if __name__ == "__main__":
    main()
