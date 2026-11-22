/* SPDX-License-Identifier: GPL-2.0-only */
#include <lib/libfdt/libfdt.h>
#include "uniloader_layout.h"
#include "uniloader_marker.h"

#define RAMOOPS_NODE "/reserved-memory/ramoops@9FA00000"
#define RAMOOPS_BASE 0x9fa00000ULL
#define ZONE_SIZE 0x40000U
#define PMSG_BASE (RAMOOPS_BASE + 3 * ZONE_SIZE)
#define RAMOOPS_END (PMSG_BASE + ZONE_SIZE)
#define RAMOOPS_SIG 0x43474244U
#define VENDOR_CMDLINE_SIZE 4096
#define RECORD_PREFIX "Y2Q-STAGE-V1 " Y2Q_MARKER " "
#define CMDLINE_TAG "codex.y2q_trace=" Y2Q_MARKER

struct persistent_ram {
    uint32_t sig;
    uint32_t start;
    uint32_t size;
    char data[];
};

static int matches(const void *tree, int node, const char *name,
                   const void *expected, int size)
{
    int length;
    const void *value = fdt_getprop(tree, node, name, &length);
    return value && length == size && !memcmp(value, expected, size);
}

static int absent(const void *tree, int node, const char *name)
{
    int length;
    return !fdt_getprop(tree, node, name, &length) && length == -FDT_ERR_NOTFOUND;
}

static int enabled(const void *tree, int node)
{
    return absent(tree, node, "status") ||
           matches(tree, node, "status", "okay", sizeof("okay")) ||
           matches(tree, node, "status", "ok", sizeof("ok"));
}

static int touches_pmsg(uint64_t address, uint64_t size)
{
    return address < RAMOOPS_END && address + size > PMSG_BASE;
}

static uint64_t address_property(const void *tree, int node, const char *name)
{
    int length;
    const fdt32_t *value = fdt_getprop(tree, node, name, &length);
    if (value && length == 8)
        return (uint64_t)fdt32_to_cpu(value[0]) << 32 | fdt32_to_cpu(value[1]);
    return value && length == 4 ? fdt32_to_cpu(value[0]) : 0;
}

static int pmsg_in_ram(const void *tree)
{
    int memory = fdt_path_offset(tree, "/memory");
    int length;
    if (memory < 0 || !enabled(tree, memory) || !absent(tree, memory, "linux,usable-memory"))
        return 0;
    const fdt32_t *reg = fdt_getprop(tree, memory, "reg", &length);
    if (!reg || length < 16 || length % 16)
        return 0;
    for (int i = 0; i < length / 4; i += 4) {
        uint64_t address = (uint64_t)fdt32_to_cpu(reg[i]) << 32 | fdt32_to_cpu(reg[i + 1]);
        uint64_t size = (uint64_t)fdt32_to_cpu(reg[i + 2]) << 32 | fdt32_to_cpu(reg[i + 3]);
        if (address <= PMSG_BASE && size >= RAMOOPS_END - address)
            return 1;
    }
    return 0;
}

/* The unchanged pre-stack guard already checked token and extent bounds,
 * including reserved-memory reg tuples and wrapper/DTB/initrd isolation.
 * Find an exact separate slot before doing any store outside wrapper RAM.
 */
static int stage_slot(const void *tree, int chosen, int ram)
{
    int root = fdt_path_offset(tree, "/");
    int reserved = fdt_path_offset(tree, "/reserved-memory");
    const fdt32_t expected_reg[] = {
        0, cpu_to_fdt32(RAMOOPS_BASE), 0, cpu_to_fdt32(4 * ZONE_SIZE),
    };
    const fdt32_t zone = cpu_to_fdt32(ZONE_SIZE);
    if (root < 0 || reserved < 0 || ram < 0 || chosen < 0 ||
        !enabled(tree, root) || !enabled(tree, reserved) || !enabled(tree, ram) ||
        !absent(tree, chosen, "linux,usable-memory-range") ||
        !matches(tree, root, "compatible", "qcom,kona", sizeof("qcom,kona")) ||
        !matches(tree, ram, "compatible", "ramoops", sizeof("ramoops")) ||
        !matches(tree, ram, "reg", expected_reg, sizeof(expected_reg)) ||
        !matches(tree, ram, "record-size", &zone, sizeof(zone)) ||
        !matches(tree, ram, "console-size", &zone, sizeof(zone)) ||
        !matches(tree, ram, "ftrace-size", &zone, sizeof(zone)) ||
        !matches(tree, ram, "pmsg-size", &zone, sizeof(zone)) ||
        !absent(tree, ram, "ecc-size") || !absent(tree, ram, "mem-type") ||
        !absent(tree, ram, "unbuffered") || !absent(tree, ram, "no-map") ||
        !absent(tree, ram, "reusable") || !absent(tree, ram, "size") || !pmsg_in_ram(tree))
        return 0;

    uint64_t initrd = address_property(tree, chosen, "linux,initrd-start");
    uint64_t initrd_end = address_property(tree, chosen, "linux,initrd-end");
    if (touches_pmsg((uintptr_t)tree, fdt_totalsize(tree)) ||
        !initrd || initrd_end <= initrd || touches_pmsg(initrd, initrd_end - initrd))
        return 0;

    int count = fdt_num_mem_rsv(tree);
    if (count < 0)
        return 0;
    for (int i = 0; i < count; ++i) {
        uint64_t address, size;
        if (fdt_get_mem_rsv(tree, i, &address, &size) ||
            (touches_pmsg(address, size) &&
             (address != RAMOOPS_BASE || size != 4 * ZONE_SIZE)))
            return 0;
    }

    int child;
    fdt_for_each_subnode(child, tree, reserved) {
        if (child == ram)
            continue;
        int length;
        const fdt32_t *reg = fdt_getprop(tree, child, "reg", &length);
        if (fdt_node_check_compatible(tree, child, "ramoops") == 0)
            return 0;
        for (int i = 0; reg && i < length / 4; i += 4) {
            uint64_t start = (uint64_t)fdt32_to_cpu(reg[i]) << 32 | fdt32_to_cpu(reg[i + 1]);
            uint64_t size = (uint64_t)fdt32_to_cpu(reg[i + 2]) << 32 | fdt32_to_cpu(reg[i + 3]);
            if (touches_pmsg(start, size))
                return 0;
        }
    }
    return child == -FDT_ERR_NOTFOUND;
}

