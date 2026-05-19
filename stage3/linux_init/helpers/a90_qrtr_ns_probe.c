#define _GNU_SOURCE
#include <endian.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/qrtr.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef AF_QIPCRTR
#define AF_QIPCRTR 42
#endif

#define A90_QRTR_NS_PROBE_VERSION "a90_qrtr_ns_probe v1"

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

static bool parse_u32(const char *text, uint32_t *out) {
    char *end = NULL;
    unsigned long value;

    if (text == NULL || *text == '\0') {
        return false;
    }
    errno = 0;
    value = strtoul(text, &end, 0);
    if (errno != 0 || end == text || *end != '\0' || value > UINT32_MAX) {
        return false;
    }
    *out = (uint32_t)value;
    return true;
}

static void usage(const char *argv0) {
    printf("usage: %s --service <u32> --instance <u32> [--allow-qrtr-ns-transmit] [--allow-wildcard-lookup] [--no-del-lookup]\n", argv0);
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
        int saved_errno = errno;
        printf("%s.rc=-1\n", prefix);
        printf("%s.errno=%d\n", prefix, saved_errno);
        printf("%s.error=%s\n", prefix, strerror(saved_errno));
        return -1;
    }
    printf("%s.rc=0\n", prefix);
    printf("%s.len=%u\n", prefix, (unsigned int)len);
    print_sockaddr(prefix, out);
    return 0;
}

static int send_lookup_packet(int fd, uint32_t cmd, uint32_t service, uint32_t instance, const char *prefix) {
    struct qrtr_ctrl_pkt packet;
    struct sockaddr_qrtr dest;
    ssize_t sent;

    memset(&packet, 0, sizeof(packet));
    packet.cmd = htole32(cmd);
    packet.server.service = htole32(service);
    packet.server.instance = htole32(instance);
    packet.server.node = 0;
    packet.server.port = 0;

    memset(&dest, 0, sizeof(dest));
    dest.sq_family = AF_QIPCRTR;
    dest.sq_node = QRTR_NODE_BCAST;
    dest.sq_port = QRTR_PORT_CTRL;

    sent = sendto(fd, &packet, sizeof(packet), 0, (const struct sockaddr *)&dest, sizeof(dest));
    if (sent < 0) {
        int saved_errno = errno;
        printf("%s.rc=-1\n", prefix);
        printf("%s.errno=%d\n", prefix, saved_errno);
        printf("%s.error=%s\n", prefix, strerror(saved_errno));
        return -saved_errno;
    }
    printf("%s.rc=0\n", prefix);
    printf("%s.bytes=%zd\n", prefix, sent);
    printf("%s.cmd=%u\n", prefix, cmd);
    printf("%s.service=%u\n", prefix, service);
    printf("%s.instance=%u\n", prefix, instance);
    return sent == (ssize_t)sizeof(packet) ? 0 : -EIO;
}

int main(int argc, char **argv) {
    uint32_t service = 0;
    uint32_t instance = 0;
    bool have_service = false;
    bool have_instance = false;
    bool allow_transmit = false;
    bool allow_wildcard = false;
    bool send_del_lookup = true;
    int fd;
    int rc;
    struct sockaddr_qrtr name;

    printf("qrtr_ns.version=%s\n", A90_QRTR_NS_PROBE_VERSION);
    printf("qrtr_ns.af=%d\n", AF_QIPCRTR);
    printf("qrtr_ns.port_ctrl=%u\n", QRTR_PORT_CTRL);
    printf("qrtr_ns.new_lookup=%u\n", QRTR_TYPE_NEW_LOOKUP);
    printf("qrtr_ns.del_lookup=%u\n", QRTR_TYPE_DEL_LOOKUP);
    printf("qrtr_ns.send_attempted=0\n");
    printf("qrtr_ns.qmi_attempted=0\n");

    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--service") == 0 && i + 1 < argc) {
            have_service = parse_u32(argv[++i], &service);
        } else if (strcmp(argv[i], "--instance") == 0 && i + 1 < argc) {
            have_instance = parse_u32(argv[++i], &instance);
        } else if (strcmp(argv[i], "--allow-qrtr-ns-transmit") == 0) {
            allow_transmit = true;
        } else if (strcmp(argv[i], "--allow-wildcard-lookup") == 0) {
            allow_wildcard = true;
        } else if (strcmp(argv[i], "--no-del-lookup") == 0) {
            send_del_lookup = false;
        } else if (strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            printf("qrtr_ns.status=usage-error\n");
            printf("qrtr_ns.error=unknown-argument\n");
            usage(argv[0]);
            return 2;
        }
    }

    printf("qrtr_ns.service=%u\n", service);
    printf("qrtr_ns.instance=%u\n", instance);
    printf("qrtr_ns.have_service=%u\n", have_service ? 1U : 0U);
    printf("qrtr_ns.have_instance=%u\n", have_instance ? 1U : 0U);
    printf("qrtr_ns.allow_transmit=%u\n", allow_transmit ? 1U : 0U);
    printf("qrtr_ns.allow_wildcard=%u\n", allow_wildcard ? 1U : 0U);

    if (!have_service || !have_instance) {
        printf("qrtr_ns.status=blocked\n");
        printf("qrtr_ns.reason=missing-service-or-instance\n");
        return 0;
    }
    if (service == 0 && instance == 0 && !allow_wildcard) {
        printf("qrtr_ns.status=blocked\n");
        printf("qrtr_ns.reason=wildcard-blocked\n");
        return 0;
    }
    if (!allow_transmit) {
        printf("qrtr_ns.status=blocked\n");
        printf("qrtr_ns.reason=missing-allow-qrtr-ns-transmit\n");
        return 0;
    }

    fd = open_qrtr_socket();
    if (fd < 0) {
        int saved_errno = errno;
        printf("qrtr_ns.socket.rc=-1\n");
        printf("qrtr_ns.socket.errno=%d\n", saved_errno);
        printf("qrtr_ns.socket.error=%s\n", strerror(saved_errno));
        printf("qrtr_ns.status=socket-failed\n");
        return 1;
    }
    printf("qrtr_ns.socket.rc=0\n");
    (void)get_qrtr_name(fd, "qrtr_ns.initial", &name);
    printf("qrtr_ns.send_attempted=1\n");

    rc = send_lookup_packet(fd, QRTR_TYPE_NEW_LOOKUP, service, instance, "qrtr_ns.new_lookup_send");
    if (rc < 0) {
        close(fd);
        printf("qrtr_ns.status=new-lookup-send-failed\n");
        return 1;
    }
    if (send_del_lookup) {
        rc = send_lookup_packet(fd, QRTR_TYPE_DEL_LOOKUP, service, instance, "qrtr_ns.del_lookup_send");
        if (rc < 0) {
            close(fd);
            printf("qrtr_ns.status=del-lookup-send-failed\n");
            return 1;
        }
    }
    close(fd);
    printf("qrtr_ns.status=lookup-sent\n");
    return 0;
}
