/*
 * The sole forced SSH command and service-account shell.
 *
 * Dropbear invokes the account shell as shell -c <forced-command>.  The
 * direct form is also bound so the same immutable binary is the only probe
 * entry point.  No shell parsing, command expansion, writes, or forwarding
 * control is present here.
 */
#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>

enum {
    A90_SERVICE_UID = 3301,
    A90_SERVICE_GID = 3301,
    A90_MAX_OUTPUT = 256,
};

static int exact_identity(void) {
    return getuid() == A90_SERVICE_UID &&
           geteuid() == A90_SERVICE_UID &&
           getgid() == A90_SERVICE_GID &&
           getegid() == A90_SERVICE_GID;
}

static int exact_request(int argc, char **argv) {
    static const char forced[] =
        "/usr/local/libexec/a90-probe --request=readiness";
    if (argc == 2 && argv[1] != NULL &&
        __builtin_strcmp(argv[1], "--request=readiness") == 0) {
        return 1;
    }
    return argc == 3 && argv[1] != NULL && argv[2] != NULL &&
           __builtin_strcmp(argv[1], "-c") == 0 &&
           __builtin_strcmp(argv[2], forced) == 0;
}

int main(int argc, char **argv) {
    static const char ready_record[] = "A90_WORKLOAD_V1 ready=1\n";
    static const char response[] =
        "A90_PROBE_V1 status=ready workload=ready\n";
    char buffer[sizeof(ready_record)];
    ssize_t count;
    int fd;
    const char *original_command;

    if (!exact_identity() || !exact_request(argc, argv)) {
        return 131;
    }
    original_command = getenv("SSH_ORIGINAL_COMMAND");
    if (original_command != NULL && original_command[0] != '\0') {
        return 132;
    }
    fd = open("/run/a90/workload.ready", O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) {
        return 133;
    }
    count = read(fd, buffer, sizeof(buffer));
    if (close(fd) != 0 || count != (ssize_t)(sizeof(ready_record) - 1) ||
        __builtin_memcmp(buffer, ready_record, sizeof(ready_record) - 1) != 0) {
        return 134;
    }
    if (sizeof(response) - 1 > A90_MAX_OUTPUT ||
        write(STDOUT_FILENO, response, sizeof(response) - 1) !=
            (ssize_t)(sizeof(response) - 1)) {
        return 135;
    }
    return 0;
}
