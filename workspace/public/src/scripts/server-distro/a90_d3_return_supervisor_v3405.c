#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/reboot.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define A90_MARKER "A90D3RET_V3405"
#define A90_SYSRQ_PATH "/proc/sysrq-trigger"
#define A90_PMSG_PATH "/dev/pmsg0"
#define A90_KMSG_PATH "/dev/kmsg"
#define A90_PROC_DEVICES_PATH "/proc/devices"
#define A90_MAX_DELAY_SEC 600U
#define A90_MAX_GRACE_SEC 60U
#define A90_POLL_NS 100000000L
#define A90_EVIDENCE_GRACE_MS 1000U
#ifdef A90_D3_SUPERVISOR_TESTING
#define A90_ARM_READY_TIMEOUT_MS 200
#define A90_REBOOT_GRACE_MS 300U
#else
#define A90_ARM_READY_TIMEOUT_MS 5000
#define A90_REBOOT_GRACE_MS 5000U
#endif

struct supervisor_io {
    int sysrq_fd;
    int pmsg_fd;
    int kmsg_fd;
};

static const char *test_path(const char *env_name, const char *production_path)
{
#ifdef A90_D3_SUPERVISOR_TESTING
    const char *value = getenv(env_name);

    if (value != NULL && value[0] != '\0')
        return value;
#else
    (void)env_name;
#endif
    return production_path;
}

static int write_all(int fd, const void *data, size_t size)
{
    const unsigned char *cursor = data;

    while (size != 0U) {
        ssize_t rc = write(fd, cursor, size);

        if (rc < 0) {
            if (errno == EINTR)
                continue;
            return -errno;
        }
        if (rc == 0)
            return -EIO;
        cursor += (size_t)rc;
        size -= (size_t)rc;
    }
    return 0;
}

static int open_write_prearmed(const char *path)
{
    int flags = O_WRONLY | O_CLOEXEC | O_APPEND | O_NONBLOCK;

    return open(path, flags);
}

static int parse_pmsg_major(const char *path)
{
    FILE *stream;
    char line[160];
    int major = -1;

    stream = fopen(path, "re");
    if (stream == NULL)
        return -errno;
    while (fgets(line, sizeof(line), stream) != NULL) {
        int candidate;
        char name[64];

        if (sscanf(line, " %d %63s", &candidate, name) != 2)
            continue;
        if (strcmp(name, "pmsg") == 0) {
            major = candidate;
            break;
        }
    }
    if (ferror(stream) != 0 && major < 0)
        major = -EIO;
    fclose(stream);
    if (major <= 0 || major > 4095)
        return major < 0 ? major : -ERANGE;
    return major;
}

static int ensure_pmsg_node(const char *path)
{
#ifdef A90_D3_SUPERVISOR_TESTING
    struct stat test_st;

    if (stat(path, &test_st) == 0 && S_ISREG(test_st.st_mode))
        return 0;
#endif
    {
        struct stat st;
        int pmsg_major;

        pmsg_major = parse_pmsg_major(
            test_path("A90_TEST_PROC_DEVICES", A90_PROC_DEVICES_PATH));
        if (pmsg_major < 0)
            return pmsg_major;
        if (lstat(path, &st) == 0) {
            if (!S_ISCHR(st.st_mode))
                return -ENOTTY;
            if ((int)major(st.st_rdev) != pmsg_major ||
                minor(st.st_rdev) != 0U)
                return -EXDEV;
            return 0;
        }
        if (errno != ENOENT)
            return -errno;
        if (mknod(path, S_IFCHR | 0220,
                  makedev((unsigned int)pmsg_major, 0U)) != 0)
            return -errno;
    }
    return 0;
}

static void sanitize_token(char *text)
{
    size_t read_index;
    size_t write_index = 0U;

    for (read_index = 0U; text[read_index] != '\0'; ++read_index) {
        unsigned char ch = (unsigned char)text[read_index];

        if ((ch >= 'a' && ch <= 'z') ||
            (ch >= 'A' && ch <= 'Z') ||
            (ch >= '0' && ch <= '9') ||
            ch == '_' || ch == '-' || ch == '.' || ch == '?') {
            text[write_index++] = (char)ch;
        } else if (ch == '\n' || ch == '\r') {
            break;
        } else {
            text[write_index++] = '_';
        }
    }
    text[write_index] = '\0';
    if (write_index == 0U)
        strcpy(text, "unknown");
}

