/* SPDX-License-Identifier: GPL-2.0-only */
/* Live prefix witness. Readback never claims a store by the current attempt. */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <lib/libfdt/libfdt.h>
#include "g0q-android-marker.h"
#include "logm-layout.h"

#define LOG_BASE 0x800200000ULL
#define LOG_PAYLOAD (0x200000U - 16U)
#define REPORT_PROPERTY "codex,uniloader-prefix-v1"

const unsigned char g0q_prefix_report_seed[256] = G0Q_PREFIX_REPORT_SEED;
extern const unsigned char g0q_prefix_image[], g0q_prefix_image_end[];
extern const unsigned char s22_retained_loader_frame[];
void s22_retained_loader(void);
void g0q_prefix_enter(uint64_t result[4], void *fdt);

static void put(volatile unsigned char *p, uint32_t value)
{
    p[0] = value >> 24; p[1] = value >> 16; p[2] = value >> 8; p[3] = value;
}

static void put64(volatile unsigned char *p, uint64_t value)
{
    put(p, value >> 32); put(p + 4, value);
}

static void barrier(void) { __asm__ volatile("dsb sy" ::: "memory"); }

static void park(void)
{
    for (;;) __asm__ volatile("wfe");
}

static void snapshot(volatile unsigned char *row, unsigned site, int after,
                     const unsigned char *frame)
{
    volatile const uint32_t *p = (const volatile uint32_t *)(uintptr_t)LOG_BASE;
    uint32_t h[4];
    for (unsigned i = 0; i < 4; ++i) { h[i] = p[i]; put(row + (after ? 16 : 0) + i * 4, h[i]); }
    if (!after || h[1] != 0x4d474f4cU || h[2] < 256) return;
    uint32_t c = h[2] % LOG_PAYLOAD;
    uint32_t slot = (c >= 256 ? c - 256 : LOG_PAYLOAD - 256) + site * 128;
    volatile const unsigned char *bytes = (const volatile unsigned char *)(uintptr_t)(LOG_BASE + 16 + slot);
    unsigned mismatch = 0;
    for (unsigned i = 0; i < 128; ++i) if (bytes[i] != frame[i]) ++mismatch;
    put(row + 32, slot); put(row + 36, mismatch); put(row + 40, 1);
}

__attribute__((noinline)) void g0q_prefix_control(void *fdt)
{
    int length;
    if ((uintptr_t)fdt != CONFIG_DTB_ENTRY) park();
    int chosen = fdt_path_offset(fdt, "/chosen");
    volatile unsigned char *report = fdt_getprop_w(fdt, chosen, REPORT_PROPERTY, &length);
    if (!report || length != 256 || !equal_bytes((const void *)report, g0q_prefix_report_seed, 256)) park();
    uint64_t el, sctlr = 0, result[4] = {0,0,0,0};
    uint32_t state = G0Q_PREFIX_SKIP_STATE;
    __asm__ volatile("mrs %0, CurrentEL" : "=r"(el));
    put64(report + 48, el);
    if (el == 4) __asm__ volatile("mrs %0, sctlr_el1" : "=r"(sctlr));
    else if (el == 8) __asm__ volatile("mrs %0, sctlr_el2" : "=r"(sctlr));
    else goto done;
    put64(report + 56, sctlr);
    if (sctlr & (5ULL | 4096 | (1ULL << 25))) goto done;
    state = G0Q_PREFIX_SKIP_FDT;
    if (!log_layout(fdt)) goto done;

    memcpy((void *)CONFIG_PAYLOAD_ENTRY, g0q_prefix_image,
           (size_t)(g0q_prefix_image_end - g0q_prefix_image));
    snapshot(report + 96, 0, 0, s22_retained_loader_frame);
    s22_retained_loader();
    snapshot(report + 96, 0, 1, s22_retained_loader_frame);
    const unsigned char *frame = (const unsigned char *)CONFIG_PAYLOAD_ENTRY + G0Q_PREFIX_FRAME_OFFSET;
    snapshot(report + 144, 1, 0, frame);
    g0q_prefix_enter(result, fdt);
    if (result[0] != CONFIG_PAYLOAD_ENTRY + G0Q_PREFIX_ENTRY_OFFSET || result[1] != el ||
        result[2] != sctlr || result[3] != G0Q_PREFIX_COOKIE) park();
    for (unsigned i = 0; i < 4; ++i) put64(report + 64 + i * 8, result[i]);
    snapshot(report + 144, 1, 1, frame);
    state = G0Q_PREFIX_RETURNED;
done:
    barrier(); put(report + 12, state); barrier();
}
