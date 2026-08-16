#define _GNU_SOURCE

/*
 * Host-qualified WP2-5b.3a effect-free /dev/kmsg observer component.
 *
 * This component has no effect-dispatch, journal, receipt, recovery, device,
 * or parent-integration API.  The real entry point uses only fixed descriptor
 * numbers and fixed leaf/path literals.  Host tests drive the same state
 * machine through the syscall table below without opening /dev/kmsg.
 */

#include "a90_wp2_5b_kmsg_owner.h"
#include "a90_wp2_5b_kmsg_contract.h"

#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <linux/audit.h>
#include <linux/capability.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <time.h>
#include <unistd.h>

#ifndef AT_EMPTY_PATH
#define AT_EMPTY_PATH 0x1000
#endif
#ifndef AT_FDCWD
#define AT_FDCWD -100
#endif
#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0400000
#endif
#ifndef O_CLOEXEC
#define O_CLOEXEC 02000000
#endif
#ifndef SECCOMP_RET_KILL_PROCESS
#define SECCOMP_RET_KILL_PROCESS SECCOMP_RET_KILL
#endif
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "observer seccomp argument layout requires little endian"
#endif

#define OWNER_TRACE_LEAF "trace.pending"
#define OWNER_KMSG_PATH "/dev/kmsg"
#define OWNER_BOOTSTRAP_RETRY_CEILING 64u
#define OWNER_BOOTSTRAP_POLL_TIMEOUT_MS 1000
#define OWNER_FILE_WRITE_CEILING 64u
#define OWNER_RUNTIME_RETRY_CEILING 1048576u
#define OWNER_RUNTIME_POLL_TIMEOUT_CEILING_MS 60000u
#define OWNER_MAX_FILTER_INSNS A90_WP2_5B_OWNER_FILTER_CAPACITY

struct owner_start {
    unsigned char run_binding_sha256[32];
    unsigned char qualification_sha256[32];
    unsigned char observer_binary_sha256[32];
    unsigned char driver_init_epoch_sha256[32];
    unsigned char capture_close_binding_sha256[32];
    uint32_t record_count_cap;
    uint64_t record_byte_cap;
    uint32_t expected_uid;
    uint32_t expected_gid;
    uint32_t read_eintr_budget;
    uint32_t poll_eintr_budget;
    uint32_t pipe_eintr_budget;
    uint32_t poll_timeout_ms;
    uint32_t fault_close_poll_budget;
};

struct owner_pipe_state {
    uint64_t control_next;
    uint64_t status_next;
};

struct owner_emit_context {
    const struct a90_wp2_5b_owner_ops *ops;
    int trace_fd;
    uint64_t bytes;
    uint32_t pending_payload_length;
    uint8_t pending_frame_type;
    uint32_t fault_reason;
    int32_t fault_errno;
    uint32_t fault_revents;
    int failed;
};

struct owner_runtime {
    const struct a90_wp2_5b_owner_ops *ops;
    struct a90_wp2_5b_owner_result *result;
    struct owner_start start;
    struct owner_pipe_state pipe;
    struct owner_emit_context emit;
    struct a90_wp2_5b_stream stream;
    int run_dir_fd;
    int control_fd;
    int status_fd;
    int trace_fd;
    int kmsg_fd;
    int stream_started;
    int close_received;
    int reader_close_uncertain;
    int fault_publication_failed;
    int control_transition_invalid;
    uint64_t durable_trace_bytes;
};

static uint16_t get_u16_be(const unsigned char value[2])
{
    return (uint16_t)(((uint16_t)value[0] << 8) | value[1]);
}

static uint32_t get_u32_be(const unsigned char value[4])
{
    return ((uint32_t)value[0] << 24) | ((uint32_t)value[1] << 16) |
           ((uint32_t)value[2] << 8) | (uint32_t)value[3];
}

static uint64_t get_u64_be(const unsigned char value[8])
{
    uint64_t result = 0;
    unsigned int index;

    for (index = 0; index < 8; ++index)
        result = (result << 8) | value[index];
    return result;
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
        value[index] = (unsigned char)(input >> (56u - (index * 8u)));
}

static int digest_nonzero(const unsigned char value[32])
{
    unsigned int index;
    unsigned char aggregate = 0;

    if (value == NULL)
        return 0;
    for (index = 0; index < 32; ++index)
        aggregate |= value[index];
    return aggregate != 0;
}

static int owner_ops_valid(const struct a90_wp2_5b_owner_ops *ops)
{
    return ops != NULL && ops->openat_fn != NULL && ops->close_fn != NULL &&
           ops->fstat_fn != NULL && ops->fcntl_fn != NULL &&
           ops->lseek_fn != NULL && ops->read_fn != NULL &&
           ops->write_fn != NULL && ops->poll_fn != NULL &&
           ops->fsync_fn != NULL && ops->apply_confinement_fn != NULL;
}

static int fd_has_cloexec(const struct a90_wp2_5b_owner_ops *ops, int fd)
{
    int value = ops->fcntl_fn(ops->context, fd, F_GETFD, 0);

    return value >= 0 && (value & FD_CLOEXEC) != 0;
}

static int fd_flags(const struct a90_wp2_5b_owner_ops *ops, int fd)
{
    return ops->fcntl_fn(ops->context, fd, F_GETFL, 0);
}

static int close_once(const struct a90_wp2_5b_owner_ops *ops, int *fd)
{
    int value;

    if (fd == NULL || *fd < 0)
        return 0;
    value = ops->close_fn(ops->context, *fd);
    *fd = -1;
    return value;
}

static int file_emit(void *opaque, const unsigned char *data, size_t length)
{
    struct owner_emit_context *context = opaque;
    size_t written = 0;
    unsigned int attempts = 0;

    if (context == NULL || context->failed || data == NULL || length == 0 ||
        length > UINT64_MAX - context->bytes)
        return -1;
    while (written < length && attempts < OWNER_FILE_WRITE_CEILING) {
        ssize_t value = context->ops->write_fn(
            context->ops->context, context->trace_fd, data + written,
            length - written);

        ++attempts;
        if (value < 0 && errno == EINTR)
            continue;
        if (value <= 0 || (size_t)value > length - written) {
            context->failed = 1;
            return -1;
        }
        written += (size_t)value;
    }
    if (written != length) {
        context->failed = 1;
        return -1;
    }
    context->bytes += length;
    if (context->pending_payload_length != 0) {
        if (length != context->pending_payload_length) {
            context->failed = 1;
            return -1;
        }
        if (context->pending_frame_type == A90_WP2_5B_FRAME_FAULT &&
            length == A90_WP2_5B_FAULT_PAYLOAD_SIZE) {
            context->fault_reason = get_u32_be(data);
            context->fault_errno = (int32_t)get_u32_be(data + 4);
            context->fault_revents = get_u32_be(data + 8);
        }
        context->pending_payload_length = 0;
        context->pending_frame_type = 0;
    } else if (length == A90_WP2_5B_FRAME_HEADER_SIZE && data[1] == 0 &&
               data[2] == 0 && data[3] == 0 &&
               data[0] >= A90_WP2_5B_FRAME_ARM &&
               data[0] <= A90_WP2_5B_FRAME_END) {
        context->pending_frame_type = data[0];
        context->pending_payload_length = get_u32_be(data + 4);
        if (context->pending_payload_length == 0) {
            context->failed = 1;
            return -1;
        }
    }
    return 0;
}

static int poll_one(const struct a90_wp2_5b_owner_ops *ops, int fd,
                    short events, uint32_t budget, int timeout_ms,
                    short *revents)
{
    uint32_t attempts = 0;

    if (budget == 0 || revents == NULL)
        return -1;
    while (attempts < budget) {
        struct pollfd descriptor;
        int value;

        memset(&descriptor, 0, sizeof(descriptor));
        descriptor.fd = fd;
        descriptor.events = events;
        value = ops->poll_fn(ops->context, &descriptor, 1, timeout_ms);
        ++attempts;
        if (value < 0 && errno == EINTR)
            continue;
        if (value != 1)
            return -1;
        *revents = descriptor.revents;
        return 0;
    }
    return -1;
}

