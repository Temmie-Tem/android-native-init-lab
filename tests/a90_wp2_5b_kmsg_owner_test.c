#define _GNU_SOURCE
#define A90_WP2_5B_HOST_TESTING 1

#include "a90_wp2_5b_kmsg_owner.h"
#include "a90_wp2_5b_kmsg_contract.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/audit.h>
#include <linux/seccomp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sysmacros.h>
#include <sys/syscall.h>

#ifndef AT_FDCWD
#define AT_FDCWD -100
#endif

#define TEST_TRACE_FD 7
#define TEST_KMSG_FD 8
#define TEST_CONTROL_CAP 1024u
#define TEST_TRACE_CAP 65536u
#define TEST_STATUS_CAP 4096u
#define TEST_FILTER_CAP 256u

#ifndef SECCOMP_RET_KILL_PROCESS
#define SECCOMP_RET_KILL_PROCESS SECCOMP_RET_KILL
#endif

enum test_mode {
    TEST_HAPPY = 0,
    TEST_EPIPE,
    TEST_EINVAL,
    TEST_EFAULT,
    TEST_READ_EINTR,
    TEST_ZERO_READ,
    TEST_READ_ERROR,
    TEST_POLLERR,
    TEST_POLL_FAILURE,
    TEST_POLL_EINTR,
    TEST_KMSG_HUP,
    TEST_SEQUENCE_GAP,
    TEST_DUPLICATE_CLOSE,
    TEST_PARTIAL_CLOSE,
    TEST_PARENT_EOF,
    TEST_WRONG_RDEV,
    TEST_WRONG_KMSG_FLAGS,
    TEST_CONFINEMENT_FAIL,
    TEST_LSEEK_FAIL,
    TEST_ARM_FSYNC_FAIL,
    TEST_RETAINED_EXEC_FD,
    TEST_SHORT_STATUS,
    TEST_FAULT_NO_CLOSE,
    TEST_FAULT_CLOSE_EINTR,
    TEST_FAULT_FSYNC_FAIL_NO_CLOSE,
    TEST_NORMAL_CLOSE_EINTR,
    TEST_PARENT_EOF_CLOSE_EINTR,
    TEST_FAULT_STATUS_FAIL_NO_CLOSE,
    TEST_FAULT_NORMAL_CLOSE,
    TEST_HEALTHY_FAULT_CLOSE,
    TEST_INVALID_CAUSE_THEN_FAULT_CLOSE,
    TEST_RESERVED_CLOSE_THEN_FAULT_CLOSE,
    TEST_UNKNOWN_KIND_THEN_FAULT_CLOSE,
    TEST_FAULTED_INVALID_CAUSE_THEN_FAULT_CLOSE,
    TEST_FINAL_END_WRITE_FAIL,
    TEST_FINAL_FSYNC_ENOSPC,
    TEST_FINAL_FSYNC_EIO,
    TEST_FINAL_FSYNC_EINTR,
    TEST_TRACE_CLOSE_EINTR,
    TEST_CLOSED_STATUS_SHORT,
    TEST_MALFORMED_RECORD,
    TEST_COUNT_CAP,
    TEST_BYTE_CAP,
};

struct fake_context {
    enum test_mode mode;
    unsigned char control[TEST_CONTROL_CAP];
    size_t control_length;
    size_t control_position;
    unsigned char trace[TEST_TRACE_CAP];
    size_t trace_length;
    unsigned char status[TEST_STATUS_CAP];
    size_t status_length;
    int open_count;
    int open_fds[9];
    int fd_flags[9];
    int kmsg_step;
    int pollerr_sent;
    int poll_interrupts;
    int confinement_calls;
    int lseek_calls;
    int fsync_calls;
    int close_calls[9];
    int fault_close_wait_polls;
    int faulted_status_saw_kmsg_closed;
    int final_end_partial_sent;
};

static void fail(const char *message)
{
    fprintf(stderr, "%s\n", message);
    exit(1);
}

static void require(int condition, const char *message)
{
    if (!condition)
        fail(message);
}

static void put_u16_be(unsigned char value[2], uint16_t input)
{
    value[0] = (unsigned char)(input >> 8);
    value[1] = (unsigned char)input;
}

static void put_u32_be(unsigned char value[4], uint32_t input)
{
    value[0] = (unsigned char)(input >> 24);
    value[1] = (unsigned char)(input >> 16);
    value[2] = (unsigned char)(input >> 8);
    value[3] = (unsigned char)input;
}

static void put_u64_be(unsigned char value[8], uint64_t input)
{
    unsigned int index;

    for (index = 0; index < 8; ++index)
        value[index] = (unsigned char)(input >> (56u - index * 8u));
}

static uint16_t get_u16_be(const unsigned char value[2])
{
    return (uint16_t)(((uint16_t)value[0] << 8) | value[1]);
}

static uint32_t get_u32_be(const unsigned char value[4])
{
    return ((uint32_t)value[0] << 24) | ((uint32_t)value[1] << 16) |
           ((uint32_t)value[2] << 8) | value[3];
}

static uint64_t get_u64_be(const unsigned char value[8])
{
    uint64_t output = 0;
    unsigned int index;

    for (index = 0; index < 8; ++index)
        output = (output << 8) | value[index];
    return output;
}

static void append_control_frame(struct fake_context *context, uint8_t kind,
                                 uint64_t sequence,
                                 const unsigned char *payload,
                                 uint16_t payload_length)
{
    unsigned char *frame;
    size_t total = A90_WP2_5B_OWNER_PIPE_HEADER_SIZE + payload_length;

    require(context->control_length + total <= sizeof(context->control),
            "control fixture overflow");
    frame = context->control + context->control_length;
    memcpy(frame, a90_wp2_5b_owner_magic, 8);
    put_u16_be(frame + 8, A90_WP2_5B_OWNER_VERSION);
    frame[10] = A90_WP2_5B_OWNER_DIRECTION_CONTROL;
    frame[11] = kind;
    put_u64_be(frame + 12, sequence);
    put_u16_be(frame + 20, payload_length);
    put_u16_be(frame + 22, 0);
    memcpy(frame + A90_WP2_5B_OWNER_PIPE_HEADER_SIZE, payload,
           payload_length);
    context->control_length += total;
}

static int mode_has_runtime_fault(enum test_mode mode)
{
    return mode == TEST_EPIPE || mode == TEST_EINVAL || mode == TEST_EFAULT ||
           mode == TEST_READ_EINTR || mode == TEST_ZERO_READ ||
           mode == TEST_READ_ERROR || mode == TEST_POLLERR ||
           mode == TEST_POLL_FAILURE || mode == TEST_POLL_EINTR ||
           mode == TEST_KMSG_HUP || mode == TEST_SEQUENCE_GAP ||
           mode == TEST_FAULT_NO_CLOSE || mode == TEST_FAULT_CLOSE_EINTR ||
           mode == TEST_FAULT_FSYNC_FAIL_NO_CLOSE ||
           mode == TEST_FAULT_STATUS_FAIL_NO_CLOSE ||
           mode == TEST_FAULT_NORMAL_CLOSE ||
           mode == TEST_FAULTED_INVALID_CAUSE_THEN_FAULT_CLOSE ||
           mode == TEST_MALFORMED_RECORD || mode == TEST_COUNT_CAP ||
           mode == TEST_BYTE_CAP;
}

static int mode_has_close_eintr(enum test_mode mode)
{
    return mode == TEST_FAULT_CLOSE_EINTR ||
           mode == TEST_NORMAL_CLOSE_EINTR ||
           mode == TEST_PARENT_EOF_CLOSE_EINTR;
}

