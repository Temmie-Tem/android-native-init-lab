/* SPDX-License-Identifier: GPL-2.0-only */
/* Before relocation: bounded FDT reads, no stack, calls, or memory stores.
 * The build checks the actual ARM64 instructions. x28 belongs to entry.S.
 * This deliberately accepts only the retained g0q two-cell memory topology.
 */
#include <stdint.h>
#include <stddef.h>
#include "g0q-android-marker.h"

#define INLINE static __attribute__((always_inline)) inline
#ifdef G0Q_LOGM_CONTROL
#define FDT_MAX (2U * 1024U * 1024U - 512U)
#define LOG_BASE 0x800200000ULL
#define LOG_END 0x800400000ULL
#else
#define FDT_MAX (2U * 1024U * 1024U - 256U)
#endif
#define BANKS 5
#define WRITES 3

struct range { uint64_t start, end; };
struct guard_plan {
    struct range writes[WRITES]; /* staging runtime, kernel runtime, new FDT */
    struct range ram[BANKS];
};

INLINE uint32_t be32(const unsigned char *p)
{
    return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 |
           (uint32_t)p[2] << 8 | p[3];
}

INLINE uint64_t be64(const unsigned char *p)
{
    return (uint64_t)be32(p) << 32 | be32(p + 4);
}

INLINE int overlap(uint64_t a, uint64_t b, uint64_t c, uint64_t d)
{
    return a < d && c < b;
}

INLINE int covered(const struct guard_plan *p, uint64_t a, uint64_t n)
{
    if (!n || n > ~(uint64_t)0 - a) return 0;
    for (unsigned i = 0; i < BANKS; ++i)
        if (p->ram[i].start <= a && a + n <= p->ram[i].end) return 1;
    return 0;
}

INLINE int protected(const struct guard_plan *p, uint64_t a, uint64_t n)
{
    if (!n) return 1;
    if (n > ~(uint64_t)0 - a) return 0;
    for (unsigned i = 0; i < WRITES; ++i)
        if (overlap(a, a + n, p->writes[i].start, p->writes[i].end)) return 0;
    return 1;
}

/* n excludes the terminator, whose existence the caller has checked. */
INLINE int equal(const unsigned char *a, uint32_t n, const char *b)
{
    uint32_t i = 0;
    while (i < n && b[i] && a[i] == (unsigned char)b[i]) ++i;
    return i == n && b[i] == 0;
}