static unsigned int publish(unsigned int offset, const char *record, unsigned int length)
{
    volatile struct persistent_ram *ring = (void *)(uintptr_t)PMSG_BASE;
    if (!offset) {
        ring->sig = 0;
        asm volatile("dsb sy" ::: "memory");
        ring->start = 0;
    }
    for (unsigned int i = 0; i < length; ++i)
        ring->data[offset + i] = record[i];
    asm volatile("dsb sy" ::: "memory");
    ring->size = offset + length;
    asm volatile("dsb sy" ::: "memory");
    if (!offset) {
        ring->sig = RAMOOPS_SIG;
        asm volatile("dsb sy" ::: "memory");
    }
    return offset + length;
}

#define PUBLISH(offset, stage) publish(offset, RECORD_PREFIX stage "\n", \
                                      sizeof(RECORD_PREFIX stage "\n") - 1)
_Static_assert(3 * sizeof(RECORD_PREFIX "handoff-ready\n") +
               sizeof(struct persistent_ram) < ZONE_SIZE, "records exceed PMSG zone");

static int mark_cmdline(void *tree, int chosen)
{
    int length;
    const char *old = fdt_getprop(tree, chosen, "bootargs", &length);
    static const char prefix[] = CMDLINE_TAG " ";
    const int prefix_length = sizeof(prefix) - 1;
    char command[VENDOR_CMDLINE_SIZE];
    if (!old || length < 1 || length > (int)sizeof(command) - prefix_length ||
        old[length - 1] || memchr(old, '\0', length - 1))
        return 0; /* The PMSG stages remain available. */
    /* Boot CPU alignment checking can be enabled. Do not call the upstream
     * assembly memcpy on arbitrary string offsets.
     */
    for (int i = 0; i < prefix_length; ++i)
        command[i] = prefix[i];
    for (int i = 0; i < length; ++i)
        command[prefix_length + i] = old[i];
    return fdt_setprop(tree, chosen, "bootargs", command, prefix_length + length);
}

void *y2q_mark_fdt(const void *original, void *scratch)
{
    int chosen = fdt_path_offset(original, "/chosen");
    int ram = fdt_path_offset(original, RAMOOPS_NODE);
    int trace = stage_slot(original, chosen, ram);
    unsigned int offset = trace ? PUBLISH(0, "guard-passed") : 0;

    if (fdt_open_into(original, scratch, Y2Q_FDT_CAPACITY))
        return NULL;
    chosen = fdt_path_offset(scratch, "/chosen");
    if (chosen < 0 || fdt_setprop_string(scratch, chosen, Y2Q_MARKER_PROPERTY, Y2Q_MARKER))
        return NULL;

    if (trace) {
        offset = PUBLISH(offset, "fdt-marked");
        ram = fdt_path_offset(scratch, RAMOOPS_NODE);
        const fdt32_t trimmed_reg[] = {
            0, cpu_to_fdt32(RAMOOPS_BASE), 0, cpu_to_fdt32(3 * ZONE_SIZE),
        };
        /* Keep the existing dump/console/ftrace zones at their original
         * addresses. Reserve the PMSG tail without binding a driver to it.
         * The original Magisk DT can bind the full area again on return.
         */
        if (ram < 0 || fdt_setprop(scratch, ram, "reg", trimmed_reg, sizeof(trimmed_reg)) ||
            fdt_setprop_u32(scratch, ram, "pmsg-size", 0) ||
            fdt_add_mem_rsv(scratch, PMSG_BASE, ZONE_SIZE))
            return NULL;
        chosen = fdt_path_offset(scratch, "/chosen");
        if (chosen < 0)
            return NULL;
        if (mark_cmdline(scratch, chosen))
            return NULL;
    }

    if (fdt_pack(scratch))
        return NULL;
    if (trace)
        PUBLISH(offset, "handoff-ready");
    return scratch;
}
