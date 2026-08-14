// SPDX-License-Identifier: MIT

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

struct timespec64 {
    int64_t tv_sec;
    int64_t tv_nsec;
};

static char p260_banner[50] =
    "0123456789012345678901234567890123456789012345678";
static int clock_calls;
static int write_calls;

static long p241_clock_gettime(struct timespec64 *value) {
    value->tv_sec = clock_calls++;
    value->tv_nsec = 0;
    return 0;
}

static long sys_write(int fd, const char *data, size_t size) {
    (void)fd;
    (void)data;
    ++write_calls;
    return (long)size;
}

static long sys_nanosleep(int64_t nanoseconds) {
    (void)nanoseconds;
    return 0;
}

#include "s22plus_fyg8_p318_banner_writer.inc.c"

int main(void) {
    struct s22plus_p318_banner_result result =
        s22plus_p318_banner_attempt(9);

    if (result.outcome != S22PLUS_P318_BANNER_WRITTEN ||
        result.error_class != S22PLUS_P318_BANNER_ERROR_NONE ||
        result.bytes_written != 49U || write_calls != 1)
        return 1;
    printf("{\"schema\":\"s22plus_fyg8_p318_banner_runtime_fixture_v1\","
           "\"bytes\":49,\"verdict\":\"PASS\"}\n");
    return 0;
}