static void initialize_context(struct fake_context *context, enum test_mode mode)
{
    unsigned char start[A90_WP2_5B_OWNER_START_PAYLOAD_SIZE];
    unsigned char close_payload[A90_WP2_5B_OWNER_CLOSE_PAYLOAD_SIZE];
    uint32_t close_cause;
    int fd;

    if (mode == TEST_FAULT_NORMAL_CLOSE)
        close_cause = A90_WP2_5B_OWNER_CLOSE_NORMAL;
    else if (mode == TEST_HEALTHY_FAULT_CLOSE)
        close_cause = A90_WP2_5B_OWNER_CLOSE_FAULT;
    else
        close_cause = mode_has_runtime_fault(mode)
                          ? A90_WP2_5B_OWNER_CLOSE_FAULT
                          : A90_WP2_5B_OWNER_CLOSE_NORMAL;

    memset(context, 0, sizeof(*context));
    context->mode = mode;
    for (fd = 0; fd <= A90_WP2_5B_OWNER_RUN_DIR_FD; ++fd)
        context->open_fds[fd] = 1;
    if (mode == TEST_RETAINED_EXEC_FD)
        context->open_fds[A90_WP2_5B_OWNER_EXEC_FD] = 1;
    memset(start, 0, sizeof(start));
    memset(start, 0x11, 32);
    memset(start + 32, 0x22, 32);
    memset(start + 64, 0x33, 32);
    memset(start + 96, 0x44, 32);
    memset(start + 128, 0x55, 32);
    put_u32_be(start + 160, mode == TEST_COUNT_CAP ? 1 : 8);
    put_u64_be(start + 164, mode == TEST_BYTE_CAP ? 1 : 16384);
    put_u32_be(start + 172, 1000);
    put_u32_be(start + 176, 1000);
    put_u32_be(start + 180, 4);
    put_u32_be(start + 184, 4);
    put_u32_be(start + 188, 4);
    put_u32_be(start + 192, 10);
    put_u32_be(start + 196, 4);
    put_u32_be(start + 200, 0);
    append_control_frame(context, A90_WP2_5B_OWNER_CONTROL_START, 0, start,
                         sizeof(start));
    if (mode == TEST_INVALID_CAUSE_THEN_FAULT_CLOSE ||
        mode == TEST_RESERVED_CLOSE_THEN_FAULT_CLOSE ||
        mode == TEST_UNKNOWN_KIND_THEN_FAULT_CLOSE ||
        mode == TEST_FAULTED_INVALID_CAUSE_THEN_FAULT_CLOSE) {
        uint8_t first_kind = mode == TEST_UNKNOWN_KIND_THEN_FAULT_CLOSE
                                 ? 99
                                 : A90_WP2_5B_OWNER_CONTROL_CLOSE;

        put_u32_be(close_payload,
                   mode == TEST_RESERVED_CLOSE_THEN_FAULT_CLOSE
                       ? A90_WP2_5B_OWNER_CLOSE_NORMAL
                       : 99);
        put_u32_be(close_payload + 4,
                   mode == TEST_RESERVED_CLOSE_THEN_FAULT_CLOSE ? 1 : 0);
        append_control_frame(context, first_kind, 1, close_payload,
                             sizeof(close_payload));
        put_u32_be(close_payload, A90_WP2_5B_OWNER_CLOSE_FAULT);
        put_u32_be(close_payload + 4, 0);
        append_control_frame(context, A90_WP2_5B_OWNER_CONTROL_CLOSE, 2,
                             close_payload, sizeof(close_payload));
        return;
    }
    if (mode != TEST_PARENT_EOF && mode != TEST_PARENT_EOF_CLOSE_EINTR &&
        mode != TEST_FAULT_NO_CLOSE &&
        mode != TEST_FAULT_CLOSE_EINTR &&
        mode != TEST_FAULT_FSYNC_FAIL_NO_CLOSE &&
        mode != TEST_FAULT_STATUS_FAIL_NO_CLOSE) {
        put_u32_be(close_payload, close_cause);
        put_u32_be(close_payload + 4, 0);
        append_control_frame(context, A90_WP2_5B_OWNER_CONTROL_CLOSE, 1,
                             close_payload, sizeof(close_payload));
        if (mode == TEST_DUPLICATE_CLOSE)
            append_control_frame(context, A90_WP2_5B_OWNER_CONTROL_CLOSE, 2,
                                 close_payload, sizeof(close_payload));
        if (mode == TEST_PARTIAL_CLOSE)
            context->control_length -= 4;
    }
}

static int fake_openat(void *opaque, int dirfd, const char *path, int flags,
                       mode_t mode)
{
    struct fake_context *context = opaque;

    ++context->open_count;
    if (context->open_count == 1) {
        if (dirfd != A90_WP2_5B_OWNER_RUN_DIR_FD ||
            strcmp(path, "trace.pending") != 0 || mode != 0600 ||
            flags != (O_WRONLY | O_APPEND | O_CREAT | O_EXCL | O_NOFOLLOW |
                      O_CLOEXEC)) {
            errno = EINVAL;
            return -1;
        }
        context->open_fds[TEST_TRACE_FD] = 1;
        context->fd_flags[TEST_TRACE_FD] = FD_CLOEXEC;
        return TEST_TRACE_FD;
    }
    if (context->open_count == 2) {
        if (dirfd != AT_FDCWD || strcmp(path, "/dev/kmsg") != 0 || mode != 0 ||
            flags != (O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC)) {
            errno = EINVAL;
            return -1;
        }
        context->open_fds[TEST_KMSG_FD] = 1;
        context->fd_flags[TEST_KMSG_FD] = FD_CLOEXEC;
        return TEST_KMSG_FD;
    }
    errno = EMFILE;
    return -1;
}

static int fake_close(void *opaque, int fd)
{
    struct fake_context *context = opaque;

    if (fd < 0 || fd >= (int)(sizeof(context->open_fds) /
                              sizeof(context->open_fds[0])) ||
        !context->open_fds[fd]) {
        errno = EBADF;
        return -1;
    }
    ++context->close_calls[fd];
    if (mode_has_close_eintr(context->mode) && fd == TEST_KMSG_FD) {
        errno = EINTR;
        return -1;
    }
    if (context->mode == TEST_TRACE_CLOSE_EINTR && fd == TEST_TRACE_FD) {
        errno = EINTR;
        return -1;
    }
    context->open_fds[fd] = 0;
    return 0;
}

static int fake_fstat(void *opaque, int fd, struct stat *status)
{
    struct fake_context *context = opaque;

    if (status == NULL || fd < 0 || fd >= 9 || !context->open_fds[fd]) {
        errno = EBADF;
        return -1;
    }
    memset(status, 0, sizeof(*status));
    if (fd <= 2) {
        status->st_mode = S_IFCHR | 0666;
        status->st_rdev = makedev(1, 3);
        status->st_dev = 2;
        status->st_ino = (ino_t)(100 + fd);
    } else if (fd == A90_WP2_5B_OWNER_RUN_DIR_FD) {
        status->st_mode = S_IFDIR | 0700;
        status->st_dev = 10;
        status->st_ino = 20;
    } else if (fd == TEST_TRACE_FD) {
        status->st_mode = S_IFREG | 0600;
        status->st_nlink = 1;
        status->st_dev = 11;
        status->st_ino = 22;
        status->st_size = 0;
    } else if (fd == TEST_KMSG_FD) {
        status->st_mode = S_IFCHR | 0600;
        status->st_dev = 12;
        status->st_ino = 23;
        status->st_rdev = context->mode == TEST_WRONG_RDEV
                              ? makedev(1, 10)
                              : makedev(1, 11);
    } else {
        status->st_mode = S_IFIFO | 0600;
        status->st_dev = 13;
        status->st_ino = (ino_t)(30 + fd);
    }
    return 0;
}

static int fake_fcntl(void *opaque, int fd, int command, long argument)
{
    struct fake_context *context = opaque;

    if (fd < 0 || fd >= 9 || !context->open_fds[fd]) {
        errno = EBADF;
        return -1;
    }
    if (command == F_GETFD)
        return context->fd_flags[fd];
    if (command == F_SETFD) {
        context->fd_flags[fd] = (int)argument;
        return 0;
    }
    if (command != F_GETFL) {
        errno = EINVAL;
        return -1;
    }
    switch (fd) {
    case 0:
    case A90_WP2_5B_OWNER_RUN_DIR_FD:
        return O_RDONLY;
    case A90_WP2_5B_OWNER_CONTROL_FD:
        return O_RDONLY | O_NONBLOCK;
    case 1:
    case 2:
        return O_WRONLY;
    case A90_WP2_5B_OWNER_STATUS_FD:
        return O_WRONLY | O_NONBLOCK;
    case TEST_TRACE_FD:
        return O_WRONLY | O_APPEND;
    case TEST_KMSG_FD:
        return context->mode == TEST_WRONG_KMSG_FLAGS
                   ? O_RDONLY
                   : O_RDONLY | O_NONBLOCK;
    default:
        errno = EINVAL;
        return -1;
    }
}

static off_t fake_lseek(void *opaque, int fd, off_t offset, int whence)
{
    struct fake_context *context = opaque;

    if (context->mode == TEST_LSEEK_FAIL || fd != TEST_KMSG_FD ||
        offset != 0 || whence != SEEK_END) {
        errno = EINVAL;
        return -1;
    }
    ++context->lseek_calls;
    return 0;
}

