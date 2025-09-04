#!/usr/bin/env python3
"""
Create a snapshot of fragmentation monitoring data.
This script safely stops the fragmentation tracker, saves its data,
and restarts it with a new output file.
"""

import os
import sys
import time
import signal
import subprocess
import json
from pathlib import Path
from datetime import datetime


def get_pid_from_file(pid_file):
    """Read PID from file."""
    try:
        with open(pid_file, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def is_process_running(pid):
    """Check if a process is running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def stop_tracker_and_save(pid):
    """Stop the tracker gracefully and wait for it to save data."""
    try:
        # Send INT signal to trigger save
        os.kill(pid, signal.SIGINT)

        # Wait indefinitely for process to exit
        print(f"Sent INT signal to tracker PID {pid}, waiting for it to save data...")
        while is_process_running(pid):
            time.sleep(0.1)

        print(f"Tracker PID {pid} has exited successfully")
        return True
    except Exception as e:
        print(f"Error stopping tracker: {e}", file=sys.stderr)
        return False


def find_latest_json(output_dir):
    """Find the most recently created JSON file in the directory."""
    json_files = list(Path(output_dir).glob("fragmentation_data*.json"))
    if not json_files:
        return None

    # Sort by modification time
    json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return json_files[0]


def start_new_tracker(output_dir):
    """Start a new fragmentation tracker process."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_output = f"{output_dir}/fragmentation_data_{timestamp}.json"
    log_file = f"{output_dir}/fragmentation_tracker.log"
    pid_file = f"{output_dir}/fragmentation_tracker.pid"

    cmd = ["python3", "/opt/fragmentation/fragmentation_tracker.py", "-o", new_output]

    # Start the process in the background
    with open(log_file, "a") as log:
        process = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd="/opt/fragmentation",
            start_new_session=True,
        )

    # Save the PID
    with open(pid_file, "w") as f:
        f.write(str(process.pid))

    return process.pid


def create_snapshot(output_dir):
    """Main function to create fragmentation data snapshot."""
    output_dir = Path(output_dir)
    pid_file = output_dir / "fragmentation_tracker.pid"
    snapshot_file = output_dir / "fragmentation_snapshot.json"

    # Check if tracker is running
    pid = get_pid_from_file(pid_file)
    if not pid:
        print("no_pid_file")
        return 1

    if not is_process_running(pid):
        print("not_running")
        return 1

    print(f"Stopping tracker (PID: {pid})...")

    # Stop the tracker to make it save data
    if not stop_tracker_and_save(pid):
        print("failed_to_stop")
        return 1

    # Find the saved JSON file
    time.sleep(0.5)  # Give filesystem time to sync
    latest_json = find_latest_json(output_dir)

    if latest_json:
        # Create snapshot
        try:
            # Copy the file content (not just rename) to preserve original
            with open(latest_json, "r") as src:
                data = json.load(src)
            with open(snapshot_file, "w") as dst:
                json.dump(data, dst, indent=2)
            print(f"Snapshot created from {latest_json.name}")
        except Exception as e:
            print(f"Error creating snapshot: {e}", file=sys.stderr)
            return 1
    else:
        print("no_json_found")
        return 1

    # Start a new tracker
    new_pid = start_new_tracker(output_dir)
    print(f"Started new tracker (PID: {new_pid})")

    return 0


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: fragmentation_snapshot.py <output_dir>", file=sys.stderr)
        sys.exit(1)

    output_dir = sys.argv[1]
    sys.exit(create_snapshot(output_dir))


if __name__ == "__main__":
    main()
