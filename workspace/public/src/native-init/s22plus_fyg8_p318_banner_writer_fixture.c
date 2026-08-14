// SPDX-License-Identifier: MIT

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

struct timespec64 {
    int64_t tv_sec;
    int64_t tv_nsec;
};

#define S22PLUS_P318_BANNER_HOST_FIXTURE 1
#include "s22plus_fyg8_p318_banner_writer.inc.c"

#define MAX_WRITE_STEPS 8U

struct fixture_context {
    int64_t now_ns;
    int64_t clock_advance_ns;
    long clock_failure_at;
    long clock_calls;
    long writes[MAX_WRITE_STEPS];
    size_t write_count;
    size_t write_index;
    long default_write;
    long sleep_result;
    size_t sleep_count;
    int64_t largest_sleep_ns;
};

static long fixture_clock(void *opaque, struct timespec64 *value) {
    struct fixture_context *context = opaque;

    ++context->clock_calls;
    if (context->clock_failure_at > 0 &&
        context->clock_calls == context->clock_failure_at)
        return -S22PLUS_P318_ERRNO_EIO;
    value->tv_sec = context->now_ns / S22PLUS_P318_NSEC_PER_SEC;
    value->tv_nsec = context->now_ns % S22PLUS_P318_NSEC_PER_SEC;
    context->now_ns += context->clock_advance_ns;
    return 0;
}

static long fixture_write(
    void *opaque, int fd, const char *data, size_t size) {
    struct fixture_context *context = opaque;

    (void)fd;
    (void)data;
    (void)size;
    if (context->write_index < context->write_count)
        return context->writes[context->write_index++];
    return context->default_write;
}

static long fixture_sleep(void *opaque, int64_t nanoseconds) {
    struct fixture_context *context = opaque;

    ++context->sleep_count;
    if (nanoseconds > context->largest_sleep_ns)
        context->largest_sleep_ns = nanoseconds;
    context->now_ns += nanoseconds;
    return context->sleep_result;
}

static int expect(
    const char *name, struct fixture_context *context,
    uint8_t outcome, uint8_t error_class, uint8_t bytes_written) {
    static const char banner[S22PLUS_P318_BANNER_SIZE] = {0};
    const struct s22plus_p318_banner_ops operations = {
        .clock_gettime = fixture_clock,
        .write = fixture_write,
        .sleep_ns = fixture_sleep,
        .context = context,
    };
    struct s22plus_p318_banner_result result =
        s22plus_p318_banner_attempt_with_ops(
            7, banner, sizeof(banner), &operations);

    if (result.outcome != outcome || result.error_class != error_class ||
        result.bytes_written != bytes_written) {
        fprintf(stderr,
            "%s: got outcome=%u error=%u bytes=%u, expected %u/%u/%u\n",
            name, result.outcome, result.error_class, result.bytes_written,
            outcome, error_class, bytes_written);
        return 1;
    }
    if (context->largest_sleep_ns > S22PLUS_P318_BANNER_POLL_NS) {
        fprintf(stderr, "%s: sleep exceeded cap\n", name);
        return 1;
    }
    return 0;
}