static int pipe_write_frame(struct owner_runtime *runtime, uint8_t direction,
                            uint8_t kind, const unsigned char *payload,
                            uint16_t payload_length)
{
    unsigned char frame[A90_WP2_5B_OWNER_MAX_FRAME_SIZE];
    uint64_t sequence;
    uint32_t budget;
    uint32_t attempts = 0;
    size_t total;

    if (runtime == NULL || direction != A90_WP2_5B_OWNER_DIRECTION_STATUS ||
        payload == NULL || payload_length != A90_WP2_5B_OWNER_STATUS_PAYLOAD_SIZE)
        return -1;
    if (runtime->pipe.status_next == UINT64_MAX)
        return -1;
    sequence = runtime->pipe.status_next;
    memcpy(frame, a90_wp2_5b_owner_magic, 8);
    put_u16_be(frame + 8, A90_WP2_5B_OWNER_VERSION);
    frame[10] = direction;
    frame[11] = kind;
    put_u64_be(frame + 12, sequence);
    put_u16_be(frame + 20, payload_length);
    put_u16_be(frame + 22, 0);
    memcpy(frame + A90_WP2_5B_OWNER_PIPE_HEADER_SIZE, payload, payload_length);
    total = A90_WP2_5B_OWNER_PIPE_HEADER_SIZE + payload_length;
    budget = runtime->start.pipe_eintr_budget;
    while (attempts < budget) {
        short revents = 0;
        ssize_t value;

        if (poll_one(runtime->ops, runtime->status_fd, POLLOUT, budget,
                     (int)runtime->start.poll_timeout_ms, &revents) != 0 ||
            revents != POLLOUT)
            return -1;
        value = runtime->ops->write_fn(runtime->ops->context,
                                       runtime->status_fd, frame, total);
        ++attempts;
        if (value < 0 && (errno == EINTR || errno == EAGAIN))
            continue;
        if (value != (ssize_t)total)
            return -1;
        runtime->pipe.status_next = sequence + 1;
        return 0;
    }
    return -1;
}

static int read_exact(const struct a90_wp2_5b_owner_ops *ops, int fd,
                      unsigned char *buffer, size_t length, uint32_t budget,
                      int *saw_eof)
{
    size_t used = 0;
    uint32_t attempts = 0;

    if (buffer == NULL || length == 0 || budget == 0 || saw_eof == NULL)
        return -1;
    *saw_eof = 0;
    while (used < length && attempts < budget) {
        ssize_t value = ops->read_fn(ops->context, fd, buffer + used,
                                     length - used);

        ++attempts;
        if (value < 0 && errno == EINTR)
            continue;
        if (value < 0 && errno == EAGAIN) {
            short revents = 0;
            if (poll_one(ops, fd, POLLIN, budget,
                         OWNER_BOOTSTRAP_POLL_TIMEOUT_MS, &revents) != 0 ||
                (revents & (POLLERR | POLLNVAL)) != 0)
                return -1;
            continue;
        }
        if (value == 0) {
            *saw_eof = 1;
            return used == 0 ? 1 : -1;
        }
        if (value < 0 || (size_t)value > length - used)
            return -1;
        used += (size_t)value;
    }
    return used == length ? 0 : -1;
}

static int pipe_read_frame(struct owner_runtime *runtime, uint8_t expected_kind,
                           unsigned char *payload, uint16_t payload_length,
                           uint32_t budget, int *saw_eof)
{
    unsigned char header[A90_WP2_5B_OWNER_PIPE_HEADER_SIZE];
    uint16_t actual_length;
    uint64_t sequence;
    int value;

    value = read_exact(runtime->ops, runtime->control_fd, header,
                       sizeof(header), budget, saw_eof);
    if (value != 0)
        return value;
    if (memcmp(header, a90_wp2_5b_owner_magic, 8) != 0 ||
        get_u16_be(header + 8) != A90_WP2_5B_OWNER_VERSION ||
        header[10] != A90_WP2_5B_OWNER_DIRECTION_CONTROL ||
        header[11] != expected_kind || get_u16_be(header + 22) != 0)
        return -1;
    sequence = get_u64_be(header + 12);
    actual_length = get_u16_be(header + 20);
    if (sequence != runtime->pipe.control_next ||
        runtime->pipe.control_next == UINT64_MAX ||
        actual_length != payload_length)
        return -1;
    value = read_exact(runtime->ops, runtime->control_fd, payload,
                       payload_length, budget, saw_eof);
    if (value != 0)
        return -1;
    runtime->pipe.control_next = sequence + 1;
    return 0;
}

static int parse_start_payload(const unsigned char *payload,
                               struct owner_start *start)
{
    uint32_t reserved;

    if (payload == NULL || start == NULL)
        return -1;
    memset(start, 0, sizeof(*start));
    memcpy(start->run_binding_sha256, payload, 32);
    memcpy(start->qualification_sha256, payload + 32, 32);
    memcpy(start->observer_binary_sha256, payload + 64, 32);
    memcpy(start->driver_init_epoch_sha256, payload + 96, 32);
    memcpy(start->capture_close_binding_sha256, payload + 128, 32);
    start->record_count_cap = get_u32_be(payload + 160);
    start->record_byte_cap = get_u64_be(payload + 164);
    start->expected_uid = get_u32_be(payload + 172);
    start->expected_gid = get_u32_be(payload + 176);
    start->read_eintr_budget = get_u32_be(payload + 180);
    start->poll_eintr_budget = get_u32_be(payload + 184);
    start->pipe_eintr_budget = get_u32_be(payload + 188);
    start->poll_timeout_ms = get_u32_be(payload + 192);
    start->fault_close_poll_budget = get_u32_be(payload + 196);
    reserved = get_u32_be(payload + 200);
    if (!digest_nonzero(start->run_binding_sha256) ||
        !digest_nonzero(start->qualification_sha256) ||
        !digest_nonzero(start->observer_binary_sha256) ||
        !digest_nonzero(start->driver_init_epoch_sha256) ||
        !digest_nonzero(start->capture_close_binding_sha256) ||
        start->record_count_cap == 0 || start->record_byte_cap == 0 ||
        start->read_eintr_budget == 0 || start->poll_eintr_budget == 0 ||
        start->pipe_eintr_budget == 0 || start->poll_timeout_ms == 0 ||
        start->fault_close_poll_budget == 0 ||
        start->read_eintr_budget > OWNER_RUNTIME_RETRY_CEILING ||
        start->poll_eintr_budget > OWNER_RUNTIME_RETRY_CEILING ||
        start->pipe_eintr_budget > OWNER_RUNTIME_RETRY_CEILING ||
        start->poll_timeout_ms > OWNER_RUNTIME_POLL_TIMEOUT_CEILING_MS ||
        start->fault_close_poll_budget > OWNER_RUNTIME_RETRY_CEILING ||
        reserved != 0)
        return -1;
    return 0;
}

static void fill_status_payload(
                                unsigned char payload[A90_WP2_5B_OWNER_STATUS_PAYLOAD_SIZE],
                                uint32_t reason,
                                int32_t os_errno, uint32_t revents,
                                uint64_t trace_dev, uint64_t trace_ino,
                                uint64_t kmsg_dev, uint64_t kmsg_ino,
                                uint64_t kmsg_rdev,
                                uint64_t durable_bytes, uint64_t auxiliary)
{
    put_u32_be(payload, reason);
    put_u32_be(payload + 4, (uint32_t)os_errno);
    put_u32_be(payload + 8, revents);
    put_u32_be(payload + 12, 0);
    put_u64_be(payload + 16, trace_dev);
    put_u64_be(payload + 24, trace_ino);
    put_u64_be(payload + 32, kmsg_dev);
    put_u64_be(payload + 40, kmsg_ino);
    put_u64_be(payload + 48, kmsg_rdev);
    put_u64_be(payload + 56, durable_bytes);
    put_u64_be(payload + 64, auxiliary);
}

static int send_status(struct owner_runtime *runtime, uint8_t kind,
                       uint32_t reason, int32_t os_errno, uint32_t revents,
                       uint64_t auxiliary)
{
    unsigned char payload[A90_WP2_5B_OWNER_STATUS_PAYLOAD_SIZE];

    fill_status_payload(payload, reason, os_errno, revents,
                        runtime->result->trace_dev,
                        runtime->result->trace_ino,
                        runtime->result->kmsg_dev,
                        runtime->result->kmsg_ino,
                        runtime->result->kmsg_rdev,
                        runtime->durable_trace_bytes, auxiliary);
    return pipe_write_frame(runtime, A90_WP2_5B_OWNER_DIRECTION_STATUS, kind,
                            payload, sizeof(payload));
}