static ssize_t fake_read(void *opaque, int fd, void *buffer, size_t length)
{
    struct fake_context *context = opaque;
    static const unsigned char record_one[] = "3,1,2,-;body\n";
    static const unsigned char record_two[] = "3,2,3,-;next\n";
    static const unsigned char record_three[] = "3,3,4,-;gap\n";
    static const unsigned char malformed_record[] = "not-a-kmsg-record\n";
    size_t remaining;

    if (fd == A90_WP2_5B_OWNER_CONTROL_FD) {
        if (context->control_position == context->control_length)
            return 0;
        remaining = context->control_length - context->control_position;
        if (remaining > length)
            remaining = length;
        memcpy(buffer, context->control + context->control_position, remaining);
        context->control_position += remaining;
        return (ssize_t)remaining;
    }
    if (fd != TEST_KMSG_FD) {
        errno = EBADF;
        return -1;
    }
    if (context->mode == TEST_EPIPE && context->kmsg_step++ == 0) {
        errno = EPIPE;
        return -1;
    }
    if (context->mode == TEST_FAULT_NO_CLOSE && context->kmsg_step++ == 0) {
        errno = EPIPE;
        return -1;
    }
    if (context->mode == TEST_FAULT_CLOSE_EINTR &&
        context->kmsg_step++ == 0) {
        errno = EPIPE;
        return -1;
    }
    if (context->mode == TEST_FAULT_FSYNC_FAIL_NO_CLOSE &&
        context->kmsg_step++ == 0) {
        errno = EPIPE;
        return -1;
    }
    if (context->mode == TEST_FAULT_STATUS_FAIL_NO_CLOSE &&
        context->kmsg_step++ == 0) {
        errno = EPIPE;
        return -1;
    }
    if (context->mode == TEST_FAULT_NORMAL_CLOSE &&
        context->kmsg_step++ == 0) {
        errno = EPIPE;
        return -1;
    }
    if (context->mode == TEST_FAULTED_INVALID_CAUSE_THEN_FAULT_CLOSE &&
        context->kmsg_step++ == 0) {
        errno = EPIPE;
        return -1;
    }
    if (context->mode == TEST_EINVAL && context->kmsg_step++ == 0) {
        errno = EINVAL;
        return -1;
    }
    if (context->mode == TEST_EFAULT && context->kmsg_step++ == 0) {
        errno = EFAULT;
        return -1;
    }
    if (context->mode == TEST_READ_EINTR) {
        ++context->kmsg_step;
        errno = EINTR;
        return -1;
    }
    if (context->mode == TEST_ZERO_READ && context->kmsg_step++ == 0)
        return 0;
    if (context->mode == TEST_READ_ERROR && context->kmsg_step++ == 0) {
        errno = EIO;
        return -1;
    }
    if (context->mode == TEST_SEQUENCE_GAP) {
        const unsigned char *record = context->kmsg_step == 0
                                          ? record_one
                                          : record_three;
        size_t record_length = context->kmsg_step == 0
                                   ? sizeof(record_one) - 1
                                   : sizeof(record_three) - 1;

        if (context->kmsg_step < 2) {
            ++context->kmsg_step;
            require(length >= record_length, "kmsg fixture buffer too small");
            memcpy(buffer, record, record_length);
            return (ssize_t)record_length;
        }
    }
    if (context->mode == TEST_COUNT_CAP && context->kmsg_step < 2) {
        const unsigned char *record = context->kmsg_step == 0
                                          ? record_one
                                          : record_two;
        size_t record_length = context->kmsg_step == 0
                                   ? sizeof(record_one) - 1
                                   : sizeof(record_two) - 1;

        ++context->kmsg_step;
        require(length >= record_length, "kmsg fixture buffer too small");
        memcpy(buffer, record, record_length);
        return (ssize_t)record_length;
    }
    if (context->mode == TEST_MALFORMED_RECORD && context->kmsg_step++ == 0) {
        require(length >= sizeof(malformed_record) - 1,
                "kmsg fixture buffer too small");
        memcpy(buffer, malformed_record, sizeof(malformed_record) - 1);
        return (ssize_t)(sizeof(malformed_record) - 1);
    }
    if (context->mode == TEST_HAPPY || context->mode == TEST_DUPLICATE_CLOSE ||
        context->mode == TEST_PARTIAL_CLOSE || context->mode == TEST_PARENT_EOF ||
        context->mode == TEST_NORMAL_CLOSE_EINTR ||
        context->mode == TEST_PARENT_EOF_CLOSE_EINTR ||
        context->mode == TEST_HEALTHY_FAULT_CLOSE ||
        context->mode == TEST_INVALID_CAUSE_THEN_FAULT_CLOSE ||
        context->mode == TEST_RESERVED_CLOSE_THEN_FAULT_CLOSE ||
        context->mode == TEST_UNKNOWN_KIND_THEN_FAULT_CLOSE ||
        context->mode == TEST_FINAL_END_WRITE_FAIL ||
        context->mode == TEST_FINAL_FSYNC_ENOSPC ||
        context->mode == TEST_FINAL_FSYNC_EIO ||
        context->mode == TEST_FINAL_FSYNC_EINTR ||
        context->mode == TEST_TRACE_CLOSE_EINTR ||
        context->mode == TEST_CLOSED_STATUS_SHORT ||
        context->mode == TEST_BYTE_CAP ||
        context->mode == TEST_SHORT_STATUS) {
        if (context->kmsg_step == 0) {
            ++context->kmsg_step;
            require(length >= sizeof(record_one) - 1,
                    "kmsg fixture buffer too small");
            memcpy(buffer, record_one, sizeof(record_one) - 1);
            return (ssize_t)(sizeof(record_one) - 1);
        }
    }
    ++context->kmsg_step;
    errno = EAGAIN;
    return -1;
}

static ssize_t fake_write(void *opaque, int fd, const void *buffer, size_t length)
{
    struct fake_context *context = opaque;

    if (fd == TEST_TRACE_FD) {
        if (context->mode == TEST_FINAL_END_WRITE_FAIL &&
            context->final_end_partial_sent) {
            errno = EIO;
            return -1;
        }
        if (context->mode == TEST_FINAL_END_WRITE_FAIL &&
            length == A90_WP2_5B_FRAME_HEADER_SIZE &&
            ((const unsigned char *)buffer)[0] == A90_WP2_5B_FRAME_END) {
            require(length > 1, "END frame header too small for partial write");
            require(context->trace_length + length - 1 <=
                        sizeof(context->trace),
                    "partial END fixture overflow");
            memcpy(context->trace + context->trace_length, buffer, length - 1);
            context->trace_length += length - 1;
            context->final_end_partial_sent = 1;
            return (ssize_t)(length - 1);
        }
        require(context->trace_length + length <= sizeof(context->trace),
                "trace fixture overflow");
        memcpy(context->trace + context->trace_length, buffer, length);
        context->trace_length += length;
        return (ssize_t)length;
    }
    if (fd == A90_WP2_5B_OWNER_STATUS_FD) {
        if (context->mode == TEST_SHORT_STATUS && context->status_length == 0)
            return (ssize_t)(length - 1);
        if (context->mode == TEST_CLOSED_STATUS_SHORT &&
            length == A90_WP2_5B_OWNER_PIPE_HEADER_SIZE +
                          A90_WP2_5B_OWNER_STATUS_PAYLOAD_SIZE &&
            ((const unsigned char *)buffer)[11] ==
                A90_WP2_5B_OWNER_STATUS_CLOSED)
            return (ssize_t)(length - 1);
        if (context->mode == TEST_FAULT_STATUS_FAIL_NO_CLOSE &&
            length == A90_WP2_5B_OWNER_PIPE_HEADER_SIZE +
                          A90_WP2_5B_OWNER_STATUS_PAYLOAD_SIZE &&
            ((const unsigned char *)buffer)[11] ==
                A90_WP2_5B_OWNER_STATUS_FAULTED)
            return (ssize_t)(length - 1);
        require(context->status_length + length <= sizeof(context->status),
                "status fixture overflow");
        if (length == A90_WP2_5B_OWNER_PIPE_HEADER_SIZE +
                          A90_WP2_5B_OWNER_STATUS_PAYLOAD_SIZE &&
            ((const unsigned char *)buffer)[11] ==
                A90_WP2_5B_OWNER_STATUS_FAULTED) {
            require(context->open_fds[TEST_KMSG_FD] == 0,
                    "FAULTED status preceded kmsg close");
            context->faulted_status_saw_kmsg_closed = 1;
        }
        memcpy(context->status + context->status_length, buffer, length);
        context->status_length += length;
        return (ssize_t)length;
    }
    errno = EBADF;
    return -1;
}

