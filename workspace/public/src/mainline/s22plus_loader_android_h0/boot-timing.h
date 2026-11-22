/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef G0Q_BOOT_TIMING_H
#define G0Q_BOOT_TIMING_H

#include <stdint.h>

#define G0Q_TIMING_PROPERTY "codex,uniloader-timing-v1"
#define G0Q_TIMING_SIZE 128

extern const unsigned char g0q_timing_seed[G0Q_TIMING_SIZE];
extern const volatile uint32_t g0q_timing_logm;
extern uint64_t g0q_guard_ticks;

static inline uint64_t g0q_timing_ticks(void)
{
    uint64_t ticks;
    __asm__ volatile("isb\n\tmrs %0, cntvct_el0" : "=r"(ticks) :: "memory");
    return ticks;
}

static inline uint64_t g0q_timing_frequency(void)
{
    uint64_t frequency;
    __asm__ volatile("mrs %0, cntfrq_el0" : "=r"(frequency) :: "memory");
    return frequency;
}

void g0q_timing_publish(void *fdt, uint64_t frequency, uint64_t prepare_done,
                        uint64_t logm_begin, uint64_t logm_end);

#endif
