/* Host model of one UFS device behind slot 0, driving the actual ufs_storage.c.
 * usage: fixture <case> <gpt-lba1-3.bin> <block.bin>
 * Prints the storage outcome and a command trace; aborts on any UPIU outside
 * the fixed read-only command set.
 */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef unsigned long long u64;
typedef uint64_t dma_addr_t;
typedef unsigned int gfp_t;
#define __iomem
#define GFP_KERNEL 0
#define PAGE_SIZE 4096UL
#define NSEC_PER_MSEC 1000000ULL
#define min(x, y) ((x) < (y) ? (x) : (y))
#define max(x, y) ((x) > (y) ? (x) : (y))
#define lower_32_bits(n) ((u32)(n))
#define upper_32_bits(n) ((u32)((u64)(n) >> 32))
#define dma_wmb() do { } while (0)
#define dma_rmb() do { } while (0)
#define SHA256_DIGEST_SIZE 32
enum {
	REG_CONTROLLER_STATUS = 0x30, REG_CONTROLLER_ENABLE = 0x34, REG_UTP_TRANSFER_REQ_LIST_BASE_L = 0x50,
	REG_UTP_TRANSFER_REQ_LIST_BASE_H = 0x54, REG_UTP_TRANSFER_REQ_DOOR_BELL = 0x58,
	REG_UTP_TRANSFER_REQ_LIST_RUN_STOP = 0x60,
};
enum {
	DEVICE_PRESENT = 1, CONTROLLER_ENABLE = 1, UTP_TRANSFER_REQ_LIST_READY = 2, HOST_ERROR_INDICATOR = 16,
	DEVICE_ERROR_INDICATOR = 32, UTP_TRANSFER_REQ_LIST_RUN_STOP_BIT = 1,
	UTP_CMD_TYPE_UFS_STORAGE = 1, OCS_SUCCESS = 0, OCS_INVALID_COMMAND_STATUS = 0xf,
};
#include "../workspace/public/src/native-init/s22plus_fyg8_max77705_result_parser.inc.c"

struct device { bool iommu; };
struct reset_control { bool asserted; };
static struct reset_control *parked_reset;
static int reset_control_assert(struct reset_control *r) { r->asserted = true; parked_reset = r; return 0; }
static bool device_iommu_mapped(struct device *dev) { return dev->iommu; }
static u64 clock_ns;
static void udelay(unsigned us) { clock_ns += us * 1000ULL; }
/* The park: a distinct status, reached only with the block reset asserted. */
static void mdelay(unsigned ms) { (void)ms; exit(parked_reset && parked_reset->asserted ? 77 : 78); }
static u32 hci[1024];
static const char *scenario;
static u8 gpt[3 * 4096], block[4096];
static unsigned commands, allocations, init_reads, tur_count;
static bool hold_doorbell;
static char trace[4096];

static bool is(const char *name) { return !strcmp(scenario, name); }
static u64 ktime_get_boottime_ns(void) { return clock_ns; }
static void usleep_range(unsigned low, unsigned high) { (void)high; clock_ns += low * 1000ULL; }
static u16 get_unaligned_be16(const void *p) { const u8 *b = p; return b[0] << 8 | b[1]; }
static u32 get_unaligned_be32(const void *p) { const u8 *b = p; return (u32)b[0] << 24 | b[1] << 16 | b[2] << 8 | b[3]; }
static u64 get_unaligned_be64(const void *p) { return (u64)get_unaligned_be32(p) << 32 | get_unaligned_be32((const u8 *)p + 4); }
static u32 get_unaligned_le32(const void *p) { const u8 *b = p; return b[0] | b[1] << 8 | b[2] << 16 | (u32)b[3] << 24; }
static u64 get_unaligned_le64(const void *p) { return get_unaligned_le32(p) | (u64)get_unaligned_le32((const u8 *)p + 4) << 32; }
static void put_unaligned_be16(u16 v, void *p) { u8 *b = p; b[0] = v >> 8; b[1] = v; }
static void put_unaligned_be32(u32 v, void *p) { u8 *b = p; b[0] = v >> 24; b[1] = v >> 16; b[2] = v >> 8; b[3] = v; }
static void put_unaligned_be64(u64 v, void *p) { put_unaligned_be32(v >> 32, p); put_unaligned_be32(v, (u8 *)p + 4); }
static void put_unaligned_le16(u16 v, void *p) { u8 *b = p; b[0] = v; b[1] = v >> 8; }
static void put_unaligned_le32(u32 v, void *p) { u8 *b = p; for (int i = 0; i < 4; i++) b[i] = v >> (8 * i); }
static void put_unaligned_le64(u64 v, void *p) { put_unaligned_le32(v, p); put_unaligned_le32(v >> 32, (u8 *)p + 4); }
static void *memchr_inv(const void *p, int c, size_t n)
{
	const u8 *b = p;
	for (size_t i = 0; i < n; i++)
		if (b[i] != (u8)c)
			return (void *)(b + i);
	return NULL;
}
static void sha256(const u8 *data, size_t size, u8 out[32])
{
	struct s22plus_max77705_runtime_sha256 h;
	s22plus_max77705_runtime_sha256_init(&h);
	s22plus_max77705_runtime_sha256_update(&h, data, size);
	s22plus_max77705_runtime_sha256_final(&h, out);
}
static void *dmam_alloc_coherent(struct device *dev, size_t size, dma_addr_t *dma, gfp_t gfp)
{
	(void)dev; (void)gfp;
	void *p = aligned_alloc(4096, (size + 4095) & ~4095UL);
	assert(p);
	memset(p, 0x5a, size);   /* stale contents the code must not trust */
	*dma = (dma_addr_t)(uintptr_t)p;
	allocations++;
	return p;
}

