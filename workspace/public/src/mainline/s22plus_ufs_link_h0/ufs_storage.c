// SPDX-License-Identifier: GPL-2.0-only
/* Phase 2a read-only UTP sequence. See ufs_storage.h for the fixed scope.
 *
 * One transfer slot (0), polled doorbell, interrupt bit clear, crypto enable
 * clear, coherent DMA through the device's SMMU domain. Every command has a
 * fixed opcode, LUN 0 and fixed fields; nothing comes from the observer.
 * A doorbell that does not clear in time marks the slot uncertain and stops:
 * it is never cleared or reused, and its buffers stay allocated (devres of a
 * device that is never unbound).
 */
#include <linux/delay.h>
#include <linux/device.h>
#include <linux/dma-mapping.h>
#include <linux/iommu.h>
#include <linux/reset.h>
#include <linux/errno.h>
#include <linux/io.h>
#include <linux/kernel.h>
#include <linux/minmax.h>
#include <linux/ktime.h>
#include <linux/string.h>
#include <linux/unaligned.h>
#include <crypto/sha2.h>
#include <ufs/ufshci.h>
#include "waipio_hci.h"
#include "ufs_storage.h"

#define UPIU 512U                     /* ALIGNED_UPIU_SIZE */
#define UCD_BYTES (2 * UPIU + 16)     /* command, response, one PRDT entry */
#define DATA_BYTES (3 * G0Q_BLOCK)    /* LBAs 1-3 */
#define T_NOP_OUT 0x00
#define T_COMMAND 0x01
#define T_QUERY_REQ 0x16
#define T_NOP_IN 0x20
#define T_RESPONSE 0x21
#define T_QUERY_RSP 0x36
#define FLAG_READ 0x40
#define Q_STD_READ 0x01
#define Q_STD_WRITE 0x81
#define Q_READ_FLAG 0x05
#define Q_SET_FLAG 0x06
#define IDN_DEVICE_INIT 0x01
#define DIR_NONE 0
#define DIR_IN 2
/* The stage ends this long before the module budget, so its outcome can never
 * turn the completed link into a budget timeout. */
#define STORAGE_MARGIN_NS (2000 * NSEC_PER_MSEC)

struct utp {
	void __iomem *hci;
	u64 deadline_ns;
	u8 *utrd, *ucd, *data;
	dma_addr_t utrd_dma, ucd_dma, data_dma;
	u8 tag;
	struct g0q_storage *out;
};

static bool expired(const struct utp *u, u64 extra_ns)
{
	return ktime_get_boottime_ns() + extra_ns >= u->deadline_ns;
}

/* Fill slot 0 and the command descriptor; the caller has written the UPIU. */
static void prepare(struct utp *u, unsigned int direction, u32 bytes)
{
	memset(u->utrd, 0, 32);
	/* DW0: command type 1 (UFS storage), data direction, no interrupt, no crypto. */
	u->utrd[3] = (UTP_CMD_TYPE_UFS_STORAGE << 4) | (direction << 1);
	u->utrd[8] = OCS_INVALID_COMMAND_STATUS;
	put_unaligned_le64(u->ucd_dma, u->utrd + 16);
	put_unaligned_le16(UPIU / 4, u->utrd + 24);        /* response length, dwords */
	put_unaligned_le16(UPIU / 4, u->utrd + 26);        /* response offset, dwords */
	put_unaligned_le16(bytes ? 1 : 0, u->utrd + 28);   /* PRDT entries */
	put_unaligned_le16(2 * UPIU / 4, u->utrd + 30);    /* PRDT offset, dwords */
	memset(u->ucd + UPIU, 0, UPIU + 16);
	if (bytes) {
		put_unaligned_le64(u->data_dma, u->ucd + 2 * UPIU);
		put_unaligned_le32(bytes - 1, u->ucd + 2 * UPIU + 12);
		memset(u->data, 0, DATA_BYTES);
	}
}

static void header(struct utp *u, u8 type, u8 flags, u8 function)
{
	memset(u->ucd, 0, UPIU);
	u->ucd[0] = type;
	u->ucd[1] = flags;
	u->ucd[2] = 0;                 /* LUN 0 only */
	u->ucd[3] = ++u->tag;
	u->ucd[5] = function;
}

