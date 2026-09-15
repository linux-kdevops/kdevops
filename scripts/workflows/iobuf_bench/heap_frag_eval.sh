#!/bin/bash
# Does the dma-buf system heap still get 2 MiB chunks when memory is
# fragmented?  Records /proc/buddyinfo, allocates HEAP_TOTAL bytes from
# /dev/dma_heap/system in HEAP_CHUNK pieces while tracing kmem:mm_page_alloc
# for the allocating process, and reports the achieved chunk-order
# distribution and the order-9 failure count.  Runs once on the host as it
# is, then again after a fragmenter pins most of free memory and punches
# 4 KiB holes into it (movable memory, but the heap allocates with
# __GFP_NORETRY and no reclaim, so it does not compact its way out).
#
# usage: sudo ./heap_frag_eval.sh [heap_total_bytes] [heap_chunk_bytes] [frag_fraction]
set -u
TOTAL=${1:-$((1<<30))}; CHUNK=${2:-$((32<<20))}; FRAC=${3:-70}
T=/sys/kernel/tracing
here=$(dirname "$(readlink -f "$0")")

buddy() { awk '/Normal|DMA32/ { printf "  %-6s", $4; for (i=5;i<=NF;i++) printf " o%d=%s", i-5, $i; printf "\n" }' /proc/buddyinfo; }

heap_alloc() { # allocate and hold TOTAL bytes of heap memory in CHUNK pieces, tracing every order >= 4 attempt
  local ev=$T/events/kmem/mm_page_alloc
  # Only the large orders are traced (the heap's ladder is 9, 8, 4, 0): that
  # keeps the ring buffer small enough never to drop an event, and the bytes
  # that did not come from an order >= 4 block are the order-0 remainder.
  echo 16384 > $T/buffer_size_kb
  echo > $T/trace
  echo 'comm == "python3" && order >= 4' > $ev/filter
  echo 1 > $ev/enable; echo 1 > $T/tracing_on
  python3 - "$TOTAL" "$CHUNK" <<'EOF2'
import fcntl, os, struct, sys, time
total, chunk = int(sys.argv[1]), int(sys.argv[2])
heap = os.open("/dev/dma_heap/system", os.O_RDONLY | os.O_CLOEXEC)
fds = []
t0 = time.perf_counter()
for i in range(total // chunk):
    req = bytearray(struct.pack("QIIQ", chunk, 0, os.O_RDWR | os.O_CLOEXEC, 0))
    fcntl.ioctl(heap, 0xC0184800, req)
    fds.append(struct.unpack("QIIQ", bytes(req))[1])
t1 = time.perf_counter()
print(f"  heap: {len(fds)} x {chunk >> 20} MiB allocated in {1e3 * (t1 - t0):.1f} ms ({(t1 - t0) * 1e3 / max(1, len(fds)):.2f} ms per chunk)")
for fd in fds: os.close(fd)
EOF2
  echo 0 > $T/tracing_on; echo 0 > $ev/enable
  grep -E "entries-in-buffer|overrun" $T/per_cpu/cpu0/stats >/dev/null 2>&1 && awk -F: '/overrun/ && $2+0 > 0 {print "  WARNING: ring buffer overrun on a cpu"}' $T/per_cpu/cpu*/stats | sort -u
  awk -v total=$TOTAL '
    /mm_page_alloc/ { match($0, /order=[0-9]+/); o = substr($0, RSTART+6, RLENGTH-6)+0;
      if ($0 ~ /pfn=-1|pfn=0xffffffffffffffff|page=\(nil\)|page=0x0 |page=0000000000000000/) fail[o]++; else ok[o]++ }
    END { printf "  achieved:"; bytes = 0;
      for (o = 10; o >= 4; o--) if (ok[o]) { printf " order%d x%d (%d MiB)", o, ok[o], ok[o]*4096*2^o/1048576; bytes += ok[o]*4096*2^o }
      rem = total - bytes; if (rem < 0) rem = 0;
      printf " order<4 remainder %d MiB\n", rem/1048576
      printf "  failed order-9 attempts: %d (order-8: %d)\n", fail[9]+0, fail[8]+0
      printf "  share of bytes in 2 MiB chunks: %.1f%%\n", (ok[9]*4096*512) * 100 / total }' $T/trace
  echo 0 > $ev/filter
}

echo "== kernel $(uname -r), MemFree $(awk '/MemFree/ {print int($2/1024)" MiB"}' /proc/meminfo)"
echo "-- buddyinfo before (free blocks per order)"; buddy
echo "-- heap allocation on the host as it is"
heap_alloc

echo "-- fragmenting: pin ${FRAC}% of free memory, punch 4 KiB holes into every other page"
"$here"/fragmenter $FRAC &
FP=$!
sleep 3
echo "   MemFree now $(awk '/MemFree/ {print int($2/1024)" MiB"}' /proc/meminfo)"
echo "-- buddyinfo fragmented"; buddy
echo "-- heap allocation under fragmentation"
heap_alloc
kill $FP 2>/dev/null; wait $FP 2>/dev/null
echo "-- buddyinfo after release"; buddy
