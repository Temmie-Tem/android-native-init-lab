#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/sysinfo.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define TCPCTL_VERSION "a90_tcpctl v1"
#define MAX_LINE 1024
#define MAX_ARGS 32
#define RUN_TIMEOUT_MS 10000
#define RUN_OUTPUT_LIMIT (128 * 1024)

struct tcpctl_server_config {
    const char *bind_addr;
    unsigned short port;
    int idle_timeout_sec;
    int max_clients;
    const char *token_path;
    bool require_auth;
};

struct tcpctl_client_state {
    bool authenticated;
};

static long monotonic_millis(void)
{
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0) {
        return 0;
    }

    return ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
}

static void usage(const char *argv0)
{
    fprintf(stderr,
            "usage: %s listen <bind_addr> <port> <idle_timeout_sec> [max_clients] [token_path]\n"
            "       %s listen <port> <idle_timeout_sec> [max_clients]  # legacy loopback/no-auth\n",
            argv0, argv0);
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

static int parse_nonnegative_int(const char *text, int max_value, int *out)
{
    char *end = NULL;
    unsigned long value;

    errno = 0;
    value = strtoul(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value > (unsigned long)max_value) {
        return -1;
    }

    *out = (int)value;
    return 0;
}

static int send_all(int fd, const void *data, size_t len)
{
    const char *cursor = data;
    size_t sent = 0;

    while (sent < len) {
        ssize_t rc = send(fd, cursor + sent, len - sent, 0);

        if (rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (rc == 0) {
            return -1;
        }
        sent += (size_t)rc;
    }

    return 0;
}

static int send_text(int fd, const char *text)
{
    return send_all(fd, text, strlen(text));
}

static int sendf(int fd, const char *fmt, ...)
{
    char buf[1024];
    va_list ap;
    int len;

    va_start(ap, fmt);
    len = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);

    if (len < 0) {
        return -1;
    }
    if ((size_t)len >= sizeof(buf)) {
        len = (int)sizeof(buf) - 1;
    }

    return send_all(fd, buf, (size_t)len);
}

static int read_line(int fd, char *buf, size_t size, int timeout_ms)
{
    size_t pos = 0;
    long deadline = monotonic_millis() + timeout_ms;

    while (pos + 1 < size) {
        struct pollfd pfd;
        long now = monotonic_millis();
        int wait_ms;
        char ch;
        ssize_t rc;

        if (now >= deadline) {
            return -ETIMEDOUT;
        }

        wait_ms = (int)(deadline - now);
        if (wait_ms > 1000) {
            wait_ms = 1000;
        }

        pfd.fd = fd;
        pfd.events = POLLIN;
        pfd.revents = 0;
        if (poll(&pfd, 1, wait_ms) < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -errno;
        }
        if ((pfd.revents & POLLIN) == 0) {
            continue;
        }

        rc = recv(fd, &ch, 1, 0);
        if (rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -errno;
        }
        if (rc == 0) {
            break;
        }
        if (ch == '\r') {
            continue;
        }
        if (ch == '\n') {
            break;
        }

        buf[pos++] = ch;
    }

    buf[pos] = '\0';
    return (int)pos;
}

static int split_args(char *line, char **argv, int argv_max)
{
    int argc = 0;
    char *cursor = line;

    while (*cursor != '\0' && argc < argv_max - 1) {
        while (*cursor == ' ' || *cursor == '\t') {
            ++cursor;
        }
        if (*cursor == '\0') {
            break;
        }
        if (*cursor == '#') {
            break;
        }

        argv[argc++] = cursor;

        while (*cursor != '\0' && *cursor != ' ' && *cursor != '\t') {
            ++cursor;
        }
        if (*cursor == '\0') {
            break;
        }
        *cursor++ = '\0';
    }

    argv[argc] = NULL;
    return argc;
}

static int set_nonblock(int fd)
{
    int flags = fcntl(fd, F_GETFL, 0);

    if (flags < 0) {
        return -1;
    }
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

static int read_token_file(const char *path, char *buf, size_t size)
{
    int fd;
    ssize_t rd;
    size_t index;

    if (path == NULL || path[0] == '\0' || strcmp(path, "-") == 0 ||
        buf == NULL || size == 0) {
        errno = EINVAL;
        return -1;
    }
    fd = open(path, O_RDONLY);
    if (fd < 0) {
        return -1;
    }
    rd = read(fd, buf, size - 1);
    close(fd);
    if (rd <= 0) {
        errno = rd == 0 ? EINVAL : errno;
        return -1;
    }
    buf[rd] = '\0';
    for (index = 0; buf[index] != '\0'; ++index) {
        if (buf[index] == '\r' || buf[index] == '\n' ||
            buf[index] == ' ' || buf[index] == '\t') {
            buf[index] = '\0';
            break;
        }
    }
    if (buf[0] == '\0') {
        errno = EINVAL;
        return -1;
    }
    return 0;
}

static bool auth_required(const struct tcpctl_server_config *config)
{
    return config != NULL && config->require_auth;
}

static bool client_authorized(const struct tcpctl_server_config *config,
                              const struct tcpctl_client_state *state)
{
    return !auth_required(config) || (state != NULL && state->authenticated);
}

static int command_auth(int client_fd,
                        const struct tcpctl_server_config *config,
                        struct tcpctl_client_state *state,
                        char **argv,
                        int argc)
{
    char expected[128];

    if (!auth_required(config)) {
        state->authenticated = true;
        return send_text(client_fd, "OK auth-not-required\n");
    }
    if (argc != 2) {
        return send_text(client_fd, "ERR usage: auth <token>\n");
    }
    if (read_token_file(config->token_path, expected, sizeof(expected)) < 0) {
        return sendf(client_fd, "ERR auth-token-unavailable: %s\n", strerror(errno));
    }
    if (strcmp(argv[1], expected) != 0) {
        return send_text(client_fd, "ERR auth-failed\n");
    }
    state->authenticated = true;
    return send_text(client_fd, "OK authenticated\n");
}

static int command_help(int client_fd, const struct tcpctl_server_config *config)
{
    send_text(client_fd, "commands:\n");
    send_text(client_fd, "  help\n");
    send_text(client_fd, "  ping\n");
    send_text(client_fd, "  version\n");
    send_text(client_fd, "  status\n");
    if (auth_required(config)) {
        send_text(client_fd, "  auth <token>\n");
    }
    send_text(client_fd, "  run <absolute-path> [args...]\n");
    send_text(client_fd, "  quit\n");
    send_text(client_fd, "  shutdown\n");
    return send_text(client_fd, "OK\n");
}

static int command_status(int client_fd, const struct tcpctl_server_config *config)
{
    struct utsname uts;
    struct sysinfo info;

    if (config != NULL) {
        sendf(client_fd, "listen: bind=%s port=%u auth=%s\n",
              config->bind_addr,
              config->port,
              auth_required(config) ? "required" : "none");
    }

    if (uname(&uts) == 0) {
        sendf(client_fd, "kernel: %s %s %s %s\n",
              uts.sysname, uts.release, uts.version, uts.machine);
    } else {
        sendf(client_fd, "kernel: uname failed: %s\n", strerror(errno));
    }

    if (sysinfo(&info) == 0) {
        unsigned long total_mb = (unsigned long)((info.totalram * info.mem_unit) / (1024UL * 1024UL));
        unsigned long free_mb = (unsigned long)((info.freeram * info.mem_unit) / (1024UL * 1024UL));

        sendf(client_fd, "uptime: %ld\n", info.uptime);
        sendf(client_fd, "load: %.2f %.2f %.2f\n",
              info.loads[0] / 65536.0,
              info.loads[1] / 65536.0,
              info.loads[2] / 65536.0);
        sendf(client_fd, "mem: %lu/%lu MB free/total\n", free_mb, total_mb);
    } else {
        sendf(client_fd, "sysinfo: %s\n", strerror(errno));
    }

    return send_text(client_fd, "OK\n");
}

static int report_child_status(int client_fd, int status)
{
    if (WIFEXITED(status)) {
        int code = WEXITSTATUS(status);

        sendf(client_fd, "[exit %d]\n", code);
        if (code == 0) {
            return send_text(client_fd, "OK\n");
        }
        return sendf(client_fd, "ERR exit=%d\n", code);
    }

    if (WIFSIGNALED(status)) {
        int sig = WTERMSIG(status);

        sendf(client_fd, "[signal %d]\n", sig);
        return sendf(client_fd, "ERR signal=%d\n", sig);
    }

    return send_text(client_fd, "ERR child-status\n");
}

static int command_run(int client_fd,
                       const struct tcpctl_server_config *config,
                       const struct tcpctl_client_state *state,
                       char **argv,
                       int argc)
{
    static char *const envp[] = {
        "PATH=/cache:/cache/bin:/bin:/system/bin",
        "HOME=/",
        "TERM=vt100",
        "LD_LIBRARY_PATH=/cache/adb/lib",
        NULL
    };
    int pipefd[2];
    int devnull;
    pid_t pid;
    int status = 0;
    int child_done = 0;
    int pipe_open = 1;
    size_t forwarded = 0;
    int truncated = 0;
    long deadline = monotonic_millis() + RUN_TIMEOUT_MS;

    if (!client_authorized(config, state)) {
        return send_text(client_fd, "ERR auth-required\n");
    }
    if (argc < 2) {
        return send_text(client_fd, "ERR usage: run <absolute-path> [args...]\n");
    }
    if (argv[1][0] != '/') {
        return send_text(client_fd, "ERR run path must be absolute\n");
    }

    if (pipe(pipefd) < 0) {
        return sendf(client_fd, "ERR pipe: %s\n", strerror(errno));
    }

    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;

        close(pipefd[0]);
        close(pipefd[1]);
        return sendf(client_fd, "ERR fork: %s\n", strerror(saved_errno));
    }

    if (pid == 0) {
        close(pipefd[0]);
        devnull = open("/dev/null", O_RDONLY);
        if (devnull >= 0) {
            dup2(devnull, STDIN_FILENO);
            close(devnull);
        }
        dup2(pipefd[1], STDOUT_FILENO);
        dup2(pipefd[1], STDERR_FILENO);
        close(pipefd[1]);
        execve(argv[1], &argv[1], envp);
        dprintf(STDERR_FILENO, "execve(%s): %s\n", argv[1], strerror(errno));
        _exit(127);
    }

    close(pipefd[1]);
    set_nonblock(pipefd[0]);
    sendf(client_fd, "[pid %ld]\n", (long)pid);

    while (pipe_open || !child_done) {
        long now = monotonic_millis();
        struct pollfd pfd;

        if (!child_done) {
            pid_t got = waitpid(pid, &status, WNOHANG);

            if (got == pid) {
                child_done = 1;
            } else if (got < 0 && errno != EINTR) {
                close(pipefd[0]);
                return sendf(client_fd, "ERR waitpid: %s\n", strerror(errno));
            }
        }

        if (!child_done && now >= deadline) {
            kill(pid, SIGKILL);
            waitpid(pid, &status, 0);
            child_done = 1;
            send_text(client_fd, "[timeout]\n");
        }

        if (!pipe_open) {
            continue;
        }

        pfd.fd = pipefd[0];
        pfd.events = POLLIN | POLLHUP | POLLERR;
        pfd.revents = 0;
        if (poll(&pfd, 1, 100) < 0) {
            if (errno == EINTR) {
                continue;
            }
            close(pipefd[0]);
            return sendf(client_fd, "ERR poll: %s\n", strerror(errno));
        }

        if ((pfd.revents & POLLIN) != 0) {
            char buf[4096];
            ssize_t rc;

            while ((rc = read(pipefd[0], buf, sizeof(buf))) > 0) {
                if (forwarded < RUN_OUTPUT_LIMIT) {
                    size_t allowed = RUN_OUTPUT_LIMIT - forwarded;
                    size_t to_send = (size_t)rc < allowed ? (size_t)rc : allowed;

                    if (to_send > 0) {
                        send_all(client_fd, buf, to_send);
                        forwarded += to_send;
                    }
                } else {
                    truncated = 1;
                }
                if ((size_t)rc > RUN_OUTPUT_LIMIT - (forwarded < RUN_OUTPUT_LIMIT ? forwarded : RUN_OUTPUT_LIMIT)) {
                    truncated = 1;
                }
            }

            if (rc < 0 && errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) {
                close(pipefd[0]);
                return sendf(client_fd, "ERR read: %s\n", strerror(errno));
            }
        }

        if ((pfd.revents & (POLLHUP | POLLERR)) != 0) {
            char buf[4096];
            ssize_t rc;

            while ((rc = read(pipefd[0], buf, sizeof(buf))) > 0) {
                if (forwarded < RUN_OUTPUT_LIMIT) {
                    size_t allowed = RUN_OUTPUT_LIMIT - forwarded;
                    size_t to_send = (size_t)rc < allowed ? (size_t)rc : allowed;

                    if (to_send > 0) {
                        send_all(client_fd, buf, to_send);
                        forwarded += to_send;
                    }
                } else {
                    truncated = 1;
                }
            }
            pipe_open = 0;
        }
    }

    close(pipefd[0]);
    if (truncated) {
        send_text(client_fd, "\n[output truncated]\n");
    }
    return report_child_status(client_fd, status);
}

static int handle_client(int client_fd,
                         const struct tcpctl_server_config *config,
                         bool *stop_server)
{
    char line[MAX_LINE];
    char *argv[MAX_ARGS];
    struct tcpctl_client_state state = { false };

    send_text(client_fd, TCPCTL_VERSION " ready\n");

    for (;;) {
        int argc;
        int rc = read_line(client_fd, line, sizeof(line), 15000);

        if (rc < 0) {
            return sendf(client_fd, "ERR read=%d\n", rc);
        }

        argc = split_args(line, argv, MAX_ARGS);
        if (argc == 0) {
            return send_text(client_fd, "ERR empty\n");
        }

        if (strcmp(argv[0], "help") == 0) {
            return command_help(client_fd, config);
        }
        if (strcmp(argv[0], "ping") == 0) {
            send_text(client_fd, "pong\n");
            return send_text(client_fd, "OK\n");
        }
        if (strcmp(argv[0], "version") == 0) {
            send_text(client_fd, TCPCTL_VERSION "\n");
            return send_text(client_fd, "OK\n");
        }
        if (strcmp(argv[0], "status") == 0) {
            return command_status(client_fd, config);
        }
        if (strcmp(argv[0], "auth") == 0) {
            if (command_auth(client_fd, config, &state, argv, argc) < 0) {
                return -1;
            }
            if (!state.authenticated && auth_required(config)) {
                return 0;
            }
            continue;
        }
        if (strcmp(argv[0], "run") == 0) {
            return command_run(client_fd, config, &state, argv, argc);
        }
        if (strcmp(argv[0], "quit") == 0) {
            return send_text(client_fd, "OK bye\n");
        }
        if (strcmp(argv[0], "shutdown") == 0) {
            if (!client_authorized(config, &state)) {
                return send_text(client_fd, "ERR auth-required\n");
            }
            *stop_server = true;
            return send_text(client_fd, "OK shutdown\n");
        }

        return sendf(client_fd, "ERR unknown command: %s\n", argv[0]);
    }
}

static int command_listen(const struct tcpctl_server_config *config)
{
    int idle_timeout_ms;
    int server_fd;
    int one = 1;
    int served = 0;
    bool stop_server = false;
    struct sockaddr_in addr;

    idle_timeout_ms = config->idle_timeout_sec * 1000;
    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        fprintf(stderr, "socket: %s\n", strerror(errno));
        return 1;
    }

    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    if (inet_pton(AF_INET, config->bind_addr, &addr.sin_addr) != 1) {
        fprintf(stderr, "listen: invalid bind_addr: %s\n", config->bind_addr);
        close(server_fd);
        return 2;
    }
    addr.sin_port = htons(config->port);

    if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        fprintf(stderr, "bind: %s\n", strerror(errno));
        close(server_fd);
        return 1;
    }

    if (listen(server_fd, 4) < 0) {
        fprintf(stderr, "listen: %s\n", strerror(errno));
        close(server_fd);
        return 1;
    }

    printf("tcpctl: listening bind=%s port=%u idle_timeout=%ds max_clients=%d auth=%s\n",
           config->bind_addr,
           config->port,
           config->idle_timeout_sec,
           config->max_clients,
           auth_required(config) ? "required" : "none");
    fflush(stdout);

    while (!stop_server && (config->max_clients == 0 || served < config->max_clients)) {
        struct pollfd pfd;
        int poll_rc;
        int client_fd;

        pfd.fd = server_fd;
        pfd.events = POLLIN;
        pfd.revents = 0;

        poll_rc = poll(&pfd, 1, idle_timeout_ms);
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            fprintf(stderr, "poll: %s\n", strerror(errno));
            close(server_fd);
            return 1;
        }
        if (poll_rc == 0) {
            printf("tcpctl: idle timeout\n");
            break;
        }

        client_fd = accept(server_fd, NULL, NULL);
        if (client_fd < 0) {
            if (errno == EINTR) {
                continue;
            }
            fprintf(stderr, "accept: %s\n", strerror(errno));
            close(server_fd);
            return 1;
        }

        ++served;
        handle_client(client_fd, config, &stop_server);
        shutdown(client_fd, SHUT_RDWR);
        close(client_fd);
    }

    close(server_fd);
    printf("tcpctl: served=%d stop=%d\n", served, stop_server ? 1 : 0);
    return 0;
}

