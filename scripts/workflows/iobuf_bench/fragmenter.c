// SPDX-License-Identifier: GPL-2.0
/*
 * Fragment free memory: map and populate a given percentage of MemFree as
 * anonymous memory, then give back every other 4 KiB page with
 * MADV_DONTNEED so the free lists hold single pages instead of large
 * blocks, and hold the rest until killed.  The pinned half is movable
 * memory, which is the point: an allocator that will not compact
 * (__GFP_NORETRY, no reclaim, as the dma-buf system heap allocates) sees a
 * free pool with no order-9 blocks in it.
 *
 * usage: fragmenter <percent-of-MemFree>
 */
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

static unsigned long memfree_kib(void)
{
	char line[128];
	unsigned long kib = 0;
	FILE *f = fopen("/proc/meminfo", "r");

	while (f && fgets(line, sizeof(line), f))
		if (sscanf(line, "MemFree: %lu kB", &kib) == 1)
			break;
	if (f)
		fclose(f);
	return kib;
}

int main(int argc, char **argv)
{
	unsigned long pct = argc > 1 ? strtoul(argv[1], NULL, 0) : 70;
	unsigned long bytes = memfree_kib() * 1024 / 100 * pct;
	unsigned long pages, i;
	unsigned char *p;

	bytes &= ~((1UL << 21) - 1);
	p = mmap(NULL, bytes, PROT_READ | PROT_WRITE,
		 MAP_PRIVATE | MAP_ANONYMOUS | MAP_POPULATE, -1, 0);
	if (p == MAP_FAILED) {
		perror("mmap");
		return 1;
	}
	/* no THP: we want 4 KiB pages so the holes are 4 KiB holes */
	madvise(p, bytes, MADV_NOHUGEPAGE);
	for (i = 0; i < bytes; i += 4096)
		p[i] = 1;
	pages = bytes / 4096;
	for (i = 1; i < pages; i += 2)
		madvise(p + i * 4096, 4096, MADV_DONTNEED);
	printf("fragmenter: pinned %lu MiB, punched %lu holes of 4 KiB\n",
	       bytes / 2 >> 20, pages / 2);
	fflush(stdout);
	pause();
	return 0;
}