static int read_bounded(const char *path, char *buffer, size_t size)
{
    int fd;
    ssize_t rc;

    if (size < 2U)
        return -EINVAL;
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0)
        return -errno;
    do {
        rc = read(fd, buffer, size - 1U);
    } while (rc < 0 && errno == EINTR);
    close(fd);
    if (rc < 0)
        return -errno;
    buffer[(size_t)rc] = '\0';
    return 0;
}

static char state_from_stat(const char *stat_text)
{
    const char *close_paren = strrchr(stat_text, ')');

    if (close_paren == NULL || close_paren[1] != ' ' ||
        close_paren[2] == '\0')
        return '?';
    return close_paren[2];
}

static int emit_marker(const struct supervisor_io *io, const char *format, ...)
{
    char body[512];
    char line[640];
    va_list args;
    int body_size;
    int line_size;
    int rc = 0;

    va_start(args, format);
    body_size = vsnprintf(body, sizeof(body), format, args);
    va_end(args);
    if (body_size < 0 || (size_t)body_size >= sizeof(body))
        return -EOVERFLOW;
    line_size = snprintf(line, sizeof(line), "%s %s\n", A90_MARKER, body);
    if (line_size < 0 || (size_t)line_size >= sizeof(line))
        return -EOVERFLOW;
    if (io->pmsg_fd >= 0)
        rc = write_all(io->pmsg_fd, line, (size_t)line_size);
    if (io->kmsg_fd >= 0)
        (void)write_all(io->kmsg_fd, line, (size_t)line_size);
    return rc;
}

static int preopen_interfaces(struct supervisor_io *io)
{
    const char *pmsg_path = test_path("A90_TEST_PMSG", A90_PMSG_PATH);
    int rc;

    memset(io, 0, sizeof(*io));
    io->sysrq_fd = -1;
    io->pmsg_fd = -1;
    io->kmsg_fd = -1;

    io->sysrq_fd = open_write_prearmed(
        test_path("A90_TEST_SYSRQ", A90_SYSRQ_PATH));
    if (io->sysrq_fd < 0)
        return -errno;
    rc = ensure_pmsg_node(pmsg_path);
    if (rc < 0)
        return rc;
    io->pmsg_fd = open_write_prearmed(pmsg_path);
    if (io->pmsg_fd < 0)
        return -errno;
    io->kmsg_fd = open_write_prearmed(
        test_path("A90_TEST_KMSG", A90_KMSG_PATH));
    return 0;
}

static void close_interfaces(struct supervisor_io *io)
{
    if (io->kmsg_fd >= 0)
        close(io->kmsg_fd);
    if (io->pmsg_fd >= 0)
        close(io->pmsg_fd);
    if (io->sysrq_fd >= 0)
        close(io->sysrq_fd);
}

static int monotonic_now(struct timespec *now)
{
    if (clock_gettime(CLOCK_MONOTONIC, now) != 0)
        return -errno;
    return 0;
}

static int sleep_until(const struct timespec *deadline)
{
    int rc;

    do {
        rc = clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, deadline, NULL);
    } while (rc == EINTR);
    return rc == 0 ? 0 : -rc;
}

static int deadline_after(unsigned int seconds, struct timespec *result)
{
    int rc;

    rc = monotonic_now(result);
    if (rc < 0)
        return rc;
    result->tv_sec += (time_t)seconds;
    return 0;
}

static int deadline_after_ms(unsigned int milliseconds, struct timespec *result)
{
    int rc = monotonic_now(result);
    long nanoseconds;

    if (rc < 0)
        return rc;
    result->tv_sec += (time_t)(milliseconds / 1000U);
    nanoseconds = result->tv_nsec +
                  (long)(milliseconds % 1000U) * 1000000L;
    result->tv_sec += nanoseconds / 1000000000L;
    result->tv_nsec = nanoseconds % 1000000000L;
    return 0;
}

