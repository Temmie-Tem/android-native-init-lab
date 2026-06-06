#define _GNU_SOURCE

#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define LINE_MAX_LEN 1024
#define TOKEN_MAX_LEN 128
#define DEFAULT_IDLE_SEC 900

static volatile sig_atomic_t stopping;

static void on_signal(int signo) {
    (void)signo;
    stopping = 1;
}

static int write_all_fd(int fd, const void *buf, size_t len) {
    const char *cursor = (const char *)buf;

    while (len > 0) {
        ssize_t wr = write(fd, cursor, len);

        if (wr < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (wr == 0) {
            errno = EPIPE;
            return -1;
        }
        cursor += wr;
        len -= (size_t)wr;
    }
    return 0;
}

static int send_text(int fd, const char *text) {
    return write_all_fd(fd, text, strlen(text));
}

static void trim_line(char *text) {
    size_t len;

    if (text == NULL) {
        return;
    }
    len = strlen(text);
    while (len > 0 && (text[len - 1] == '\n' || text[len - 1] == '\r' ||
                       text[len - 1] == ' ' || text[len - 1] == '\t')) {
        text[--len] = '\0';
    }
}

static int read_token(const char *path, char *out, size_t out_size) {
    int fd;
    ssize_t rd;

    if (out == NULL || out_size == 0) {
        errno = EINVAL;
        return -1;
    }
    out[0] = '\0';
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    rd = read(fd, out, out_size - 1);
    if (rd < 0) {
        int saved_errno = errno;

        close(fd);
        errno = saved_errno;
        return -1;
    }
    close(fd);
    out[rd] = '\0';
    trim_line(out);
    if (out[0] == '\0') {
        errno = EINVAL;
        return -1;
    }
    return 0;
}

static int read_line_timeout(int fd, char *out, size_t out_size, int timeout_ms) {
    size_t used = 0;
    long deadline_ms;
    struct timespec ts;

    if (out == NULL || out_size == 0) {
        errno = EINVAL;
        return -1;
    }
    out[0] = '\0';
    clock_gettime(CLOCK_MONOTONIC, &ts);
    deadline_ms = ts.tv_sec * 1000L + ts.tv_nsec / 1000000L + timeout_ms;

    while (!stopping) {
        struct pollfd pfd = { .fd = fd, .events = POLLIN };
        long now_ms;
        int wait_ms;
        char ch;
        ssize_t rd;

        clock_gettime(CLOCK_MONOTONIC, &ts);
        now_ms = ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
        wait_ms = (int)(deadline_ms - now_ms);
        if (wait_ms <= 0) {
            errno = ETIMEDOUT;
            return -1;
        }
        if (poll(&pfd, 1, wait_ms) < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if ((pfd.revents & (POLLHUP | POLLERR | POLLNVAL)) != 0) {
            errno = ECONNRESET;
            return -1;
        }
        if ((pfd.revents & POLLIN) == 0) {
            continue;
        }
        rd = read(fd, &ch, 1);
        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (rd == 0) {
            errno = ECONNRESET;
            return -1;
        }
        if (ch == '\n') {
            out[used] = '\0';
            trim_line(out);
            return 0;
        }
        if (used + 1 < out_size) {
            out[used++] = ch;
        }
    }
    errno = EINTR;
    return -1;
}

static void set_busybox_path_env(const char *busybox_path) {
    char dir[512];
    char *slash;

    if (busybox_path == NULL || busybox_path[0] == '\0') {
        return;
    }
    snprintf(dir, sizeof(dir), "%s", busybox_path);
    slash = strrchr(dir, '/');
    if (slash == NULL || slash == dir) {
        return;
    }
    *slash = '\0';
    {
        char path_env[768];

        snprintf(path_env,
                 sizeof(path_env),
                 "%s:/cache/bin:/cache:/bin:/system/bin",
                 dir);
        setenv("PATH", path_env, 1);
    }
}

static int run_exec_command(int client_fd, const char *busybox_path, const char *command) {
    int pipe_fds[2];
    pid_t pid;
    int status = 0;
    char trailer[96];

    if (command == NULL || command[0] == '\0') {
        send_text(client_fd, "ERR empty-command\n");
        return -EINVAL;
    }
    if (pipe(pipe_fds) < 0) {
        send_text(client_fd, "ERR pipe\n");
        return -errno;
    }

    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;

        close(pipe_fds[0]);
        close(pipe_fds[1]);
        send_text(client_fd, "ERR fork\n");
        return -saved_errno;
    }

    if (pid == 0) {
        int null_fd;

        signal(SIGPIPE, SIG_DFL);
        close(pipe_fds[0]);
        null_fd = open("/dev/null", O_RDONLY | O_CLOEXEC);
        if (null_fd >= 0) {
            dup2(null_fd, STDIN_FILENO);
        }
        dup2(pipe_fds[1], STDOUT_FILENO);
        dup2(pipe_fds[1], STDERR_FILENO);
        set_busybox_path_env(busybox_path);
        if (pipe_fds[1] > STDERR_FILENO) {
            close(pipe_fds[1]);
        }
        if (null_fd > STDERR_FILENO) {
            close(null_fd);
        }
        execl(busybox_path, "busybox", "sh", "-c", command, (char *)NULL);
        dprintf(STDERR_FILENO, "a90_rshell: exec %s: %s\n", busybox_path, strerror(errno));
        _exit(127);
    }

    close(pipe_fds[1]);
    send_text(client_fd, "A90RSH1 BEGIN\n");
    while (!stopping) {
        char buf[1024];
        ssize_t rd = read(pipe_fds[0], buf, sizeof(buf));

        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            break;
        }
        if (rd == 0) {
            break;
        }
        if (write_all_fd(client_fd, buf, (size_t)rd) < 0) {
            kill(pid, SIGTERM);
            break;
        }
    }
    close(pipe_fds[0]);

    while (waitpid(pid, &status, 0) < 0) {
        if (errno == EINTR) {
            continue;
        }
        status = 0x7f00;
        break;
    }

    if (WIFEXITED(status)) {
        snprintf(trailer, sizeof(trailer), "A90RSH1 END rc=%d\n", WEXITSTATUS(status));
    } else if (WIFSIGNALED(status)) {
        snprintf(trailer, sizeof(trailer), "A90RSH1 END rc=%d signal=%d\n",
                 128 + WTERMSIG(status), WTERMSIG(status));
    } else {
        snprintf(trailer, sizeof(trailer), "A90RSH1 END rc=127\n");
    }
    send_text(client_fd, trailer);
    return 0;
}

