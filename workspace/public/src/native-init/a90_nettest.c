#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

static void usage(const char *argv0)
{
    fprintf(stderr, "usage: %s listen <port> <timeout_sec> <expect>\n", argv0);
    fprintf(stderr, "       %s send <ipv4> <port> <payload>\n", argv0);
}

static int parse_u16(const char *text, unsigned short *out)
{
    char *end = NULL;
    unsigned long value;

    errno = 0;
    value = strtoul(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value == 0 || value > 65535) {
        return -1;
    }

    *out = (unsigned short)value;
    return 0;
}

static int parse_timeout_ms(const char *text, int *out)
{
    char *end = NULL;
    unsigned long value;

    errno = 0;
    value = strtoul(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value > 3600) {
        return -1;
    }

    *out = (int)(value * 1000UL);
    return 0;
}

static void set_socket_timeout(int fd, int timeout_ms)
{
    struct timeval tv;

    tv.tv_sec = timeout_ms / 1000;
    tv.tv_usec = (timeout_ms % 1000) * 1000;
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
}

static int send_all(int fd, const char *payload)
{
    size_t sent = 0;
    size_t len = strlen(payload);

    while (sent < len) {
        ssize_t rc = send(fd, payload + sent, len - sent, 0);

        if (rc < 0) {
            fprintf(stderr, "send: %s\n", strerror(errno));
            return 1;
        }
        if (rc == 0) {
            fprintf(stderr, "send: short write\n");
            return 1;
        }
        sent += (size_t)rc;
    }

    return 0;
}

static int command_listen(const char *port_text,
                          const char *timeout_text,
                          const char *expect)
{
    unsigned short port;
    int timeout_ms;
    int server_fd;
    int client_fd;
    int one = 1;
    struct sockaddr_in addr;
    struct pollfd pfd;
    char buffer[4096];
    size_t used = 0;

    if (parse_u16(port_text, &port) < 0 || parse_timeout_ms(timeout_text, &timeout_ms) < 0) {
        fprintf(stderr, "listen: invalid port or timeout\n");
        return 2;
    }

    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        fprintf(stderr, "socket: %s\n", strerror(errno));
        return 1;
    }

    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(port);

    if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        fprintf(stderr, "bind: %s\n", strerror(errno));
        close(server_fd);
        return 1;
    }

    if (listen(server_fd, 1) < 0) {
        fprintf(stderr, "listen: %s\n", strerror(errno));
        close(server_fd);
        return 1;
    }

    printf("listen: port=%u timeout_ms=%d expect=%s\n", port, timeout_ms, expect);
    fflush(stdout);

    pfd.fd = server_fd;
    pfd.events = POLLIN;
    if (poll(&pfd, 1, timeout_ms) <= 0) {
        fprintf(stderr, "listen: accept timeout\n");
        close(server_fd);
        return 1;
    }

    client_fd = accept(server_fd, NULL, NULL);
    if (client_fd < 0) {
        fprintf(stderr, "accept: %s\n", strerror(errno));
        close(server_fd);
        return 1;
    }

    set_socket_timeout(client_fd, timeout_ms);
    while (used + 1 < sizeof(buffer)) {
        ssize_t rc = recv(client_fd, buffer + used, sizeof(buffer) - used - 1, 0);

        if (rc < 0) {
            fprintf(stderr, "recv: %s\n", strerror(errno));
            close(client_fd);
            close(server_fd);
            return 1;
        }
        if (rc == 0) {
            break;
        }

        used += (size_t)rc;
        buffer[used] = '\0';
        if (strstr(buffer, expect) != NULL) {
            printf("received: ");
            fwrite(buffer, 1, used, stdout);
            if (used == 0 || buffer[used - 1] != '\n') {
                printf("\n");
            }
            printf("PASS listen received expected payload\n");
            close(client_fd);
            close(server_fd);
            return 0;
        }
    }

    buffer[used] = '\0';
    printf("received: ");
    fwrite(buffer, 1, used, stdout);
    if (used == 0 || buffer[used - 1] != '\n') {
        printf("\n");
    }
    fprintf(stderr, "FAIL listen did not see expected payload\n");
    close(client_fd);
    close(server_fd);
    return 1;
}

static int command_send(const char *host_text,
                        const char *port_text,
                        const char *payload)
{
    unsigned short port;
    int fd;
    struct sockaddr_in addr;

    if (parse_u16(port_text, &port) < 0) {
        fprintf(stderr, "send: invalid port\n");
        return 2;
    }

    fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        fprintf(stderr, "socket: %s\n", strerror(errno));
        return 1;
    }

    set_socket_timeout(fd, 10000);

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    if (inet_pton(AF_INET, host_text, &addr.sin_addr) != 1) {
        fprintf(stderr, "send: invalid IPv4 address: %s\n", host_text);
        close(fd);
        return 2;
    }

    printf("send: host=%s port=%u payload=%s\n", host_text, port, payload);
    fflush(stdout);

    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        fprintf(stderr, "connect: %s\n", strerror(errno));
        close(fd);
        return 1;
    }

    if (send_all(fd, payload) != 0) {
        close(fd);
        return 1;
    }

    shutdown(fd, SHUT_WR);
    close(fd);
    printf("PASS send delivered payload\n");
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        usage(argv[0]);
        return 2;
    }

    if (strcmp(argv[1], "listen") == 0) {
        if (argc != 5) {
            usage(argv[0]);
            return 2;
        }
        return command_listen(argv[2], argv[3], argv[4]);
    }

    if (strcmp(argv[1], "send") == 0) {
        if (argc != 5) {
            usage(argv[0]);
            return 2;
        }
        return command_send(argv[2], argv[3], argv[4]);
    }

    usage(argv[0]);
    return 2;
}
