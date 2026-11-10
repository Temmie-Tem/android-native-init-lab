/* SPDX-License-Identifier: GPL-2.0-only */
/* Included at the end of the selected built-in UDC core in an H0 build. */
#include <asm/barrier.h>
#include <crypto/sha2.h>
#include <linux/io.h>
#include <linux/of_address.h>
#include <linux/random.h>
#include "g0q-udc-key.h"

#define G0Q_LOG_BASE 0x800200000ULL
#define G0Q_LOG_PAYLOAD (SZ_2M - 16)
#define G0Q_WINDOW_MS 120000
#define G0Q_SLOT 128
static const unsigned int g0q_due_ms[] = {7000, 17000, 27000, 60000, 90000, 119000};

struct g0q_udc_sample {
	__le32 time_ms;
	__le16 state;
} __packed;

struct g0q_udc_record {
	u8 magic[8], candidate[16], boot[16];
	__le32 bind_start, bind_end, bind_rc;
	struct g0q_udc_sample samples[ARRAY_SIZE(g0q_due_ms)];
	__le32 seen, bind_count;
	u8 mac[32];
} __packed;

static struct g0q_udc_record g0q_record;
static unsigned int g0q_next;
static u32 g0q_latched[4];
static bool g0q_has_header, g0q_enabled;
static DEFINE_SPINLOCK(g0q_bind_lock);
static u32 g0q_bind_start, g0q_bind_end, g0q_bind_count;
static s32 g0q_bind_rc;

static u64 g0q_boot_ms(void)
{
	return ktime_to_ms(ktime_get_boottime());
}

/* Called only for the sole fixed configfs gadget/controller write. Preserve
 * its return unchanged and keep firmware mapping out of the USB path. */
void g0q_udc_bind_observed(bool done, ssize_t result);
void g0q_udc_bind_observed(bool done, ssize_t result)
{
	u64 now;

	if (!READ_ONCE(g0q_enabled))
		return;
	spin_lock(&g0q_bind_lock);
	now = g0q_boot_ms();
	if (now >= G0Q_WINDOW_MS) {
		spin_unlock(&g0q_bind_lock);
		return;
	}
	if (!done) {
		if (g0q_bind_count < 2)
			g0q_bind_count++;
		if (g0q_bind_count == 1)
			g0q_bind_start = now;
	} else if (g0q_bind_count == 1) {
		g0q_bind_end = now;
		g0q_bind_rc = result;
	}
	spin_unlock(&g0q_bind_lock);
}

/* The original Android reader rotates its own firmware-shared ring. These
 * 256 bytes precede its cursor, using the same fit rule as the early marks.
 * Latch all header words for this boot. Never repair or advance the header. */
static void __iomem *g0q_map(phys_addr_t address, size_t length)
{
	/* Both fixed mappings are shorter than a page, but a slot can cross
	 * one page boundary. Check both PFNs before invoking arm64 ioremap. */
	if (pfn_is_map_memory(PHYS_PFN(address)) ||
	    pfn_is_map_memory(PHYS_PFN(address + length - 1)))
		return NULL;
	return ioremap_wc(address, length);
}

static bool g0q_publish(unsigned int index)
{
	u32 header[4], pos, cursor;
	u8 __iomem *slot;
	u32 __iomem *map;
	unsigned int i;
	bool ok = false;

	static_assert(sizeof(g0q_record) == G0Q_SLOT);
	map = g0q_map(G0Q_LOG_BASE, sizeof(header));
	if (!map)
		return false;
	for (i = 0; i < ARRAY_SIZE(header); i++)
		header[i] = readl(map + i);
	if (header[1] != 0x4d474f4c || header[2] < 2 * G0Q_SLOT)
		goto out;
	if (g0q_has_header && memcmp(g0q_latched, header, sizeof(header)))
		goto out;
	memcpy(g0q_latched, header, sizeof(header));
	g0q_has_header = true;
	cursor = header[2] % G0Q_LOG_PAYLOAD;
	pos = (cursor >= 2 * G0Q_SLOT ? cursor : G0Q_LOG_PAYLOAD) - 2 * G0Q_SLOT;
	pos += (index % 2) * G0Q_SLOT;
	slot = g0q_map(G0Q_LOG_BASE + sizeof(header) + pos, G0Q_SLOT);
	if (!slot)
		goto out;
	for (i = 0; i < ARRAY_SIZE(header); i++)
		if (readl(map + i) != header[i])
			goto out_slot;
	/* Copy bytewise: the dynamic cursor need not be naturally aligned. */
	for (i = 0; i < 8; i++)
		writeb(0, slot + i);
	dsb(sy);
	for (i = 8; i < G0Q_SLOT; i++)
		writeb(((const u8 *)&g0q_record)[i], slot + i);
	dsb(sy);
	for (i = 0; i < ARRAY_SIZE(header); i++)
		if (readl(map + i) != header[i])
			goto out_slot;
	for (i = 0; i < 8; i++)
		writeb(g0q_record.magic[i], slot + i);
	dsb(sy);
	ok = true;
out_slot:
	iounmap(slot);
out:
	iounmap(map);
	return ok;
}

