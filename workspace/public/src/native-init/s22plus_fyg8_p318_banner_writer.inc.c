/* P3.18 one-shot ACM banner attempt with one absolute monotonic deadline. */

#define S22PLUS_P318_BANNER_SIZE 49U
#define S22PLUS_P318_BANNER_DEADLINE_SEC 5LL
#define S22PLUS_P318_BANNER_POLL_NS 100000000LL
#define S22PLUS_P318_NSEC_PER_SEC 1000000000LL

#define S22PLUS_P318_ERRNO_EINTR 4L
#define S22PLUS_P318_ERRNO_EIO 5L
#define S22PLUS_P318_ERRNO_EAGAIN 11L
#define S22PLUS_P318_ERRNO_ENODEV 19L
#define S22PLUS_P318_ERRNO_EPIPE 32L
#define S22PLUS_P318_ERRNO_ETIMEDOUT 110L

enum s22plus_p318_banner_outcome {
    S22PLUS_P318_BANNER_NOT_ATTEMPTED = 0,
    S22PLUS_P318_BANNER_WRITTEN = 1,
    S22PLUS_P318_BANNER_EAGAIN_TIMEOUT = 2,
    S22PLUS_P318_BANNER_FAILURE = 3,
    S22PLUS_P318_BANNER_PARTIAL = 4,
};

enum s22plus_p318_banner_error_class {
    S22PLUS_P318_BANNER_ERROR_NONE = 0,
    S22PLUS_P318_BANNER_ERROR_EAGAIN_DEADLINE = 1,
    S22PLUS_P318_BANNER_ERROR_EINTR_DEADLINE = 2,
    S22PLUS_P318_BANNER_ERROR_EPIPE = 3,
    S22PLUS_P318_BANNER_ERROR_ENODEV = 4,
    S22PLUS_P318_BANNER_ERROR_ETIMEDOUT = 5,
    S22PLUS_P318_BANNER_ERROR_ZERO_WRITE = 6,
    S22PLUS_P318_BANNER_ERROR_INVALID_WRITE = 7,
    S22PLUS_P318_BANNER_ERROR_CLOCK = 8,
    S22PLUS_P318_BANNER_ERROR_OTHER = 9,
};

enum s22plus_p318_banner_retry_reason {
    S22PLUS_P318_BANNER_RETRY_NONE = 0,
    S22PLUS_P318_BANNER_RETRY_EINTR = 1,
    S22PLUS_P318_BANNER_RETRY_EAGAIN = 2,
};

struct s22plus_p318_banner_result {
    uint8_t outcome;
    uint8_t error_class;
    uint8_t bytes_written;
};

struct s22plus_p318_banner_ops {
    long (*clock_gettime)(void *context, struct timespec64 *value);
    long (*write)(void *context, int fd, const char *data, size_t size);
    long (*sleep_ns)(void *context, int64_t nanoseconds);
    void *context;
};

_Static_assert(S22PLUS_P318_BANNER_SIZE <= 255U,
    "P3.18 banner byte count must fit one byte");
_Static_assert(sizeof(struct s22plus_p318_banner_result) == 3U,
    "P3.18 banner result must remain three bytes");

static int s22plus_p318_timespec_valid(const struct timespec64 *value) {
    return value->tv_nsec >= 0 && value->tv_nsec < S22PLUS_P318_NSEC_PER_SEC;
}

static int s22plus_p318_timespec_before(
    const struct timespec64 *left, const struct timespec64 *right) {
    return left->tv_sec < right->tv_sec ||
        (left->tv_sec == right->tv_sec && left->tv_nsec < right->tv_nsec);
}

static int64_t s22plus_p318_sleep_cap_ns(
    const struct timespec64 *now, const struct timespec64 *deadline) {
    int64_t seconds = deadline->tv_sec - now->tv_sec;
    int64_t remaining;

    if (seconds > 1)
        return S22PLUS_P318_BANNER_POLL_NS;
    remaining = seconds * S22PLUS_P318_NSEC_PER_SEC +
        deadline->tv_nsec - now->tv_nsec;
    if (remaining <= 0)
        return 0;
    return remaining < S22PLUS_P318_BANNER_POLL_NS
        ? remaining : S22PLUS_P318_BANNER_POLL_NS;
}

static uint8_t s22plus_p318_errno_class(long rc) {
    if (rc == -S22PLUS_P318_ERRNO_EPIPE)
        return S22PLUS_P318_BANNER_ERROR_EPIPE;
    if (rc == -S22PLUS_P318_ERRNO_ENODEV)
        return S22PLUS_P318_BANNER_ERROR_ENODEV;
    if (rc == -S22PLUS_P318_ERRNO_ETIMEDOUT)
        return S22PLUS_P318_BANNER_ERROR_ETIMEDOUT;
    return S22PLUS_P318_BANNER_ERROR_OTHER;
}

static struct s22plus_p318_banner_result s22plus_p318_finish_error(
    size_t written, uint8_t error_class) {
    struct s22plus_p318_banner_result result = {0};

    result.outcome = written == 0U
        ? (error_class == S22PLUS_P318_BANNER_ERROR_EAGAIN_DEADLINE
            ? S22PLUS_P318_BANNER_EAGAIN_TIMEOUT
            : S22PLUS_P318_BANNER_FAILURE)
        : S22PLUS_P318_BANNER_PARTIAL;
    result.error_class = error_class;
    result.bytes_written = (uint8_t)written;
    return result;
}