static int close_reader_once(struct owner_runtime *runtime)
{
    int close_error;
    int value;

    if (runtime == NULL)
        return -1;
    if (runtime->kmsg_fd < 0)
        return runtime->reader_close_uncertain ? -1 : 0;
    value = close_once(runtime->ops, &runtime->kmsg_fd);
    if (value != 0) {
        close_error = errno != 0 ? errno : EIO;
        runtime->reader_close_uncertain = 1;
        if (!runtime->result->faulted) {
            runtime->result->faulted = 1;
            runtime->result->fault_reason = A90_WP2_5B_FAULT_BOUNDARY;
            runtime->result->os_errno = close_error;
            runtime->result->poll_revents = 0;
            if (runtime->stream_started && !runtime->emit.failed) {
                if (a90_wp2_5b_stream_note_fault(
                        &runtime->stream, A90_WP2_5B_FAULT_BOUNDARY,
                        close_error, 0) != 0)
                    runtime->emit.failed = 1;
                else if (runtime->ops->fsync_fn(runtime->ops->context,
                                                runtime->trace_fd) != 0)
                    runtime->emit.failed = 1;
                else {
                    runtime->durable_trace_bytes = runtime->emit.bytes;
                    runtime->result->durable_trace_bytes =
                        runtime->durable_trace_bytes;
                }
            }
        }
    }
    return value;
}

static int note_fault(struct owner_runtime *runtime, uint32_t reason,
                      int32_t os_errno, uint32_t revents)
{
    int trace_failed;
    int close_failed;

    if (!runtime->result->faulted) {
        runtime->result->faulted = 1;
        runtime->result->fault_reason = reason;
        runtime->result->os_errno = os_errno;
        runtime->result->poll_revents = revents;
        if (runtime->stream_started && !runtime->emit.failed) {
            if (a90_wp2_5b_stream_note_fault(&runtime->stream, reason,
                                             os_errno, revents) != 0)
                runtime->emit.failed = 1;
            else if (runtime->ops->fsync_fn(runtime->ops->context,
                                            runtime->trace_fd) != 0)
                runtime->emit.failed = 1;
            else {
                runtime->durable_trace_bytes = runtime->emit.bytes;
                runtime->result->durable_trace_bytes =
                    runtime->durable_trace_bytes;
            }
        }
        trace_failed = runtime->emit.failed;
        close_failed = close_reader_once(runtime) != 0;
        if (trace_failed || close_failed) {
            runtime->fault_publication_failed = 1;
            return -1;
        }
        if (send_status(runtime, A90_WP2_5B_OWNER_STATUS_FAULTED, reason,
                        os_errno, revents, 0) != 0) {
            runtime->fault_publication_failed = 1;
            return -1;
        }
    }
    return -1;
}

static int adopt_stream_fault(struct owner_runtime *runtime)
{
    uint32_t reason;
    int trace_failed;
    int close_failed;

    if (runtime == NULL || !runtime->stream.faulted || runtime->emit.failed)
        return -1;
    reason = runtime->emit.fault_reason;
    if (reason < A90_WP2_5B_FAULT_READ || reason > A90_WP2_5B_FAULT_EFAULT)
        return -1;
    runtime->result->faulted = 1;
    runtime->result->fault_reason = reason;
    runtime->result->os_errno = runtime->emit.fault_errno;
    runtime->result->poll_revents = runtime->emit.fault_revents;
    trace_failed = runtime->ops->fsync_fn(runtime->ops->context,
                                          runtime->trace_fd) != 0;
    if (!trace_failed) {
        runtime->durable_trace_bytes = runtime->emit.bytes;
        runtime->result->durable_trace_bytes = runtime->durable_trace_bytes;
    }
    close_failed = close_reader_once(runtime) != 0;
    if (trace_failed || close_failed) {
        runtime->fault_publication_failed = 1;
        return -1;
    }
    if (send_status(runtime, A90_WP2_5B_OWNER_STATUS_FAULTED, reason,
                    runtime->emit.fault_errno, runtime->emit.fault_revents,
                    runtime->stream.record_count) != 0) {
        runtime->fault_publication_failed = 1;
        return -1;
    }
    return -1;
}

static int rearm_bootstrap_fds(struct owner_runtime *runtime)
{
    const int descriptors[] = {
        A90_WP2_5B_OWNER_CONTROL_FD,
        A90_WP2_5B_OWNER_STATUS_FD,
        A90_WP2_5B_OWNER_RUN_DIR_FD,
    };
    unsigned int index;

    for (index = 0; index < sizeof(descriptors) / sizeof(descriptors[0]);
         ++index) {
        int flags = runtime->ops->fcntl_fn(runtime->ops->context,
                                           descriptors[index], F_GETFD, 0);
        if (flags < 0 ||
            runtime->ops->fcntl_fn(runtime->ops->context, descriptors[index],
                                   F_SETFD, flags | FD_CLOEXEC) != 0 ||
            !fd_has_cloexec(runtime->ops, descriptors[index]))
            return -1;
    }
    errno = 0;
    if (runtime->ops->fcntl_fn(runtime->ops->context,
                              A90_WP2_5B_OWNER_EXEC_FD, F_GETFD, 0) >= 0 ||
        errno != EBADF)
        return -1;
    return 0;
}

static int validate_initial_fds(struct owner_runtime *runtime)
{
    struct stat status;
    struct stat control_status;
    struct stat output_status;
    int flags;
    int fd;

    for (fd = 0; fd <= 2; ++fd) {
        if (runtime->ops->fstat_fn(runtime->ops->context, fd, &status) != 0 ||
            !S_ISCHR(status.st_mode) || major(status.st_rdev) != 1 ||
            minor(status.st_rdev) != 3)
            return -1;
        flags = fd_flags(runtime->ops, fd);
        if (flags < 0 ||
            (fd == 0 && (flags & O_ACCMODE) != O_RDONLY) ||
            (fd != 0 && (flags & O_ACCMODE) != O_WRONLY))
            return -1;
    }

    if (!fd_has_cloexec(runtime->ops, runtime->control_fd) ||
        !fd_has_cloexec(runtime->ops, runtime->status_fd) ||
        !fd_has_cloexec(runtime->ops, runtime->run_dir_fd))
        return -1;
    if (runtime->ops->fstat_fn(runtime->ops->context, runtime->control_fd,
                               &control_status) != 0 ||
        runtime->ops->fstat_fn(runtime->ops->context, runtime->status_fd,
                               &output_status) != 0 ||
        !S_ISFIFO(control_status.st_mode) || !S_ISFIFO(output_status.st_mode) ||
        (control_status.st_dev == output_status.st_dev &&
         control_status.st_ino == output_status.st_ino))
        return -1;
    flags = fd_flags(runtime->ops, runtime->control_fd);
    if (flags < 0 || (flags & O_ACCMODE) != O_RDONLY ||
        (flags & O_NONBLOCK) == 0)
        return -1;
    flags = fd_flags(runtime->ops, runtime->status_fd);
    if (flags < 0 || (flags & O_ACCMODE) != O_WRONLY ||
        (flags & O_NONBLOCK) == 0)
        return -1;
    flags = fd_flags(runtime->ops, runtime->run_dir_fd);
    if (flags < 0 || (flags & O_ACCMODE) != O_RDONLY)
        return -1;
    if (runtime->ops->fstat_fn(runtime->ops->context, runtime->run_dir_fd,
                               &status) != 0 || !S_ISDIR(status.st_mode))
        return -1;
    return 0;
}

