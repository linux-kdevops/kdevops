// SPDX-License-Identifier: GPL-2.0
/*
 * iobuf_bench - A/B microbenchmark for blk_iobuf_pool io_uring fixed buffers.
 *
 * Drives an identical O_DIRECT io_uring workload against a block device using
 * two buffer sources, isolating the effect of the pool's higher-order folios:
 *
 *   mode=pool   : fixed buffers allocated from the device's blk_iobuf_pool via
 *                 IORING_REGISTER_BUFFERS_ALLOC_FOR_FILE (opcode 38). Each buffer
 *                 is one (or few) large contiguous folios -> few bio segments.
 *   mode=malloc : fixed buffers from posix_memalign + IORING_REGISTER_BUFFERS.
 *                 Backed by ordinary (possibly fragmented) pages.
 *   mode=mallocnh: like malloc but MADV_NOHUGEPAGE (worst-case fragmentation).
 *
 * Same device, same queue depth, same block size, same offsets: the only
 * variable is the physical layout of the registered buffer. Reports IOPS,
 * bandwidth, latency percentiles, and CPU (process + system-wide) as JSON.
 *
 * Raw syscalls only (no liburing dependency).
 *
 *   ./iobuf_bench <dev> <pool|malloc|mallocnh> <read|write|randread|randwrite> \
 *                 <bs_bytes> <qd> <secs>
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/uio.h>
#include <linux/fs.h>
#include <linux/io_uring.h>

#ifndef IORING_REGISTER_BUFFERS_ALLOC_FOR_FILE
#define IORING_REGISTER_BUFFERS_ALLOC_FOR_FILE 38
#endif
#ifndef IORING_BUF_ALLOC_READ
#define IORING_BUF_ALLOC_READ  (1U << 3)
#define IORING_BUF_ALLOC_WRITE (1U << 4)
#endif

struct io_uring_buf_alloc_for_file {
	__u32 fd, index, nr_buffers, flags;
	__u64 buffer_size;
	__u32 min_order, pref_order, reserved[2];
};

static int io_uring_setup(unsigned e, struct io_uring_params *p)
{ return syscall(__NR_io_uring_setup, e, p); }
static int io_uring_register(int fd, unsigned op, void *a, unsigned n)
{ return syscall(__NR_io_uring_register, fd, op, a, n); }
static int io_uring_enter(int fd, unsigned ts, unsigned mc, unsigned fl)
{ return syscall(__NR_io_uring_enter, fd, ts, mc, fl, NULL, 0); }

/* SQ/CQ ring shared pointers */
static unsigned *sq_tail, *sq_mask, *sq_array;
static unsigned *cq_head, *cq_tail, *cq_mask;
static struct io_uring_cqe *cqes;
static struct io_uring_sqe *sqes;

static uint64_t now_ns(void)
{
	struct timespec t;
	clock_gettime(CLOCK_MONOTONIC, &t);
	return (uint64_t)t.tv_sec * 1000000000ull + t.tv_nsec;
}

/* read total non-idle CPU ns across all guest CPUs from /proc/stat */
static uint64_t proc_stat_busy_ns(void)
{
	FILE *f = fopen("/proc/stat", "r");
	if (!f)
		return 0;
	unsigned long u, n, s, idle, iow, irq, sirq, st = 0;
	int r = fscanf(f, "cpu  %lu %lu %lu %lu %lu %lu %lu %lu",
		       &u, &n, &s, &idle, &iow, &irq, &sirq, &st);
	fclose(f);
	if (r < 7)
		return 0;
	long hz = sysconf(_SC_CLK_TCK);
	uint64_t busy = u + n + s + irq + sirq + st;  /* exclude idle+iowait */
	return busy * (1000000000ull / (hz ? hz : 100));
}

/* log2(ns) histogram for percentiles */
#define NBKT 48
static uint64_t hist[NBKT];
static void hist_add(uint64_t ns)
{
	int b = 0;
	while (ns > 1 && b < NBKT - 1) { ns >>= 1; b++; }
	hist[b]++;
}
static uint64_t hist_pct(uint64_t total, double p)
{
	uint64_t want = (uint64_t)(total * p), acc = 0;
	for (int b = 0; b < NBKT; b++) {
		acc += hist[b];
		if (acc >= want)
			return 1ull << b;   /* upper bound of bucket */
	}
	return 1ull << (NBKT - 1);
}