static void note(const char *fmt, unsigned a, unsigned b)
{
	char item[64];
	snprintf(item, sizeof(item), fmt, a, b);
	strncat(trace, item, sizeof(trace) - strlen(trace) - 1);
}

/* The device: complete slot 0 once, or never in the timeout case. */
static void complete(void)
{
	u8 *utrd = (u8 *)(uintptr_t)((u64)hci[REG_UTP_TRANSFER_REQ_LIST_BASE_H / 4] << 32 |
				     hci[REG_UTP_TRANSFER_REQ_LIST_BASE_L / 4]);
	u8 *ucd = (u8 *)(uintptr_t)get_unaligned_le64(utrd + 16), *rsp = ucd + 512;
	unsigned direction = utrd[3] >> 1 & 3, prdt = utrd[28] | utrd[29] << 8;
	u8 *data = prdt ? (u8 *)(uintptr_t)get_unaligned_le64(ucd + 1024) : NULL;
	u32 bytes = prdt ? get_unaligned_le32(ucd + 1024 + 12) + 1 : 0;
	u8 ocs = OCS_SUCCESS;

	commands++;
	/* Fixed descriptor shape: storage type, no interrupt, no crypto, OCS preset. */
	assert(utrd[3] >> 4 == 1 && !(utrd[3] & 1) && !(utrd[2] & 0x80) && utrd[8] == 0xf);
	assert((utrd[24] | utrd[25] << 8) == 128 && (utrd[26] | utrd[27] << 8) == 128 &&
	       (utrd[30] | utrd[31] << 8) == 256 && prdt <= 1);
	assert(ucd[2] == 0);                      /* LUN 0 only */
	memset(rsp, 0, 512);
	rsp[3] = ucd[3];
	switch (ucd[0]) {
	case 0x00:                                /* NOP OUT */
		assert(!direction && !prdt);
		note("NOP;", 0, 0);
		rsp[0] = is("nop-bad-ehs") ? 0x00 : 0x20;   /* a malformed reply type */
		if (is("nop-bad-ehs"))
			rsp[8] = 1;
		if (is("timeout-nop") || is("hce-stuck-timeout"))
			hold_doorbell = true;
		break;
	case 0x16:                                /* QUERY: only fDeviceInit set/read */
		assert(!direction && !prdt && ucd[13] == 1 && !ucd[14] && !ucd[15]);
		assert((ucd[5] == 0x81 && ucd[12] == 0x06) || (ucd[5] == 0x01 && ucd[12] == 0x05));
		note(ucd[12] == 6 ? "SETFLAG;" : "READFLAG;", 0, 0);
		rsp[0] = 0x36;
		rsp[12] = ucd[12];
		rsp[13] = ucd[13];
		if (ucd[12] == 0x05)
			put_unaligned_be32(is("init-stuck") || ++init_reads < 3, rsp + 20);
		break;
	case 0x01: {                              /* SCSI COMMAND */
		const u8 *cdb = ucd + 16;
		u32 expected = get_unaligned_be32(ucd + 12);
		rsp[0] = 0x21;
		assert(expected == bytes && (expected ? direction == 2 && ucd[1] == 0x40 : !direction && !ucd[1]));
		if (cdb[0] == 0x00) {
			note("TUR;", 0, 0);
			if ((++tur_count == 1 && !is("no-ua")) || is("tur-not-ready") || is("ehs-twice")) {
				rsp[7] = 0x02;
				put_unaligned_be16(18, rsp + 32);
				if (is("ehs") || is("ehs-twice") || is("ehs-garbage"))
					rsp[8] = 1;                  /* an unrequested extra header */
				if (!is("ua-no-segment"))   /* data segment: length field + sense bytes */
					put_unaligned_be16(2 + 18, rsp + 10);
				if (is("descriptor-ua")) {
					put_unaligned_be16(2 + 8, rsp + 10);
					put_unaligned_be16(8, rsp + 32);
					rsp[34] = 0x72;
					rsp[35] = 0x6;
					rsp[36] = 0x29;
				} else {
					rsp[34] = 0x70;
					rsp[41] = is("short-additional") ? 0 : 10;   /* additional sense length */
					rsp[36] = is("tur-not-ready") ? 0x2 : 0x6;
					rsp[46] = is("tur-not-ready") ? 0x04 : 0x29;
				}
				if (is("ehs-garbage"))       /* the legacy sense place holds EHS bytes */
					memset(rsp + 32, 0xff, 32);
			}
		} else if (cdb[0] == 0x9e) {
			assert(cdb[1] == 0x10 && get_unaligned_be32(cdb + 10) == 32 && bytes == 32);
			note("CAPACITY;", 0, 0);
			if (is("ehs-capacity")) {             /* CHECK CONDITION with an extra header */
				rsp[7] = 0x02;
				rsp[8] = 1;
				break;
			}
			put_unaligned_be64(is("capacity") ? 62305278ULL : 62305279ULL, data);
			put_unaligned_be32(4096, data + 8);
		} else if (cdb[0] == 0x28) {
			u32 lba = get_unaligned_be32(cdb + 2);
			u16 count = get_unaligned_be16(cdb + 7);
			assert((lba == 1 && count == 3) || (lba == 62305152 && count == 1));
			assert(bytes == count * 4096U);
			note("READ %u+%u;", lba, count);
			if (lba == 1 && is("ocs"))
				ocs = 0x2;
			else if (lba == 62305152 && is("short-read"))
				put_unaligned_be32(4096, rsp + 12);          /* GOOD, residual, no data */
			else if (lba == 62305152 && is("underflow"))
				rsp[1] = 0x20;
			else
				memcpy(data, lba == 1 ? gpt : block, bytes);
		} else {
			fprintf(stderr, "forbidden CDB %02x\n", cdb[0]);
			abort();
		}
		break;
	}
	default:
		fprintf(stderr, "forbidden UPIU %02x\n", ucd[0]);
		abort();
	}
	if (is("ehs-all"))
		rsp[8] = 1;                          /* every response, GOOD ones included */
	utrd[8] = ocs;
}