static int open_trace_and_kmsg(struct owner_runtime *runtime)
{
    struct stat status;
    int flags;

    runtime->trace_fd = runtime->ops->openat_fn(
        runtime->ops->context, runtime->run_dir_fd, OWNER_TRACE_LEAF,
        O_WRONLY | O_APPEND | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC,
        0600);
    if (runtime->trace_fd < 0 ||
        runtime->ops->fstat_fn(runtime->ops->context, runtime->trace_fd,
                               &status) != 0 || !S_ISREG(status.st_mode) ||
        (status.st_mode & 0777) != 0600 || status.st_nlink != 1 ||
        !fd_has_cloexec(runtime->ops, runtime->trace_fd))
        return -1;
    if (status.st_size != 0)
        return -1;
    flags = fd_flags(runtime->ops, runtime->trace_fd);
    if (flags < 0 || (flags & O_ACCMODE) != O_WRONLY ||
        (flags & O_APPEND) == 0)
        return -1;
    runtime->result->trace_dev = (uint64_t)status.st_dev;
    runtime->result->trace_ino = (uint64_t)status.st_ino;
    if (close_once(runtime->ops, &runtime->run_dir_fd) != 0)
        return -1;
    runtime->kmsg_fd = runtime->ops->openat_fn(
        runtime->ops->context, AT_FDCWD, OWNER_KMSG_PATH,
        O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC, 0);
    if (runtime->kmsg_fd < 0 ||
        runtime->ops->fstat_fn(runtime->ops->context, runtime->kmsg_fd,
                               &status) != 0 || !S_ISCHR(status.st_mode) ||
        major(status.st_rdev) != 1 || minor(status.st_rdev) != 11 ||
        !fd_has_cloexec(runtime->ops, runtime->kmsg_fd))
        return -1;
    runtime->result->kmsg_dev = (uint64_t)status.st_dev;
    runtime->result->kmsg_ino = (uint64_t)status.st_ino;
    runtime->result->kmsg_rdev = (uint64_t)status.st_rdev;
    if (runtime->trace_fd <= A90_WP2_5B_OWNER_STATUS_FD ||
        runtime->kmsg_fd <= A90_WP2_5B_OWNER_STATUS_FD ||
        runtime->trace_fd == runtime->kmsg_fd)
        return -1;
    flags = fd_flags(runtime->ops, runtime->kmsg_fd);
    if (flags < 0 || (flags & O_ACCMODE) != O_RDONLY ||
        (flags & O_NONBLOCK) == 0)
        return -1;
    return 0;
}

static int validate_kmsg_fd(struct owner_runtime *runtime)
{
    struct stat status;
    int flags;

    if (runtime->ops->fstat_fn(runtime->ops->context, runtime->kmsg_fd,
                               &status) != 0 || !S_ISCHR(status.st_mode) ||
        (uint64_t)status.st_dev != runtime->result->kmsg_dev ||
        (uint64_t)status.st_ino != runtime->result->kmsg_ino ||
        (uint64_t)status.st_rdev != runtime->result->kmsg_rdev ||
        major(status.st_rdev) != 1 || minor(status.st_rdev) != 11 ||
        !fd_has_cloexec(runtime->ops, runtime->kmsg_fd))
        return -1;
    flags = fd_flags(runtime->ops, runtime->kmsg_fd);
    if (flags < 0 || (flags & O_ACCMODE) != O_RDONLY ||
        (flags & O_NONBLOCK) == 0)
        return -1;
    return 0;
}

static int drain_kmsg(struct owner_runtime *runtime)
{
    unsigned char record[A90_WP2_5B_KMSG_RECORD_MAX];
    uint32_t interrupted = 0;

    while (!runtime->result->faulted) {
        ssize_t value;

        ++runtime->result->kmsg_read_calls;
        value = runtime->ops->read_fn(runtime->ops->context,
                                      runtime->kmsg_fd, record,
                                      sizeof(record));
        if (runtime->result->faulted)
            ++runtime->result->kmsg_reads_after_fault;
        if (value > 0) {
            interrupted = 0;
            if (a90_wp2_5b_stream_add_record(&runtime->stream, record,
                                              (size_t)value) != 0) {
                if (runtime->stream.faulted)
                    return adopt_stream_fault(runtime);
                return note_fault(runtime, A90_WP2_5B_FAULT_BOUNDARY,
                                  EIO, 0);
            }
            continue;
        }
        if (value == 0)
            return note_fault(runtime, A90_WP2_5B_FAULT_BOUNDARY, 0, 0);
        if (errno == EAGAIN)
            return 0;
        if (errno == EINTR) {
            ++interrupted;
            if (interrupted < runtime->start.read_eintr_budget)
                continue;
            return note_fault(runtime, A90_WP2_5B_FAULT_BOUNDARY, EINTR, 0);
        }
        if (errno == EPIPE)
            return note_fault(runtime, A90_WP2_5B_FAULT_EPIPE, EPIPE, POLLERR);
        if (errno == EINVAL)
            return note_fault(runtime, A90_WP2_5B_FAULT_EINVAL, EINVAL, 0);
        if (errno == EFAULT)
            return note_fault(runtime, A90_WP2_5B_FAULT_EFAULT, EFAULT, 0);
        return note_fault(runtime, A90_WP2_5B_FAULT_READ, errno, 0);
    }
    return -1;
}

static int read_close(struct owner_runtime *runtime, uint32_t *cause)
{
    unsigned char payload[A90_WP2_5B_OWNER_CLOSE_PAYLOAD_SIZE];
    int saw_eof = 0;
    int value = pipe_read_frame(runtime, A90_WP2_5B_OWNER_CONTROL_CLOSE,
                                payload, sizeof(payload),
                                runtime->start.pipe_eintr_budget, &saw_eof);

    if (value == 1 && saw_eof) {
        *cause = A90_WP2_5B_OWNER_CLOSE_PARENT_EOF;
        return 0;
    }
    if (value != 0 || get_u32_be(payload + 4) != 0) {
        runtime->control_transition_invalid = 1;
        return -1;
    }
    *cause = get_u32_be(payload);
    if (*cause != A90_WP2_5B_OWNER_CLOSE_NORMAL &&
        *cause != A90_WP2_5B_OWNER_CLOSE_FAULT) {
        runtime->control_transition_invalid = 1;
        return -1;
    }
    if ((*cause == A90_WP2_5B_OWNER_CLOSE_NORMAL &&
         runtime->result->faulted) ||
        (*cause == A90_WP2_5B_OWNER_CLOSE_FAULT &&
         !runtime->result->faulted)) {
        runtime->control_transition_invalid = 1;
        return -1;
    }
    return 0;
}

static int control_writer_closed_cleanly(struct owner_runtime *runtime)
{
    struct pollfd descriptor;
    uint32_t interrupted = 0;

    for (;;) {
        int value;

        memset(&descriptor, 0, sizeof(descriptor));
        descriptor.fd = runtime->control_fd;
        descriptor.events = POLLIN | POLLHUP | POLLERR;
        value = runtime->ops->poll_fn(runtime->ops->context, &descriptor, 1,
                                      (int)runtime->start.poll_timeout_ms);
        if (value < 0 && errno == EINTR) {
            ++interrupted;
            if (interrupted < runtime->start.poll_eintr_budget)
                continue;
            return -1;
        }
        if (value < 0 || value > 1 ||
            (descriptor.revents & (POLLIN | POLLERR | POLLNVAL)) != 0 ||
            value != 1 || (descriptor.revents & POLLHUP) == 0)
            return -1;
        return 0;
    }
}

static int wait_for_activity(struct owner_runtime *runtime, uint32_t *close_cause)
{
    uint32_t interrupted = 0;

    while (!runtime->close_received) {
        struct pollfd descriptors[2];
        int value;

        memset(descriptors, 0, sizeof(descriptors));
        descriptors[0].fd = runtime->control_fd;
        descriptors[0].events = POLLIN | POLLHUP | POLLERR;
        descriptors[1].fd = runtime->kmsg_fd;
        descriptors[1].events = POLLIN | POLLERR;
        value = runtime->ops->poll_fn(runtime->ops->context, descriptors, 2,
                                      (int)runtime->start.poll_timeout_ms);
        if (value < 0 && errno == EINTR) {
            ++interrupted;
            if (interrupted < runtime->start.poll_eintr_budget)
                continue;
            return note_fault(runtime, A90_WP2_5B_FAULT_BOUNDARY, EINTR, 0);
        }
        interrupted = 0;
        if (value < 0)
            return note_fault(runtime, A90_WP2_5B_FAULT_POLL, errno, 0);
        if (value == 0)
            continue;
        if ((descriptors[0].revents & (POLLERR | POLLNVAL)) != 0)
            return note_fault(runtime, A90_WP2_5B_FAULT_BOUNDARY, 0,
                              (uint32_t)descriptors[0].revents);
        if ((descriptors[0].revents & (POLLIN | POLLHUP)) != 0) {
            if (read_close(runtime, close_cause) != 0)
                return note_fault(runtime, A90_WP2_5B_FAULT_BOUNDARY,
                                  EPROTO, (uint32_t)descriptors[0].revents);
            runtime->close_received = 1;
            if (control_writer_closed_cleanly(runtime) != 0) {
                runtime->control_transition_invalid = 1;
                return note_fault(runtime, A90_WP2_5B_FAULT_BOUNDARY,
                                  EPROTO, 0);
            }
            return 0;
        }
        if (runtime->result->faulted)
            continue;
        if ((descriptors[1].revents & POLLNVAL) != 0)
            return note_fault(runtime, A90_WP2_5B_FAULT_BOUNDARY, 0,
                              (uint32_t)descriptors[1].revents);
        if ((descriptors[1].revents & POLLERR) != 0)
            return note_fault(runtime, A90_WP2_5B_FAULT_EPIPE, EPIPE,
                              (uint32_t)descriptors[1].revents);
        if ((descriptors[1].revents & POLLHUP) != 0)
            return note_fault(runtime, A90_WP2_5B_FAULT_BOUNDARY, 0,
                              (uint32_t)descriptors[1].revents);
        if ((descriptors[1].revents & POLLIN) != 0 && drain_kmsg(runtime) != 0)
            return -1;
    }
    return 0;
}