static int remaining_ms(const struct timespec *deadline)
{
    struct timespec now;
    int64_t milliseconds;

    if (monotonic_now(&now) < 0)
        return 0;
    milliseconds = (int64_t)(deadline->tv_sec - now.tv_sec) * 1000LL;
    milliseconds +=
        (int64_t)(deadline->tv_nsec - now.tv_nsec) / 1000000LL;
    if (milliseconds <= 0)
        return 0;
    if (milliseconds > INT32_MAX)
        return INT32_MAX;
    return (int)milliseconds;
}

static bool deadline_reached(const struct timespec *deadline)
{
    struct timespec now;

    if (monotonic_now(&now) < 0)
        return true;
    if (now.tv_sec != deadline->tv_sec)
        return now.tv_sec > deadline->tv_sec;
    return now.tv_nsec >= deadline->tv_nsec;
}

static void poll_pause_until(const struct timespec *deadline)
{
    struct timespec wake;

    if (monotonic_now(&wake) < 0)
        return;
    wake.tv_nsec += A90_POLL_NS;
    if (wake.tv_nsec >= 1000000000L) {
        wake.tv_sec += 1;
        wake.tv_nsec -= 1000000000L;
    }
    if (wake.tv_sec > deadline->tv_sec ||
        (wake.tv_sec == deadline->tv_sec &&
         wake.tv_nsec > deadline->tv_nsec))
        wake = *deadline;
    (void)sleep_until(&wake);
}

static int wait_child_until(pid_t child, const struct timespec *deadline,
                            int *status_out)
{
    for (;;) {
        pid_t waited = waitpid(child, status_out, WNOHANG);

        if (waited == child)
            return 1;
        if (waited < 0 && errno != EINTR)
            return -errno;
        if (deadline_reached(deadline))
            return 0;
        poll_pause_until(deadline);
    }
}

static void sync_child(const struct supervisor_io *io)
{
    (void)emit_marker(io, "phase=sync-enter");
#ifdef A90_D3_SUPERVISOR_TESTING
    {
        const char *mode = getenv("A90_TEST_SYNC_MODE");

        if (mode != NULL && strcmp(mode, "block") == 0) {
            for (;;)
                pause();
        }
    }
#else
    sync();
#endif
    (void)emit_marker(io, "phase=sync-return");
    _exit(0);
}

static int read_sync_evidence(pid_t sync_pid, char *state_out,
                              char *wchan, size_t wchan_size)
{
    char stat_path[96];
    char wchan_path[96];
    char stat_text[1024];
    int stat_rc;
    int wchan_rc;

#ifdef A90_D3_SUPERVISOR_TESTING
    {
        const char *test_stat = getenv("A90_TEST_PROC_STAT");
        const char *test_wchan = getenv("A90_TEST_PROC_WCHAN");

        if (test_stat != NULL && test_stat[0] != '\0')
            snprintf(stat_path, sizeof(stat_path), "%s", test_stat);
        else
            snprintf(stat_path, sizeof(stat_path), "/proc/%ld/stat",
                     (long)sync_pid);
        if (test_wchan != NULL && test_wchan[0] != '\0')
            snprintf(wchan_path, sizeof(wchan_path), "%s", test_wchan);
        else
            snprintf(wchan_path, sizeof(wchan_path), "/proc/%ld/wchan",
                     (long)sync_pid);
    }
#else
    snprintf(stat_path, sizeof(stat_path), "/proc/%ld/stat", (long)sync_pid);
    snprintf(wchan_path, sizeof(wchan_path), "/proc/%ld/wchan", (long)sync_pid);
#endif

    stat_rc = read_bounded(stat_path, stat_text, sizeof(stat_text));
    wchan_rc = read_bounded(wchan_path, wchan, wchan_size);
    *state_out = stat_rc == 0 ? state_from_stat(stat_text) : '?';
    if (wchan_rc == 0)
        sanitize_token(wchan);
    else
        strcpy(wchan, "unreadable");
    if (stat_rc < 0)
        return stat_rc;
    return wchan_rc;
}

