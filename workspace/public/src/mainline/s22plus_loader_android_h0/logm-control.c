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

#include "logm-layout.h"

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