static struct s22plus_p318_banner_result s22plus_p318_banner_attempt_with_ops(
    int fd, const char *banner, size_t size,
    const struct s22plus_p318_banner_ops *ops) {
    struct timespec64 deadline = {0};
    enum s22plus_p318_banner_retry_reason retry_reason =
        S22PLUS_P318_BANNER_RETRY_NONE;
    size_t written = 0U;

    if (fd < 0 || banner == NULL || size != S22PLUS_P318_BANNER_SIZE ||
        ops == NULL ||
        ops->clock_gettime == NULL || ops->write == NULL ||
        ops->sleep_ns == NULL) {
        return s22plus_p318_finish_error(
            0U, S22PLUS_P318_BANNER_ERROR_INVALID_WRITE);
    }
    if (ops->clock_gettime(ops->context, &deadline) != 0 ||
        !s22plus_p318_timespec_valid(&deadline)) {
        return s22plus_p318_finish_error(
            0U, S22PLUS_P318_BANNER_ERROR_CLOCK);
    }
    deadline.tv_sec += S22PLUS_P318_BANNER_DEADLINE_SEC;

    while (written < size) {
        struct timespec64 now = {0};
        long rc;

        if (ops->clock_gettime(ops->context, &now) != 0 ||
            !s22plus_p318_timespec_valid(&now)) {
            return s22plus_p318_finish_error(
                written, S22PLUS_P318_BANNER_ERROR_CLOCK);
        }
        if (!s22plus_p318_timespec_before(&now, &deadline)) {
            uint8_t error_class = S22PLUS_P318_BANNER_ERROR_ETIMEDOUT;
            if (retry_reason == S22PLUS_P318_BANNER_RETRY_EAGAIN)
                error_class = S22PLUS_P318_BANNER_ERROR_EAGAIN_DEADLINE;
            else if (retry_reason == S22PLUS_P318_BANNER_RETRY_EINTR)
                error_class = S22PLUS_P318_BANNER_ERROR_EINTR_DEADLINE;
            return s22plus_p318_finish_error(written, error_class);
        }

        rc = ops->write(ops->context, fd, banner + written, size - written);
        if (rc == -S22PLUS_P318_ERRNO_EINTR) {
            retry_reason = S22PLUS_P318_BANNER_RETRY_EINTR;
            continue;
        }
        if (rc == -S22PLUS_P318_ERRNO_EAGAIN) {
            int64_t sleep_ns;
            long sleep_rc;

            retry_reason = S22PLUS_P318_BANNER_RETRY_EAGAIN;
            if (ops->clock_gettime(ops->context, &now) != 0 ||
                !s22plus_p318_timespec_valid(&now)) {
                return s22plus_p318_finish_error(
                    written, S22PLUS_P318_BANNER_ERROR_CLOCK);
            }
            if (!s22plus_p318_timespec_before(&now, &deadline)) {
                return s22plus_p318_finish_error(
                    written, S22PLUS_P318_BANNER_ERROR_EAGAIN_DEADLINE);
            }
            sleep_ns = s22plus_p318_sleep_cap_ns(&now, &deadline);
            if (sleep_ns <= 0) {
                return s22plus_p318_finish_error(
                    written, S22PLUS_P318_BANNER_ERROR_EAGAIN_DEADLINE);
            }
            sleep_rc = ops->sleep_ns(ops->context, sleep_ns);
            if (sleep_rc != 0 && sleep_rc != -S22PLUS_P318_ERRNO_EINTR) {
                return s22plus_p318_finish_error(
                    written, s22plus_p318_errno_class(sleep_rc));
            }
            continue;
        }
        if (rc < 0) {
            return s22plus_p318_finish_error(
                written, s22plus_p318_errno_class(rc));
        }
        if (rc == 0) {
            return s22plus_p318_finish_error(
                written, S22PLUS_P318_BANNER_ERROR_ZERO_WRITE);
        }
        if ((size_t)rc > size - written) {
            return s22plus_p318_finish_error(
                written, S22PLUS_P318_BANNER_ERROR_INVALID_WRITE);
        }
        written += (size_t)rc;
        retry_reason = S22PLUS_P318_BANNER_RETRY_NONE;
    }

    {
        struct s22plus_p318_banner_result result = {
            .outcome = S22PLUS_P318_BANNER_WRITTEN,
            .error_class = S22PLUS_P318_BANNER_ERROR_NONE,
            .bytes_written = S22PLUS_P318_BANNER_SIZE,
        };
        return result;
    }
}

#ifndef S22PLUS_P318_BANNER_HOST_FIXTURE
static long s22plus_p318_banner_clock(
    void *context, struct timespec64 *value) {
    (void)context;
    return p241_clock_gettime(value);
}

static long s22plus_p318_banner_write(
    void *context, int fd, const char *data, size_t size) {
    (void)context;
    return sys_write(fd, data, size);
}

static long s22plus_p318_banner_sleep(void *context, int64_t nanoseconds) {
    (void)context;
    return sys_nanosleep(nanoseconds);
}

static struct s22plus_p318_banner_result s22plus_p318_banner_attempt(int fd) {
    static const struct s22plus_p318_banner_ops operations = {
        .clock_gettime = s22plus_p318_banner_clock,
        .write = s22plus_p318_banner_write,
        .sleep_ns = s22plus_p318_banner_sleep,
        .context = NULL,
    };

    _Static_assert(sizeof(p260_banner) - 1U == S22PLUS_P318_BANNER_SIZE,
        "P3.18 encoder assumes the exact P2.60 49-byte banner");
    return s22plus_p318_banner_attempt_with_ops(
        fd, p260_banner, sizeof(p260_banner) - 1U, &operations);
}
#endif
