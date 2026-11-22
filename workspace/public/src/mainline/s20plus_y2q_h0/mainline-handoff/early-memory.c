/* SPDX-License-Identifier: GPL-2.0-only */
/* Byte accesses are valid for the unaligned libfdt strings and overlapping
 * slices before the CPU has enabled translation for normal cacheable RAM. */
#include <stddef.h>
#include <stdint.h>

void *memcpy(void *destination, const void *source, size_t count)
{
    volatile unsigned char *to = destination;
    const volatile unsigned char *from = source;
    for (size_t i = 0; i < count; i++)
        to[i] = from[i];
    return destination;
}

void *memmove(void *destination, const void *source, size_t count)
{
    uintptr_t to_addr = (uintptr_t)destination;
    uintptr_t from_addr = (uintptr_t)source;
    if (to_addr <= from_addr || to_addr - from_addr >= count)
        return memcpy(destination, source, count);
    volatile unsigned char *to = destination;
    const volatile unsigned char *from = source;
    while (count) {
        count--;
        to[count] = from[count];
    }
    return destination;
}

void *memset(void *destination, int value, size_t count)
{
    volatile unsigned char *to = destination;
    for (size_t i = 0; i < count; i++)
        to[i] = (unsigned char)value;
    return destination;
}