static int fake_poll(void *opaque, struct pollfd *fds, nfds_t count,
                     int timeout_ms)
{
    struct fake_context *context = opaque;

    (void)timeout_ms;
    if (count == 1 && fds[0].fd == A90_WP2_5B_OWNER_STATUS_FD) {
        fds[0].revents = POLLOUT;
        return 1;
    }
    if (count == 1 && fds[0].fd == A90_WP2_5B_OWNER_CONTROL_FD) {
        if (context->mode == TEST_FAULT_NO_CLOSE ||
            context->mode == TEST_FAULT_CLOSE_EINTR ||
            context->mode == TEST_FAULT_FSYNC_FAIL_NO_CLOSE ||
            context->mode == TEST_FAULT_STATUS_FAIL_NO_CLOSE) {
            ++context->fault_close_wait_polls;
            fds[0].revents = 0;
            return 0;
        }
        fds[0].revents = context->control_position < context->control_length
                             ? (short)(POLLIN | POLLHUP)
                             : POLLHUP;
        return 1;
    }
    if (count != 2 || fds[0].fd != A90_WP2_5B_OWNER_CONTROL_FD ||
        fds[1].fd != TEST_KMSG_FD) {
        errno = EINVAL;
        return -1;
    }
    if (context->mode == TEST_POLL_FAILURE && !context->pollerr_sent) {
        context->pollerr_sent = 1;
        errno = EIO;
        return -1;
    }
    if (context->mode == TEST_POLL_EINTR && context->poll_interrupts < 4) {
        ++context->poll_interrupts;
        errno = EINTR;
        return -1;
    }
    if (context->mode == TEST_POLLERR && !context->pollerr_sent) {
        context->pollerr_sent = 1;
        fds[1].revents = POLLERR;
        return 1;
    }
    if (context->mode == TEST_KMSG_HUP && !context->pollerr_sent) {
        context->pollerr_sent = 1;
        fds[1].revents = POLLHUP;
        return 1;
    }
    if (((context->mode == TEST_SEQUENCE_GAP ||
          context->mode == TEST_COUNT_CAP) &&
         context->kmsg_step < 2) ||
        (context->mode != TEST_POLLERR && context->kmsg_step == 0)) {
        fds[1].revents = POLLIN;
        return 1;
    }
    fds[0].revents = (short)(POLLIN | POLLHUP);
    return 1;
}

static int fake_fsync(void *opaque, int fd)
{
    struct fake_context *context = opaque;

    if (fd != TEST_TRACE_FD || !context->open_fds[fd]) {
        errno = EBADF;
        return -1;
    }
    if (context->mode == TEST_ARM_FSYNC_FAIL && context->fsync_calls == 0) {
        ++context->fsync_calls;
        errno = ENOSPC;
        return -1;
    }
    if (context->mode == TEST_FAULT_FSYNC_FAIL_NO_CLOSE &&
        context->fsync_calls == 1) {
        ++context->fsync_calls;
        errno = ENOSPC;
        return -1;
    }
    if ((context->mode == TEST_FINAL_FSYNC_ENOSPC ||
         context->mode == TEST_FINAL_FSYNC_EIO ||
         context->mode == TEST_FINAL_FSYNC_EINTR) &&
        context->fsync_calls == 1) {
        ++context->fsync_calls;
        errno = context->mode == TEST_FINAL_FSYNC_ENOSPC
                    ? ENOSPC
                : context->mode == TEST_FINAL_FSYNC_EIO ? EIO
                                                        : EINTR;
        return -1;
    }
    ++context->fsync_calls;
    return 0;
}

static int fake_confinement(
    void *opaque, const struct a90_wp2_5b_owner_confinement *request)
{
    struct fake_context *context = opaque;

    if (request == NULL || request->control_fd != 3 || request->status_fd != 4 ||
        request->trace_fd != TEST_TRACE_FD || request->kmsg_fd != TEST_KMSG_FD ||
        request->expected_uid != 1000 || request->expected_gid != 1000)
        return -1;
    if (context->mode == TEST_CONFINEMENT_FAIL)
        return -1;
    ++context->confinement_calls;
    return 0;
}

static struct a90_wp2_5b_owner_ops fake_operations(struct fake_context *context)
{
    struct a90_wp2_5b_owner_ops operations = {
        context, fake_openat, fake_close, fake_fstat, fake_fcntl, fake_lseek,
        fake_read, fake_write, fake_poll, fake_fsync, fake_confinement,
    };

    return operations;
}

static unsigned int status_frame_count(const struct fake_context *context)
{
    const size_t frame_size = A90_WP2_5B_OWNER_PIPE_HEADER_SIZE +
                              A90_WP2_5B_OWNER_STATUS_PAYLOAD_SIZE;

    require(context->status_length % frame_size == 0,
            "status stream contains a partial frame");
    return (unsigned int)(context->status_length / frame_size);
}

static uint8_t validate_status_frame(const struct fake_context *context,
                                     unsigned int index)
{
    const size_t frame_size = A90_WP2_5B_OWNER_PIPE_HEADER_SIZE +
                              A90_WP2_5B_OWNER_STATUS_PAYLOAD_SIZE;
    const unsigned char *frame = context->status + index * frame_size;

    require(index < status_frame_count(context), "status index out of range");
    require(memcmp(frame, a90_wp2_5b_owner_magic, 8) == 0,
            "status magic mismatch");
    require(get_u16_be(frame + 8) == A90_WP2_5B_OWNER_VERSION,
            "status version mismatch");
    require(frame[10] == A90_WP2_5B_OWNER_DIRECTION_STATUS,
            "status direction mismatch");
    require(get_u64_be(frame + 12) == index, "status sequence mismatch");
    require(get_u16_be(frame + 20) == A90_WP2_5B_OWNER_STATUS_PAYLOAD_SIZE,
            "status payload length mismatch");
    require(get_u16_be(frame + 22) == 0, "status reserved mismatch");
    require(get_u32_be(frame + 24 + 12) == 0,
            "status payload reserved mismatch");
    return frame[11];
}

static uint64_t status_durable_bytes(const struct fake_context *context,
                                     unsigned int index)
{
    const size_t frame_size = A90_WP2_5B_OWNER_PIPE_HEADER_SIZE +
                              A90_WP2_5B_OWNER_STATUS_PAYLOAD_SIZE;
    const unsigned char *frame = context->status + index * frame_size;

    require(index < status_frame_count(context), "status index out of range");
    return get_u64_be(frame + A90_WP2_5B_OWNER_PIPE_HEADER_SIZE + 56);
}

static int trace_contains_frame_type(const struct fake_context *context,
                                     uint8_t frame_type)
{
    size_t position = A90_WP2_5B_TRACE_HEADER_SIZE;

    require(context->trace_length >= A90_WP2_5B_TRACE_HEADER_SIZE,
            "trace is missing its fixed header");

    while (position < context->trace_length) {
        uint32_t payload_length;

        require(context->trace_length - position >=
                    A90_WP2_5B_FRAME_HEADER_SIZE,
                "trace contains a partial frame header");
        payload_length = get_u32_be(context->trace + position + 4);
        require(payload_length <= context->trace_length - position -
                                      A90_WP2_5B_FRAME_HEADER_SIZE,
                "trace contains a partial frame payload");
        if (context->trace[position] == frame_type)
            return 1;
        position += A90_WP2_5B_FRAME_HEADER_SIZE + payload_length;
    }
    return 0;
}