/* An absolute wait end: now + wait, never past the stage deadline. */
static u64 within(const struct utp *u, u64 wait_ns)
{
	return min(u->deadline_ns, ktime_get_boottime_ns() + wait_ns);
}

/* Ring slot 0 once and wait until the absolute end for it to clear.
 * Returns the UPIU type on OCS 0. */
static int ring(struct utp *u, u64 until)
{
	u8 ocs;

	until = min(until, u->deadline_ns);
	if (ktime_get_boottime_ns() >= until || readl(u->hci + REG_UTP_TRANSFER_REQ_DOOR_BELL))
		return -EBUSY;
	dma_wmb();
	writel(1, u->hci + REG_UTP_TRANSFER_REQ_DOOR_BELL);
	while (readl(u->hci + REG_UTP_TRANSFER_REQ_DOOR_BELL) & 1) {
		if (ktime_get_boottime_ns() >= until) {
			u->out->flags |= G0Q_SF_UNCERTAIN;
			return -ETIMEDOUT;
		}
		usleep_range(20, 40);
	}
	/* A completion first observed after the end never advances the sequence;
	 * the slot itself is clear, so it is not uncertain. */
	if (ktime_get_boottime_ns() >= until)
		return -ETIMEDOUT;
	dma_rmb();
	ocs = u->utrd[8];
	u->out->last_status = ocs | u->ucd[UPIU + 6] << 8 | u->ucd[UPIU + 7] << 16 |
			      u->ucd[UPIU] << 24;
#ifdef G0Q_STORAGE_HEADER
	u->out->rsp_header = get_unaligned_be32(u->ucd + UPIU + 8);
#endif
	if (ocs != OCS_SUCCESS)
		return -EIO;
#ifndef G0Q_STORAGE_HEADER
	/* No command requests an extra header; one would move every later offset. */
	if (u->ucd[UPIU + 8])
		return -EPROTO;
#endif
	/* V15: an extra header segment follows the 32-byte header, so every header
	 * field used here keeps its offset; only a data segment would move, and the
	 * one data segment read (sense) is refused unparsed when EHS is present. */
	return u->ucd[UPIU];
}

static int nop_out(struct utp *u)
{
	u64 until = within(u, 500 * NSEC_PER_MSEC);
	int type;

	header(u, T_NOP_OUT, 0, 0);
	prepare(u, DIR_NONE, 0);
	type = ring(u, until);
	if (type < 0)
		return type;
	return type == T_NOP_IN && !u->ucd[UPIU + 6] ? 0 : -EPROTO;
}

static int query_flag(struct utp *u, u8 function, u8 opcode, u32 *value, u64 until)
{
	int type;

	header(u, T_QUERY_REQ, 0, function);
	u->ucd[12] = opcode;
	u->ucd[13] = IDN_DEVICE_INIT;
	prepare(u, DIR_NONE, 0);
	type = ring(u, until);
	if (type < 0)
		return type;
	if (type != T_QUERY_RSP || u->ucd[UPIU + 6] || u->ucd[UPIU + 12] != opcode ||
	    u->ucd[UPIU + 13] != IDN_DEVICE_INIT)
		return -EPROTO;
	if (value)
		*value = get_unaligned_be32(u->ucd + UPIU + 20) & 1;
	return 0;
}

