#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1
"""
Smart region inference for Lambda Labs.

This is a thin wrapper around lambda-cli for backward compatibility
with existing Kconfig shell commands.
"""

import sys
import subprocess
import json
import os

def get_best_region_for_instance(instance_type):
    """Get best region for a specific instance type using lambda-cli"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cli_path = os.path.join(script_dir, 'lambda-cli')
    
    try:
        # First try to get regions where this instance is available
        result = subprocess.run(
            [cli_path, '--output', 'json', 'instance-types', 'list'],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            instances = json.loads(result.stdout)
            for instance in instances:
                if instance.get('name') == instance_type:
                    # This instance exists, try smart selection
                    smart_result = subprocess.run(
                        [cli_path, '--output', 'json', 'smart-select', '--mode', 'cheapest'],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if smart_result.returncode == 0:
                        data = json.loads(smart_result.stdout)
                        if 'error' not in data:
                            return data.get('region', 'us-west-1')
    except (subprocess.SubprocessError, json.JSONDecodeError):
        pass
    
    # Return default if lambda-cli fails
    return 'us-west-1'

def main():
    """Main function for command-line usage."""
    if len(sys.argv) != 2:
        print("us-west-1")  # Default
        sys.exit(0)
    
    instance_type = sys.argv[1]
    region = get_best_region_for_instance(instance_type)
    print(region)

if __name__ == "__main__":
    main()