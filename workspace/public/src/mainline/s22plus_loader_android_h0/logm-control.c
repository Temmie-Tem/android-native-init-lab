/* SPDX-License-Identifier: GPL-2.0-only */
/* One header-preserving LOGM probe after the final kernel/FDT copies.
 * Diagnostic readback is not persistence, recovery or boot-attempt identity.
 */
#include <stdint.h>
#include <stddef.h>
#include <lib/libfdt/libfdt.h>
#include "g0q-android-marker.h"

#ifdef G0Q_LOGM_CONTROL
#define LOG_BASE 0x800200000ULL
#define LOG_PAYLOAD (0x200000U - 16U)
#define REPORT_PROPERTY "codex,uniloader-logm-v1"

const unsigned char g0q_logm_frame[128] = G0Q_LOGM_FRAME;
const unsigned char g0q_logm_report_seed[128] = G0Q_LOGM_REPORT_SEED;

static int equal_bytes(const void *a, const void *b, unsigned n)
{
    const unsigned char *x = a, *y = b;
    for (unsigned i = 0; i < n; ++i) if (x[i] != y[i]) return 0;
    return 1;
}

static int property(const void *fdt, int node, const char *name,
                    const void *expected, unsigned size)
{
    int length;
    const void *p = fdt_getprop(fdt, node, name, &length);
    if (!p || length != (int)size || !equal_bytes(p, expected, size)) return 0;
    unsigned count = 0;
    int offset;
    fdt_for_each_property_offset(offset, fdt, node) {
        const char *key;
        if (!fdt_getprop_by_offset(fdt, offset, &key, &length)) return 0;
        unsigned i = 0;
        while (key[i] && name[i] && key[i] == name[i]) ++i;
        if (!key[i] && !name[i]) ++count;
    }
    return offset == -FDT_ERR_NOTFOUND && count == 1;
}

static int absent(const void *fdt, int node, const char *name)
{
    int length;
    return !fdt_getprop(fdt, node, name, &length) && length == -FDT_ERR_NOTFOUND;
}

static int active(const void *fdt, int node)
{
    return node >= 0 && (absent(fdt, node, "status") ||
        property(fdt, node, "status", "okay", 5) || property(fdt, node, "status", "ok", 3));
}

static int named(const void *fdt, int node, const char *name, unsigned size)
{
    int length;
    const char *p = fdt_get_name(fdt, node, &length);
    return p && length == (int)size && equal_bytes(p, name, size);
}

static int log_layout(const void *fdt)
{
    static const unsigned char log_reg[16] = {0,0,0,8,0,0x20,0,0,0,0,0,0,0,0x20,0,0};
    static const unsigned char reserved_reg[16] = {0,0,0,8,0,0x1f,0xf0,0,0,0,0,0,0,0x90,0x10,0};
    static const unsigned char two[4] = {0,0,0,2}, three[4] = {0,0,0,3};
    const char *log_name = "samsung,kernel_log_buf", *reserved_name = "sec_debug_region_log@8001FF000";
    int log = fdt_path_offset(fdt, "/soc/samsung,kernel_log_buf");
    int reserved = fdt_path_offset(fdt, "/reserved-memory/sec_debug_region_log@8001FF000");
    if (!active(fdt, log) || !active(fdt, reserved) ||
        !active(fdt, fdt_path_offset(fdt, "/soc")) ||
        !active(fdt, fdt_path_offset(fdt, "/reserved-memory")) ||
        !named(fdt, log, log_name, 22) || !named(fdt, reserved, reserved_name, 30) ||
        !property(fdt, log, "compatible", "samsung,kernel_log_buf", 23) ||
        !property(fdt, reserved, "compatible", "samsung,carve-out", 18) ||
        !property(fdt, log, "reg", log_reg, 16) ||
        !property(fdt, reserved, "reg", reserved_reg, 16) ||
        !property(fdt, log, "#address-cells", two, 4) ||
        !property(fdt, log, "#size-cells", two, 4) ||
        !property(fdt, log, "sec,strategy", three, 4) ||
        !property(fdt, log, "sec,use-partial_reserved_mem", "", 0) ||
        !property(fdt, log, "sec,use-last_kmsg_compression", "", 0) ||
        !property(fdt, log, "sec,last_kmsg_compressor", "zstd", 5) ||
        !absent(fdt, reserved, "no-map") || !absent(fdt, reserved, "reusable")) return 0;
    int length;
    const fdt32_t *ref = fdt_getprop(fdt, log, "memory-region", &length);
    if (!ref || length != 4 || !property(fdt, log, "memory-region", ref, 4)) return 0;
    uint32_t phandle = fdt32_to_cpu(*ref);
    if (!phandle || phandle == 0xffffffffU || fdt_get_phandle(fdt, reserved) != phandle) return 0;
    unsigned log_count = 0, name_count = 0, reserved_count = 0, refs = 0;
    int depth = 0, node = -1;
    while ((node = fdt_next_node(fdt, node, &depth)) >= 0) {
        if (!absent(fdt, node, "linux,phandle") || !absent(fdt, node, "ibm,phandle")) return 0;
        int phandle_size;
        const void *handle = fdt_getprop(fdt, node, "phandle", &phandle_size);
        if (handle && !property(fdt, node, "phandle", handle, 4)) return 0;
        if (fdt_node_check_compatible(fdt, node, log_name) == 0) ++log_count;
        if (named(fdt, node, log_name, 22)) ++name_count;
        if (named(fdt, node, reserved_name, 30)) ++reserved_count;
        if (fdt_get_phandle(fdt, node) == phandle) ++refs;
    }
    return node == -FDT_ERR_NOTFOUND && log_count == 1 && name_count == 1 &&
        reserved_count == 1 && refs == 1;
}