/* SCSI command on LU 0. A CHECK CONDITION records fixed-format sense. */
static int scsi(struct utp *u, const u8 *cdb, unsigned int length, u32 bytes)
{
	u64 until = within(u, 500 * NSEC_PER_MSEC);
	int type;

	header(u, T_COMMAND, bytes ? FLAG_READ : 0, 0);
	put_unaligned_be32(bytes, u->ucd + 12);
	memcpy(u->ucd + 16, cdb, length);
	prepare(u, bytes ? DIR_IN : DIR_NONE, bytes);
	type = ring(u, until);
	if (type < 0)
		return type;
#ifdef G0Q_STORAGE_RESPONSE
	/* V16: a CHECK CONDITION may carry response Target Failure (0x01), as the
	 * device does for the first TEST UNIT READY after reset; upstream ufshcd
	 * takes only the status of a SCSI response. GOOD still needs response 0. */
	if (type != T_RESPONSE ||
	    (u->ucd[UPIU + 6] && (u->ucd[UPIU + 6] != 0x01 || u->ucd[UPIU + 7] != 0x02)))
		return -EPROTO;
	if (u->ucd[UPIU + 6])
		u->out->flags |= G0Q_SF_TARGET_FAILURE;
#else
	if (type != T_RESPONSE || u->ucd[UPIU + 6])
		return -EPROTO;
#endif
	if (u->ucd[UPIU + 7] == 0x02) {   /* CHECK CONDITION: fixed or descriptor sense */
		const u8 *sense = u->ucd + UPIU + 34;
		u16 segment, length;

		u->out->sense = 0;
#ifdef G0Q_STORAGE_HEADER
		/* With an extra header segment the data segment moves: no byte past the
		 * 32-byte header is read, and the sense stays unparsed. */
		if (u->ucd[UPIU + 8]) {
			u->out->flags |= G0Q_SF_SENSE_UNPARSED;
			return -EAGAIN;
		}
#endif
		/* Sense counts only inside the declared data segment (length field + bytes). */
		segment = get_unaligned_be16(u->ucd + UPIU + 10);
		length = get_unaligned_be16(u->ucd + UPIU + 32);
		if (segment < 2 || length > segment - 2 || length > 18)
			return -EAGAIN;
		/* Each format's own record length (8 + additional length) must fit the bytes. */
		if (length < 8 || 8 + sense[7] > length)
			return -EAGAIN;
		if ((sense[0] & 0x7e) == 0x70)          /* fixed: ASC at 12, ASCQ at 13 */
			u->out->sense = (sense[2] & 0xf) << 16 | (sense[7] >= 5 ? sense[12] << 8 : 0) |
					(sense[7] >= 6 ? sense[13] : 0);
		else if ((sense[0] & 0x7e) == 0x72)     /* descriptor: header bytes 1-3 */
			u->out->sense = (sense[1] & 0xf) << 16 | sense[2] << 8 | sense[3];
		return -EAGAIN;
	}
	if (u->ucd[UPIU + 7])
		return -EIO;
	/* GOOD must move every expected byte: no underflow/overflow, no residual. */
	if ((u->ucd[UPIU + 1] & 0x60) || get_unaligned_be32(u->ucd + UPIU + 12))
		return -ENODATA;
	return 0;
}

static int read10(struct utp *u, u32 lba, u16 blocks)
{
	u8 cdb[10] = { 0x28 };

	put_unaligned_be32(lba, cdb + 2);
	put_unaligned_be16(blocks, cdb + 7);
	return scsi(u, cdb, sizeof(cdb), blocks * G0Q_BLOCK);
}

/* The test block lies past every GPT entry and inside the last usable LBA. */
static bool range_ok(const u8 *gpt)
{
	u32 count = get_unaligned_le32(gpt + 80), size = get_unaligned_le32(gpt + 84);
	u64 highest = 0;

	if (memcmp(gpt, "EFI PART", 8) || get_unaligned_le64(gpt + 72) != 2 || size != 128 ||
	    !count || count > 2 * G0Q_BLOCK / size ||
	    get_unaligned_le64(gpt + 48) != G0Q_LU0_LAST_USABLE)
		return false;
	for (u32 i = 0; i < count; i++) {
		const u8 *entry = gpt + G0Q_BLOCK + i * size;
		u64 first = get_unaligned_le64(entry + 32), last = get_unaligned_le64(entry + 40);

		if (!memchr_inv(entry, 0, 16))
			continue;
		if (first > last || (G0Q_TEST_LBA >= first && G0Q_TEST_LBA <= last))
			return false;
		highest = max(highest, last);
	}
	return highest == G0Q_NATIVE_LAST_LBA && G0Q_TEST_LBA > highest &&
	       G0Q_TEST_LBA <= G0Q_LU0_LAST_USABLE;
}

