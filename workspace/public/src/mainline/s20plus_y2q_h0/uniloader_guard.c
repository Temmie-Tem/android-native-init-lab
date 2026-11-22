/* SPDX-License-Identifier: GPL-2.0-only */
/* Adapted from the repository's pre-stack FDT guard for a file-backed prefix. */
#include <stdint.h>
#include "uniloader_layout.h"

#define INLINE static inline __attribute__((always_inline))
#define PHYS_END (1ULL << 48)

INLINE uint32_t be32(const uint8_t *p)
{
    return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 |
           (uint32_t)p[2] << 8 | p[3];
}

INLINE uint64_t be64(const uint8_t *p)
{
    return (uint64_t)be32(p) << 32 | be32(p + 4);
}

INLINE int valid(uint64_t start, uint64_t size)
{
    return start < PHYS_END && size && size <= PHYS_END - start;
}

INLINE int overlap(uint64_t a, uint64_t b, uint64_t c, uint64_t d)
{
    return a < d && c < b;
}

INLINE int equal(const uint8_t *p, uint32_t length, const char *s)
{
    uint32_t i = 0;
    while (i < length && s[i] && p[i] == (uint8_t)s[i])
        ++i;
    return i == length && !s[i];
}

INLINE int lookalike(const uint8_t *p, uint32_t length, uint32_t prefix, const char *s)
{
    return length >= prefix && equal(p, prefix, s);
}

/* The entry ABI supplies a readable x0. All subsequent reads are bounded
 * by its header, and all stack/scratch writes wait for the memory check. */
