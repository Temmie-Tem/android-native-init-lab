#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/android/binder.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/select.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define DEFAULT_BINDER_PATH "/dev/binder"
#define DEFAULT_MAP_LENGTH (1024UL * 1024UL)
#define MAX_MAP_LENGTH (4UL * 1024UL * 1024UL)
#define ROLE_A 1
#define ROLE_B 2
#define A_READY_OK 0x41393054
#define CHILD_TIMEOUT_MS 3000L
#define PARENT_TIMEOUT_MS 6000L
#define TEST_PAYLOAD "A90-BBT"
#define BBT_UID_TARGET 1000
#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))

struct child_result {
    int role;
    int exit_rc;
    int open_rc;
    int open_errno;
    int mmap_mode;
    int mmap_rc;
    int mmap_errno;
    int ruid_before;
    int euid_before;
    int suid_before;
    int setresuid1000_rc;
    int setresuid1000_errno;
    int ruid_after;
    int euid_after;
    int suid_after;
    int set_context_mgr_rc;
    int set_context_mgr_errno;
    int enter_looper_rc;
    int enter_looper_errno;
    int transaction_write_rc;
    int transaction_write_errno;
    uint64_t write_consumed;
    uint64_t write_expected;
    uint64_t read_consumed;
    int saw_transaction_complete;
    int saw_br_transaction;
    int saw_br_noop;
    int saw_spawn_looper;
    int unexpected_cmd;
    int target_data_size;
    int target_offsets_size;
    int target_flags_oneway;
    int target_sender_pid_nonzero;
    int timeout;
};

struct ready_msg {
    int magic;
    struct child_result result;
};

static long monotonic_ms(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
        return 0;
    }
    return (long)ts.tv_sec * 1000L + (long)(ts.tv_nsec / 1000000L);
}

static void sleep_ms(long ms) {
    struct timespec ts;

    if (ms <= 0) {
        return;
    }
    ts.tv_sec = ms / 1000L;
    ts.tv_nsec = (ms % 1000L) * 1000000L;
    while (nanosleep(&ts, &ts) != 0 && errno == EINTR) {
    }
}