static int sequence(struct utp *u)
{
	static const u8 tur[6] = { 0x00 };
	u8 capacity[16] = { 0x9e, 0x10 };
	u8 digest[SHA256_DIGEST_SIZE];
	struct g0q_storage *out = u->out;
	u32 value = 1;
	int rc;

	out->step = G0Q_ST_NOP;
	rc = nop_out(u);
	if (rc)
		return rc;
	out->flags |= G0Q_SF_NOP;

	out->step = G0Q_ST_INIT_SET;
	rc = query_flag(u, Q_STD_WRITE, Q_SET_FLAG, NULL, within(u, 500 * NSEC_PER_MSEC));
	if (rc)
		return rc;
	out->flags |= G0Q_SF_INIT_SET;
	out->step = G0Q_ST_INIT_POLL;
	/* Bounded poll, one read per millisecond, inside the module budget. */
	for (u64 until = ktime_get_boottime_ns() + 1500 * NSEC_PER_MSEC; value; ) {
		usleep_range(1000, 1100);
		if (ktime_get_boottime_ns() >= until || expired(u, 0))
			return -ETIMEDOUT;
		/* Each read's absolute wait ends with the 1.5-second poll window. */
		rc = query_flag(u, Q_STD_READ, Q_READ_FLAG, &value,
				min(until, within(u, 500 * NSEC_PER_MSEC)));
		out->init_polls++;
		if (rc)
			return rc;
	}
	out->flags |= G0Q_SF_INIT_CLEAR;

	out->step = G0Q_ST_TUR;
	rc = scsi(u, tur, sizeof(tur), 0);
#ifdef G0Q_STORAGE_HEADER
	/* One repeat for a UNIT ATTENTION, or for a CHECK CONDITION whose sense could
	 * not be located; TEST UNIT READY moves no data either way. */
	if (rc == -EAGAIN && ((out->sense >> 16) == 0x6 || (out->flags & G0Q_SF_SENSE_UNPARSED))) {
		if ((out->sense >> 16) == 0x6)
			out->flags |= G0Q_SF_UNIT_ATTENTION;
		out->flags |= G0Q_SF_TUR_REPEAT;
		rc = scsi(u, tur, sizeof(tur), 0);
	}
#else
	if (rc == -EAGAIN && (out->sense >> 16) == 0x6) {   /* one UNIT ATTENTION repeat */
		out->flags |= G0Q_SF_UNIT_ATTENTION;
		rc = scsi(u, tur, sizeof(tur), 0);
	}
#endif
	if (rc)
		return rc;
	out->flags |= G0Q_SF_TUR;

	out->step = G0Q_ST_CAPACITY;
	put_unaligned_be32(32, capacity + 10);
	rc = scsi(u, capacity, sizeof(capacity), 32);
	if (rc)
		return rc;
	out->capacity_low = (u32)get_unaligned_be64(u->data);
	if (get_unaligned_be64(u->data) != G0Q_LU0_LAST_LBA ||
	    get_unaligned_be32(u->data + 8) != G0Q_BLOCK)
		return -ERANGE;
	out->flags |= G0Q_SF_CAPACITY;

	out->step = G0Q_ST_GPT;
	rc = read10(u, 1, 3);
	if (rc)
		return rc;
	out->flags |= G0Q_SF_GPT_READ;
	sha256(u->data, DATA_BYTES, digest);
	out->gpt_word = get_unaligned_be32(digest);
	if (memcmp(digest, G0Q_GPT_SHA256, SHA256_DIGEST_SIZE))
		return -ENXIO;
	out->flags |= G0Q_SF_GPT_MATCH;
	/* Parsed only after the exact table matched; the bound is also explicit. */
	if (!range_ok(u->data))
		return -ENXIO;
	out->flags |= G0Q_SF_RANGE;

	out->step = G0Q_ST_BLOCK;
	rc = read10(u, G0Q_TEST_LBA, 1);
	if (rc)
		return rc;
	out->flags |= G0Q_SF_BLOCK_READ;
	sha256(u->data, G0Q_BLOCK, digest);
	for (unsigned int i = 0; i < 8; i++)
		out->block_digest[i] = get_unaligned_be32(digest + 4 * i);
	if (!memchr_inv(u->data, 0, G0Q_BLOCK))
		out->flags |= G0Q_SF_BLOCK_ZERO;
	out->step = G0Q_ST_DONE;
	return 0;
}