static int trigger_b_only(const struct supervisor_io *io, const char *reason)
{
    int rc;

    (void)reason;
    rc = write_all(io->sysrq_fd, "b\n", 2U);
#ifdef A90_D3_SUPERVISOR_TESTING
    return rc;
#else
    for (;;)
        pause();
    return rc;
#endif
}

static void evidence_child(const struct supervisor_io *io, pid_t sync_pid)
{
    char state = '?';
    char wchan[160] = "unreadable";
    int evidence_rc;

#ifdef A90_D3_SUPERVISOR_TESTING
    {
        const char *mode = getenv("A90_TEST_EVIDENCE_MODE");

        if (mode != NULL && strcmp(mode, "block") == 0) {
            for (;;)
                pause();
        }
    }
#endif
    evidence_rc = read_sync_evidence(sync_pid, &state, wchan, sizeof(wchan));
    (void)emit_marker(io,
                      "phase=sync-timeout stat_read=%d state=%c "
                      "wchan_read=%d wchan=%s",
                      state != '?', state,
                      strcmp(wchan, "unreadable") != 0, wchan);
    _exit(evidence_rc == 0 ? 0 : 1);
}

static int collect_evidence_then_b(const struct supervisor_io *io,
                                   pid_t sync_pid)
{
    struct timespec evidence_deadline;
    pid_t evidence_pid;
    int evidence_status = 0;

    evidence_pid = fork();
    if (evidence_pid >= 0) {
        if (evidence_pid == 0)
            evidence_child(io, sync_pid);
        if (deadline_after_ms(A90_EVIDENCE_GRACE_MS,
                              &evidence_deadline) == 0)
            (void)wait_child_until(evidence_pid, &evidence_deadline,
                                   &evidence_status);
    }
    (void)trigger_b_only(io, "sync-timeout");
#ifdef A90_D3_SUPERVISOR_TESTING
    if (evidence_pid > 0) {
        (void)kill(evidence_pid, SIGKILL);
        (void)waitpid(evidence_pid, NULL, 0);
    }
    (void)kill(sync_pid, SIGKILL);
    (void)waitpid(sync_pid, NULL, 0);
    return 0;
#else
    return -EIO;
#endif
}

static void reboot_child(const struct supervisor_io *io)
{
    (void)emit_marker(io, "phase=reboot-enter");
#ifdef A90_D3_SUPERVISOR_TESTING
    const char *action_path = getenv("A90_TEST_ACTION");
    const char *mode = getenv("A90_TEST_REBOOT_MODE");
    int fd;

    if (mode != NULL && strcmp(mode, "block") == 0) {
        for (;;)
            pause();
    }
    if (action_path == NULL || action_path[0] == '\0')
        _exit(1);
    fd = open(action_path, O_WRONLY | O_CLOEXEC | O_APPEND);
    if (fd < 0)
        _exit(1);
    {
        int write_rc = write_all(fd, "reboot\n", 7U);

        if (write_rc < 0) {
            close(fd);
            _exit(1);
        }
    }
    close(fd);
    _exit(0);
#else
    (void)reboot(LINUX_REBOOT_CMD_RESTART);
    _exit(1);
#endif
}

static int request_reboot_bounded(const struct supervisor_io *io)
{
    struct timespec reboot_deadline;
    pid_t reboot_pid;
    int reboot_status = 0;

    reboot_pid = fork();
    if (reboot_pid < 0)
        return trigger_b_only(io, "reboot-fork-failure");
    if (reboot_pid == 0)
        reboot_child(io);
    if (deadline_after_ms(A90_REBOOT_GRACE_MS, &reboot_deadline) < 0)
        return trigger_b_only(io, "reboot-clock-failure");
    (void)wait_child_until(reboot_pid, &reboot_deadline, &reboot_status);
    (void)trigger_b_only(io, "reboot-return-or-timeout");
#ifdef A90_D3_SUPERVISOR_TESTING
    (void)kill(reboot_pid, SIGKILL);
    (void)waitpid(reboot_pid, NULL, 0);
    return 0;
#else
    return -EIO;
#endif
}

