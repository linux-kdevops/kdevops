#!/usr/bin/env python3
"""
Enhanced eBPF-based memory fragmentation tracker.
Primary focus on mm_page_alloc_extfrag events with optional compaction tracking.
"""

from bcc import BPF
import time
import signal
import sys
import os
import json
import argparse
from collections import defaultdict
from datetime import datetime

# eBPF program to trace fragmentation events
bpf_program = """
#include <uapi/linux/ptrace.h>
#include <linux/mm.h>
#include <linux/mmzone.h>

// Event types
#define EVENT_COMPACTION_SUCCESS 1
#define EVENT_COMPACTION_FAILURE 2
#define EVENT_EXTFRAG 3

struct fragmentation_event {
    u64 timestamp;
    u32 pid;
    u32 tid;
    u8 event_type;  // 1=compact_success, 2=compact_fail, 3=extfrag

    // Common fields
    u32 order;
    int fragmentation_index;
    int zone_idx;
    int node_id;

    // ExtFrag specific fields
    int fallback_order;         // Order of the fallback allocation
    int migrate_from;           // Original migrate type
    int migrate_to;             // Fallback migrate type
    int fallback_blocks;        // Number of pageblocks involved
    int is_steal;               // Whether this is a steal vs claim

    // Process info
    char comm[16];
};

BPF_PERF_OUTPUT(events);

// Statistics tracking
BPF_HASH(extfrag_stats, u32, u64);  // Key: order, Value: count
BPF_HASH(compact_stats, u32, u64);  // Key: order|success<<16, Value: count

// Helper to get current fragmentation state (simplified)
static inline int get_fragmentation_estimate(int order) {
    // This is a simplified estimate
    // In real implementation, we'd need to walk buddy lists
    // For now, return a placeholder that indicates we need fragmentation data
    if (order <= 3) return 100;  // Low order usually OK
    if (order <= 6) return 400;  // Medium order moderate frag
    return 700;  // High order typically fragmented
}

// Trace external fragmentation events (page steal/claim from different migratetype)
TRACEPOINT_PROBE(kmem, mm_page_alloc_extfrag) {
    struct fragmentation_event event = {};

    event.timestamp = bpf_ktime_get_ns();
    event.pid = bpf_get_current_pid_tgid() >> 32;
    event.tid = bpf_get_current_pid_tgid() & 0xFFFFFFFF;
    event.event_type = EVENT_EXTFRAG;

    // Extract tracepoint arguments
    // Note: Field names may vary by kernel version
    // Typical fields: alloc_order, fallback_order,
    //                alloc_migratetype, fallback_migratetype, change_ownership

    event.order = args->alloc_order;
    event.fallback_order = args->fallback_order;
    event.migrate_from = args->fallback_migratetype;
    event.migrate_to = args->alloc_migratetype;

    // change_ownership indicates if the whole pageblock was claimed
    // 0 = steal (partial), 1 = claim (whole block)
    event.is_steal = args->change_ownership ? 0 : 1;

    // Node ID - set to -1 as page struct access is kernel-specific
    // Could be enhanced with kernel version detection
    event.node_id = -1;
    event.zone_idx = -1;

    // Estimate fragmentation at this point
    event.fragmentation_index = get_fragmentation_estimate(event.order);

    // Get process name
    bpf_get_current_comm(&event.comm, sizeof(event.comm));

    events.perf_submit(args, &event, sizeof(event));

    // Update statistics
    u64 *count = extfrag_stats.lookup(&event.order);
    if (count) {
        (*count)++;
    } else {
        u64 initial = 1;
        extfrag_stats.update(&event.order, &initial);
    }

    return 0;
}

// Optional: Trace compaction success (if tracepoint exists)
#ifdef TRACE_COMPACTION
TRACEPOINT_PROBE(page_alloc, mm_compaction_success) {
    struct fragmentation_event event = {};

    event.timestamp = bpf_ktime_get_ns();
    event.pid = bpf_get_current_pid_tgid() >> 32;
    event.tid = bpf_get_current_pid_tgid() & 0xFFFFFFFF;
    event.event_type = EVENT_COMPACTION_SUCCESS;

    event.order = args->order;
    event.fragmentation_index = args->ret;
    event.zone_idx = args->idx;
    event.node_id = args->nid;

    bpf_get_current_comm(&event.comm, sizeof(event.comm));

    events.perf_submit(args, &event, sizeof(event));

    u32 key = (event.order) | (1 << 16);  // Set success bit
    u64 *count = compact_stats.lookup(&key);
    if (count) {
        (*count)++;
    } else {
        u64 initial = 1;
        compact_stats.update(&key, &initial);
    }

    return 0;
}

TRACEPOINT_PROBE(page_alloc, mm_compaction_failure) {
    struct fragmentation_event event = {};

    event.timestamp = bpf_ktime_get_ns();
    event.pid = bpf_get_current_pid_tgid() >> 32;
    event.tid = bpf_get_current_pid_tgid() & 0xFFFFFFFF;
    event.event_type = EVENT_COMPACTION_FAILURE;

    event.order = args->order;
    event.fragmentation_index = -1;
    event.zone_idx = -1;
    event.node_id = -1;

    bpf_get_current_comm(&event.comm, sizeof(event.comm));

    events.perf_submit(args, &event, sizeof(event));

    u32 key = event.order;  // No success bit
    u64 *count = compact_stats.lookup(&key);
    if (count) {
        (*count)++;
    } else {
        u64 initial = 1;
        compact_stats.update(&key, &initial);
    }

    return 0;
}
#endif
"""