static void g0q_sample_work(struct work_struct *work);
static DECLARE_DELAYED_WORK(g0q_work, g0q_sample_work);

static void g0q_schedule(void)
{
	u64 now = g0q_boot_ms();

	/* A late start/stalled worker never backfills scheduled observations. */
	while (g0q_next < ARRAY_SIZE(g0q_due_ms) && g0q_due_ms[g0q_next] < now)
		g0q_next++;
	if (g0q_next < ARRAY_SIZE(g0q_due_ms))
		schedule_delayed_work(&g0q_work, msecs_to_jiffies(g0q_due_ms[g0q_next] - now));
}

static void g0q_sample_work(struct work_struct *work)
{
	struct usb_udc *udc;
	u64 now = g0q_boot_ms();
	int state = -ENODEV;
	bool locked;
	unsigned int i = g0q_next++;

	if (now >= G0Q_WINDOW_MS)
		return;
	/* Same device name as configfs, same enum as the class state file. */
	locked = mutex_trylock(&udc_lock);
	spin_lock(&g0q_bind_lock);
	now = g0q_boot_ms();
	if (locked) {
		list_for_each_entry(udc, &udc_list, list) {
			if (!strcmp(dev_name(&udc->dev), "a600000.usb")) {
				state = READ_ONCE(udc->gadget->state);
				break;
			}
		}
	} else {
		state = -EBUSY;
	}
	g0q_record.bind_start = cpu_to_le32(g0q_bind_start);
	g0q_record.bind_end = cpu_to_le32(g0q_bind_end);
	g0q_record.bind_rc = cpu_to_le32(g0q_bind_rc);
	g0q_record.bind_count = cpu_to_le32(g0q_bind_count);
	spin_unlock(&g0q_bind_lock);
	if (locked)
		mutex_unlock(&udc_lock);
	/* Interrupts may have delayed the read past the window. */
	if (g0q_boot_ms() >= G0Q_WINDOW_MS)
		return;
	g0q_record.samples[i].time_ms = cpu_to_le32(now);
	g0q_record.samples[i].state = cpu_to_le16(state);
	g0q_record.seen |= cpu_to_le32(BIT(i));
	hmac_sha256_usingrawkey(g0q_key, sizeof(g0q_key), (const u8 *)&g0q_record,
				offsetof(struct g0q_udc_record, mac), g0q_record.mac);
	if (g0q_publish(i))
		g0q_schedule();
}

static int __init g0q_observe_init(void)
{
	struct device_node *np;
	struct resource r;
	bool eligible;

	if (!of_machine_is_compatible("samsung,g0q"))
		return 0;
	np = of_find_node_by_path("/reserved-memory/g0q-retained-5@800100000");
	if (!np)
		return 0;
	eligible = of_device_is_available(np) && of_property_read_bool(np, "no-map") &&
		!of_property_read_bool(np, "reusable") && !of_address_to_resource(np, 0, &r) &&
		r.start == 0x800100000ULL && resource_size(&r) == 0xa02000;
	of_node_put(np);
	if (!eligible)
		return 0;
	memcpy(g0q_record.magic, "G0QUDC01", 8);
	memcpy(g0q_record.candidate, g0q_candidate, sizeof(g0q_candidate));
	get_random_bytes(g0q_record.boot, sizeof(g0q_record.boot));
	WRITE_ONCE(g0q_enabled, true);
	g0q_schedule();
	return 0;
}
late_initcall(g0q_observe_init);
