/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef G0Q_RESET_PIN_H
#define G0Q_RESET_PIN_H

#if defined(G0Q_RESET_CONFIG) && (!defined(G0Q_HCE_HANDOFF) || !defined(G0Q_PRE_EFFECT_RETURN))
#error "Dedicated reset configuration requires HCE handoff and explicit return"
#endif

/* V7 binds the complete observed dedicated-pad configuration. The UFS_RESET
 * table has no OE/input bit; a truncated -1 sentinel is not direction proof.
 * No CTL write is permitted. IO bit zero is an output latch, not pad sensing.
 * Older report modes retain their original BIT(31) predicate and provenance.
 */
#ifdef G0Q_RESET_CONFIG
#define G0Q_RESET_CTL_MASK (~0U)
#define G0Q_RESET_CTL_EXPECTED 0x0000000bU
#else
#define G0Q_RESET_CTL_MASK BIT(31)
#define G0Q_RESET_CTL_EXPECTED BIT(31)
#endif

static inline bool g0q_reset_ctl_admitted(u32 value)
{
	return (value & G0Q_RESET_CTL_MASK) == G0Q_RESET_CTL_EXPECTED;
}

#endif