static void handle_client(int client_fd,
                          const char *token_path,
                          const char *busybox_path,
                          int idle_ms) {
    char expected[TOKEN_MAX_LEN];
    char line[LINE_MAX_LEN];

    send_text(client_fd, "A90RSH1 READY auth=token\n");
    if (read_token(token_path, expected, sizeof(expected)) < 0) {
        send_text(client_fd, "ERR auth-unavailable\n");
        return;
    }
    if (read_line_timeout(client_fd, line, sizeof(line), idle_ms) < 0) {
        send_text(client_fd, "ERR auth-timeout\n");
        return;
    }
    if (strncmp(line, "AUTH ", 5) != 0 || strcmp(line + 5, expected) != 0) {
        send_text(client_fd, "ERR auth\n");
        return;
    }
    send_text(client_fd, "OK auth\n");

    while (!stopping) {
        if (read_line_timeout(client_fd, line, sizeof(line), idle_ms) < 0) {
            send_text(client_fd, "BYE idle\n");
            return;
        }
        if (strcmp(line, "PING") == 0) {
            send_text(client_fd, "PONG\n");
        } else if (strcmp(line, "QUIT") == 0) {
            send_text(client_fd, "BYE\n");
            return;
        } else if (strncmp(line, "EXEC ", 5) == 0) {
            (void)run_exec_command(client_fd, busybox_path, line + 5);
        } else {
            send_text(client_fd, "ERR command\n");
        }
    }
}

static int open_listener(const char *bind_addr, int port) {
    int server_fd;
    int one = 1;
    struct sockaddr_in addr;

    server_fd = socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (server_fd < 0) {
        return -1;
    }
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((uint16_t)port);
    if (inet_pton(AF_INET, bind_addr, &addr.sin_addr) != 1) {
        close(server_fd);
        errno = EINVAL;
        return -1;
    }
    if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        int saved_errno = errno;

        close(server_fd);
        errno = saved_errno;
        return -1;
    }
    if (listen(server_fd, 1) < 0) {
        int saved_errno = errno;

        close(server_fd);
        errno = saved_errno;
        return -1;
    }
    return server_fd;
}

int main(int argc, char **argv) {
    const char *bind_addr;
    const char *token_path;
    const char *busybox_path;
    int port;
    int idle_sec;
    int server_fd;

    if (argc != 6) {
        fprintf(stderr, "usage: a90_rshell <bind_addr> <port> <token_path> <busybox_path> <idle_sec>\n");
        return 2;
    }

    bind_addr = argv[1];
    port = atoi(argv[2]);
    token_path = argv[3];
    busybox_path = argv[4];
    idle_sec = atoi(argv[5]);
    if (port <= 0 || port > 65535 || idle_sec <= 0) {
        fprintf(stderr, "a90_rshell: invalid port or idle seconds\n");
        return 2;
    }

    signal(SIGTERM, on_signal);
    signal(SIGINT, on_signal);
    signal(SIGHUP, SIG_IGN);
    signal(SIGPIPE, SIG_IGN);

    server_fd = open_listener(bind_addr, port);
    if (server_fd < 0) {
        fprintf(stderr, "a90_rshell: listen %s:%d: %s\n", bind_addr, port, strerror(errno));
        return 1;
    }

    printf("a90_rshell: listening %s:%d token=%s shell=%s idle=%ds\n",
           bind_addr, port, token_path, busybox_path, idle_sec);
    fflush(stdout);

    while (!stopping) {
        struct pollfd pfd = { .fd = server_fd, .events = POLLIN };
        int prc = poll(&pfd, 1, 1000);

        if (prc < 0) {
            if (errno == EINTR) {
                continue;
            }
            break;
        }
        if (prc == 0 || (pfd.revents & POLLIN) == 0) {
            continue;
        }
        while (!stopping) {
            int client_fd = accept4(server_fd, NULL, NULL, SOCK_CLOEXEC);

            if (client_fd < 0) {
                if (errno == EINTR) {
                    continue;
                }
                break;
            }
            handle_client(client_fd, token_path, busybox_path, idle_sec * 1000);
            close(client_fd);
            break;
        }
    }

    close(server_fd);
    return 0;
}