static int run_supervisor(unsigned int delay_sec, unsigned int grace_sec,
                          int ready_fd)
{
    struct supervisor_io io;
    struct timespec sync_deadline;
    pid_t sync_pid;
    int rc;
    int status = 0;

    rc = preopen_interfaces(&io);
    if (rc < 0)
        goto fail_before_ready;
#ifndef A90_D3_SUPERVISOR_TESTING
    if (mlockall(MCL_CURRENT | MCL_FUTURE) != 0) {
        rc = -errno;
        goto fail_before_ready;
    }
#endif
    rc = emit_marker(&io,
                     "phase=armed delay_sec=%u grace_sec=%u sysrq_preopened=1 "
                     "pmsg_preopened=1 action=b-only",
                     delay_sec, grace_sec);
    if (rc < 0)
        goto fail_before_ready;
#ifdef A90_D3_SUPERVISOR_TESTING
    {
        const char *ready_mode = getenv("A90_TEST_READY_MODE");

        if (ready_mode != NULL && strcmp(ready_mode, "block") == 0) {
            for (;;)
                pause();
        }
    }
#endif
    if (ready_fd >= 0) {
        const unsigned char ready = 1U;

        rc = write_all(ready_fd, &ready, sizeof(ready));
        if (rc < 0)
            goto fail_before_ready;
        close(ready_fd);
        ready_fd = -1;
    }

    rc = deadline_after(delay_sec, &sync_deadline);
    if (rc < 0)
        return trigger_b_only(&io, "delay-clock-failure");
    rc = sleep_until(&sync_deadline);
    if (rc < 0)
        return trigger_b_only(&io, "delay-clock-failure");

    sync_pid = fork();
    if (sync_pid < 0)
        return trigger_b_only(&io, "sync-fork-failure");
    if (sync_pid == 0)
        sync_child(&io);

    rc = deadline_after(grace_sec, &sync_deadline);
    if (rc < 0)
        return trigger_b_only(&io, "grace-clock-failure");
    for (;;) {
        int wait_rc = wait_child_until(sync_pid, &sync_deadline, &status);

        if (wait_rc == 1)
            break;
        if (wait_rc < 0)
            return trigger_b_only(&io, "sync-wait-failure");
        return collect_evidence_then_b(&io, sync_pid);
    }

    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0)
        return trigger_b_only(&io, "sync-child-failed");
    return request_reboot_bounded(&io);

fail_before_ready:
    if (ready_fd >= 0) {
        const unsigned char failed = 0U;

        (void)write_all(ready_fd, &failed, sizeof(failed));
        close(ready_fd);
    }
    close_interfaces(&io);
    return rc;
}

static int parse_seconds(const char *text, unsigned int maximum,
                         unsigned int *value_out)
{
    char *end = NULL;
    unsigned long value;

    errno = 0;
    value = strtoul(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value > maximum)
        return -EINVAL;
    *value_out = (unsigned int)value;
    return 0;
}

static int arm_parent_b_only(int sysrq_fd, int error)
{
    (void)write_all(sysrq_fd, "b\n", 2U);
#ifdef A90_D3_SUPERVISOR_TESTING
    close(sysrq_fd);
    return error;
#else
    (void)error;
    for (;;)
        pause();
    return -EIO;
#endif
}

static int arm_child_failure_b_only(int sysrq_fd, int error, pid_t child)
{
    int rc = arm_parent_b_only(sysrq_fd, error);

#ifdef A90_D3_SUPERVISOR_TESTING
    (void)kill(child, SIGKILL);
    (void)waitpid(child, NULL, 0);
#else
    (void)child;
#endif
    return rc;
}