static int parse_listen_config(int argc, char **argv, struct tcpctl_server_config *config)
{
    const char *max_clients_text = NULL;

    memset(config, 0, sizeof(*config));
    config->bind_addr = "127.0.0.1";
    config->max_clients = 16;
    config->token_path = NULL;
    config->require_auth = false;

    if (argc == 4 || argc == 5) {
        if (parse_u16(argv[2], &config->port) < 0 ||
            parse_nonnegative_int(argv[3], 3600, &config->idle_timeout_sec) < 0) {
            return -1;
        }
        max_clients_text = argc == 5 ? argv[4] : NULL;
    } else if (argc == 6 || argc == 7) {
        config->bind_addr = argv[2];
        if (parse_u16(argv[3], &config->port) < 0 ||
            parse_nonnegative_int(argv[4], 3600, &config->idle_timeout_sec) < 0) {
            return -1;
        }
        max_clients_text = argv[5];
        if (argc == 7 && strcmp(argv[6], "-") != 0) {
            config->token_path = argv[6];
            config->require_auth = true;
        }
    } else {
        return -1;
    }

    if (max_clients_text != NULL &&
        parse_nonnegative_int(max_clients_text, 10000, &config->max_clients) < 0) {
        return -1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        usage(argv[0]);
        return 2;
    }

    if (strcmp(argv[1], "listen") == 0) {
        struct tcpctl_server_config config;

        if (parse_listen_config(argc, argv, &config) < 0) {
            usage(argv[0]);
            return 2;
        }
        return command_listen(&config);
    }

    usage(argv[0]);
    return 2;
}