static int wait_fault_close_only(struct owner_runtime *runtime,
                                 uint32_t *close_cause)
{
    uint32_t interrupted = 0;
    uint32_t poll_calls = 0;

    while (!runtime->close_received) {
        struct pollfd descriptor;
        int value;

        memset(&descriptor, 0, sizeof(descriptor));
        descriptor.fd = runtime->control_fd;
        descriptor.events = POLLIN | POLLHUP | POLLERR;
        if (poll_calls == runtime->start.fault_close_poll_budget)
            return -1;
        value = runtime->ops->poll_fn(runtime->ops->context, &descriptor, 1,
                                      (int)runtime->start.poll_timeout_ms);
        ++poll_calls;
        if (value < 0 && errno == EINTR) {
            ++interrupted;
            if (interrupted < runtime->start.poll_eintr_budget)
                continue;
            return -1;
        }
        interrupted = 0;
        if (value < 0 || (descriptor.revents & (POLLERR | POLLNVAL)) != 0)
            return -1;
        if (value == 0)
            continue;
        if ((descriptor.revents & (POLLIN | POLLHUP)) != 0) {
            if (read_close(runtime, close_cause) != 0)
                return -1;
            runtime->close_received = 1;
            if (control_writer_closed_cleanly(runtime) != 0) {
                runtime->control_transition_invalid = 1;
                return -1;
            }
            return 0;
        }
    }
    return 0;
}

static int finalize_capture(struct owner_runtime *runtime, uint32_t close_cause)
{
    if (runtime->control_transition_invalid)
        return -1;
    if (close_cause == A90_WP2_5B_OWNER_CLOSE_PARENT_EOF &&
        !runtime->result->faulted) {
        (void)note_fault(runtime, A90_WP2_5B_FAULT_BOUNDARY, EPROTO, 0);
        if (runtime->reader_close_uncertain ||
            runtime->fault_publication_failed)
            return -1;
    } else if ((close_cause == A90_WP2_5B_OWNER_CLOSE_NORMAL &&
                runtime->result->faulted) ||
               (close_cause == A90_WP2_5B_OWNER_CLOSE_FAULT &&
                !runtime->result->faulted)) {
        runtime->control_transition_invalid = 1;
        return -1;
    }
    if (runtime->reader_close_uncertain)
        return -1;
    if (close_reader_once(runtime) != 0)
        return -1;
    if (runtime->stream_started && !runtime->emit.failed &&
        a90_wp2_5b_stream_end(
            &runtime->stream, runtime->start.driver_init_epoch_sha256,
            runtime->start.capture_close_binding_sha256) != 0)
        runtime->emit.failed = 1;
    if (runtime->emit.failed) {
        if (!runtime->result->faulted) {
            runtime->result->faulted = 1;
            runtime->result->fault_reason = A90_WP2_5B_FAULT_BOUNDARY;
            runtime->result->os_errno = EIO;
        }
        runtime->result->durable_trace_bytes = runtime->durable_trace_bytes;
        (void)close_once(runtime->ops, &runtime->trace_fd);
        return -1;
    }
    if (runtime->ops->fsync_fn(runtime->ops->context, runtime->trace_fd) != 0) {
        int final_error = errno != 0 ? errno : EIO;

        if (!runtime->result->faulted) {
            runtime->result->faulted = 1;
            runtime->result->fault_reason = A90_WP2_5B_FAULT_BOUNDARY;
            runtime->result->os_errno = final_error;
        }
        runtime->result->durable_trace_bytes = runtime->durable_trace_bytes;
        (void)close_once(runtime->ops, &runtime->trace_fd);
        return -1;
    }
    runtime->durable_trace_bytes = runtime->emit.bytes;
    runtime->result->durable_trace_bytes = runtime->durable_trace_bytes;
    if (close_once(runtime->ops, &runtime->trace_fd) != 0) {
        int close_error = errno != 0 ? errno : EIO;

        if (!runtime->result->faulted) {
            runtime->result->faulted = 1;
            runtime->result->fault_reason = A90_WP2_5B_FAULT_BOUNDARY;
            runtime->result->os_errno = close_error;
        }
        return -1;
    }
    if (send_status(runtime, A90_WP2_5B_OWNER_STATUS_CLOSED,
                    runtime->result->fault_reason,
                    runtime->result->os_errno,
                    runtime->result->poll_revents,
                    runtime->stream.record_count) != 0) {
        if (!runtime->result->faulted) {
            runtime->result->faulted = 1;
            runtime->result->fault_reason = A90_WP2_5B_FAULT_BOUNDARY;
            runtime->result->os_errno = EIO;
        }
        return -1;
    }
    runtime->result->closed = 1;
    return 0;
}

static int owner_run_internal(const struct a90_wp2_5b_owner_ops *ops,
                              struct a90_wp2_5b_owner_result *result)
{
    struct owner_runtime runtime;
    struct a90_wp2_5b_owner_confinement confinement;
    unsigned char start_payload[A90_WP2_5B_OWNER_START_PAYLOAD_SIZE];
    struct stat trace_status;
    int saw_eof = 0;
    uint32_t close_cause = 0;
    int rc = -1;