void g0q_storage_read(struct g0q_link *link, struct device *dev, struct g0q_storage *out,
		      bool *list_started)
{
	struct utp u = { .hci = link->hw.hci, .out = out };
	u32 status;

	out->step = G0Q_ST_ADMIT;
	if (link->hw.deadline_ns <= STORAGE_MARGIN_NS) {
		out->rc = -ETIMEDOUT;
		return;
	}
	u.deadline_ns = link->hw.deadline_ns - STORAGE_MARGIN_NS;
	/* Only after this boot's one completed link: result 0, Device Present,
	 * no error indicator, transfer list ready, list stopped and empty. */
	status = readl(u.hci + REG_CONTROLLER_STATUS);
	if (!link->link_issued || link->result || !(link->after & DEVICE_PRESENT) ||
	    (status & (DEVICE_PRESENT | UTP_TRANSFER_REQ_LIST_READY | HOST_ERROR_INDICATOR |
		       DEVICE_ERROR_INDICATOR)) != (DEVICE_PRESENT | UTP_TRANSFER_REQ_LIST_READY) ||
	    readl(u.hci + REG_UTP_TRANSFER_REQ_LIST_RUN_STOP) ||
	    readl(u.hci + REG_UTP_TRANSFER_REQ_DOOR_BELL) || expired(&u, 0)) {
		out->rc = -EBUSY;
		return;
	}
	/* DMA only through this device's own translated SMMU stream. */
	if (!device_iommu_mapped(dev)) {
		out->rc = -ENODEV;
		return;
	}
	out->step = G0Q_ST_LIST;
	u.utrd = dmam_alloc_coherent(dev, PAGE_SIZE, &u.utrd_dma, GFP_KERNEL);
	u.ucd = dmam_alloc_coherent(dev, PAGE_SIZE, &u.ucd_dma, GFP_KERNEL);
	u.data = dmam_alloc_coherent(dev, DATA_BYTES, &u.data_dma, GFP_KERNEL);
	if (!u.utrd || !u.ucd || !u.data) {
		out->rc = -ENOMEM;
		return;
	}
	if (expired(&u, 0)) {
		out->rc = -ETIMEDOUT;
		return;
	}
	*list_started = true;
	writel(lower_32_bits(u.utrd_dma), u.hci + REG_UTP_TRANSFER_REQ_LIST_BASE_L);
	writel(upper_32_bits(u.utrd_dma), u.hci + REG_UTP_TRANSFER_REQ_LIST_BASE_H);
	writel(UTP_TRANSFER_REQ_LIST_RUN_STOP_BIT, u.hci + REG_UTP_TRANSFER_REQ_LIST_RUN_STOP);
	if (readl(u.hci + REG_UTP_TRANSFER_REQ_LIST_BASE_L) != lower_32_bits(u.utrd_dma) ||
	    readl(u.hci + REG_UTP_TRANSFER_REQ_LIST_BASE_H) != upper_32_bits(u.utrd_dma) ||
	    !(readl(u.hci + REG_UTP_TRANSFER_REQ_LIST_RUN_STOP) & UTP_TRANSFER_REQ_LIST_RUN_STOP_BIT)) {
		out->rc = -EIO;
		return;
	}
	out->flags |= G0Q_SF_LIST;
	out->rc = sequence(&u);
}

/* Driver shutdown, before the SMMU's own shutdown: stop the transfer list and
 * reset the host so no slot can still DMA once translation is disabled. */
void g0q_storage_shutdown(struct g0q_link *link, struct reset_control *host)
{
	void __iomem *hci = link->hw.hci;
	u64 until;

	writel(0, hci + REG_UTP_TRANSFER_REQ_LIST_RUN_STOP);
	/* With no slot outstanding there is no DMA to stop. */
	if (!readl(hci + REG_UTP_TRANSFER_REQ_DOOR_BELL))
		return;
	/* An outstanding slot: clearing HCE aborts it. Proven only by HCE reading 0. */
	writel(0, hci + REG_CONTROLLER_ENABLE);
	until = ktime_get_boottime_ns() + 1000 * NSEC_PER_MSEC;
	while (ktime_get_boottime_ns() < until) {
		if (!(readl(hci + REG_CONTROLLER_ENABLE) & CONTROLLER_ENABLE))
			return;
		udelay(100);
	}
	/* Not proven stopped: hold the block reset and never return, so the SMMU
	 * never stops translating under a possibly live slot. The attended
	 * physical Download (a PMIC reset of the whole SoC) is the recovery. */
	reset_control_assert(host);
	for (;;)
		mdelay(1000);
}