static void run_owner_case(enum test_mode mode, uint32_t expected_fault,
                           int expected_success)
{
    struct fake_context context;
    struct a90_wp2_5b_owner_ops operations;
    struct a90_wp2_5b_owner_result result;
    int rc;

    initialize_context(&context, mode);
    operations = fake_operations(&context);
    rc = a90_wp2_5b_owner_run_with_ops(&operations, &result);
    if (!expected_success) {
        require(rc != 0, "pre-arm rejection unexpectedly succeeded");
        require(context.open_fds[TEST_TRACE_FD] == 0,
                "pre-arm rejection retained trace fd");
        require(context.open_fds[TEST_KMSG_FD] == 0,
                "pre-arm rejection retained kmsg fd");
        return;
    }
    require(rc == 0, "owner state machine did not close cleanly");
    require(result.armed == 1 && result.closed == 1,
            "owner did not report armed and closed");
    require(result.kmsg_reads_after_fault == 0,
            "owner read kmsg after terminal fault");
    require(context.lseek_calls == 1, "owner did not seek exactly once");
    require(context.confinement_calls == 1,
            "owner did not apply confinement exactly once");
    require(context.open_fds[TEST_TRACE_FD] == 0 &&
                context.open_fds[TEST_KMSG_FD] == 0,
            "owner retained campaign fds");
    if (expected_fault == 0) {
        require(result.faulted == 0, "happy owner reported a fault");
        require(status_frame_count(&context) == 2,
                "happy status cardinality mismatch");
        require(validate_status_frame(&context, 0) ==
                    A90_WP2_5B_OWNER_STATUS_ARMED,
                "happy status did not begin armed");
        require(validate_status_frame(&context, 1) ==
                    A90_WP2_5B_OWNER_STATUS_CLOSED,
                "happy status did not end closed");
    } else {
        uint64_t armed_durable = status_durable_bytes(&context, 0);
        uint64_t fault_durable = status_durable_bytes(&context, 1);

        require(result.faulted == 1 && result.fault_reason == expected_fault,
                "owner fault reason mismatch");
        require(status_frame_count(&context) == 3,
                "fault status cardinality mismatch");
        require(validate_status_frame(&context, 0) ==
                    A90_WP2_5B_OWNER_STATUS_ARMED,
                "fault status did not begin armed");
        require(validate_status_frame(&context, 1) ==
                    A90_WP2_5B_OWNER_STATUS_FAULTED,
                "fault status did not publish faulted");
        require(context.faulted_status_saw_kmsg_closed == 1,
                "fault status did not follow immediate reader close");
        require(fault_durable > armed_durable,
                "FAULTED status did not bind the fsynced fault prefix");
        require(result.durable_trace_bytes >= fault_durable,
                "owner result regressed below the FAULTED durable prefix");
        require(validate_status_frame(&context, 2) ==
                    A90_WP2_5B_OWNER_STATUS_CLOSED,
                "fault status did not end closed");
    }
}

static void test_fault_without_parent_close_is_bounded(void)
{
    struct fake_context context;
    struct a90_wp2_5b_owner_ops operations;
    struct a90_wp2_5b_owner_result result;

    initialize_context(&context, TEST_FAULT_NO_CLOSE);
    operations = fake_operations(&context);
    require(a90_wp2_5b_owner_run_with_ops(&operations, &result) != 0,
            "fault without CLOSE unexpectedly completed");
    require(result.armed == 1 && result.faulted == 1 && result.closed == 0,
            "fault without CLOSE returned the wrong terminal prefix");
    require(result.fault_reason == A90_WP2_5B_FAULT_EPIPE,
            "fault without CLOSE lost the reader fault");
    require(context.close_calls[TEST_KMSG_FD] == 1 &&
                context.open_fds[TEST_KMSG_FD] == 0,
            "fault without CLOSE did not close kmsg exactly once");
    require(context.fault_close_wait_polls == 4,
            "fault-close wait did not consume the exact bounded budget");
    require(result.kmsg_reads_after_fault == 0,
            "fault-close wait performed a later kmsg read");
    require(status_frame_count(&context) == 2 &&
                validate_status_frame(&context, 0) ==
                    A90_WP2_5B_OWNER_STATUS_ARMED &&
                validate_status_frame(&context, 1) ==
                    A90_WP2_5B_OWNER_STATUS_FAULTED,
            "fault-close timeout did not leave the exact bounded status prefix");
    require(trace_contains_frame_type(&context, A90_WP2_5B_FRAME_FAULT) &&
                !trace_contains_frame_type(&context, A90_WP2_5B_FRAME_END),
            "fault-close timeout fabricated a complete trace");
    require(context.open_fds[TEST_TRACE_FD] == 0 &&
                context.open_fds[A90_WP2_5B_OWNER_CONTROL_FD] == 0 &&
                context.open_fds[A90_WP2_5B_OWNER_STATUS_FD] == 0,
            "fault-close timeout retained observer descriptors");
}

static void test_fault_close_uncertainty_exits_immediately(void)
{
    struct fake_context context;
    struct a90_wp2_5b_owner_ops operations;
    struct a90_wp2_5b_owner_result result;

    initialize_context(&context, TEST_FAULT_CLOSE_EINTR);
    operations = fake_operations(&context);
    require(a90_wp2_5b_owner_run_with_ops(&operations, &result) != 0,
            "uncertain reader close unexpectedly completed");
    require(result.armed == 1 && result.faulted == 1 && result.closed == 0,
            "uncertain reader close returned the wrong terminal prefix");
    require(result.fault_reason == A90_WP2_5B_FAULT_EPIPE,
            "uncertain reader close lost the originating fault");
    require(context.close_calls[TEST_KMSG_FD] == 1,
            "uncertain reader close was retried");
    require(context.open_fds[TEST_KMSG_FD] == 1,
            "close-EINTR fixture did not model an uncertain kernel FD");
    require(context.fault_close_wait_polls == 0,
            "uncertain reader close entered the control wait");
    require(status_frame_count(&context) == 1 &&
                validate_status_frame(&context, 0) ==
                    A90_WP2_5B_OWNER_STATUS_ARMED,
            "uncertain reader close emitted a FAULTED-as-closed status");
    require(trace_contains_frame_type(&context, A90_WP2_5B_FRAME_FAULT) &&
                !trace_contains_frame_type(&context, A90_WP2_5B_FRAME_END),
            "uncertain reader close fabricated a complete trace");
    require(result.kmsg_reads_after_fault == 0,
            "uncertain reader close performed a later kmsg read");
    require(context.open_fds[TEST_TRACE_FD] == 0 &&
                context.open_fds[A90_WP2_5B_OWNER_CONTROL_FD] == 0 &&
                context.open_fds[A90_WP2_5B_OWNER_STATUS_FD] == 0,
            "uncertain reader close retained non-kmsg observer descriptors");
}

static void test_fault_fsync_failure_still_closes_reader(void)
{
    struct fake_context context;
    struct a90_wp2_5b_owner_ops operations;
    struct a90_wp2_5b_owner_result result;

    initialize_context(&context, TEST_FAULT_FSYNC_FAIL_NO_CLOSE);
    operations = fake_operations(&context);
    require(a90_wp2_5b_owner_run_with_ops(&operations, &result) != 0,
            "fault-prefix fsync failure unexpectedly completed");
    require(result.armed == 1 && result.faulted == 1 && result.closed == 0,
            "fault-prefix fsync failure returned the wrong terminal prefix");
    require(context.close_calls[TEST_KMSG_FD] == 1 &&
                context.open_fds[TEST_KMSG_FD] == 0,
            "fault-prefix fsync failure did not close kmsg exactly once");
    require(context.fault_close_wait_polls == 0,
            "fault-prefix fsync failure entered the control wait");
    require(status_frame_count(&context) == 1 &&
                validate_status_frame(&context, 0) ==
                    A90_WP2_5B_OWNER_STATUS_ARMED,
            "fault-prefix fsync failure fabricated a FAULTED status");
    require(trace_contains_frame_type(&context, A90_WP2_5B_FRAME_FAULT) &&
                !trace_contains_frame_type(&context, A90_WP2_5B_FRAME_END),
            "fault-prefix fsync failure fabricated a complete trace");
    require(result.kmsg_reads_after_fault == 0,
            "fault-prefix fsync failure performed a later kmsg read");
    require(context.open_fds[TEST_TRACE_FD] == 0 &&
                context.open_fds[A90_WP2_5B_OWNER_CONTROL_FD] == 0 &&
                context.open_fds[A90_WP2_5B_OWNER_STATUS_FD] == 0,
            "fault-prefix fsync failure retained observer descriptors");
}

static void test_fault_status_failure_exits_immediately(void)
{
    struct fake_context context;
    struct a90_wp2_5b_owner_ops operations;
    struct a90_wp2_5b_owner_result result;

    initialize_context(&context, TEST_FAULT_STATUS_FAIL_NO_CLOSE);
    operations = fake_operations(&context);
    require(a90_wp2_5b_owner_run_with_ops(&operations, &result) != 0,
            "FAULTED status failure unexpectedly completed");
    require(result.armed == 1 && result.faulted == 1 && result.closed == 0,
            "FAULTED status failure returned the wrong terminal prefix");
    require(context.close_calls[TEST_KMSG_FD] == 1 &&
                context.open_fds[TEST_KMSG_FD] == 0,
            "FAULTED status failure did not close kmsg exactly once");
    require(context.fault_close_wait_polls == 0,
            "FAULTED status failure entered the control wait");
    require(status_frame_count(&context) == 1 &&
                validate_status_frame(&context, 0) ==
                    A90_WP2_5B_OWNER_STATUS_ARMED,
            "FAULTED status failure later emitted a terminal status");
    require(trace_contains_frame_type(&context, A90_WP2_5B_FRAME_FAULT) &&
                !trace_contains_frame_type(&context, A90_WP2_5B_FRAME_END),
            "FAULTED status failure fabricated a complete trace");
    require(result.kmsg_reads_after_fault == 0,
            "FAULTED status failure performed a later kmsg read");
}