    if (!owner_ops_valid(ops) || result == NULL)
        return -1;
    memset(&runtime, 0, sizeof(runtime));
    memset(result, 0, sizeof(*result));
    runtime.ops = ops;
    runtime.result = result;
    runtime.run_dir_fd = A90_WP2_5B_OWNER_RUN_DIR_FD;
    runtime.control_fd = A90_WP2_5B_OWNER_CONTROL_FD;
    runtime.status_fd = A90_WP2_5B_OWNER_STATUS_FD;
    runtime.trace_fd = -1;
    runtime.kmsg_fd = -1;
    runtime.emit.ops = ops;
    runtime.emit.trace_fd = -1;
    if (rearm_bootstrap_fds(&runtime) != 0 ||
        validate_initial_fds(&runtime) != 0)
        goto out;
    if (pipe_read_frame(&runtime, A90_WP2_5B_OWNER_CONTROL_START,
                        start_payload, sizeof(start_payload),
                        OWNER_BOOTSTRAP_RETRY_CEILING, &saw_eof) != 0 ||
        saw_eof || parse_start_payload(start_payload, &runtime.start) != 0)
        goto out;
    if (open_trace_and_kmsg(&runtime) != 0)
        goto out;
    memset(&confinement, 0, sizeof(confinement));
    confinement.control_fd = runtime.control_fd;
    confinement.status_fd = runtime.status_fd;
    confinement.trace_fd = runtime.trace_fd;
    confinement.kmsg_fd = runtime.kmsg_fd;
    confinement.expected_uid = runtime.start.expected_uid;
    confinement.expected_gid = runtime.start.expected_gid;
    if (ops->apply_confinement_fn(ops->context, &confinement) != 0)
        goto out;
    if (runtime.ops->lseek_fn(runtime.ops->context, runtime.kmsg_fd, 0,
                              SEEK_END) != 0 || validate_kmsg_fd(&runtime) != 0)
        goto out;
    runtime.emit.trace_fd = runtime.trace_fd;
    if (a90_wp2_5b_stream_begin(
            &runtime.stream, file_emit, &runtime.emit,
            runtime.start.run_binding_sha256,
            runtime.start.qualification_sha256,
            runtime.start.observer_binary_sha256,
            runtime.start.record_count_cap,
            runtime.start.record_byte_cap) != 0)
        goto out;
    runtime.stream_started = 1;
    if (runtime.ops->fsync_fn(runtime.ops->context, runtime.trace_fd) != 0 ||
        runtime.ops->fstat_fn(runtime.ops->context, runtime.trace_fd,
                              &trace_status) != 0 ||
        (uint64_t)trace_status.st_dev != result->trace_dev ||
        (uint64_t)trace_status.st_ino != result->trace_ino)
        goto out;
    runtime.durable_trace_bytes = runtime.emit.bytes;
    result->durable_trace_bytes = runtime.durable_trace_bytes;
    result->armed = 1;
    if (send_status(&runtime, A90_WP2_5B_OWNER_STATUS_ARMED, 0, 0, 0,
                    (uint64_t)makedev(1, 11)) != 0)
        goto out;
    if (wait_for_activity(&runtime, &close_cause) != 0 &&
        result->faulted && !runtime.close_received &&
        !runtime.reader_close_uncertain &&
        !runtime.fault_publication_failed &&
        !runtime.control_transition_invalid) {
        if (wait_fault_close_only(&runtime, &close_cause) != 0)
            goto out;
    }
    if (!runtime.close_received)
        goto out;
    if (!result->faulted && close_cause == A90_WP2_5B_OWNER_CLOSE_NORMAL)
        (void)drain_kmsg(&runtime);
    rc = finalize_capture(&runtime, close_cause);

out:
    if (runtime.kmsg_fd >= 0)
        (void)close_once(runtime.ops, &runtime.kmsg_fd);
    if (runtime.trace_fd >= 0)
        (void)close_once(runtime.ops, &runtime.trace_fd);
    if (runtime.run_dir_fd >= 0)
        (void)close_once(runtime.ops, &runtime.run_dir_fd);
    if (runtime.status_fd >= 0)
        (void)close_once(runtime.ops, &runtime.status_fd);
    if (runtime.control_fd >= 0)
        (void)close_once(runtime.ops, &runtime.control_fd);
    return rc;
}

#ifdef A90_WP2_5B_HOST_TESTING
int a90_wp2_5b_owner_run_with_ops(const struct a90_wp2_5b_owner_ops *ops,
                                  struct a90_wp2_5b_owner_result *result)
{
    return owner_run_internal(ops, result);
}
#endif

static int digest_array_nonzero(const unsigned char value[32])
{
    return digest_nonzero(value);
}

int a90_wp2_5b_validate_launch_snapshot(
    const struct a90_wp2_5b_launch_snapshot *snapshot)
{
    if (snapshot == NULL || snapshot->sched_other != 1 ||
        snapshot->priority_zero != 1 || snapshot->reset_on_fork != 1 ||
        snapshot->nice_nonnegative != 1 ||
        !digest_array_nonzero(snapshot->profile_sha256) ||
        !digest_array_nonzero(snapshot->affinity_sha256) ||
        !digest_array_nonzero(snapshot->ioprio_sha256) ||
        !digest_array_nonzero(snapshot->uclamp_sha256) ||
        !digest_array_nonzero(snapshot->cgroup_sha256) ||
        !digest_array_nonzero(snapshot->native_reserve_sha256) ||
        snapshot->rlimit_rtprio_zero != 1 ||
        snapshot->rlimit_rttime_positive_bounded != 1 ||
        snapshot->cap_sys_nice_absent != 1 ||
        snapshot->cap_sys_resource_absent != 1 ||
        snapshot->sigchld_blocked != 1 || snapshot->sigchld_default != 1 ||
        snapshot->sigchld_no_cldwait_absent != 1 ||
        snapshot->waiter_reserved != 1 ||
        snapshot->static_elf_fd_validated != 1 ||
        snapshot->clean_mappings != 1 ||
        snapshot->exact_inherited_fd_set != 1 ||
        snapshot->fixed_argv != 1 || snapshot->empty_environment != 1 ||
        snapshot->null_stdio != 1 ||
        !digest_array_nonzero(snapshot->root_sha256) ||
        !digest_array_nonzero(snapshot->cwd_sha256) ||
        !digest_array_nonzero(snapshot->umask_sha256) ||
        !digest_array_nonzero(snapshot->credentials_sha256) ||
        !digest_array_nonzero(snapshot->groups_sha256) ||
        !digest_array_nonzero(snapshot->rlimits_sha256) ||
        !digest_array_nonzero(snapshot->capabilities_sha256) ||
        !digest_array_nonzero(snapshot->signal_mask_sha256) ||
        !digest_array_nonzero(snapshot->signal_dispositions_sha256) ||
        !digest_array_nonzero(snapshot->observer_identity_sha256) ||
        !digest_array_nonzero(snapshot->parent_identity_sha256) ||
        !digest_array_nonzero(snapshot->executable_sha256) ||
        !digest_array_nonzero(snapshot->fd_set_sha256) ||
        !digest_array_nonzero(snapshot->mapping_set_sha256))
        return -1;
    return 0;
}

int a90_wp2_5b_waiter_reserve(struct a90_wp2_5b_waiter_reservation *reservation,
                              pid_t pid, uint64_t starttime)
{
    if (reservation == NULL || pid <= 0 || starttime == 0 ||
        reservation->pid != 0 || reservation->starttime != 0 ||
        reservation->active || reservation->reaped)
        return -1;
    reservation->pid = pid;
    reservation->starttime = starttime;
    reservation->active = 1;
    return 0;
}

int a90_wp2_5b_waiter_generic_reaper_may_reap(
    const struct a90_wp2_5b_waiter_reservation *reservation,
    pid_t pid, uint64_t starttime)
{
    if (reservation == NULL || pid <= 0 || starttime == 0)
        return -1;
    if (reservation->active && reservation->pid == pid &&
        reservation->starttime == starttime)
        return 0;
    return 1;
}

int a90_wp2_5b_waiter_mark_reaped(
    struct a90_wp2_5b_waiter_reservation *reservation,
    pid_t pid, uint64_t starttime)
{
    if (reservation == NULL || !reservation->active || reservation->reaped ||
        reservation->pid != pid || reservation->starttime != starttime)
        return -1;
    reservation->reaped = 1;
    return 0;
}

int a90_wp2_5b_waiter_release(struct a90_wp2_5b_waiter_reservation *reservation)
{
    if (reservation == NULL || !reservation->active || !reservation->reaped)
        return -1;
    memset(reservation, 0, sizeof(*reservation));
    return 0;
}

static int exec_rearm(const struct a90_wp2_5b_exec_ops *ops)
{
    const int descriptors[] = {
        A90_WP2_5B_OWNER_CONTROL_FD,
        A90_WP2_5B_OWNER_STATUS_FD,
        A90_WP2_5B_OWNER_RUN_DIR_FD,
    };
    unsigned int index;
    int rc = 0;

    for (index = 0; index < sizeof(descriptors) / sizeof(descriptors[0]); ++index) {
        int flags = ops->fcntl_fn(ops->context, descriptors[index], F_GETFD, 0);
        if (flags < 0 || ops->fcntl_fn(ops->context, descriptors[index],
                                      F_SETFD, flags | FD_CLOEXEC) != 0 ||
            (ops->fcntl_fn(ops->context, descriptors[index], F_GETFD, 0) &
             FD_CLOEXEC) == 0)
            rc = -1;
    }
    return rc;
}

