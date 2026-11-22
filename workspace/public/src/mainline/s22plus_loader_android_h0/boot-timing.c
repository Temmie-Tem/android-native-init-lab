/* SPDX-License-Identifier: GPL-2.0-only */
#include "g0q-android-marker.h"

#ifdef G0Q_BOOT_TIMING
#include <lib/libfdt/libfdt.h>
#include "boot-timing.h"

const unsigned char g0q_timing_seed[G0Q_TIMING_SIZE] = G0Q_TIMING_SEED;
const volatile uint32_t g0q_timing_logm = G0Q_TIMING_LOGM;
uint64_t g0q_guard_ticks;

static void put_be(volatile unsigned char *out, uint64_t value, unsigned int bytes)
{
    for (unsigned int i = 0; i < bytes; ++i)
        out[i] = value >> (8 * (bytes - 1 - i));
}

void g0q_timing_publish(void *fdt, uint64_t frequency, uint64_t prepare_done,
                        uint64_t logm_begin, uint64_t logm_end)
{
    if ((uintptr_t)fdt != CONFIG_DTB_ENTRY)
        return;

    int length;
    int chosen = fdt_path_offset(fdt, "/chosen");
    volatile unsigned char *report = fdt_getprop_w(fdt, chosen, G0Q_TIMING_PROPERTY, &length);
    if (!report || length != G0Q_TIMING_SIZE)
        return;
    for (unsigned int i = 0; i < G0Q_TIMING_SIZE; ++i)
        if (report[i] != g0q_timing_seed[i])
            return;

    uint32_t mode = g0q_timing_logm;
    if (!frequency || frequency > 0xffffffffULL || mode > 1 ||
        g0q_guard_ticks > prepare_done || prepare_done > logm_begin || logm_begin > logm_end)
        return;

    put_be(report + 48, mode, 4);
    put_be(report + 52, frequency, 4);
    put_be(report + 56, g0q_guard_ticks, 8);
    put_be(report + 64, prepare_done, 8);
    put_be(report + 72, logm_begin, 8);
    put_be(report + 80, logm_end, 8);
    put_be(report + 88, g0q_timing_ticks(), 8);

    __asm__ volatile("dsb sy" ::: "memory");
    put_be(report + 12, 1, 4);
    __asm__ volatile("dsb sy" ::: "memory");
}
#endif
