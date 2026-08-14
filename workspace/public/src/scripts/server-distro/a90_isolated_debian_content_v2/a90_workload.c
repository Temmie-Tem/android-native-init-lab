/*
 * The selected appliance workload: a bounded, consoleless readiness process.
 * It publishes one fixed readiness record into the native-created /run tmpfs
 * and then remains alive until the exact parent-owned stop path ends it.
 */
#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/types.h>
#include <unistd.h>

enum {
    A90_SERVICE_UID = 3301,
    A90_SERVICE_GID = 3301,
};

static volatile sig_atomic_t stop_requested;

static void request_stop(int signal_number) {
    (void)signal_number;
    stop_requested = 1;
}

static int exact_identity(void) {
    return getuid() == A90_SERVICE_UID &&
           geteuid() == A90_SERVICE_UID &&
           getgid() == A90_SERVICE_GID &&
           getegid() == A90_SERVICE_GID;
}

int main(int argc, char **argv) {
    static const char ready_record[] = "A90_WORKLOAD_V1 ready=1\n";
    struct sigaction action = {
        .sa_handler = request_stop,
        .sa_flags = 0,
    };
    int fd;

    if (argc != 2 || argv[1] == NULL ||
        __builtin_strcmp(argv[1], "--serve") != 0 || !exact_identity()) {
        return 121;
    }
    if (sigemptyset(&action.sa_mask) != 0 ||
        sigaction(SIGTERM, &action, NULL) != 0 ||
        sigaction(SIGINT, &action, NULL) != 0 ||
        sigaction(SIGHUP, &action, NULL) != 0) {
        return 122;
    }
    fd = open("/run/a90/workload.ready",
              O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC,
              0644);
    if (fd < 0) {
        return errno == EEXIST ? 123 : 124;
    }
    if (write(fd, ready_record, sizeof(ready_record) - 1) !=
            (ssize_t)(sizeof(ready_record) - 1) ||
        fsync(fd) != 0 || close(fd) != 0) {
        (void)close(fd);
        return 125;
    }
    while (!stop_requested) {
        pause();
    }
    if (unlink("/run/a90/workload.ready") != 0 && errno != ENOENT) {
        return 126;
    }
    return 0;
}