static int arm_background(unsigned int delay_sec, unsigned int grace_sec)
{
    struct pollfd ready_poll;
    struct timespec ready_deadline;
    int ready_pipe[2];
    int parent_sysrq_fd;
    pid_t child;
    unsigned char status = 0U;
    ssize_t got;
    int poll_rc;

    parent_sysrq_fd = open_write_prearmed(
        test_path("A90_TEST_SYSRQ", A90_SYSRQ_PATH));
    if (parent_sysrq_fd < 0)
        return -errno;
#ifndef A90_D3_SUPERVISOR_TESTING
    if (mlockall(MCL_CURRENT | MCL_FUTURE) != 0) {
        int saved = errno;

        return arm_parent_b_only(parent_sysrq_fd, -saved);
    }
#endif
    if (pipe2(ready_pipe, O_CLOEXEC | O_NONBLOCK) != 0) {
        int saved = errno;

        return arm_parent_b_only(parent_sysrq_fd, -saved);
    }
    child = fork();
    if (child < 0) {
        int saved = errno;

        close(ready_pipe[0]);
        close(ready_pipe[1]);
        return arm_parent_b_only(parent_sysrq_fd, -saved);
    }
    if (child == 0) {
        int rc;

        close(ready_pipe[0]);
        close(parent_sysrq_fd);
        close(STDIN_FILENO);
        close(STDOUT_FILENO);
        close(STDERR_FILENO);
        (void)setsid();
        rc = run_supervisor(delay_sec, grace_sec, ready_pipe[1]);
        _exit(rc == 0 ? 0 : 1);
    }

    close(ready_pipe[1]);
    ready_poll.fd = ready_pipe[0];
    ready_poll.events = POLLIN | POLLHUP;
    ready_poll.revents = 0;
    if (deadline_after_ms(A90_ARM_READY_TIMEOUT_MS, &ready_deadline) < 0) {
        close(ready_pipe[0]);
        return arm_child_failure_b_only(parent_sysrq_fd, -EIO, child);
    }
    for (;;) {
        int timeout_ms = remaining_ms(&ready_deadline);

        if (timeout_ms == 0) {
            close(ready_pipe[0]);
            return arm_child_failure_b_only(
                parent_sysrq_fd, -ETIMEDOUT, child);
        }
        ready_poll.revents = 0;
        poll_rc = poll(&ready_poll, 1, timeout_ms);
        if (poll_rc < 0) {
            if (errno == EINTR)
                continue;
            close(ready_pipe[0]);
            return arm_child_failure_b_only(
                parent_sysrq_fd, -errno, child);
        }
        if (poll_rc == 0)
            continue;
        got = read(ready_pipe[0], &status, sizeof(status));
        if (got < 0 && (errno == EINTR || errno == EAGAIN))
            continue;
        break;
    }
    close(ready_pipe[0]);
    if (got != (ssize_t)sizeof(status) || status != 1U)
        return arm_child_failure_b_only(parent_sysrq_fd, -EIO, child);
    close(parent_sysrq_fd);
    printf("%ld\n", (long)child);
    return 0;
}

int main(int argc, char **argv)
{
    unsigned int delay_sec;
    unsigned int grace_sec;
    int rc;

    if (argc != 4 ||
        (strcmp(argv[1], "--arm") != 0
#ifdef A90_D3_SUPERVISOR_TESTING
         && strcmp(argv[1], "--test-foreground") != 0
#endif
        )) {
        fprintf(stderr, "usage: %s --arm <delay-sec> <grace-sec>\n", argv[0]);
        return 2;
    }
    rc = parse_seconds(argv[2], A90_MAX_DELAY_SEC, &delay_sec);
    if (rc == 0)
        rc = parse_seconds(argv[3], A90_MAX_GRACE_SEC, &grace_sec);
    if (rc < 0 || grace_sec == 0U
#ifndef A90_D3_SUPERVISOR_TESTING
        || delay_sec == 0U
#endif
    ) {
        fprintf(stderr, "invalid delay/grace bounds\n");
        return 2;
    }
#ifdef A90_D3_SUPERVISOR_TESTING
    if (strcmp(argv[1], "--test-foreground") == 0)
        rc = run_supervisor(delay_sec, grace_sec, -1);
    else
#endif
        rc = arm_background(delay_sec, grace_sec);
    if (rc < 0) {
        fprintf(stderr, "supervisor arm failed: %s\n", strerror(-rc));
        return 1;
    }
    return 0;
}
