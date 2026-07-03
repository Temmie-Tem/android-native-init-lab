/*
 * Minimal loopback-only HTTP smoke server for the D-public live gate.
 *
 * The server intentionally binds 127.0.0.1 by default.  D-public exposes it
 * only through an explicit outbound tunnel; it must not listen on the public
 * network interface directly.
 */
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

static volatile sig_atomic_t keep_running = 1;

static void on_signal(int signo) {
    (void)signo;
    keep_running = 0;
}

static int parse_port(const char *text) {
    char *end = NULL;
    long port = strtol(text, &end, 10);
    if (text == end || end == NULL || *end != '\0' || port < 1 || port > 65535) {
        return -1;
    }
    return (int)port;
}

static void write_all_best_effort(int fd, const char *data, size_t len) {
    size_t off = 0;
    while (off < len) {
        ssize_t written = write(fd, data + off, len - off);
        if (written < 0) {
            if (errno == EINTR) {
                continue;
            }
            return;
        }
        if (written == 0) {
            return;
        }
        off += (size_t)written;
    }
}

int main(int argc, char **argv) {
    const char *bind_ip = "127.0.0.1";
    int port = 8080;
    int server_fd = -1;
    int one = 1;
    struct sockaddr_in addr;

    if (argc >= 2) {
        bind_ip = argv[1];
    }
    if (argc >= 3) {
        port = parse_port(argv[2]);
        if (port < 0) {
            fprintf(stderr, "bad port\n");
            return 2;
        }
    }

    signal(SIGTERM, on_signal);
    signal(SIGINT, on_signal);
    signal(SIGPIPE, SIG_IGN);

    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("socket");
        return 1;
    }
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((unsigned short)port);
    if (inet_pton(AF_INET, bind_ip, &addr.sin_addr) != 1) {
        fprintf(stderr, "bad bind ip\n");
        close(server_fd);
        return 2;
    }
    if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        close(server_fd);
        return 1;
    }
    if (listen(server_fd, 8) < 0) {
        perror("listen");
        close(server_fd);
        return 1;
    }

    fprintf(stderr, "a90-dpublic-smoke listening on %s:%d\n", bind_ip, port);
    fflush(stderr);

    while (keep_running) {
        int client_fd = accept(server_fd, NULL, NULL);
        const char body[] =
            "A90_DPUBLIC_SMOKE_OK\n"
            "service=loopback-http\n"
            "public_exposure=outbound-tunnel-only\n";
        char header[256];
        int header_len;

        if (client_fd < 0) {
            if (errno == EINTR) {
                continue;
            }
            perror("accept");
            break;
        }

        header_len = snprintf(
            header,
            sizeof(header),
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            "Cache-Control: no-store\r\n"
            "Connection: close\r\n"
            "Content-Length: %zu\r\n"
            "\r\n",
            strlen(body));
        if (header_len > 0) {
            write_all_best_effort(client_fd, header, (size_t)header_len);
            write_all_best_effort(client_fd, body, sizeof(body) - 1);
        }
        close(client_fd);
    }

    close(server_fd);
    return 0;
}
