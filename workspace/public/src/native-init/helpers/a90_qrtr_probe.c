#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/qrtr.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef AF_QIPCRTR
#define AF_QIPCRTR 42
#endif

#define A90_QRTR_PROBE_VERSION "a90_qrtr_probe v1"

static int open_qrtr_socket(void) {
    int fd = socket(AF_QIPCRTR, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    if (fd >= 0) {
        return fd;
    }
    if (errno == EINVAL) {
        fd = socket(AF_QIPCRTR, SOCK_DGRAM, 0);
        if (fd >= 0) {
            int flags = fcntl(fd, F_GETFD);
            if (flags >= 0) {
                (void)fcntl(fd, F_SETFD, flags | FD_CLOEXEC);
            }
        }
    }
    return fd;
}

static void print_sockaddr(const char *prefix, const struct sockaddr_qrtr *addr) {
    printf("%s.family=%u\n", prefix, (unsigned int)addr->sq_family);
    printf("%s.node=%u\n", prefix, addr->sq_node);
    printf("%s.port=%u\n", prefix, addr->sq_port);
}

static int get_qrtr_name(int fd, const char *prefix, struct sockaddr_qrtr *out) {
    socklen_t len = sizeof(*out);
    memset(out, 0, sizeof(*out));
    if (getsockname(fd, (struct sockaddr *)out, &len) < 0) {
        printf("%s.rc=-1\n", prefix);
        printf("%s.errno=%d\n", prefix, errno);
        printf("%s.error=%s\n", prefix, strerror(errno));
        return -1;
    }
    printf("%s.rc=0\n", prefix);
    printf("%s.len=%u\n", prefix, (unsigned int)len);
    print_sockaddr(prefix, out);
    return 0;
}

static void print_sockopts(int fd) {
    int value = 0;
    socklen_t len = sizeof(value);
    if (getsockopt(fd, SOL_SOCKET, SO_DOMAIN, &value, &len) == 0) {
        printf("qrtr_probe.sockopt.domain=%d\n", value);
    } else {
        printf("qrtr_probe.sockopt.domain_errno=%d\n", errno);
    }
    value = 0;
    len = sizeof(value);
    if (getsockopt(fd, SOL_SOCKET, SO_TYPE, &value, &len) == 0) {
        printf("qrtr_probe.sockopt.type=%d\n", value);
    } else {
        printf("qrtr_probe.sockopt.type_errno=%d\n", errno);
    }
}

static bool seen_node(const unsigned int *nodes, size_t count, unsigned int value) {
    for (size_t i = 0; i < count; ++i) {
        if (nodes[i] == value) {
            return true;
        }
    }
    return false;
}

static int probe_bind_candidate(unsigned int node, int index) {
    int fd = open_qrtr_socket();
    struct sockaddr_qrtr pre;
    struct sockaddr_qrtr post;
    struct sockaddr_qrtr bind_addr;
    int saved_errno = 0;

    printf("qrtr_probe.bind%d.node=%u\n", index, node);
    if (fd < 0) {
        saved_errno = errno;
        printf("qrtr_probe.bind%d.open_rc=-1\n", index);
        printf("qrtr_probe.bind%d.open_errno=%d\n", index, saved_errno);
        printf("qrtr_probe.bind%d.open_error=%s\n", index, strerror(saved_errno));
        return -1;
    }
    printf("qrtr_probe.bind%d.open_rc=0\n", index);
    (void)get_qrtr_name(fd, "qrtr_probe.bind_pre", &pre);

    memset(&bind_addr, 0, sizeof(bind_addr));
    bind_addr.sq_family = AF_QIPCRTR;
    bind_addr.sq_node = node;
    bind_addr.sq_port = 0;
    if (bind(fd, (const struct sockaddr *)&bind_addr, sizeof(bind_addr)) < 0) {
        saved_errno = errno;
        printf("qrtr_probe.bind%d.rc=-1\n", index);
        printf("qrtr_probe.bind%d.errno=%d\n", index, saved_errno);
        printf("qrtr_probe.bind%d.error=%s\n", index, strerror(saved_errno));
        close(fd);
        return -1;
    }

    printf("qrtr_probe.bind%d.rc=0\n", index);
    (void)get_qrtr_name(fd, "qrtr_probe.bind_post", &post);
    close(fd);
    return 0;
}

int main(int argc, char **argv) {
    int fd;
    int status = 1;
    struct sockaddr_qrtr name;
    unsigned int candidates[4] = {0};
    size_t candidate_count = 0;

    (void)argc;
    (void)argv;
    printf("qrtr_probe.version=%s\n", A90_QRTR_PROBE_VERSION);
    printf("qrtr_probe.af=%d\n", AF_QIPCRTR);
    printf("qrtr_probe.socktype=SOCK_DGRAM\n");
    printf("qrtr_probe.send_attempted=0\n");
    printf("qrtr_probe.connect_attempted=0\n");

    fd = open_qrtr_socket();
    if (fd < 0) {
        int saved_errno = errno;
        printf("qrtr_probe.socket.rc=-1\n");
        printf("qrtr_probe.socket.errno=%d\n", saved_errno);
        printf("qrtr_probe.socket.error=%s\n", strerror(saved_errno));
        printf("qrtr_probe.status=socket-failed\n");
        return 1;
    }

    printf("qrtr_probe.socket.rc=0\n");
    print_sockopts(fd);
    if (get_qrtr_name(fd, "qrtr_probe.initial", &name) == 0) {
        if (!seen_node(candidates, candidate_count, name.sq_node)) {
            candidates[candidate_count++] = name.sq_node;
        }
    }
    close(fd);

    if (!seen_node(candidates, candidate_count, 1)) {
        candidates[candidate_count++] = 1;
    }
    if (!seen_node(candidates, candidate_count, 0)) {
        candidates[candidate_count++] = 0;
    }
    if (!seen_node(candidates, candidate_count, QRTR_NODE_BCAST)) {
        candidates[candidate_count++] = QRTR_NODE_BCAST;
    }

    for (size_t i = 0; i < candidate_count; ++i) {
        if (probe_bind_candidate(candidates[i], (int)i) == 0) {
            status = 0;
            printf("qrtr_probe.bind.selected_index=%zu\n", i);
            printf("qrtr_probe.bind.selected_node=%u\n", candidates[i]);
            break;
        }
    }

    if (status == 0) {
        printf("qrtr_probe.status=bind-pass\n");
        return 0;
    }
    printf("qrtr_probe.status=open-only\n");
    return 0;
}