static uint64_t xs[256];  /* per-slot xorshift state for random offsets */
static uint64_t xorshift(uint64_t *s)
{
	uint64_t x = *s;
	x ^= x << 13; x ^= x >> 7; x ^= x << 17;
	return *s = x;
}

int main(int argc, char **argv)
{
	if (argc < 7) {
		fprintf(stderr, "usage: %s <dev> <pool|malloc|mallocnh> "
			"<read|write|randread|randwrite> <bs> <qd> <secs>\n", argv[0]);
		return 2;
	}
	const char *dev = argv[1], *mode = argv[2], *rw = argv[3];
	size_t bs = strtoul(argv[4], NULL, 0);
	unsigned qd = strtoul(argv[5], NULL, 0);
	unsigned secs = strtoul(argv[6], NULL, 0);
	/* optional: limit offsets to first <span_mb> MiB (0 = whole device).
	 * Small span -> cache-resident/CPU-bound; large span -> device-bound. */
	uint64_t span_mb = argc > 7 ? strtoull(argv[7], NULL, 0) : 0;
	/* optional: shift this run's region by <span_off_mb> MiB. Lets N parallel
	 * instances work disjoint cache-resident regions for multi-core scaling. */
	uint64_t span_off_mb = argc > 8 ? strtoull(argv[8], NULL, 0) : 0;
	int is_write = (strstr(rw, "write") != NULL);
	int is_rand  = (strstr(rw, "rand")  != NULL);
	int is_pool  = !strcmp(mode, "pool");
	int is_nh    = !strcmp(mode, "mallocnh");

	if (qd > 256) qd = 256;
	if (bs % 16384) {
		fprintf(stderr, "bs must be a multiple of 16384 (LBS)\n");
		return 2;
	}

	int dev_fd = open(dev, O_RDWR | O_DIRECT);
	if (dev_fd < 0) { perror("open dev"); return 1; }
	uint64_t dev_sz = 0;
	if (ioctl(dev_fd, BLKGETSIZE64, &dev_sz)) { perror("BLKGETSIZE64"); return 1; }
	uint64_t nblocks = dev_sz / bs;
	uint64_t base_block = (span_off_mb << 20) / bs;   /* region start offset */
	if (span_mb) {
		uint64_t span_blocks = (span_mb << 20) / bs;
		if (span_blocks && span_blocks < nblocks)
			nblocks = span_blocks;
	}
	if (base_block + nblocks > dev_sz / bs) {
		fprintf(stderr, "span_off+span exceeds device\n");
		return 1;
	}
	if (nblocks < qd * 4) { fprintf(stderr, "device too small\n"); return 1; }

	/* io_uring setup */
	struct io_uring_params p = {0};
	int ring = io_uring_setup(qd * 2 < 8 ? 8 : qd * 2, &p);
	if (ring < 0) { perror("io_uring_setup"); return 1; }

	size_t sqring_sz = p.sq_off.array + p.sq_entries * sizeof(unsigned);
	size_t cqring_sz = p.cq_off.cqes + p.cq_entries * sizeof(struct io_uring_cqe);
	int single_mmap = (p.features & IORING_FEAT_SINGLE_MMAP);
	if (single_mmap) {
		if (cqring_sz > sqring_sz) sqring_sz = cqring_sz;
		cqring_sz = sqring_sz;
	}
	void *sq = mmap(0, sqring_sz, PROT_READ | PROT_WRITE,
			MAP_SHARED | MAP_POPULATE, ring, IORING_OFF_SQ_RING);
	void *cq = single_mmap ? sq :
		mmap(0, cqring_sz, PROT_READ | PROT_WRITE,
		     MAP_SHARED | MAP_POPULATE, ring, IORING_OFF_CQ_RING);
	sqes = mmap(0, p.sq_entries * sizeof(struct io_uring_sqe),
		    PROT_READ | PROT_WRITE, MAP_SHARED | MAP_POPULATE,
		    ring, IORING_OFF_SQES);
	if (sq == MAP_FAILED || cq == MAP_FAILED || sqes == MAP_FAILED) {
		perror("mmap ring"); return 1;
	}
	sq_tail  = sq + p.sq_off.tail;
	sq_mask  = sq + p.sq_off.ring_mask;
	sq_array = sq + p.sq_off.array;
	cq_head  = cq + p.cq_off.head;
	cq_tail  = cq + p.cq_off.tail;
	cq_mask  = cq + p.cq_off.ring_mask;
	cqes     = cq + p.cq_off.cqes;

	/* Register qd fixed-buffer slots, one buffer per in-flight I/O. */
	void **ubuf = calloc(qd, sizeof(void *));
	if (is_pool) {
		struct iovec *iov = calloc(qd, sizeof(*iov));   /* sparse table */
		if (io_uring_register(ring, IORING_REGISTER_BUFFERS, iov, qd)) {
			perror("REGISTER_BUFFERS(sparse)"); return 1;
		}
		for (unsigned i = 0; i < qd; i++) {
			struct io_uring_buf_alloc_for_file req = {
				.fd = (unsigned)dev_fd, .index = i, .nr_buffers = 1,
				/* direction must match the op: READ->DEST, WRITE->SOURCE */
				.flags = is_write ? IORING_BUF_ALLOC_WRITE
						  : IORING_BUF_ALLOC_READ,
				.buffer_size = bs,
			};
			if (io_uring_register(ring,
				IORING_REGISTER_BUFFERS_ALLOC_FOR_FILE, &req, 1)) {
				fprintf(stderr, "{\"error\":\"pool register slot %u: %s\","
					"\"mode\":\"pool\",\"bs\":%zu,\"qd\":%u}\n",
					i, strerror(errno), bs, qd);
				return 3;
			}
		}
	} else {
		struct iovec *iov = calloc(qd, sizeof(*iov));
		for (unsigned i = 0; i < qd; i++) {
			if (posix_memalign(&ubuf[i], 16384, bs)) {
				perror("posix_memalign"); return 1;
			}
			if (is_nh)
				madvise(ubuf[i], bs, MADV_NOHUGEPAGE);
			memset(ubuf[i], 0xa5, bs);   /* fault in, defeat THP merge for nh */
			iov[i].iov_base = ubuf[i];
			iov[i].iov_len  = bs;
		}
		if (io_uring_register(ring, IORING_REGISTER_BUFFERS, iov, qd)) {
			perror("REGISTER_BUFFERS"); return 1;
		}
	}

	for (unsigned i = 0; i < qd; i++)
		xs[i] = 0x9e3779b97f4a7c15ull ^ ((uint64_t)(i + 1) * 0x2545F4914F6CDD1Dull);

	uint64_t seq = 0;                /* sequential cursor in blocks */
	uint64_t *submit_t = calloc(qd, sizeof(uint64_t));
	uint8_t opcode = is_write ? IORING_OP_WRITE_FIXED : IORING_OP_READ_FIXED;

	/* prep one sqe for slot i */
	#define PREP(i) do {                                                      \
		unsigned _idx = (i);                                              \
		uint64_t _blk = base_block + (is_rand ?                           \
					(xorshift(&xs[_idx]) % nblocks) :         \
					(seq++ % nblocks));                      \
		struct io_uring_sqe *s = &sqes[_idx];                            \
		memset(s, 0, sizeof(*s));                                        \
		s->opcode = opcode;                                              \
		s->fd = dev_fd;                                                  \
		s->off = _blk * bs;                                             \
		s->addr = is_pool ? 0 : (uint64_t)(uintptr_t)ubuf[_idx];         \
		s->len = bs;                                                     \
		s->buf_index = _idx;                                            \
		s->user_data = _idx;                                            \
		submit_t[_idx] = now_ns();                                      \
		sq_array[(*sq_tail) & (*sq_mask)] = _idx;                       \
		__atomic_store_n(sq_tail, (*sq_tail) + 1, __ATOMIC_RELEASE);     \
	} while (0)

	/* prime the pipeline */
	for (unsigned i = 0; i < qd; i++)
		PREP(i);
	unsigned to_submit = qd;

	struct rusage ru0, ru1;
	getrusage(RUSAGE_SELF, &ru0);
	uint64_t sys0 = proc_stat_busy_ns();
	uint64_t start = now_ns(), deadline = start + (uint64_t)secs * 1000000000ull;
	uint64_t ops = 0, bytes = 0, lat_sum = 0, lat_min = ~0ull, lat_max = 0, errs = 0;

	while (now_ns() < deadline) {
		int r = io_uring_enter(ring, to_submit, 1, IORING_ENTER_GETEVENTS);
		if (r < 0) {
			if (errno == EINTR) { to_submit = 0; continue; }
			perror("io_uring_enter"); break;
		}
		to_submit = 0;
		unsigned head = __atomic_load_n(cq_head, __ATOMIC_ACQUIRE);
		unsigned tail = __atomic_load_n(cq_tail, __ATOMIC_ACQUIRE);
		uint64_t tnow = now_ns();
		while (head != tail) {
			struct io_uring_cqe *c = &cqes[head & (*cq_mask)];
			unsigned slot = c->user_data;
			if (c->res < 0) errs++;
			else { ops++; bytes += c->res; }
			uint64_t lat = tnow - submit_t[slot];
			lat_sum += lat;
			if (lat < lat_min) lat_min = lat;
			if (lat > lat_max) lat_max = lat;
			hist_add(lat);
			head++;
			/* refill this slot */
			if (now_ns() < deadline) { PREP(slot); to_submit++; }
		}
		__atomic_store_n(cq_head, head, __ATOMIC_RELEASE);
	}
	uint64_t elapsed = now_ns() - start;
	getrusage(RUSAGE_SELF, &ru1);
	uint64_t sys1 = proc_stat_busy_ns();

	double secs_f = elapsed / 1e9;
	double iops = ops / secs_f;
	double mbs = (bytes / 1048576.0) / secs_f;
	uint64_t proc_ns =
		((uint64_t)(ru1.ru_utime.tv_sec - ru0.ru_utime.tv_sec) * 1000000000ull
		 + (ru1.ru_utime.tv_usec - ru0.ru_utime.tv_usec) * 1000ull) +
		((uint64_t)(ru1.ru_stime.tv_sec - ru0.ru_stime.tv_sec) * 1000000000ull
		 + (ru1.ru_stime.tv_usec - ru0.ru_stime.tv_usec) * 1000ull);
	uint64_t stime_ns =
		(uint64_t)(ru1.ru_stime.tv_sec - ru0.ru_stime.tv_sec) * 1000000000ull
		+ (ru1.ru_stime.tv_usec - ru0.ru_stime.tv_usec) * 1000ull;
	uint64_t sysbusy_ns = sys1 - sys0;

	printf("{\"mode\":\"%s\",\"rw\":\"%s\",\"bs\":%zu,\"qd\":%u,"
	       "\"span_mb\":%llu,"
	       "\"secs\":%.3f,\"ops\":%llu,\"errs\":%llu,"
	       "\"iops\":%.1f,\"mb_s\":%.2f,"
	       "\"lat_min_ns\":%llu,\"lat_mean_ns\":%llu,\"lat_max_ns\":%llu,"
	       "\"p50_ns\":%llu,\"p99_ns\":%llu,\"p999_ns\":%llu,"
	       "\"proc_cpu_ns\":%llu,\"proc_stime_ns\":%llu,\"sys_busy_ns\":%llu,"
	       "\"cpu_per_io_ns\":%.1f,\"sys_per_io_ns\":%.1f}\n",
	       mode, rw, bs, qd, (unsigned long long)span_mb, secs_f,
	       (unsigned long long)ops, (unsigned long long)errs,
	       iops, mbs,
	       (unsigned long long)(lat_min == ~0ull ? 0 : lat_min),
	       (unsigned long long)(ops ? lat_sum / ops : 0),
	       (unsigned long long)lat_max,
	       (unsigned long long)hist_pct(ops, 0.50),
	       (unsigned long long)hist_pct(ops, 0.99),
	       (unsigned long long)hist_pct(ops, 0.999),
	       (unsigned long long)proc_ns, (unsigned long long)stime_ns,
	       (unsigned long long)sysbusy_ns,
	       ops ? (double)proc_ns / ops : 0.0,
	       ops ? (double)sysbusy_ns / ops : 0.0);
	return errs ? 4 : 0;
}