__attribute__((section(".head.text"), noinline))
int loader_guard(const unsigned char *f, const struct guard_plan *p,
                 uint64_t source, uint64_t source_end)
{
    uint64_t address = (uint64_t)(uintptr_t)f;
    if ((address & 7) || !covered(p, address, 40) || be32(f) != 0xd00dfeedU)
        return 0;
    uint32_t total = be32(f + 4), pos = be32(f + 8), strings = be32(f + 12);
    uint32_t reserve = be32(f + 16), string_size = be32(f + 32);
    uint32_t struct_size = be32(f + 36);
    if (total < 40 || total > FDT_MAX || !covered(p, address, total) ||
        !protected(p, address, total) || overlap(address, address + total, source, source_end) ||
        be32(f + 20) != 17 || be32(f + 24) > 17 ||
        pos < 40 || (pos & 3) || struct_size < 16 || (struct_size & 3) ||
        pos > total || struct_size > total - pos || strings < 40 ||
        strings > total || string_size > total - strings || !string_size ||
        overlap(pos, pos + struct_size, strings, strings + string_size) ||
        reserve < 40 || (reserve & 7) || reserve >= pos || reserve >= strings)
        return 0;
#ifdef G0Q_LOGM_CONTROL
    if (!covered(p, LOG_BASE, LOG_END - LOG_BASE) ||
        !protected(p, LOG_BASE, LOG_END - LOG_BASE) ||
        overlap(LOG_BASE, LOG_END, address, address + total) ||
        overlap(LOG_BASE, LOG_END, source, source_end)) return 0;
#endif
    uint32_t reserve_limit = pos < strings ? pos : strings;
    for (;;) {
        if (reserve > reserve_limit || reserve_limit - reserve < 16) return 0;
        uint64_t start = be64(f + reserve), size = be64(f + reserve + 8);
        reserve += 16;
        if (!start && !size) break;
        if (!size || !protected(p, start, size)) return 0;
    }

    uint32_t end = pos + struct_size, depth = 0, section = 0, seen = 0;
    uint32_t child_reg = 0;
    uint64_t initrd_start = 0, initrd_end = 0;
    /* seen: root cells 0/1; chosen/reserved/memory nodes 2/3/4;
     * reserved cells/ranges 5/6/7; initrd 8/9; memory reg/type 10/11. */
    while (pos <= end && end - pos >= 4) {
        uint32_t token = be32(f + pos);
        pos += 4;
        if (token == 1) {
            uint32_t name = pos;
            while (pos < end && f[pos]) ++pos;
            if (pos == end || pos - name > 255 || depth == 64) return 0;
            uint32_t length = pos - name;
            pos = (pos + 4U) & ~3U;
            if (pos > end || (!depth && (length || seen))) return 0;
            if (!depth) seen |= 1U << 12;
            if (depth == 1) {
                /* libfdt path lookup also matches unit-address suffixes.
                 * This exact profile admits only the retained bare names;
                 * never guard one node and hand a different alias to Linux.
                 */
                if ((length >= 7 && (equal(f + name, 7, "chosen@") ||
                                     equal(f + name, 7, "memory@"))) ||
                    (length >= 16 && equal(f + name, 16, "reserved-memory@"))) return 0;
                uint32_t bit = 0;
                section = 0;
                if (equal(f + name, length, "chosen")) { bit = 1U << 2; section = 1; }
                if (equal(f + name, length, "reserved-memory")) { bit = 1U << 3; section = 2; }
                if (equal(f + name, length, "memory")) { bit = 1U << 4; section = 3; }
                if (bit && (seen & bit)) return 0;
                seen |= bit;
            }
            if (section == 2) {
                if (depth > 2) return 0;
                child_reg = 0;
            }
            ++depth;
        } else if (token == 2) {
            if (!depth) return 0;
            if (depth == 2) section = 0;
            --depth;
        } else if (token == 3) {
            if (!depth || end - pos < 8) return 0;
            uint32_t size = be32(f + pos), nameoff = be32(f + pos + 4);
            pos += 8;
            if (size > end - pos || nameoff >= string_size) return 0;
            uint32_t n = nameoff;
            while (n < string_size && f[strings + n]) ++n;
            if (n == string_size || n - nameoff > 255) return 0;
            const unsigned char *name = f + strings + nameoff;
            uint32_t length = n - nameoff, bit = 0;
            if (depth == 2 && section != 3 && equal(name, length, "device_type") &&
                size == 7 && equal(f + pos, 6, "memory") && !f[pos + 6]) return 0;
            if (depth == 1 || (section == 2 && depth == 2)) {
                if (equal(name, length, "#address-cells")) bit = depth == 1 ? 1U : 1U << 5;
                if (equal(name, length, "#size-cells")) bit = depth == 1 ? 2U : 1U << 6;
                if (bit && (size != 4 || be32(f + pos) != 2)) return 0;
                if (section == 2 && equal(name, length, "ranges")) {
                    if (size) return 0;
                    bit = 1U << 7;
                }
            }
            if (section == 1 && depth == 2) {
                if (equal(name, length, "codex,uniloader-android-v1")) return 0;
#ifdef G0Q_LOGM_CONTROL
                if (equal(name, length, "codex,uniloader-logm-v1")) return 0;
#endif
                if (equal(name, length, "linux,initrd-start")) {
                    if (size != 8) return 0;
                    initrd_start = be64(f + pos); bit = 1U << 8;
                }
                if (equal(name, length, "linux,initrd-end")) {
                    if (size != 8) return 0;
                    initrd_end = be64(f + pos); bit = 1U << 9;
                }
            }
            if (section == 2 && depth == 3 && equal(name, length, "reg")) {
                if (child_reg || !size || (size & 15)) return 0;
                child_reg = 1;
                for (uint32_t j = 0; j < size; j += 16)
                    if (!protected(p, be64(f + pos + j), be64(f + pos + j + 8))) return 0;
            }
            if (section == 3 && depth == 2) {
                if (equal(name, length, "reg")) {
                    if (size != BANKS * 16) return 0;
                    for (unsigned j = 0; j < BANKS; ++j)
                        if (be64(f + pos + j * 16) != p->ram[j].start ||
                            be64(f + pos + j * 16 + 8) != p->ram[j].end - p->ram[j].start) return 0;
                    bit = 1U << 10;
                }
                if (equal(name, length, "device_type")) {
                    if (size != 7 || !equal(f + pos, 6, "memory") || f[pos + 6]) return 0;
                    bit = 1U << 11;
                }
            }
            if (bit && (seen & bit)) return 0;
            seen |= bit;
            pos = (pos + size + 3U) & ~3U;
            if (pos > end) return 0;
        } else if (token == 4) {
            continue;
        } else if (token == 9) {
            if (depth || pos != end || seen != 0x1fffU || initrd_start >= initrd_end ||
                initrd_end - initrd_start > 256U * 1024U * 1024U ||
                !covered(p, initrd_start, initrd_end - initrd_start) ||
                !protected(p, initrd_start, initrd_end - initrd_start) ||
                overlap(initrd_start, initrd_end, address, address + total)) return 0;
            /* Recompute the current source only after parsing. Keeping both
             * argument values live through the tree walk makes GCC spill.
             * Entry already requires the equal 4 KiB PC-relative slide. */
            uint64_t live_start, live_end;
            __asm__ volatile("adrp %0, _head\n\tadd %0, %0, :lo12:_head\n\t"
                             "adrp %1, _file_end\n\tadd %1, %1, :lo12:_file_end"
                             : "=&r"(live_start), "=&r"(live_end));
            if (overlap(initrd_start, initrd_end, live_start, live_end)) return 0;
#ifdef G0Q_LOGM_CONTROL
            if (overlap(LOG_BASE, LOG_END, initrd_start, initrd_end)) return 0;
#endif
            return 1;
        } else return 0;
    }
    return 0;
}