int main(void) {
    unsigned int cases = 0U;
    struct fixture_context context;

#define RESET_CONTEXT() do { \
    memset(&context, 0, sizeof(context)); \
    context.default_write = S22PLUS_P318_BANNER_SIZE; \
} while (0)
#define RUN(name, outcome, error, bytes) do { \
    if (expect((name), &context, (outcome), (error), (bytes)) != 0) return 1; \
    ++cases; \
} while (0)

    RESET_CONTEXT();
    RUN("complete", S22PLUS_P318_BANNER_WRITTEN,
        S22PLUS_P318_BANNER_ERROR_NONE, 49U);

    RESET_CONTEXT();
    context.writes[0] = 10;
    context.writes[1] = 39;
    context.write_count = 2;
    RUN("short-then-complete", S22PLUS_P318_BANNER_WRITTEN,
        S22PLUS_P318_BANNER_ERROR_NONE, 49U);

    RESET_CONTEXT();
    context.writes[0] = -S22PLUS_P318_ERRNO_EAGAIN;
    context.writes[1] = 49;
    context.write_count = 2;
    RUN("eagain-then-complete", S22PLUS_P318_BANNER_WRITTEN,
        S22PLUS_P318_BANNER_ERROR_NONE, 49U);

    RESET_CONTEXT();
    context.default_write = -S22PLUS_P318_ERRNO_EAGAIN;
    RUN("eagain-deadline", S22PLUS_P318_BANNER_EAGAIN_TIMEOUT,
        S22PLUS_P318_BANNER_ERROR_EAGAIN_DEADLINE, 0U);
    if (context.sleep_count == 0U || context.now_ns < 5000000000LL)
        return 1;

    RESET_CONTEXT();
    context.default_write = -S22PLUS_P318_ERRNO_EINTR;
    context.clock_advance_ns = 1000000000LL;
    RUN("eintr-deadline", S22PLUS_P318_BANNER_FAILURE,
        S22PLUS_P318_BANNER_ERROR_EINTR_DEADLINE, 0U);

    RESET_CONTEXT();
    context.writes[0] = 12;
    context.write_count = 1;
    context.default_write = -S22PLUS_P318_ERRNO_EINTR;
    context.clock_advance_ns = 1000000000LL;
    RUN("short-eintr-deadline", S22PLUS_P318_BANNER_PARTIAL,
        S22PLUS_P318_BANNER_ERROR_EINTR_DEADLINE, 12U);

    RESET_CONTEXT();
    context.default_write = -S22PLUS_P318_ERRNO_EPIPE;
    RUN("epipe", S22PLUS_P318_BANNER_FAILURE,
        S22PLUS_P318_BANNER_ERROR_EPIPE, 0U);

    RESET_CONTEXT();
    context.writes[0] = 8;
    context.writes[1] = -S22PLUS_P318_ERRNO_EPIPE;
    context.write_count = 2;
    RUN("partial-epipe", S22PLUS_P318_BANNER_PARTIAL,
        S22PLUS_P318_BANNER_ERROR_EPIPE, 8U);

    RESET_CONTEXT();
    context.default_write = -S22PLUS_P318_ERRNO_ENODEV;
    RUN("enodev", S22PLUS_P318_BANNER_FAILURE,
        S22PLUS_P318_BANNER_ERROR_ENODEV, 0U);

    RESET_CONTEXT();
    context.default_write = -S22PLUS_P318_ERRNO_ETIMEDOUT;
    RUN("direct-timeout", S22PLUS_P318_BANNER_FAILURE,
        S22PLUS_P318_BANNER_ERROR_ETIMEDOUT, 0U);

    RESET_CONTEXT();
    context.default_write = 0;
    RUN("zero-write", S22PLUS_P318_BANNER_FAILURE,
        S22PLUS_P318_BANNER_ERROR_ZERO_WRITE, 0U);

    RESET_CONTEXT();
    context.default_write = 50;
    RUN("invalid-write", S22PLUS_P318_BANNER_FAILURE,
        S22PLUS_P318_BANNER_ERROR_INVALID_WRITE, 0U);

    RESET_CONTEXT();
    context.clock_failure_at = 1;
    RUN("initial-clock-failure", S22PLUS_P318_BANNER_FAILURE,
        S22PLUS_P318_BANNER_ERROR_CLOCK, 0U);

    RESET_CONTEXT();
    context.writes[0] = 7;
    context.write_count = 1;
    context.clock_failure_at = 3;
    RUN("partial-clock-failure", S22PLUS_P318_BANNER_PARTIAL,
        S22PLUS_P318_BANNER_ERROR_CLOCK, 7U);

    RESET_CONTEXT();
    context.default_write = -S22PLUS_P318_ERRNO_EAGAIN;
    context.sleep_result = -S22PLUS_P318_ERRNO_ENODEV;
    RUN("sleep-failure", S22PLUS_P318_BANNER_FAILURE,
        S22PLUS_P318_BANNER_ERROR_ENODEV, 0U);

    printf("{\"schema\":\"s22plus_fyg8_p318_banner_writer_fixture_v1\","
           "\"cases\":%u,\"verdict\":\"PASS\"}\n", cases);
    return 0;
}