static int write_full(int fd, const void *data, size_t size) {
    const char *cursor = (const char *)data;

    while (size > 0) {
        ssize_t written = write(fd, cursor, size);
        if (written < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (written == 0) {
            return -1;
        }
        cursor += written;
        size -= (size_t)written;
    }
    return 0;
}

static int read_full(int fd, void *data, size_t size) {
    char *cursor = (char *)data;

    while (size > 0) {
        ssize_t got = read(fd, cursor, size);
        if (got < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (got == 0) {
            return -1;
        }
        cursor += got;
        size -= (size_t)got;
    }
    return 0;
}

static int parse_ulong(const char *text, unsigned long *out) {
    char *end = NULL;
    unsigned long value;

    errno = 0;
    value = strtoul(text, &end, 0);
    if (errno || end == text || *end != '\0') {
        return -1;
    }
    *out = value;
    return 0;
}

static int open_binder(const char *path, struct child_result *result) {
    int fd = open(path, O_RDWR | O_CLOEXEC | O_NONBLOCK);

    result->open_rc = fd < 0 ? -1 : 0;
    result->open_errno = fd < 0 ? errno : 0;
    return fd;
}

static void *map_binder(int fd, unsigned long map_length, struct child_result *result) {
    void *mapping;

    result->mmap_mode = 1;
    mapping = mmap(NULL, map_length, PROT_READ, MAP_PRIVATE | MAP_NORESERVE, fd, 0);
    result->mmap_rc = mapping == MAP_FAILED ? -1 : 0;
    result->mmap_errno = mapping == MAP_FAILED ? errno : 0;
    return mapping;
}

static int binder_write_read(int fd,
                             void *write_buffer,
                             size_t write_size,
                             void *read_buffer,
                             size_t read_size,
                             struct binder_write_read *out_bwr) {
    struct binder_write_read bwr;
    int rc;

    memset(&bwr, 0, sizeof(bwr));
    bwr.write_size = write_size;
    bwr.write_buffer = (binder_uintptr_t)(uintptr_t)write_buffer;
    bwr.read_size = read_size;
    bwr.read_buffer = (binder_uintptr_t)(uintptr_t)read_buffer;

    rc = ioctl(fd, BINDER_WRITE_READ, &bwr);
    if (out_bwr) {
        *out_bwr = bwr;
    }
    return rc;
}

static int send_enter_looper(int fd, struct child_result *result) {
    uint32_t command = BC_ENTER_LOOPER;
    struct binder_write_read bwr;
    int rc;

    rc = binder_write_read(fd, &command, sizeof(command), NULL, 0, &bwr);
    result->enter_looper_rc = rc == 0 ? 0 : -1;
    result->enter_looper_errno = rc == 0 ? 0 : errno;
    return rc;
}

static void capture_resuid(int *ruid, int *euid, int *suid) {
    uid_t current_ruid = (uid_t)-1;
    uid_t current_euid = (uid_t)-1;
    uid_t current_suid = (uid_t)-1;

    if (getresuid(&current_ruid, &current_euid, &current_suid) != 0) {
        *ruid = -1;
        *euid = -1;
        *suid = -1;
        return;
    }
    *ruid = (int)current_ruid;
    *euid = (int)current_euid;
    *suid = (int)current_suid;
}

static int drop_child_a_to_uid1000(struct child_result *result) {
    capture_resuid(&result->ruid_before, &result->euid_before, &result->suid_before);

    errno = 0;
    if (syscall(SYS_setresuid,
                (uid_t)BBT_UID_TARGET,
                (uid_t)BBT_UID_TARGET,
                (uid_t)BBT_UID_TARGET) != 0) {
        result->setresuid1000_rc = -1;
        result->setresuid1000_errno = errno;
        capture_resuid(&result->ruid_after, &result->euid_after, &result->suid_after);
        return -1;
    }
    result->setresuid1000_rc = 0;
    result->setresuid1000_errno = 0;
    capture_resuid(&result->ruid_after, &result->euid_after, &result->suid_after);
    if (result->ruid_after != BBT_UID_TARGET ||
        result->euid_after != BBT_UID_TARGET ||
        result->suid_after != BBT_UID_TARGET) {
        return -2;
    }
    return 0;
}

static int parse_a_read_buffer(const uint32_t *buffer,
                               size_t consumed,
                               struct child_result *result) {
    size_t offset = 0;

    while (offset + sizeof(uint32_t) <= consumed) {
        uint32_t command = buffer[offset / sizeof(uint32_t)];
        offset += sizeof(uint32_t);

        if (command == BR_NOOP) {
            result->saw_br_noop = 1;
            continue;
        }
        if (command == BR_SPAWN_LOOPER) {
            result->saw_spawn_looper = 1;
            continue;
        }
        if (command == BR_TRANSACTION) {
            struct binder_transaction_data transaction;

            if (offset + sizeof(transaction) > consumed) {
                result->unexpected_cmd = (int)command;
                return -1;
            }
            memcpy(&transaction, ((const char *)buffer) + offset, sizeof(transaction));
            result->saw_br_transaction = 1;
            result->target_data_size = (int)transaction.data_size;
            result->target_offsets_size = (int)transaction.offsets_size;
            result->target_flags_oneway = (transaction.flags & TF_ONE_WAY) ? 1 : 0;
            result->target_sender_pid_nonzero = transaction.sender_pid != 0 ? 1 : 0;
            return 1;
        }

        result->unexpected_cmd = (int)command;
        return -1;
    }
    return 0;
}

static int participant_a(const char *path,
                         unsigned long map_length,
                         int ready_fd,
                         int result_fd) {
    struct child_result result;
    struct ready_msg ready;
    int fd = -1;
    void *mapping = MAP_FAILED;
    long deadline;

    memset(&result, 0, sizeof(result));
    result.role = ROLE_A;
    result.mmap_rc = -2;
    result.setresuid1000_rc = -2;
    result.set_context_mgr_rc = -2;
    result.enter_looper_rc = -2;

    fd = open_binder(path, &result);
    if (fd < 0) {
        result.exit_rc = 10;
        goto out;
    }

    mapping = map_binder(fd, map_length, &result);
    if (mapping == MAP_FAILED) {
        result.exit_rc = 11;
        goto out;
    }

    if (drop_child_a_to_uid1000(&result) != 0) {
        result.exit_rc = 19;
        goto out;
    }

    errno = 0;
    if (ioctl(fd, BINDER_SET_CONTEXT_MGR, 0) != 0) {
        result.set_context_mgr_rc = -1;
        result.set_context_mgr_errno = errno;
        result.exit_rc = result.set_context_mgr_errno == EBUSY ? 12 : 13;
        goto out;
    }
    result.set_context_mgr_rc = 0;
    result.set_context_mgr_errno = 0;

    if (send_enter_looper(fd, &result) != 0) {
        result.exit_rc = 14;
        goto out;
    }

    memset(&ready, 0, sizeof(ready));
    ready.magic = A_READY_OK;
    ready.result = result;
    if (write_full(ready_fd, &ready, sizeof(ready)) != 0) {
        result.exit_rc = 15;
        goto out;
    }
    close(ready_fd);
    ready_fd = -1;

    deadline = monotonic_ms() + CHILD_TIMEOUT_MS;
    while (monotonic_ms() < deadline) {
        uint32_t read_buffer[128];
        struct binder_write_read bwr;
        int rc;

        memset(read_buffer, 0, sizeof(read_buffer));
        errno = 0;
        rc = binder_write_read(fd, NULL, 0, read_buffer, sizeof(read_buffer), &bwr);
        if (rc == 0 || (rc < 0 && errno == EAGAIN)) {
            result.read_consumed += bwr.read_consumed;
            if (bwr.read_consumed > 0) {
                int parsed = parse_a_read_buffer(read_buffer,
                                                 (size_t)bwr.read_consumed,
                                                 &result);
                if (parsed == 1) {
                    result.exit_rc = 0;
                    goto out;
                }
                if (parsed < 0) {
                    result.exit_rc = 16;
                    goto out;
                }
            }
            sleep_ms(20);
            continue;
        }
        result.unexpected_cmd = -errno;
        result.exit_rc = 17;
        goto out;
    }

    result.timeout = 1;
    result.exit_rc = 18;

out:
    if (ready_fd >= 0) {
        memset(&ready, 0, sizeof(ready));
        ready.result = result;
        write_full(ready_fd, &ready, sizeof(ready));
        close(ready_fd);
    }
    if (mapping != MAP_FAILED) {
        munmap(mapping, map_length);
    }
    if (fd >= 0) {
        close(fd);
    }
    write_full(result_fd, &result, sizeof(result));
    return result.exit_rc;
}

static int participant_b(const char *path, int result_fd) {
    struct child_result result;
    int fd = -1;
    char payload[] = TEST_PAYLOAD;
    binder_size_t offsets_dummy = 0;
    struct {
        uint32_t command;
        struct binder_transaction_data transaction;
    } __attribute__((packed)) write_buffer;
    struct binder_write_read bwr;
    int rc;

    memset(&result, 0, sizeof(result));
    result.role = ROLE_B;
    result.mmap_mode = 0;
    result.mmap_rc = 0;
    result.write_expected = sizeof(write_buffer);

    fd = open_binder(path, &result);
    if (fd < 0) {
        result.exit_rc = 20;
        goto out;
    }

    memset(&write_buffer, 0, sizeof(write_buffer));
    write_buffer.command = BC_TRANSACTION;
    write_buffer.transaction.target.handle = 0;
    write_buffer.transaction.code = 0x413930u;
    write_buffer.transaction.flags = TF_ONE_WAY;
    write_buffer.transaction.data_size = sizeof(payload);
    write_buffer.transaction.offsets_size = 0;
    write_buffer.transaction.data.ptr.buffer = (binder_uintptr_t)(uintptr_t)payload;
    write_buffer.transaction.data.ptr.offsets =
        (binder_uintptr_t)(uintptr_t)&offsets_dummy;

    errno = 0;
    rc = binder_write_read(fd, &write_buffer, sizeof(write_buffer), NULL, 0, &bwr);
    result.transaction_write_rc = rc == 0 ? 0 : -1;
    result.transaction_write_errno = rc == 0 ? 0 : errno;
    result.write_consumed = bwr.write_consumed;
    result.read_consumed = bwr.read_consumed;

    if (rc != 0) {
        result.exit_rc = 21;
        goto out;
    }
    if (bwr.write_consumed != sizeof(write_buffer)) {
        result.exit_rc = 22;
        goto out;
    }

    result.exit_rc = 0;

out:
    if (fd >= 0) {
        close(fd);
    }
    write_full(result_fd, &result, sizeof(result));
    return result.exit_rc;
}

static const char *decision_for_results(const struct child_result *a,
                                        int have_a,
                                        const struct child_result *b,
                                        int have_b,
                                        int parent_timeout) {
    if (!have_a) {
        return "bbt-missing-child-result";
    }
    if (parent_timeout || a->timeout) {
        return "bbt-timeout";
    }
    if (a->setresuid1000_rc != 0) {
        return "bbt-uid-drop-failed";
    }
    if (a->ruid_after != BBT_UID_TARGET ||
        a->euid_after != BBT_UID_TARGET ||
        a->suid_after != BBT_UID_TARGET) {
        return "bbt-uid-drop-incomplete";
    }
    if (a->set_context_mgr_rc != 0) {
        if (a->set_context_mgr_errno == EBUSY) {
            return "bbt-context-mgr-ebusy";
        }
        if (a->set_context_mgr_errno == EPERM) {
            return "bbt-context-mgr-eperm-after-uid-drop";
        }
        return "bbt-context-mgr-fail";
    }
    if (a->enter_looper_rc != 0) {
        return "bbt-looper-fail";
    }
    if (!have_b) {
        return "bbt-missing-child-result";
    }
    if (b->transaction_write_rc != 0 ||
        b->write_consumed != b->write_expected) {
        return "bbt-client-write-fail";
    }
    if (a->unexpected_cmd || b->unexpected_cmd) {
        return "bbt-protocol-unexpected";
    }
    if (!a->saw_br_transaction) {
        return "bbt-target-not-received";
    }
    if (a->target_offsets_size != 0 ||
        a->target_data_size != (int)sizeof(TEST_PAYLOAD) ||
        !a->target_flags_oneway ||
        !a->target_sender_pid_nonzero) {
        return "bbt-protocol-unexpected";
    }
    return "bbt-uid-target-ok";
}

static int collect_result_from_pipe(int fd,
                                    struct child_result *a,
                                    int *have_a,
                                    struct child_result *b,
                                    int *have_b) {
    struct child_result result;
    int count = 0;

    while (read_full(fd, &result, sizeof(result)) == 0) {
        if (result.role == ROLE_A) {
            *a = result;
            *have_a = 1;
        } else if (result.role == ROLE_B) {
            *b = result;
            *have_b = 1;
        }
        count++;
        if (count >= 2) {
            break;
        }
    }
    return count;
}

static void print_result(const struct child_result *a,
                         int have_a,
                         const struct child_result *b,
                         int have_b,
                         const char *path,
                         unsigned long map_length,
                         const char *decision,
                         int parent_timeout) {
    printf("bbt.helper=a90_binder_target_bbt_uid\n");
    printf("bbt.helper_version=1\n");
    printf("bbt.mode=two-process-oneway-zero-object-uid1000\n");
    printf("bbt.path=%s\n", path);
    printf("bbt.a.map_length=%lu\n", map_length);
    printf("bbt.no_malformed_objects=1\n");
    printf("bbt.no_free_buffer=1\n");
    printf("bbt.no_reply=1\n");
    printf("bbt.no_sg=1\n");
    printf("bbt.parent_timeout=%d\n", parent_timeout);
    printf("bbt.have_a=%d\n", have_a);
    printf("bbt.have_b=%d\n", have_b);

    if (have_a) {
        printf("bbt.a.exit_rc=%d\n", a->exit_rc);
        printf("bbt.a.open_rc=%d\n", a->open_rc);
        printf("bbt.a.open_errno=%d\n", a->open_errno);
        printf("bbt.a.mmap_rc=%d\n", a->mmap_rc);
        printf("bbt.a.mmap_errno=%d\n", a->mmap_errno);
        printf("bbt.a.ruid_before=%d\n", a->ruid_before);
        printf("bbt.a.euid_before=%d\n", a->euid_before);
        printf("bbt.a.suid_before=%d\n", a->suid_before);
        printf("bbt.a.setresuid1000_rc=%d\n", a->setresuid1000_rc);
        printf("bbt.a.setresuid1000_errno=%d\n", a->setresuid1000_errno);
        printf("bbt.a.ruid_after=%d\n", a->ruid_after);
        printf("bbt.a.euid_after=%d\n", a->euid_after);
        printf("bbt.a.suid_after=%d\n", a->suid_after);
        printf("bbt.a.uid_gate_expected=%d\n", BBT_UID_TARGET);
        printf("bbt.a.uid_drop_mode=setresuid1000_all\n");
        printf("bbt.a.set_context_mgr_rc=%d\n", a->set_context_mgr_rc);
        printf("bbt.a.set_context_mgr_errno=%d\n", a->set_context_mgr_errno);
        printf("bbt.a.enter_looper_rc=%d\n", a->enter_looper_rc);
        printf("bbt.a.enter_looper_errno=%d\n", a->enter_looper_errno);
        printf("bbt.a.saw_br_noop=%d\n", a->saw_br_noop);
        printf("bbt.a.saw_spawn_looper=%d\n", a->saw_spawn_looper);
        printf("bbt.a.saw_br_transaction=%d\n", a->saw_br_transaction);
        printf("bbt.a.tr_data_size=%d\n", a->target_data_size);
        printf("bbt.a.tr_offsets_size=%d\n", a->target_offsets_size);
        printf("bbt.a.tr_flags_oneway=%d\n", a->target_flags_oneway);
        printf("bbt.a.tr_sender_pid_nonzero=%d\n", a->target_sender_pid_nonzero);
        printf("bbt.a.unexpected_cmd=%d\n", a->unexpected_cmd);
        printf("bbt.a.timeout=%d\n", a->timeout);
    }

    if (have_b) {
        printf("bbt.b.exit_rc=%d\n", b->exit_rc);
        printf("bbt.b.open_rc=%d\n", b->open_rc);
        printf("bbt.b.open_errno=%d\n", b->open_errno);
        printf("bbt.b.mmap_mode=omitted\n");
        printf("bbt.b.transaction_write_rc=%d\n", b->transaction_write_rc);
        printf("bbt.b.transaction_write_errno=%d\n", b->transaction_write_errno);
        printf("bbt.b.write_consumed=%llu\n",
               (unsigned long long)b->write_consumed);
        printf("bbt.b.write_expected=%llu\n",
               (unsigned long long)b->write_expected);
        printf("bbt.b.saw_transaction_complete=%d\n", b->saw_transaction_complete);
        printf("bbt.b.unexpected_cmd=%d\n", b->unexpected_cmd);
    }

    printf("bbt.decision=%s\n", decision);
    printf("bbt.exit_rc=%d\n", strcmp(decision, "bbt-uid-target-ok") == 0 ? 0 : 1);
}

static void usage(const char *program) {
    fprintf(stderr, "usage: %s [--path /dev/binder] [--length BYTES]\n", program);
}

int main(int argc, char **argv) {
    const char *path = DEFAULT_BINDER_PATH;
    unsigned long map_length = DEFAULT_MAP_LENGTH;
    int ready_pipe[2] = {-1, -1};
    int result_pipe[2] = {-1, -1};
    pid_t child_a = -1;
    pid_t child_b = -1;
    struct ready_msg ready;
    struct child_result result_a;
    struct child_result result_b;
    int have_a = 0;
    int have_b = 0;
    int parent_timeout = 0;
    long deadline;
    const char *decision;

    for (int index = 1; index < argc; index++) {
        if (strcmp(argv[index], "--path") == 0) {
            if (++index >= argc) {
                usage(argv[0]);
                return 2;
            }
            path = argv[index];
        } else if (strcmp(argv[index], "--length") == 0) {
            if (++index >= argc || parse_ulong(argv[index], &map_length) != 0) {
                usage(argv[0]);
                return 2;
            }
        } else {
            usage(argv[0]);
            return 2;
        }
    }

    if (map_length == 0 || map_length > MAX_MAP_LENGTH || (map_length % 4096UL) != 0) {
        printf("bbt.helper=a90_binder_target_bbt_uid\n");
        printf("bbt.decision=bbt-uid-helper-invalid-length\n");
        printf("bbt.exit_rc=2\n");
        return 2;
    }

    memset(&ready, 0, sizeof(ready));
    memset(&result_a, 0, sizeof(result_a));
    memset(&result_b, 0, sizeof(result_b));

    if (pipe(ready_pipe) != 0 || pipe(result_pipe) != 0) {
        printf("bbt.helper=a90_binder_target_bbt_uid\n");
        printf("bbt.decision=bbt-parent-pipe-fail\n");
        printf("bbt.exit_rc=2\n");
        return 2;
    }

    child_a = fork();
    if (child_a < 0) {
        printf("bbt.helper=a90_binder_target_bbt_uid\n");
        printf("bbt.decision=bbt-parent-fork-a-fail\n");
        printf("bbt.exit_rc=2\n");
        return 2;
    }
    if (child_a == 0) {
        close(ready_pipe[0]);
        close(result_pipe[0]);
        return participant_a(path, map_length, ready_pipe[1], result_pipe[1]);
    }
    close(ready_pipe[1]);

    if (read_full(ready_pipe[0], &ready, sizeof(ready)) != 0 ||
        ready.magic != A_READY_OK ||
        ready.result.set_context_mgr_rc != 0 ||
        ready.result.enter_looper_rc != 0) {
        result_a = ready.result;
        have_a = 1;
        parent_timeout = 0;
        kill(child_a, SIGTERM);
        waitpid(child_a, NULL, 0);
        close(result_pipe[1]);
        collect_result_from_pipe(result_pipe[0], &result_a, &have_a, &result_b, &have_b);
        decision = decision_for_results(&result_a, have_a, &result_b, have_b, parent_timeout);
        print_result(&result_a, have_a, &result_b, have_b, path, map_length,
                     decision, parent_timeout);
        return strcmp(decision, "bbt-uid-target-ok") == 0 ? 0 : 1;
    }
    result_a = ready.result;
    have_a = 1;

    child_b = fork();
    if (child_b < 0) {
        kill(child_a, SIGTERM);
        waitpid(child_a, NULL, 0);
        printf("bbt.helper=a90_binder_target_bbt_uid\n");
        printf("bbt.decision=bbt-parent-fork-b-fail\n");
        printf("bbt.exit_rc=2\n");
        return 2;
    }
    if (child_b == 0) {
        close(ready_pipe[0]);
        close(result_pipe[0]);
        return participant_b(path, result_pipe[1]);
    }

    close(result_pipe[1]);
    deadline = monotonic_ms() + PARENT_TIMEOUT_MS;
    while (monotonic_ms() < deadline) {
        int status;
        pid_t done_a = waitpid(child_a, &status, WNOHANG);
        pid_t done_b = waitpid(child_b, &status, WNOHANG);

        if ((done_a == child_a || done_a == -1) &&
            (done_b == child_b || done_b == -1)) {
            break;
        }
        sleep_ms(20);
    }

    if (monotonic_ms() >= deadline) {
        parent_timeout = 1;
        kill(child_a, SIGTERM);
        kill(child_b, SIGTERM);
    }
    waitpid(child_a, NULL, 0);
    waitpid(child_b, NULL, 0);

    collect_result_from_pipe(result_pipe[0], &result_a, &have_a, &result_b, &have_b);
    decision = decision_for_results(&result_a, have_a, &result_b, have_b, parent_timeout);
    print_result(&result_a, have_a, &result_b, have_b, path, map_length,
                 decision, parent_timeout);
    return strcmp(decision, "bbt-uid-target-ok") == 0 ? 0 : 1;
}