static void test_finalize_close_uncertainty_exits_without_terminal_status(
    enum test_mode mode)
{
    struct fake_context context;
    struct a90_wp2_5b_owner_ops operations;
    struct a90_wp2_5b_owner_result result;

    initialize_context(&context, mode);
    operations = fake_operations(&context);
    require(a90_wp2_5b_owner_run_with_ops(&operations, &result) != 0,
            "finalize close uncertainty unexpectedly completed");
    require(result.armed == 1 && result.faulted == 1 && result.closed == 0,
            "finalize close uncertainty returned the wrong terminal prefix");
    require(result.fault_reason == A90_WP2_5B_FAULT_BOUNDARY,
            "finalize close uncertainty lost the boundary fault");
    require(context.close_calls[TEST_KMSG_FD] == 1,
            "finalize close uncertainty retried kmsg close");
    require(context.open_fds[TEST_KMSG_FD] == 1,
            "finalize close fixture did not preserve uncertain kernel state");
    require(status_frame_count(&context) == 1 &&
                validate_status_frame(&context, 0) ==
                    A90_WP2_5B_OWNER_STATUS_ARMED,
            "finalize close uncertainty emitted FAULTED or CLOSED");
    require(trace_contains_frame_type(&context, A90_WP2_5B_FRAME_FAULT) &&
                !trace_contains_frame_type(&context, A90_WP2_5B_FRAME_END),
            "finalize close uncertainty fabricated a complete trace");
    require(context.faulted_status_saw_kmsg_closed == 0,
            "finalize close uncertainty claimed a closed reader");
    require(result.kmsg_reads_after_fault == 0,
            "finalize close uncertainty performed a later kmsg read");
    require(context.open_fds[TEST_TRACE_FD] == 0 &&
                context.open_fds[A90_WP2_5B_OWNER_CONTROL_FD] == 0 &&
                context.open_fds[A90_WP2_5B_OWNER_STATUS_FD] == 0,
            "finalize close uncertainty retained non-kmsg descriptors");
}

static void test_invalid_close_transition_does_not_complete(enum test_mode mode)
{
    struct fake_context context;
    struct a90_wp2_5b_owner_ops operations;
    struct a90_wp2_5b_owner_result result;
    uint32_t expected_fault = mode == TEST_FAULT_NORMAL_CLOSE
                                  ? A90_WP2_5B_FAULT_EPIPE
                              : mode ==
                                    TEST_FAULTED_INVALID_CAUSE_THEN_FAULT_CLOSE
                                  ? A90_WP2_5B_FAULT_EPIPE
                                  : A90_WP2_5B_FAULT_BOUNDARY;

    initialize_context(&context, mode);
    operations = fake_operations(&context);
    require(a90_wp2_5b_owner_run_with_ops(&operations, &result) != 0,
            "invalid CLOSE transition unexpectedly completed");
    require(result.armed == 1 && result.faulted == 1 && result.closed == 0,
            "invalid CLOSE transition returned the wrong terminal prefix");
    require(result.fault_reason == expected_fault,
            "invalid CLOSE transition lost the bound fault reason");
    require(context.close_calls[TEST_KMSG_FD] == 1 &&
                context.open_fds[TEST_KMSG_FD] == 0,
            "invalid CLOSE transition did not close kmsg exactly once");
    require(status_frame_count(&context) == 2 &&
                validate_status_frame(&context, 0) ==
                    A90_WP2_5B_OWNER_STATUS_ARMED &&
                validate_status_frame(&context, 1) ==
                    A90_WP2_5B_OWNER_STATUS_FAULTED,
            "invalid CLOSE transition emitted a canonical CLOSED status");
    require(trace_contains_frame_type(&context, A90_WP2_5B_FRAME_FAULT) &&
                !trace_contains_frame_type(&context, A90_WP2_5B_FRAME_END),
            "invalid CLOSE transition fabricated a complete trace");
    require(result.kmsg_reads_after_fault == 0,
            "invalid CLOSE transition performed a later kmsg read");
    require(context.open_fds[TEST_TRACE_FD] == 0 &&
                context.open_fds[A90_WP2_5B_OWNER_CONTROL_FD] == 0 &&
                context.open_fds[A90_WP2_5B_OWNER_STATUS_FD] == 0,
            "invalid CLOSE transition retained observer descriptors");
}

static void test_final_publication_failure_has_no_closed(enum test_mode mode)
{
    struct fake_context context;
    struct a90_wp2_5b_owner_ops operations;
    struct a90_wp2_5b_owner_result result;
    uint64_t armed_durable;
    int final_fsync_failed = mode == TEST_FINAL_FSYNC_ENOSPC ||
                             mode == TEST_FINAL_FSYNC_EIO ||
                             mode == TEST_FINAL_FSYNC_EINTR;
    int final_bytes_durable = mode == TEST_TRACE_CLOSE_EINTR ||
                              mode == TEST_CLOSED_STATUS_SHORT;

    initialize_context(&context, mode);
    operations = fake_operations(&context);
    require(a90_wp2_5b_owner_run_with_ops(&operations, &result) != 0,
            "final publication failure unexpectedly completed");
    require(result.armed == 1 && result.faulted == 1 && result.closed == 0,
            "final publication failure returned the wrong state");
    require(result.fault_reason == A90_WP2_5B_FAULT_BOUNDARY,
            "final publication failure lost the boundary fault");
    require(context.close_calls[TEST_KMSG_FD] == 1 &&
                context.open_fds[TEST_KMSG_FD] == 0,
            "final publication failure did not close kmsg exactly once");
    require(status_frame_count(&context) == 1 &&
                validate_status_frame(&context, 0) ==
                    A90_WP2_5B_OWNER_STATUS_ARMED,
            "final publication failure emitted a complete CLOSED status");
    armed_durable = status_durable_bytes(&context, 0);
    if (final_bytes_durable) {
        require(result.durable_trace_bytes == context.trace_length &&
                    result.durable_trace_bytes > armed_durable,
                "post-fsync failure lost the exact durable trace length");
    } else {
        require(result.durable_trace_bytes == armed_durable &&
                    context.trace_length > armed_durable,
                "pre-fsync failure claimed undurable trace bytes");
    }
    if (mode == TEST_TRACE_CLOSE_EINTR) {
        require(context.close_calls[TEST_TRACE_FD] == 1 &&
                    context.open_fds[TEST_TRACE_FD] == 1,
                "trace close uncertainty was retried or hidden");
    } else {
        require(context.close_calls[TEST_TRACE_FD] == 1 &&
                    context.open_fds[TEST_TRACE_FD] == 0,
                "final publication failure retained the trace unexpectedly");
    }
    if (final_fsync_failed)
        require(context.fsync_calls == 2,
                "final fsync failure was retried or misattributed");
    require(result.kmsg_reads_after_fault == 0,
            "final publication failure performed a post-fault kmsg read");
}

struct exec_context {
    int flags[7];
    int exec_called;
    int exec_result;
    int ignore_setfd;
};

static int exec_fcntl(void *opaque, int fd, int command, long argument)
{
    struct exec_context *context = opaque;

    if (fd < 3 || fd > 6) {
        errno = EBADF;
        return -1;
    }
    if (command == F_GETFD)
        return context->flags[fd];
    if (command == F_SETFD) {
        if (!context->ignore_setfd)
            context->flags[fd] = (int)argument;
        return 0;
    }
    errno = EINVAL;
    return -1;
}

static int execveat_result(void *opaque, int fd, const char *path,
                           char *const argv[], char *const envp[], int flags)
{
    struct exec_context *context = opaque;

    require(fd == A90_WP2_5B_OWNER_EXEC_FD, "exec fd mismatch");
    require(path != NULL && path[0] == '\0', "exec path was not empty");
    require(argv != NULL && argv[0] != NULL && argv[1] == NULL &&
                strcmp(argv[0], "a90-wp2-5b-observer") == 0,
            "exec argv mismatch");
    require(envp != NULL && envp[0] == NULL, "exec environment not empty");
    require(flags == AT_EMPTY_PATH, "exec flags mismatch");
    ++context->exec_called;
    errno = ENOEXEC;
    return context->exec_result;
}