# Migrate type names for better readability
MIGRATE_TYPES = {
    0: "UNMOVABLE",
    1: "MOVABLE",
    2: "RECLAIMABLE",
    3: "PCPTYPES",
    4: "HIGHATOMIC",
    5: "CMA",
    6: "ISOLATE",
}


class FragmentationTracker:
    def __init__(self, verbose=True, output_file=None):
        self.start_time = time.time()
        self.events_data = []
        self.extfrag_stats = defaultdict(int)
        self.compact_stats = defaultdict(lambda: {"success": 0, "failure": 0})
        self.zone_names = ["DMA", "DMA32", "Normal", "Movable", "Device"]
        self.verbose = verbose
        self.output_file = output_file
        self.event_count = 0
        self.interrupted = False

    def process_event(self, cpu, data, size):
        """Process a fragmentation event from eBPF."""
        event = self.b["events"].event(data)

        # Calculate relative time from start
        rel_time = (event.timestamp - self.start_ns) / 1e9

        # Decode process name
        try:
            comm = event.comm.decode("utf-8", "replace")
        except:
            comm = "unknown"

        # Determine event type and format output
        if event.event_type == 3:  # EXTFRAG event
            event_name = "EXTFRAG"
            color = "\033[93m"  # Yellow

            # Get migrate type names
            from_type = MIGRATE_TYPES.get(
                event.migrate_from, f"TYPE_{event.migrate_from}"
            )
            to_type = MIGRATE_TYPES.get(event.migrate_to, f"TYPE_{event.migrate_to}")

            # Store event data
            event_dict = {
                "timestamp": rel_time,
                "absolute_time": datetime.now().isoformat(),
                "event_type": "extfrag",
                "pid": event.pid,
                "tid": event.tid,
                "comm": comm,
                "order": event.order,
                "fallback_order": event.fallback_order,
                "migrate_from": from_type,
                "migrate_to": to_type,
                "is_steal": bool(event.is_steal),
                "node": event.node_id,
                "fragmentation_index": event.fragmentation_index,
            }

            self.extfrag_stats[event.order] += 1

            if self.verbose:
                action = "steal" if event.is_steal else "claim"
                print(
                    f"{color}[{rel_time:8.3f}s] {event_name:10s}\033[0m "
                    f"Order={event.order:2d} FallbackOrder={event.fallback_order:2d} "
                    f"{from_type:10s}->{to_type:10s} ({action}) "
                    f"Process={comm:12s} PID={event.pid:6d}"
                )

        elif event.event_type == 1:  # COMPACTION_SUCCESS
            event_name = "COMPACT_OK"
            color = "\033[92m"  # Green

            zone_name = (
                self.zone_names[event.zone_idx]
                if 0 <= event.zone_idx < len(self.zone_names)
                else "Unknown"
            )

            event_dict = {
                "timestamp": rel_time,
                "absolute_time": datetime.now().isoformat(),
                "event_type": "compaction_success",
                "pid": event.pid,
                "comm": comm,
                "order": event.order,
                "fragmentation_index": event.fragmentation_index,
                "zone": zone_name,
                "node": event.node_id,
            }

            self.compact_stats[event.order]["success"] += 1

            if self.verbose:
                print(
                    f"{color}[{rel_time:8.3f}s] {event_name:10s}\033[0m "
                    f"Order={event.order:2d} FragIdx={event.fragmentation_index:5d} "
                    f"Zone={zone_name:8s} Node={event.node_id:2d} "
                    f"Process={comm:12s} PID={event.pid:6d}"
                )

        else:  # COMPACTION_FAILURE
            event_name = "COMPACT_FAIL"
            color = "\033[91m"  # Red

            event_dict = {
                "timestamp": rel_time,
                "absolute_time": datetime.now().isoformat(),
                "event_type": "compaction_failure",
                "pid": event.pid,
                "comm": comm,
                "order": event.order,
                "fragmentation_index": -1,
            }

            self.compact_stats[event.order]["failure"] += 1

            if self.verbose:
                print(
                    f"{color}[{rel_time:8.3f}s] {event_name:10s}\033[0m "
                    f"Order={event.order:2d} "
                    f"Process={comm:12s} PID={event.pid:6d}"
                )

        self.events_data.append(event_dict)
        self.event_count += 1

    def print_summary(self):
        """Print summary statistics."""
        print("\n" + "=" * 80)
        print("FRAGMENTATION TRACKING SUMMARY")
        print("=" * 80)

        total_events = len(self.events_data)
        print(f"\nTotal events captured: {total_events}")

        if total_events > 0:
            # Count by type
            extfrag_count = sum(
                1 for e in self.events_data if e["event_type"] == "extfrag"
            )
            compact_success = sum(
                1 for e in self.events_data if e["event_type"] == "compaction_success"
            )
            compact_fail = sum(
                1 for e in self.events_data if e["event_type"] == "compaction_failure"
            )

            print(f"\nEvent breakdown:")
            print(f"  External Fragmentation: {extfrag_count}")
            print(f"  Compaction Success: {compact_success}")
            print(f"  Compaction Failure: {compact_fail}")

            # ExtFrag analysis
            if extfrag_count > 0:
                print("\nExternal Fragmentation Events by Order:")
                print("-" * 40)
                print(f"{'Order':<8} {'Count':<10} {'Percentage':<10}")
                print("-" * 40)

                for order in sorted(self.extfrag_stats.keys()):
                    count = self.extfrag_stats[order]
                    pct = (count / extfrag_count) * 100
                    print(f"{order:<8} {count:<10} {pct:<10.1f}%")

                # Analyze migrate type patterns
                extfrag_events = [
                    e for e in self.events_data if e["event_type"] == "extfrag"
                ]
                migrate_patterns = defaultdict(int)
                steal_vs_claim = {"steal": 0, "claim": 0}

                for e in extfrag_events:
                    pattern = f"{e['migrate_from']}->{e['migrate_to']}"
                    migrate_patterns[pattern] += 1
                    if e["is_steal"]:
                        steal_vs_claim["steal"] += 1
                    else:
                        steal_vs_claim["claim"] += 1

                print("\nMigrate Type Patterns:")
                print("-" * 40)
                for pattern, count in sorted(
                    migrate_patterns.items(), key=lambda x: x[1], reverse=True
                )[:5]:
                    print(
                        f"  {pattern:<30} {count:5d} ({count/extfrag_count*100:5.1f}%)"
                    )

                print(f"\nSteal vs Claim:")
                print(
                    f"  Steal (partial): {steal_vs_claim['steal']} ({steal_vs_claim['steal']/extfrag_count*100:.1f}%)"
                )
                print(
                    f"  Claim (whole):   {steal_vs_claim['claim']} ({steal_vs_claim['claim']/extfrag_count*100:.1f}%)"
                )

            # Compaction analysis
            if self.compact_stats:
                print("\nCompaction Events by Order:")
                print("-" * 40)
                print(
                    f"{'Order':<8} {'Success':<10} {'Failure':<10} {'Total':<10} {'Success%':<10}"
                )
                print("-" * 40)

                for order in sorted(self.compact_stats.keys()):
                    stats = self.compact_stats[order]
                    total = stats["success"] + stats["failure"]
                    success_pct = (stats["success"] / total * 100) if total > 0 else 0
                    print(
                        f"{order:<8} {stats['success']:<10} {stats['failure']:<10} "
                        f"{total:<10} {success_pct:<10.1f}"
                    )

    def save_data(self, filename=None):
        """Save captured data to JSON file for visualization."""
        if filename is None and self.output_file:
            filename = self.output_file

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fragmentation_data_{timestamp}.json"

        # Prepare statistics
        stats = {}

        # ExtFrag stats
        stats["extfrag"] = dict(self.extfrag_stats)

        # Compaction stats
        stats["compaction"] = {}
        for order, counts in self.compact_stats.items():
            stats["compaction"][str(order)] = counts

        output = {
            "metadata": {
                "start_time": self.start_time,
                "end_time": time.time(),
                "duration": time.time() - self.start_time,
                "total_events": len(self.events_data),
                "kernel_version": os.uname().release,
            },
            "events": self.events_data,
            "statistics": stats,
        }

        with open(filename, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nData saved to {filename}")
        return filename

    def run(self):
        """Main execution loop."""
        print("Compiling eBPF program...")

        # Check if compaction tracepoints are available
        has_compaction = os.path.exists(
            "/sys/kernel/debug/tracing/events/page_alloc/mm_compaction_success"
        )

        # Modify BPF program based on available tracepoints
        program = bpf_program
        if has_compaction:
            program = program.replace("#ifdef TRACE_COMPACTION", "#if 1")
            print("  Compaction tracepoints: AVAILABLE")
        else:
            program = program.replace("#ifdef TRACE_COMPACTION", "#if 0")
            print("  Compaction tracepoints: NOT AVAILABLE (will track extfrag only)")

        self.b = BPF(text=program)
        self.start_ns = time.perf_counter_ns()

        # Setup event handler
        self.b["events"].open_perf_buffer(self.process_event)

        # Determine output filename upfront
        if self.output_file:
            save_file = self.output_file
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_file = f"fragmentation_data_{timestamp}.json"

        print("\nStarting fragmentation event tracking...")
        print(f"Primary focus: mm_page_alloc_extfrag events")
        print(f"Data will be saved to: {save_file}")
        print("Press Ctrl+C to stop and see summary\n")
        print("-" * 80)
        print(f"{'Time':>10s} {'Event':>12s} {'Details'}")
        print("-" * 80)

        try:
            while not self.interrupted:
                self.b.perf_buffer_poll()
        except KeyboardInterrupt:
            self.interrupted = True
        finally:
            # Always save data on exit
            self.print_summary()
            self.save_data()


def main():
    parser = argparse.ArgumentParser(
        description="Track memory fragmentation events using eBPF"
    )
    parser.add_argument("-o", "--output", help="Output JSON file")
    parser.add_argument(
        "-t", "--time", type=int, help="Run for specified seconds then exit"
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress event output (summary only)",
    )

    args = parser.parse_args()

    # Check for root privileges
    if os.geteuid() != 0:
        print("This script must be run as root (uses eBPF)")
        sys.exit(1)

    # Create tracker instance
    tracker = FragmentationTracker(verbose=not args.quiet, output_file=args.output)

    # Set up signal handler
    def signal_handler_with_tracker(sig, frame):
        tracker.interrupted = True

    signal.signal(signal.SIGINT, signal_handler_with_tracker)

    if args.time:
        # Run for specified time
        import threading

        def timeout_handler():
            time.sleep(args.time)
            tracker.interrupted = True

        timer = threading.Thread(target=timeout_handler)
        timer.daemon = True
        timer.start()

    tracker.run()


if __name__ == "__main__":
    main()