int a90_wp2_5b_child_exec_transition(const struct a90_wp2_5b_exec_ops *ops)
{
    const int descriptors[] = {
        A90_WP2_5B_OWNER_CONTROL_FD,
        A90_WP2_5B_OWNER_STATUS_FD,
        A90_WP2_5B_OWNER_RUN_DIR_FD,
    };
    char *const argv[] = {(char *)"a90-wp2-5b-observer", NULL};
    char *const envp[] = {NULL};
    unsigned int index;
    int exec_flags;

    if (ops == NULL || ops->fcntl_fn == NULL || ops->execveat_fn == NULL)
        return -1;
    exec_flags = ops->fcntl_fn(ops->context, A90_WP2_5B_OWNER_EXEC_FD,
                               F_GETFD, 0);
    if (exec_flags < 0 || (exec_flags & FD_CLOEXEC) == 0)
        return -1;
    for (index = 0; index < sizeof(descriptors) / sizeof(descriptors[0]); ++index) {
        int flags = ops->fcntl_fn(ops->context, descriptors[index], F_GETFD, 0);
        if (flags < 0 || (flags & FD_CLOEXEC) == 0 ||
            ops->fcntl_fn(ops->context, descriptors[index], F_SETFD,
                          flags & ~FD_CLOEXEC) != 0 ||
            (ops->fcntl_fn(ops->context, descriptors[index], F_GETFD, 0) &
             FD_CLOEXEC) != 0) {
            (void)exec_rearm(ops);
            return -1;
        }
    }
    if (ops->execveat_fn(ops->context, A90_WP2_5B_OWNER_EXEC_FD, "", argv,
                         envp, AT_EMPTY_PATH) == 0) {
        (void)exec_rearm(ops);
        return -1;
    }
    (void)exec_rearm(ops);
    return -1;
}

struct filter_builder {
    struct sock_filter instructions[OWNER_MAX_FILTER_INSNS];
    unsigned int count;
};

static int filter_add(struct filter_builder *builder, struct sock_filter value)
{
    if (builder->count >= OWNER_MAX_FILTER_INSNS)
        return -1;
    builder->instructions[builder->count++] = value;
    return 0;
}

static int filter_stmt(struct filter_builder *builder, uint16_t code,
                       uint32_t value)
{
    struct sock_filter instruction = BPF_STMT(code, value);
    return filter_add(builder, instruction);
}

static int filter_jump(struct filter_builder *builder, uint16_t code,
                       uint32_t value, uint8_t yes, uint8_t no)
{
    struct sock_filter instruction = BPF_JUMP(code, value, yes, no);
    return filter_add(builder, instruction);
}

static int filter_rule_simple(struct filter_builder *builder, int syscall_nr)
{
    unsigned int start = builder->count;

    if (filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K,
                    (uint32_t)syscall_nr, 0, 0) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_ALLOW) != 0)
        return -1;
    builder->instructions[start].jf = 1;
    return 0;
}

static int filter_rule_fd2(struct filter_builder *builder, int syscall_nr,
                           int first_fd, int second_fd)
{
    unsigned int start = builder->count;

    if (filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K,
                    (uint32_t)syscall_nr, 0, 0) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[0])) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K,
                    (uint32_t)first_fd, 2, 0) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K,
                    (uint32_t)second_fd, 1, 0) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[0]) + 4u) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 0u, 0, 1) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_ALLOW) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS) != 0)
        return -1;
    builder->instructions[start].jf = 8;
    return 0;
}

static int filter_rule_fd4(struct filter_builder *builder, int syscall_nr,
                           int a, int b, int c, int d)
{
    unsigned int start = builder->count;

    if (filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K,
                    (uint32_t)syscall_nr, 0, 0) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[0])) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, (uint32_t)a, 4, 0) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, (uint32_t)b, 3, 0) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, (uint32_t)c, 2, 0) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, (uint32_t)d, 1, 0) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[0]) + 4u) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 0u, 0, 1) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_ALLOW) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS) != 0)
        return -1;
    builder->instructions[start].jf = 10;
    return 0;
}

static int filter_rule_fcntl(struct filter_builder *builder, int trace_fd,
                             int kmsg_fd)
{
    unsigned int start = builder->count;

    if (filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K,
                    (uint32_t)__NR_fcntl, 0, 0) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[0])) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K,
                    A90_WP2_5B_OWNER_CONTROL_FD, 4, 0) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K,
                    A90_WP2_5B_OWNER_STATUS_FD, 3, 0) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K,
                    (uint32_t)trace_fd, 2, 0) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K,
                    (uint32_t)kmsg_fd, 1, 0) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[0]) + 4u) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 0u, 0, 6) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[1])) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, F_GETFD, 1, 0) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, F_GETFL, 0, 3) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[1]) + 4u) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 0u, 0, 1) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_ALLOW) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS) != 0)
        return -1;
    builder->instructions[start].jf = 15;
    return 0;
}

static int filter_rule_lseek(struct filter_builder *builder, int kmsg_fd)
{
    unsigned int start = builder->count;

    if (filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K,
                    (uint32_t)__NR_lseek, 0, 0) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[0])) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K,
                    (uint32_t)kmsg_fd, 0, 11) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[0]) + 4u) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 0u, 0, 9) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[1])) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 0u, 0, 7) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[1]) + 4u) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 0u, 0, 5) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[2])) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, SEEK_END, 0, 3) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[2]) + 4u) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 0u, 0, 1) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_ALLOW) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS) != 0)
        return -1;
    builder->instructions[start].jf = 14;
    return 0;
}

#ifdef __NR_poll
static int filter_rule_poll(struct filter_builder *builder)
{
    unsigned int start = builder->count;

    if (filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K,
                    (uint32_t)__NR_poll, 0, 0) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[1])) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 1u, 1, 0) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 2u, 0, 7) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[1]) + 4u) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 0u, 0, 5) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[2])) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JGT | BPF_K,
                    OWNER_RUNTIME_POLL_TIMEOUT_CEILING_MS, 3, 0) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[2]) + 4u) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 0u, 0, 1) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_ALLOW) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS) != 0)
        return -1;
    builder->instructions[start].jf = 11;
    return 0;
}
#endif

#ifdef __NR_ppoll
static int filter_rule_ppoll(struct filter_builder *builder)
{
    unsigned int start = builder->count;

    if (filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K,
                    (uint32_t)__NR_ppoll, 0, 0) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[1])) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 1u, 1, 0) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 2u, 0, 11) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[1]) + 4u) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 0u, 0, 9) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[3])) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 0u, 0, 7) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[3]) + 4u) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 0u, 0, 5) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[4])) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 0u, 0, 3) != 0 ||
        filter_stmt(builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, args[4]) + 4u) != 0 ||
        filter_jump(builder, BPF_JMP | BPF_JEQ | BPF_K, 0u, 0, 1) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_ALLOW) != 0 ||
        filter_stmt(builder, BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS) != 0)
        return -1;
    builder->instructions[start].jf = 15;
    return 0;
}
#endif

int a90_wp2_5b_owner_build_filter(
    const struct a90_wp2_5b_owner_confinement *request,
    struct sock_filter *instructions, size_t capacity,
    unsigned short *instruction_count)
{
    struct filter_builder builder;
#if defined(__aarch64__)
    const uint32_t expected_arch = AUDIT_ARCH_AARCH64;
#elif defined(__x86_64__)
    const uint32_t expected_arch = AUDIT_ARCH_X86_64;
#else
#error "unsupported observer architecture"
#endif

    if (request == NULL || instructions == NULL || instruction_count == NULL ||
        capacity < OWNER_MAX_FILTER_INSNS ||
        request->control_fd != A90_WP2_5B_OWNER_CONTROL_FD ||
        request->status_fd != A90_WP2_5B_OWNER_STATUS_FD ||
        request->trace_fd <= A90_WP2_5B_OWNER_STATUS_FD ||
        request->kmsg_fd <= A90_WP2_5B_OWNER_STATUS_FD ||
        request->trace_fd == request->kmsg_fd)
        return -1;
    memset(&builder, 0, sizeof(builder));
    if (filter_stmt(&builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, arch)) != 0 ||
        filter_jump(&builder, BPF_JMP | BPF_JEQ | BPF_K,
                    expected_arch, 1, 0) != 0 ||
        filter_stmt(&builder, BPF_RET | BPF_K,
                    SECCOMP_RET_KILL_PROCESS) != 0 ||
        filter_stmt(&builder, BPF_LD | BPF_W | BPF_ABS,
                    (uint32_t)offsetof(struct seccomp_data, nr)) != 0 ||
        filter_rule_fd2(&builder, __NR_read,
                        request->control_fd, request->kmsg_fd) != 0 ||
        filter_rule_fd2(&builder, __NR_write,
                        request->status_fd, request->trace_fd) != 0 ||
        filter_rule_fd4(&builder, __NR_close,
                        request->control_fd, request->status_fd,
                        request->trace_fd, request->kmsg_fd) != 0 ||
        filter_rule_fd4(&builder, __NR_fstat,
                        request->control_fd, request->status_fd,
                        request->trace_fd, request->kmsg_fd) != 0 ||
        filter_rule_fd2(&builder, __NR_fsync, request->trace_fd,
                        request->trace_fd) != 0 ||
        filter_rule_fcntl(&builder, request->trace_fd,
                          request->kmsg_fd) != 0 ||
        filter_rule_lseek(&builder, request->kmsg_fd) != 0)
        return -1;