/* The property has only four-byte alignment. Explicit byte encoding also
 * keeps its wire byte order independent from the native LOGM header. */
static void put(volatile unsigned char *report, unsigned offset, uint32_t value)
{
    report[offset] = value >> 24; report[offset + 1] = value >> 16;
    report[offset + 2] = value >> 8; report[offset + 3] = value;
}

static void barrier(void) { __asm__ volatile("dsb sy" ::: "memory"); }

__attribute__((noinline)) void g0q_logm_control(void *fdt)
{
    int length, chosen;
    if ((uintptr_t)fdt != CONFIG_DTB_ENTRY) return;
    chosen = fdt_path_offset(fdt, "/chosen");
    volatile unsigned char *report = fdt_getprop_w(fdt, chosen, REPORT_PROPERTY, &length);
    if (!report || length != 128 || !equal_bytes((const void *)report, g0q_logm_report_seed, 128)) return;
    uint64_t el, sctlr = 0;
    uint32_t status = G0Q_LOGM_SKIP_STATE, flags = 0, before[4], check[4], after[4];
    __asm__ volatile("mrs %0, CurrentEL" : "=r"(el));
    put(report, 48, (uint32_t)el);
    if (el == 4) __asm__ volatile("mrs %0, sctlr_el1" : "=r"(sctlr));
    else if (el == 8) __asm__ volatile("mrs %0, sctlr_el2" : "=r"(sctlr));
    else goto done;
    put(report, 52, (uint32_t)sctlr);
    if (sctlr & (1ULL | 4 | (1ULL << 25))) goto done;
    status = G0Q_LOGM_SKIP_FDT;
    if (!log_layout(fdt)) goto done;
    flags |= 128;
    volatile const uint32_t *header = (const volatile uint32_t *)(uintptr_t)LOG_BASE;
    for (unsigned i = 0; i < 4; ++i) { before[i] = header[i]; put(report, 64 + i * 4, before[i]); }
    flags |= 1;
    status = G0Q_LOGM_SKIP_MAGIC;
    if (before[1] != 0x4d474f4cU) goto done;
    status = G0Q_LOGM_SKIP_INDEX;
    if (before[2] < 256) goto done;
    uint32_t cursor = before[2] % LOG_PAYLOAD;
    uint32_t slot = cursor >= 256 ? cursor - 256 : LOG_PAYLOAD - 256;
    put(report, 56, slot);
    volatile unsigned char *destination = (volatile unsigned char *)(uintptr_t)(LOG_BASE + 16 + slot);
    for (unsigned i = 0; i < 8; ++i) destination[i] = 0;
    barrier(); flags |= 2;
    for (unsigned i = 8; i < 128; ++i) destination[i] = g0q_logm_frame[i];
    barrier(); flags |= 4;
    for (unsigned i = 0; i < 4; ++i) { check[i] = header[i]; put(report, 80 + i * 4, check[i]); }
    flags |= 8;
    status = G0Q_LOGM_HEADER_CHANGED;
    for (unsigned i = 0; i < 4; ++i) if (check[i] != before[i]) goto done;
    for (unsigned i = 0; i < 8; ++i) destination[i] = g0q_logm_frame[i];
    barrier(); flags |= 16;
    uint32_t mismatches = 0;
    for (unsigned i = 0; i < 128; ++i) if (destination[i] != g0q_logm_frame[i]) ++mismatches;
    flags |= 32; put(report, 60, mismatches);
    for (unsigned i = 0; i < 4; ++i) { after[i] = header[i]; put(report, 96 + i * 4, after[i]); }
    flags |= 64;
    status = mismatches ? G0Q_LOGM_READBACK_MISMATCH : G0Q_LOGM_READBACK_MATCH;
done:
    put(report, 112, flags);
    barrier(); put(report, 12, status); barrier();
}
#endif
