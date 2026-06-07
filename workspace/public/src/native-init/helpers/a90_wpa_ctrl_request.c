#include <errno.h>
#include <poll.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <unistd.h>

#ifndef SOCK_CLOEXEC
#define SOCK_CLOEXEC 02000000
#endif

static long monotonic_ms(void) {
    struct timeval tv;

    gettimeofday(&tv, NULL);
    return (long)tv.tv_sec * 1000L + (long)tv.tv_usec / 1000L;
}

static const char *reply_category(const char *reply) {
    if (reply == NULL || reply[0] == '\0') {
        return "empty";
    }
    if (strncmp(reply, "OK", 2) == 0) {
        return "ok";
    }
    if (strncmp(reply, "FAIL", 4) == 0) {
        return "fail";
    }
    if (strncmp(reply, "PONG", 4) == 0) {
        return "pong";
    }
    if (strncmp(reply, "UNKNOWN", 7) == 0) {
        return "unknown";
    }
    return "other";
}

static int bind_local_abstract(int fd) {
    struct sockaddr_un local;
    char name[64];
    size_t name_len;

    memset(&local, 0, sizeof(local));
    local.sun_family = AF_UNIX;
    if (snprintf(name,
                 sizeof(name),
                 "a90-wpa-probe-%ld-%ld",
                 (long)getpid(),
                 monotonic_ms()) >= (int)sizeof(name)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    name_len = strlen(name);
    local.sun_path[0] = '\0';
    memcpy(local.sun_path + 1, name, name_len);
    return bind(fd,
                (const struct sockaddr *)&local,
                (socklen_t)(offsetof(struct sockaddr_un, sun_path) + 1 + name_len));
}

static int connect_remote(int fd, const char *remote, int abstract) {
    struct sockaddr_un addr;
    size_t remote_len = strlen(remote);

    if (remote_len == 0 || remote_len + (abstract ? 1U : 0U) >= sizeof(addr.sun_path)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    if (abstract) {
        addr.sun_path[0] = '\0';
        memcpy(addr.sun_path + 1, remote, remote_len);
        return connect(fd,
                       (const struct sockaddr *)&addr,
                       (socklen_t)(offsetof(struct sockaddr_un, sun_path) + 1 + remote_len));
    }
    memcpy(addr.sun_path, remote, remote_len + 1);
    return connect(fd,
                   (const struct sockaddr *)&addr,
                   (socklen_t)(offsetof(struct sockaddr_un, sun_path) + remote_len + 1));
}

static int ctrl_request(const char *remote,
                        int abstract,
                        const char *command,
                        char *reply,
                        size_t reply_size) {
    struct pollfd pfd;
    ssize_t received;
    size_t command_len = strlen(command);
    int fd;

    if (reply_size == 0) {
        errno = EINVAL;
        return -1;
    }
    reply[0] = '\0';
    fd = socket(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    if (fd < 0) {
        return -1;
    }
    if (bind_local_abstract(fd) < 0 || connect_remote(fd, remote, abstract) < 0) {
        int saved_errno = errno;

        close(fd);
        errno = saved_errno;
        return -1;
    }
    if (send(fd, command, command_len, 0) != (ssize_t)command_len) {
        int saved_errno = errno == 0 ? EIO : errno;

        close(fd);
        errno = saved_errno;
        return -1;
    }
    memset(&pfd, 0, sizeof(pfd));
    pfd.fd = fd;
    pfd.events = POLLIN;
    if (poll(&pfd, 1, 2500) <= 0) {
        int saved_errno = errno == 0 ? ETIMEDOUT : errno;

        close(fd);
        errno = saved_errno;
        return -1;
    }
    received = recv(fd, reply, reply_size - 1, 0);
    if (received < 0) {
        int saved_errno = errno;

        close(fd);
        errno = saved_errno;
        return -1;
    }
    reply[received] = '\0';
    while (received > 0 && (reply[received - 1] == '\n' || reply[received - 1] == '\r')) {
        reply[received - 1] = '\0';
        --received;
    }
    close(fd);
    return 0;
}

static int append_arg(char *out, size_t out_size, const char *arg, int first) {
    size_t used = strlen(out);
    int written;

    written = snprintf(out + used,
                       out_size > used ? out_size - used : 0,
                       "%s%s",
                       first ? "" : " ",
                       arg);
    if (written < 0 || used + (size_t)written >= out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    return 0;
}

int main(int argc, char **argv) {
    char command[512] = "";
    char reply[4096];
    const char *remote;
    int abstract = 0;
    int rc;
    int saved_errno = 0;
    int arg_index;
    int first_command_arg = 1;

    if (argc < 3) {
        fprintf(stderr, "usage: %s [--abstract] <socket-or-name> <command> [args...]\n", argv[0]);
        return 64;
    }
    arg_index = 1;
    if (strcmp(argv[arg_index], "--abstract") == 0) {
        abstract = 1;
        ++arg_index;
    }
    if (argc - arg_index < 2) {
        fprintf(stderr, "usage: %s [--abstract] <socket-or-name> <command> [args...]\n", argv[0]);
        return 64;
    }
    remote = argv[arg_index++];
    if (remote[0] == '@') {
        abstract = 1;
        ++remote;
    }
    for (; arg_index < argc; ++arg_index) {
        if (append_arg(command, sizeof(command), argv[arg_index], first_command_arg) < 0) {
            saved_errno = errno;
            printf("wpa_ctrl.rc=-1\n");
            printf("wpa_ctrl.errno=%d\n", saved_errno);
            printf("wpa_ctrl.reply_category=error\n");
            return 65;
        }
        first_command_arg = 0;
    }

    rc = ctrl_request(remote, abstract, command, reply, sizeof(reply));
    if (rc < 0) {
        saved_errno = errno;
    }
    printf("wpa_ctrl.rc=%d\n", rc);
    printf("wpa_ctrl.errno=%d\n", saved_errno);
    printf("wpa_ctrl.reply_category=%s\n", rc == 0 ? reply_category(reply) : "error");
    printf("wpa_ctrl.reply_len=%ld\n", rc == 0 ? (long)strlen(reply) : 0L);
    return rc == 0 ? 0 : 1;
}