static void test_exec_waiter_and_launch_gates(void)
{
    struct exec_context exec_context;
    struct a90_wp2_5b_exec_ops exec_ops;
    struct a90_wp2_5b_waiter_reservation reservation;
    struct a90_wp2_5b_launch_snapshot snapshot;
    unsigned char *digests[] = {
        snapshot.profile_sha256,
        snapshot.affinity_sha256,
        snapshot.ioprio_sha256,
        snapshot.uclamp_sha256,
        snapshot.cgroup_sha256,
        snapshot.native_reserve_sha256,
        snapshot.root_sha256,
        snapshot.cwd_sha256,
        snapshot.umask_sha256,
        snapshot.credentials_sha256,
        snapshot.groups_sha256,
        snapshot.rlimits_sha256,
        snapshot.capabilities_sha256,
        snapshot.signal_mask_sha256,
        snapshot.signal_dispositions_sha256,
        snapshot.observer_identity_sha256,
        snapshot.parent_identity_sha256,
        snapshot.executable_sha256,
        snapshot.fd_set_sha256,
        snapshot.mapping_set_sha256,
    };
    unsigned int index;

    memset(&exec_context, 0, sizeof(exec_context));
    exec_context.exec_result = -1;
    exec_context.flags[3] = FD_CLOEXEC;
    exec_context.flags[4] = FD_CLOEXEC;
    exec_context.flags[5] = FD_CLOEXEC;
    exec_context.flags[6] = FD_CLOEXEC;
    exec_ops.context = &exec_context;
    exec_ops.fcntl_fn = exec_fcntl;
    exec_ops.execveat_fn = execveat_result;
    require(a90_wp2_5b_child_exec_transition(&exec_ops) != 0,
            "failed exec transition unexpectedly returned");
    require(exec_context.exec_called == 1, "exec transition did not call execveat");
    require((exec_context.flags[3] & FD_CLOEXEC) != 0 &&
                (exec_context.flags[4] & FD_CLOEXEC) != 0 &&
                (exec_context.flags[5] & FD_CLOEXEC) != 0,
            "failed exec transition did not rearm cloexec");

    exec_context.exec_result = 0;
    exec_context.exec_called = 0;
    require(a90_wp2_5b_child_exec_transition(&exec_ops) != 0,
            "impossible exec return was accepted");
    require(exec_context.exec_called == 1,
            "impossible exec fixture did not call execveat");
    require((exec_context.flags[3] & FD_CLOEXEC) != 0 &&
                (exec_context.flags[4] & FD_CLOEXEC) != 0 &&
                (exec_context.flags[5] & FD_CLOEXEC) != 0,
            "impossible exec return did not rearm cloexec");

    exec_context.exec_result = -1;
    exec_context.exec_called = 0;
    exec_context.ignore_setfd = 1;
    require(a90_wp2_5b_child_exec_transition(&exec_ops) != 0,
            "unreadable cloexec transition was accepted");
    require(exec_context.exec_called == 0,
            "execveat ran before cloexec clear readback");

    memset(&reservation, 0, sizeof(reservation));
    reservation.pid = 99;
    require(a90_wp2_5b_waiter_reserve(&reservation, 123, 456) != 0,
            "stale waiter reservation was overwritten");
    memset(&reservation, 0, sizeof(reservation));
    require(a90_wp2_5b_waiter_reserve(&reservation, 123, 456) == 0,
            "waiter reservation failed");
    require(a90_wp2_5b_waiter_generic_reaper_may_reap(&reservation, 123, 456) == 0,
            "generic reaper did not skip exact reservation");
    require(a90_wp2_5b_waiter_generic_reaper_may_reap(&reservation, 124, 457) == 1,
            "generic reaper rejected unrelated identity");
    require(a90_wp2_5b_waiter_mark_reaped(&reservation, 123, 456) == 0,
            "exact waiter could not mark reaped");
    require(a90_wp2_5b_waiter_release(&reservation) == 0,
            "waiter reservation did not release");

    memset(&snapshot, 0, sizeof(snapshot));
    for (index = 0; index < sizeof(digests) / sizeof(digests[0]); ++index)
        memset(digests[index], (int)(index + 1), 32);
    snapshot.sched_other = 1;
    snapshot.priority_zero = 1;
    snapshot.reset_on_fork = 1;
    snapshot.nice_nonnegative = 1;
    snapshot.rlimit_rtprio_zero = 1;
    snapshot.rlimit_rttime_positive_bounded = 1;
    snapshot.cap_sys_nice_absent = 1;
    snapshot.cap_sys_resource_absent = 1;
    snapshot.sigchld_blocked = 1;
    snapshot.sigchld_default = 1;
    snapshot.sigchld_no_cldwait_absent = 1;
    snapshot.waiter_reserved = 1;
    snapshot.static_elf_fd_validated = 1;
    snapshot.clean_mappings = 1;
    snapshot.exact_inherited_fd_set = 1;
    snapshot.fixed_argv = 1;
    snapshot.empty_environment = 1;
    snapshot.null_stdio = 1;
    require(a90_wp2_5b_validate_launch_snapshot(&snapshot) == 0,
            "valid launch snapshot rejected");
    snapshot.sigchld_no_cldwait_absent = 0;
    require(a90_wp2_5b_validate_launch_snapshot(&snapshot) != 0,
            "unsafe launch snapshot accepted");
}

static uint32_t evaluate_filter(const struct sock_filter *instructions,
                                unsigned short count,
                                const struct seccomp_data *data)
{
    uint32_t accumulator = 0;
    unsigned int pc = 0;

    while (pc < count) {
        const struct sock_filter *instruction = &instructions[pc];

        if (instruction->code == (BPF_LD | BPF_W | BPF_ABS)) {
            require(instruction->k <= sizeof(*data) - sizeof(uint32_t),
                    "filter load outside seccomp_data");
            memcpy(&accumulator, (const unsigned char *)data + instruction->k,
                   sizeof(accumulator));
            ++pc;
        } else if (instruction->code == (BPF_JMP | BPF_JEQ | BPF_K)) {
            pc += 1u + (accumulator == instruction->k ? instruction->jt
                                                      : instruction->jf);
        } else if (instruction->code == (BPF_JMP | BPF_JGT | BPF_K)) {
            pc += 1u + (accumulator > instruction->k ? instruction->jt
                                                     : instruction->jf);
        } else if (instruction->code == (BPF_RET | BPF_K)) {
            return instruction->k;
        } else {
            fail("filter emitted an unsupported instruction");
        }
    }
    fail("filter fell off the end");
    return 0;
}

static uint32_t filter_decision5(const struct sock_filter *instructions,
                                 unsigned short count, int syscall_nr,
                                 uint64_t arg0, uint64_t arg1, uint64_t arg2,
                                 uint64_t arg3, uint64_t arg4)
{
    struct seccomp_data data;

    memset(&data, 0, sizeof(data));
    data.arch = AUDIT_ARCH_X86_64;
    data.nr = syscall_nr;
    data.args[0] = arg0;
    data.args[1] = arg1;
    data.args[2] = arg2;
    data.args[3] = arg3;
    data.args[4] = arg4;
    return evaluate_filter(instructions, count, &data);
}

static uint32_t filter_decision(const struct sock_filter *instructions,
                                unsigned short count, int syscall_nr,
                                uint64_t arg0, uint64_t arg1, uint64_t arg2)
{
    return filter_decision5(instructions, count, syscall_nr, arg0, arg1, arg2,
                            0, 0);
}