#ifdef __NR_poll
    if (filter_rule_poll(&builder) != 0)
        return -1;
#endif
#ifdef __NR_ppoll
    if (filter_rule_ppoll(&builder) != 0)
        return -1;
#endif
    if (filter_rule_simple(&builder, __NR_rt_sigreturn) != 0 ||
        filter_rule_simple(&builder, __NR_exit) != 0 ||
        filter_rule_simple(&builder, __NR_exit_group) != 0 ||
        filter_stmt(&builder, BPF_RET | BPF_K,
                    SECCOMP_RET_KILL_PROCESS) != 0)
        return -1;
    if (builder.count > capacity || builder.count > UINT16_MAX)
        return -1;
    memcpy(instructions, builder.instructions,
           builder.count * sizeof(builder.instructions[0]));
    *instruction_count = (unsigned short)builder.count;
    return 0;
}

static int install_filter(
    const struct a90_wp2_5b_owner_confinement *request)
{
    struct sock_filter instructions[OWNER_MAX_FILTER_INSNS];
    struct sock_fprog program;
    unsigned short instruction_count;

    if (a90_wp2_5b_owner_build_filter(request, instructions,
                                      OWNER_MAX_FILTER_INSNS,
                                      &instruction_count) != 0)
        return -1;
    program.len = instruction_count;
    program.filter = instructions;
    return prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program, 0, 0);
}

int a90_wp2_5b_owner_install_confinement(
    const struct a90_wp2_5b_owner_confinement *request)
{
    struct rlimit core_limit;
    struct __user_cap_header_struct header;
    struct __user_cap_data_struct data[2];
    struct rlimit verified_core_limit;
    uid_t real_uid, effective_uid, saved_uid;
    gid_t real_gid, effective_gid, saved_gid;
    int capability;

    if (request == NULL ||
        request->control_fd != A90_WP2_5B_OWNER_CONTROL_FD ||
        request->status_fd != A90_WP2_5B_OWNER_STATUS_FD ||
        request->trace_fd <= A90_WP2_5B_OWNER_STATUS_FD ||
        request->kmsg_fd <= A90_WP2_5B_OWNER_STATUS_FD ||
        request->trace_fd == request->kmsg_fd ||
        getgroups(0, NULL) != 0 ||
        getresuid(&real_uid, &effective_uid, &saved_uid) != 0 ||
        getresgid(&real_gid, &effective_gid, &saved_gid) != 0 ||
        real_uid != request->expected_uid ||
        effective_uid != request->expected_uid ||
        saved_uid != request->expected_uid ||
        real_gid != request->expected_gid ||
        effective_gid != request->expected_gid ||
        saved_gid != request->expected_gid)
        return -1;
    core_limit.rlim_cur = 0;
    core_limit.rlim_max = 0;
    if (setrlimit(RLIMIT_CORE, &core_limit) != 0 ||
        getrlimit(RLIMIT_CORE, &verified_core_limit) != 0 ||
        verified_core_limit.rlim_cur != 0 || verified_core_limit.rlim_max != 0 ||
        prctl(PR_SET_DUMPABLE, 0, 0, 0, 0) != 0 ||
        prctl(PR_GET_DUMPABLE, 0, 0, 0, 0) != 0)
        return -1;
    for (capability = 0; capability < 64; ++capability) {
        int present = prctl(PR_CAPBSET_READ, capability, 0, 0, 0);
        if (present < 0 && errno == EINVAL)
            break;
        if (present < 0 ||
            (present == 1 && prctl(PR_CAPBSET_DROP, capability, 0, 0, 0) != 0) ||
            prctl(PR_CAPBSET_READ, capability, 0, 0, 0) != 0)
            return -1;
    }
    if (capability == 0 || capability == 64)
        return -1;
    memset(&header, 0, sizeof(header));
    memset(data, 0, sizeof(data));
    header.version = _LINUX_CAPABILITY_VERSION_3;
    header.pid = 0;
    if (syscall(SYS_capset, &header, data) != 0 ||
        syscall(SYS_capget, &header, data) != 0 ||
        data[0].effective != 0 || data[0].permitted != 0 ||
        data[0].inheritable != 0 || data[1].effective != 0 ||
        data[1].permitted != 0 || data[1].inheritable != 0)
        return -1;
#ifdef PR_CAP_AMBIENT
    if (prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL, 0, 0, 0) != 0)
        return -1;
    {
        int ambient_capability;

        for (ambient_capability = 0; ambient_capability < capability;
             ++ambient_capability) {
            if (prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_IS_SET,
                      ambient_capability, 0, 0) != 0)
                return -1;
        }
    }
#endif
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0 ||
        prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0) != 1 ||
        install_filter(request) != 0)
        return -1;
    return 0;
}

static int real_openat(void *context, int dirfd, const char *path, int flags,
                       mode_t mode)
{
    (void)context;
    return (int)syscall(SYS_openat, dirfd, path, flags, mode);
}

static int real_close(void *context, int fd)
{
    (void)context;
    return (int)syscall(SYS_close, fd);
}

static int real_fstat(void *context, int fd, struct stat *status)
{
    (void)context;
    return (int)syscall(SYS_fstat, fd, status);
}

static int real_fcntl(void *context, int fd, int command, long argument)
{
    (void)context;
    return (int)syscall(SYS_fcntl, fd, command, argument);
}

static off_t real_lseek(void *context, int fd, off_t offset, int whence)
{
    (void)context;
    return (off_t)syscall(SYS_lseek, fd, offset, whence);
}

static ssize_t real_read(void *context, int fd, void *buffer, size_t length)
{
    (void)context;
    return (ssize_t)syscall(SYS_read, fd, buffer, length);
}

static ssize_t real_write(void *context, int fd, const void *buffer, size_t length)
{
    (void)context;
    return (ssize_t)syscall(SYS_write, fd, buffer, length);
}

static int real_poll(void *context, struct pollfd *fds, nfds_t count,
                     int timeout_ms)
{
    (void)context;
#ifdef SYS_poll
    return (int)syscall(SYS_poll, fds, count, timeout_ms);
#else
    {
        struct timespec timeout;
        struct timespec *timeout_pointer = NULL;

        if (timeout_ms >= 0) {
            timeout.tv_sec = timeout_ms / 1000;
            timeout.tv_nsec = (long)(timeout_ms % 1000) * 1000000L;
            timeout_pointer = &timeout;
        }
        return (int)syscall(SYS_ppoll, fds, count, timeout_pointer, NULL, 0);
    }
#endif
}

static int real_fsync(void *context, int fd)
{
    (void)context;
    return (int)syscall(SYS_fsync, fd);
}

static int real_confinement(
    void *context, const struct a90_wp2_5b_owner_confinement *request)
{
    (void)context;
    return a90_wp2_5b_owner_install_confinement(request);
}

int a90_wp2_5b_owner_run(void)
{
    const struct a90_wp2_5b_owner_ops operations = {
        .context = NULL,
        .openat_fn = real_openat,
        .close_fn = real_close,
        .fstat_fn = real_fstat,
        .fcntl_fn = real_fcntl,
        .lseek_fn = real_lseek,
        .read_fn = real_read,
        .write_fn = real_write,
        .poll_fn = real_poll,
        .fsync_fn = real_fsync,
        .apply_confinement_fn = real_confinement,
    };
    struct a90_wp2_5b_owner_result result;

    return owner_run_internal(&operations, &result);
}

#ifdef A90_WP2_5B_OWNER_MAIN
int main(int argc, char **argv)
{
    if (argc != 1 || argv == NULL || argv[0] == NULL ||
        strcmp(argv[0], "a90-wp2-5b-observer") != 0)
        return 126;
    return a90_wp2_5b_owner_run() == 0 ? 0 : 125;
}
#endif