static u32 readl(const void *addr)
{
	unsigned offset = (unsigned)((const u8 *)addr - (const u8 *)hci);
	if (offset == REG_UTP_TRANSFER_REQ_DOOR_BELL && hci[offset / 4] && !hold_doorbell) {
		complete();
		if (!hold_doorbell)
			hci[offset / 4] = 0;
	}
	return hci[offset / 4];
}
static void writel(u32 value, void *addr)
{
	unsigned offset = (unsigned)((u8 *)addr - (u8 *)hci);
	if (offset == REG_CONTROLLER_ENABLE && is("hce-stuck-timeout"))
		return;                                   /* HCE never clears */
	if (offset == REG_UTP_TRANSFER_REQ_DOOR_BELL) {
		assert(value == 1 && !hci[offset / 4]);   /* one slot, never reused while busy */
		assert(hci[REG_UTP_TRANSFER_REQ_LIST_RUN_STOP / 4] == 1);
	}
	hci[offset / 4] = value;
}

#include "waipio_hci.h"
#include "ufs_storage.c"

static void load(const char *path, u8 *out, size_t size)
{
	FILE *f = fopen(path, "rb");
	assert(f && fread(out, 1, size, f) == size);
	fclose(f);
}

int main(int argc, char **argv)
{
	static struct g0q_link link;
	struct g0q_storage out = {0};
	struct device dev = { .iommu = true };
	struct reset_control host = { false };
	bool started = false;

	assert(argc == 4);
	scenario = argv[1];
	load(argv[2], gpt, sizeof(gpt));
	load(argv[3], block, sizeof(block));
	link.hw.hci = hci;
	link.hw.deadline_ns = (is("short-budget") ? 1500 : 15000) * NSEC_PER_MSEC;
	if (is("no-iommu"))
		dev.iommu = false;
	link.link_issued = true;
	link.after = 0xf;
	hci[REG_CONTROLLER_STATUS / 4] = 0xf;
	if (is("link-failed"))
		link.result = 1;
	if (is("list-running"))
		hci[REG_UTP_TRANSFER_REQ_LIST_RUN_STOP / 4] = 1;
	if (is("host-error"))
		hci[REG_CONTROLLER_STATUS / 4] |= HOST_ERROR_INDICATOR;
	hci[REG_CONTROLLER_ENABLE / 4] = 1;
	g0q_storage_read(&link, &dev, &out, &started);
	if (started) {   /* the restart path: stop the list and reset the host */
		g0q_storage_shutdown(&link, &host);
		assert(!hci[REG_UTP_TRANSFER_REQ_LIST_RUN_STOP / 4] && !host.asserted);
		/* HCE is cleared exactly when a slot was outstanding. */
		assert(!hci[REG_CONTROLLER_ENABLE / 4] == !!hci[REG_UTP_TRANSFER_REQ_DOOR_BELL / 4]);
	}
	printf("%d %u %u %u %u %u %u %u", out.rc, out.step, out.flags, out.init_polls,
	       out.sense, out.last_status, out.capacity_low, out.gpt_word);
	for (int i = 0; i < 8; i++)
		printf(" %u", out.block_digest[i]);
#ifdef G0Q_STORAGE_HEADER
	printf(" %u", out.rsp_header);
#endif
	printf("\n%u %u %u %d\n%s\n", commands, allocations, hci[REG_UTP_TRANSFER_REQ_DOOR_BELL / 4], started, trace);
	return 0;
}