static void test_filter_bytecode(void)
{
    struct a90_wp2_5b_owner_confinement request;
    struct sock_filter instructions[TEST_FILTER_CAP];
    struct seccomp_data wrong_arch;
    unsigned short count = 0;

    memset(&request, 0, sizeof(request));
    request.control_fd = A90_WP2_5B_OWNER_CONTROL_FD;
    request.status_fd = A90_WP2_5B_OWNER_STATUS_FD;
    request.trace_fd = TEST_TRACE_FD;
    request.kmsg_fd = TEST_KMSG_FD;
    require(a90_wp2_5b_owner_build_filter(&request, instructions,
                                           TEST_FILTER_CAP, &count) == 0 &&
                count != 0,
            "unable to build observer filter");
    require(filter_decision(instructions, count, __NR_read, 3, 0, 0) ==
                SECCOMP_RET_ALLOW,
            "filter rejected control read");
    require(filter_decision(instructions, count, __NR_read, 8, 0, 0) ==
                SECCOMP_RET_ALLOW,
            "filter rejected kmsg read");
    require(filter_decision(instructions, count, __NR_read, 7, 0, 0) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter allowed trace read");
    require(filter_decision(instructions, count, __NR_read,
                            (UINT64_C(1) << 32) | 8u, 0, 0) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter ignored high fd bits");
    require(filter_decision(instructions, count, __NR_write, 4, 0, 0) ==
                SECCOMP_RET_ALLOW,
            "filter rejected status write");
    require(filter_decision(instructions, count, __NR_write, 7, 0, 0) ==
                SECCOMP_RET_ALLOW,
            "filter rejected trace write");
    require(filter_decision(instructions, count, __NR_write, 8, 0, 0) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter allowed kmsg write");
    require(filter_decision(instructions, count, __NR_fsync, 7, 0, 0) ==
                SECCOMP_RET_ALLOW,
            "filter rejected trace fsync");
    require(filter_decision(instructions, count, __NR_fsync, 4, 0, 0) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter allowed status fsync");
    require(filter_decision(instructions, count, __NR_fcntl, 7, F_GETFD, 0) ==
                SECCOMP_RET_ALLOW,
            "filter rejected read-only fcntl");
    require(filter_decision(instructions, count, __NR_fcntl, 7, F_SETFD, 0) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter allowed mutating fcntl");
    require(filter_decision(instructions, count, __NR_fcntl, 7,
                            (UINT64_C(1) << 32) | F_GETFD, 0) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter ignored high fcntl-command bits");
    require(filter_decision(instructions, count, __NR_lseek, 8, 0, SEEK_END) ==
                SECCOMP_RET_ALLOW,
            "filter rejected exact kmsg seek");
    require(filter_decision(instructions, count, __NR_lseek, 8, 1, SEEK_END) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter allowed nonzero seek offset");
    require(filter_decision(instructions, count, __NR_lseek, 8,
                            UINT64_C(1) << 32, SEEK_END) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter ignored high seek-offset bits");
    require(filter_decision(instructions, count, __NR_lseek, 8, 0,
                            (UINT64_C(1) << 32) | SEEK_END) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter ignored high seek-whence bits");
    require(filter_decision(instructions, count, __NR_openat, AT_FDCWD, 0, 0) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter allowed post-seal path open");
#ifdef __NR_socket
    require(filter_decision(instructions, count, __NR_socket, 2, 1, 0) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter allowed socket");
#endif
#ifdef __NR_ioctl
    require(filter_decision(instructions, count, __NR_ioctl, 8, 0, 0) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter allowed ioctl");
#endif
#ifdef __NR_poll
    require(filter_decision(instructions, count, __NR_poll, 0, 2, 10) ==
                SECCOMP_RET_ALLOW,
            "filter rejected bounded poll");
    require(filter_decision(instructions, count, __NR_poll, 0, 3, 10) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter allowed excessive poll descriptors");
    require(filter_decision(instructions, count, __NR_poll, 0, 2, 60001) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter allowed excessive poll timeout");
#endif
#ifdef __NR_ppoll
    require(filter_decision5(instructions, count, __NR_ppoll, 0, 2, 1, 0, 0) ==
                SECCOMP_RET_ALLOW,
            "filter rejected exact ppoll shape");
    require(filter_decision5(instructions, count, __NR_ppoll, 0, 2, 1, 1, 0) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter allowed ppoll signal-mask mutation");
    require(filter_decision5(instructions, count, __NR_ppoll, 0, 2, 1, 0, 8) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter allowed nonzero ppoll sigset size");
#endif
    memset(&wrong_arch, 0, sizeof(wrong_arch));
    wrong_arch.arch = AUDIT_ARCH_AARCH64;
    wrong_arch.nr = __NR_read;
    wrong_arch.args[0] = 8;
    require(evaluate_filter(instructions, count, &wrong_arch) ==
                SECCOMP_RET_KILL_PROCESS,
            "filter allowed wrong architecture");
}

int main(void)
{
    run_owner_case(TEST_HAPPY, 0, 1);
    run_owner_case(TEST_EPIPE, A90_WP2_5B_FAULT_EPIPE, 1);
    run_owner_case(TEST_EINVAL, A90_WP2_5B_FAULT_EINVAL, 1);
    run_owner_case(TEST_EFAULT, A90_WP2_5B_FAULT_EFAULT, 1);
    run_owner_case(TEST_READ_EINTR, A90_WP2_5B_FAULT_BOUNDARY, 1);
    run_owner_case(TEST_ZERO_READ, A90_WP2_5B_FAULT_BOUNDARY, 1);
    run_owner_case(TEST_READ_ERROR, A90_WP2_5B_FAULT_READ, 1);
    run_owner_case(TEST_POLLERR, A90_WP2_5B_FAULT_EPIPE, 1);
    run_owner_case(TEST_POLL_FAILURE, A90_WP2_5B_FAULT_POLL, 1);
    run_owner_case(TEST_POLL_EINTR, A90_WP2_5B_FAULT_BOUNDARY, 1);
    run_owner_case(TEST_KMSG_HUP, A90_WP2_5B_FAULT_BOUNDARY, 1);
    run_owner_case(TEST_SEQUENCE_GAP, A90_WP2_5B_FAULT_SEQUENCE, 1);
    run_owner_case(TEST_MALFORMED_RECORD,
                   A90_WP2_5B_FAULT_RECORD_FORMAT, 1);
    run_owner_case(TEST_COUNT_CAP, A90_WP2_5B_FAULT_COUNT_CAP, 1);
    run_owner_case(TEST_BYTE_CAP, A90_WP2_5B_FAULT_BYTE_CAP, 1);
    test_invalid_close_transition_does_not_complete(TEST_DUPLICATE_CLOSE);
    test_invalid_close_transition_does_not_complete(TEST_PARTIAL_CLOSE);
    run_owner_case(TEST_PARENT_EOF, A90_WP2_5B_FAULT_BOUNDARY, 1);
    run_owner_case(TEST_WRONG_RDEV, 0, 0);
    run_owner_case(TEST_WRONG_KMSG_FLAGS, 0, 0);
    run_owner_case(TEST_CONFINEMENT_FAIL, 0, 0);
    run_owner_case(TEST_LSEEK_FAIL, 0, 0);
    run_owner_case(TEST_ARM_FSYNC_FAIL, 0, 0);
    run_owner_case(TEST_RETAINED_EXEC_FD, 0, 0);
    run_owner_case(TEST_SHORT_STATUS, 0, 0);
    test_fault_without_parent_close_is_bounded();
    test_fault_close_uncertainty_exits_immediately();
    test_fault_fsync_failure_still_closes_reader();
    test_fault_status_failure_exits_immediately();
    test_finalize_close_uncertainty_exits_without_terminal_status(
        TEST_NORMAL_CLOSE_EINTR);
    test_finalize_close_uncertainty_exits_without_terminal_status(
        TEST_PARENT_EOF_CLOSE_EINTR);
    test_invalid_close_transition_does_not_complete(TEST_FAULT_NORMAL_CLOSE);
    test_invalid_close_transition_does_not_complete(TEST_HEALTHY_FAULT_CLOSE);
    test_invalid_close_transition_does_not_complete(
        TEST_INVALID_CAUSE_THEN_FAULT_CLOSE);
    test_invalid_close_transition_does_not_complete(
        TEST_RESERVED_CLOSE_THEN_FAULT_CLOSE);
    test_invalid_close_transition_does_not_complete(
        TEST_UNKNOWN_KIND_THEN_FAULT_CLOSE);
    test_invalid_close_transition_does_not_complete(
        TEST_FAULTED_INVALID_CAUSE_THEN_FAULT_CLOSE);
    test_final_publication_failure_has_no_closed(TEST_FINAL_END_WRITE_FAIL);
    test_final_publication_failure_has_no_closed(TEST_FINAL_FSYNC_ENOSPC);
    test_final_publication_failure_has_no_closed(TEST_FINAL_FSYNC_EIO);
    test_final_publication_failure_has_no_closed(TEST_FINAL_FSYNC_EINTR);
    test_final_publication_failure_has_no_closed(TEST_TRACE_CLOSE_EINTR);
    test_final_publication_failure_has_no_closed(TEST_CLOSED_STATUS_SHORT);
    test_exec_waiter_and_launch_gates();
    test_filter_bytecode();
    return 0;
}