__attribute__((section(".head.text"), noinline))
int y2q_guard(const uint8_t *fdt, uint64_t base)
{
    const uint64_t source = (uint64_t)(uintptr_t)fdt;
    const uint64_t end = base + Y2Q_WRAPPER_RUNTIME;
    if (!valid(base, Y2Q_WRAPPER_RUNTIME) || (source & 7) ||
        !source || !valid(source, 40) || overlap(base, end, source, source + 40) ||
        be32(fdt) != 0xd00dfeed)
        return 0;

    const uint32_t total = be32(fdt + 4), strings = be32(fdt + 12);
    uint32_t pos = be32(fdt + 8), reserve = be32(fdt + 16);
    const uint32_t strings_size = be32(fdt + 32), structure_size = be32(fdt + 36);
    if (total < 40 || total > Y2Q_FDT_CAPACITY - 256 ||
        !valid(source, total) || overlap(base, end, source, source + total) ||
        be32(fdt + 20) != 17 || be32(fdt + 24) > 17 ||
        pos < 40 || pos > total || (pos & 3) || structure_size < 16 ||
        (structure_size & 3) || structure_size > total - pos ||
        strings < 40 || strings > total || !strings_size || strings_size > total - strings ||
        overlap(pos, pos + structure_size, strings, strings + strings_size) ||
        reserve < 40 || (reserve & 7) || reserve >= pos || reserve >= strings)
        return 0;

    const uint32_t reserve_limit = pos < strings ? pos : strings;
    for (;;) {
        if (reserve > reserve_limit || reserve_limit - reserve < 16)
            return 0;
        const uint64_t address = be64(fdt + reserve), size = be64(fdt + reserve + 8);
        reserve += 16;
        if (!address && !size)
            break;
        if (!valid(address, size) || overlap(base, end, address, address + size))
            return 0;
    }

    const uint32_t limit = pos + structure_size;
    uint32_t depth = 0, seen = 0, child_reg = 0, child_size = 0;
    unsigned int section = 0;
    uint64_t memory_pos = 0, memory_size = 0, initrd_start = 0, initrd_end = 0;
    enum {
        ROOT_START = 1, ROOT_ADDR = 2, ROOT_SIZE = 4, CHOSEN = 8, MEMORY = 16,
        RESERVED = 32, RES_ADDR = 64, RES_SIZE = 128, RES_RANGES = 256,
        MEMORY_REG = 512, MEMORY_TYPE = 1024, INITRD_START = 2048, INITRD_END = 4096,
        COMPLETE = 8191,
    };
    while (pos < limit) {
        const uint32_t token = be32(fdt + pos);
        pos += 4;
        if (token == 1) {
            const uint32_t name = pos;
            while (pos < limit && fdt[pos])
                ++pos;
            const uint32_t length = pos - name;
            if (pos == limit || length > 255 || depth == 64)
                return 0;
            pos = (pos + 4) & ~3U;
            if (!depth) {
                if (length || seen)
                    return 0;
                seen |= ROOT_START;
            } else if (depth == 1) {
                if (lookalike(fdt + name, length, 7, "chosen@") ||
                    lookalike(fdt + name, length, 7, "memory@") ||
                    lookalike(fdt + name, length, 16, "reserved-memory@"))
                    return 0;
                section = equal(fdt + name, length, "chosen") ? CHOSEN :
                          equal(fdt + name, length, "memory") ? MEMORY :
                          equal(fdt + name, length, "reserved-memory") ? RESERVED : 0;
                if (seen & section)
                    return 0;
                seen |= section;
            } else if (section == RESERVED) {
                if (depth != 2)
                    return 0;
                child_reg = 0;
                child_size = 0;
            }
            ++depth;
        } else if (token == 2) {
            if (!depth)
                return 0;
            if (section == RESERVED && depth == 3 && !child_reg && !child_size)
                return 0;
            if (depth == 2)
                section = 0;
            --depth;
        } else if (token == 3) {
            if (!depth || limit - pos < 8)
                return 0;
            const uint32_t length = be32(fdt + pos), off = be32(fdt + pos + 4);
            pos += 8;
            if (length > limit - pos || off >= strings_size)
                return 0;
            uint32_t stop = off;
            while (stop < strings_size && fdt[strings + stop])
                ++stop;
            if (stop == strings_size || stop - off > 255)
                return 0;
            const uint8_t *name = fdt + strings + off;
            const uint32_t n = stop - off;
            unsigned int bit = 0;
            if (depth == 1 || (depth == 2 && section == RESERVED)) {
                if (equal(name, n, "#address-cells"))
                    bit = depth == 1 ? ROOT_ADDR : RES_ADDR;
                if (equal(name, n, "#size-cells"))
                    bit = depth == 1 ? ROOT_SIZE : RES_SIZE;
                if (bit && (length != 4 || be32(fdt + pos) != 2))
                    return 0;
                if (depth == 2 && equal(name, n, "ranges")) {
                    if (length)
                        return 0;
                    bit = RES_RANGES;
                }
            } else if (depth == 2 && equal(name, n, "device_type") &&
                       length == 7 && equal(fdt + pos, 6, "memory") && !fdt[pos + 6]) {
                if (section != MEMORY)
                    return 0;
                bit = MEMORY_TYPE;
            } else if (depth == 2 && section == MEMORY && equal(name, n, "reg")) {
                if (!length || (length & 15))
                    return 0;
                memory_pos = pos;
                memory_size = length;
                bit = MEMORY_REG;
            } else if (depth == 2 && section == CHOSEN) {
                if (equal(name, n, Y2Q_MARKER_PROPERTY))
                    return 0;
                if (equal(name, n, "linux,initrd-start"))
                    bit = INITRD_START;
                if (equal(name, n, "linux,initrd-end"))
                    bit = INITRD_END;
                if (bit) {
                    if (length != 4 && length != 8)
                        return 0;
                    const uint64_t value = length == 4 ? be32(fdt + pos) : be64(fdt + pos);
                    if (bit == INITRD_START)
                        initrd_start = value;
                    else
                        initrd_end = value;
                }
            } else if (depth == 3 && section == RESERVED && equal(name, n, "reg")) {
                if (child_reg || !length || (length & 15))
                    return 0;
                child_reg = 1;
                for (uint32_t i = 0; i < length; i += 16) {
                    const uint64_t address = be64(fdt + pos + i);
                    const uint64_t size = be64(fdt + pos + i + 8);
                    if (!valid(address, size) || overlap(base, end, address, address + size))
                        return 0;
                }
            } else if (depth == 3 && section == RESERVED && equal(name, n, "size")) {
                /* Linux allocates dynamic pools later. Keep their DTS properties. */
                if (child_size || length != 8 || !valid(0, be64(fdt + pos)))
                    return 0;
                child_size = 1;
            }
            if (seen & bit)
                return 0;
            seen |= bit;
            pos += (length + 3) & ~3U;
        } else if (token == 9) {
            if (depth || pos != limit || seen != COMPLETE ||
                !initrd_start || initrd_end <= initrd_start ||
                overlap(base, end, initrd_start, initrd_end) ||
                overlap(source, source + total, initrd_start, initrd_end))
                return 0;
            unsigned int coverage = 0;
            for (uint64_t i = memory_pos; i < memory_pos + memory_size; i += 16) {
                const uint64_t a = be64(fdt + i), size = be64(fdt + i + 8);
                if (!valid(a, size))
                    return 0;
                if (a <= base && end <= a + size)
                    coverage |= 1;
                if (a <= source && source + total <= a + size)
                    coverage |= 2;
                if (a <= initrd_start && initrd_end <= a + size)
                    coverage |= 4;
            }
            return coverage == 7;
        } else if (token != 4) {
            return 0;
        }
    }
    return 0;
}
