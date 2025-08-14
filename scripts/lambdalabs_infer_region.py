#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Smart region inference for Lambda Labs.
Uses the smart inference algorithm to find the best region for a given instance type.
"""

import sys
import os

# Import the smart inference module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lambdalabs_smart_inference import get_best_instance_and_region


def main():
    """Main function for command-line usage."""
    if len(sys.argv) != 2:
        print("us-east-1")  # Default
        sys.exit(0)

    # The instance type is passed but we'll get the best region from smart inference
    # This maintains backward compatibility while using the smart algorithm
    instance_type_requested = sys.argv[1]

    # Get the best instance and region combo
    best_instance, best_region = get_best_instance_and_region()

    # For now, just return the best region
    # In the future, we could check if the requested instance is available in the best region
    print(best_region)


if __name__ == "__main__":
    main()
