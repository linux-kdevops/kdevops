#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1
"""
Lambda Labs smart inference for Kconfig.

This is a thin wrapper around lambda-cli for backward compatibility
with existing Kconfig shell commands.
"""

import sys
import subprocess
import json
import os

def get_smart_selection():
    """Get smart selection from lambda-cli"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cli_path = os.path.join(script_dir, 'lambda-cli')
    
    try:
        result = subprocess.run(
            [cli_path, '--output', 'json', 'smart-select', '--mode', 'cheapest'],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if 'error' not in data:
                return data
    except (subprocess.SubprocessError, json.JSONDecodeError):
        pass
    
    # Return defaults if lambda-cli fails
    return {
        'instance_type': 'gpu_1x_a10',
        'region': 'us-west-1',
        'price_per_hour': '$0.75'
    }

def main():
    """Main entry point for Kconfig shell commands"""
    if len(sys.argv) < 2:
        print("Usage: lambdalabs_smart_inference.py [instance|region|price]")
        sys.exit(1)
    
    query_type = sys.argv[1]
    selection = get_smart_selection()
    
    if query_type == 'instance':
        print(selection.get('instance_type', 'gpu_1x_a10'))
    elif query_type == 'region':
        print(selection.get('region', 'us-west-1'))
    elif query_type == 'price':
        print(selection.get('price_per_hour', '$0.75'))
    else:
        print(f"Unknown query type: {query_type}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()