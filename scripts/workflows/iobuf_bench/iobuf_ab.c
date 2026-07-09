// SPDX-License-Identifier: GPL-2.0
// blk_iobuf_pool op-38 A/B: same io_uring ReadFixed loop on a block device,
// buffer from the queue folio pool (op 38, arm B) vs an ordinary user buffer
// (op 0, arm A). Pool is the only variable.
//   ./iobuf_ab <blockdev> <buffer_size> <nr_ops> <use_pool 0|1>
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <liburing.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/syscall.h>

#ifndef IORING_REGISTER_BUFFERS_ALLOC_FOR_FILE
#define IORING_REGISTER_BUFFERS_ALLOC_FOR_FILE 38
#endif
#define IORING_BUF_ALLOC_REQUIRE_QUEUE_POOL (1U << 1)
#define IORING_BUF_ALLOC_ALLOW_FALLBACK     (1U << 2)
#define IORING_BUF_ALLOC_READ               (1U << 3)
#define IORING_BUF_ALLOC_WRITE              (1U << 4)

struct io_uring_buf_alloc_for_file {
	uint32_t fd, index, nr_buffers, flags;
	uint64_t buffer_size;
	uint32_t min_order, pref_order, reserved[2];
};

static double now_ms(void)
{
	struct timespec t;
	clock_gettime(CLOCK_MONOTONIC, &t);
	return t.tv_sec * 1e3 + t.tv_nsec / 1e6;
}

int main(int argc, char **argv)
{
	if (argc < 5) {
		fprintf(stderr, "usage: %s <blkdev> <buf_size> <nr_ops> <use_pool 0|1>\n", argv[0]);
		return 2;
	}
	const char *dev = argv[1];
	uint64_t bufsz = strtoull(argv[2], NULL, 0);
	uint64_t nops  = strtoull(argv[3], NULL, 0);
	int use_pool   = atoi(argv[4]);

	int dev_fd = open(dev, O_RDWR);
	if (dev_fd < 0) { perror("open"); return 1; }

	struct io_uring ring;
	int r = io_uring_queue_init(8, &ring, 0);
	if (r) { fprintf(stderr, "queue_init: %s\n", strerror(-r)); return 1; }

	void *ubuf = NULL;
	if (use_pool) {
		/* sparse table so op 38 has an empty slot 0 to fill */
		r = io_uring_register_buffers_sparse(&ring, 16);
		if (r) { fprintf(stderr, "register_sparse: %s\n", strerror(-r)); return 1; }
		struct io_uring_buf_alloc_for_file req = {
			.fd = dev_fd, .index = 0, .nr_buffers = 1,
			.flags = IORING_BUF_ALLOC_READ | IORING_BUF_ALLOC_REQUIRE_QUEUE_POOL,
			.buffer_size = bufsz,
		};
		r = syscall(__NR_io_uring_register, ring.ring_fd,
			    IORING_REGISTER_BUFFERS_ALLOC_FOR_FILE, &req, 1);
		if (r < 0) { fprintf(stderr, "op38 register: %s\n", strerror(errno)); return 1; }
		/* KBUF: addr is a 0-based offset into the buffer */
	} else {
		if (posix_memalign(&ubuf, 4096, bufsz)) { perror("memalign"); return 1; }
		memset(ubuf, 0, bufsz);
		struct iovec iov = { .iov_base = ubuf, .iov_len = bufsz };
		r = io_uring_register_buffers(&ring, &iov, 1);
		if (r) { fprintf(stderr, "register_buffers: %s\n", strerror(-r)); return 1; }
	}

	uint64_t span = bufsz * 1024, off = 0, done = 0;
	double t0 = now_ms();
	for (uint64_t i = 0; i < nops; i++) {
		struct io_uring_sqe *sqe = io_uring_get_sqe(&ring);
		io_uring_prep_read_fixed(sqe, dev_fd, ubuf, (unsigned)bufsz, off, 0);
		r = io_uring_submit(&ring);
		if (r < 0) { fprintf(stderr, "submit: %s\n", strerror(-r)); return 1; }
		struct io_uring_cqe *cqe;
		r = io_uring_wait_cqe(&ring, &cqe);
		if (r) { fprintf(stderr, "wait_cqe: %s\n", strerror(-r)); return 1; }
		if (cqe->res < 0) { fprintf(stderr, "io op %llu: %s\n",
			(unsigned long long)i, strerror(-cqe->res)); return 1; }
		io_uring_cqe_seen(&ring, cqe);
		done++;
		off += bufsz;
		if (off + bufsz > span) off = 0;
	}
	double ms = now_ms() - t0;
	printf("%s: %llu ops in %.3f ms  (%.0f ops/s)\n",
	       use_pool ? "B pool-ON " : "A pool-OFF",
	       (unsigned long long)done, ms, done / (ms / 1e3));
	io_uring_queue_exit(&ring);
	return 0;
}
