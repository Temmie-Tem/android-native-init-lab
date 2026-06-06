#include "a90_console.h"

#include "a90_config.h"
#include "a90_log.h"
#include "a90_util.h"

#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/poll.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <termios.h>
#include <unistd.h>

#ifndef ECANCELED
#define ECANCELED 125
#endif

static int console_fd = -1;
static long last_console_reattach_ms = 0;

static void console_klogf(const char *fmt, ...) {
    char buf[512];
    va_list ap;
    int fd;
    int len;

    va_start(ap, fmt);
    len = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);

    if (len <= 0) {
        return;
    }
    if ((size_t)len >= sizeof(buf)) {
        len = (int)sizeof(buf) - 1;
    }

    fd = open("/dev/kmsg", O_WRONLY);
    if (fd < 0) {
        return;
    }
    write_all(fd, buf, (size_t)len);
    close(fd);
}

void a90_console_printf(const char *fmt, ...) {
    char buf[1024];
    va_list ap;
    int len;

    if (console_fd < 0) {
        return;
    }

    va_start(ap, fmt);
    len = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);

    if (len <= 0) {
        return;
    }
    if ((size_t)len >= sizeof(buf)) {
        len = (int)sizeof(buf) - 1;
    }
    write_all(console_fd, buf, (size_t)len);
}

int a90_console_write(const void *buf, size_t len) {
    if (console_fd < 0) {
        errno = ENODEV;
        return -1;
    }
    return write_all_checked(console_fd, (const char *)buf, len);
}

static void consume_escape_sequence(void) {
    int index;

    for (index = 0; index < 8; ++index) {
        struct pollfd pfd;
        char ch;

        pfd.fd = STDIN_FILENO;
        pfd.events = POLLIN;
        pfd.revents = 0;

        if (poll(&pfd, 1, 20) <= 0 || (pfd.revents & POLLIN) == 0) {
            return;
        }

        if (read(STDIN_FILENO, &ch, 1) != 1) {
            return;
        }

        if (index == 0 && ch != '[' && ch != 'O') {
            return;
        }
        if (index > 0 && ch >= 0x40 && ch <= 0x7e) {
            return;
        }
    }
}

static void drain_console_cancel_tail(void) {
    int index;

    for (index = 0; index < 32; ++index) {
        struct pollfd pfd;
        char ch;

        pfd.fd = STDIN_FILENO;
        pfd.events = POLLIN;
        pfd.revents = 0;

        if (poll(&pfd, 1, 10) <= 0 || (pfd.revents & POLLIN) == 0) {
            return;
        }
        if (read(STDIN_FILENO, &ch, 1) != 1) {
            return;
        }
        if (ch == '\r' || ch == '\n') {
            return;
        }
    }
}

static enum a90_cancel_kind classify_console_cancel_char(char ch) {
    if (ch == 0x03) {
        return CANCEL_HARD;
    }
    if (ch == 'q' || ch == 'Q') {
        drain_console_cancel_tail();
        return CANCEL_SOFT;
    }
    if (ch == 0x1b) {
        consume_escape_sequence();
    }
    return CANCEL_NONE;
}

enum a90_cancel_kind a90_console_read_cancel_event(void) {
    char ch;
    ssize_t rd = read(STDIN_FILENO, &ch, 1);

    if (rd != 1) {
        return CANCEL_NONE;
    }
    return classify_console_cancel_char(ch);
}

enum a90_cancel_kind a90_console_poll_cancel(int timeout_ms) {
    struct pollfd pfd;

    pfd.fd = STDIN_FILENO;
    pfd.events = POLLIN;
    pfd.revents = 0;

    if (poll(&pfd, 1, timeout_ms) <= 0 || (pfd.revents & POLLIN) == 0) {
        return CANCEL_NONE;
    }

    return a90_console_read_cancel_event();
}

int a90_console_cancelled(const char *tag, enum a90_cancel_kind cancel) {
    if (cancel == CANCEL_NONE) {
        return 0;
    }
    if (cancel == CANCEL_HARD) {
        a90_console_printf("%s: cancelled by Ctrl-C\r\n", tag);
        a90_logf("cancel", "%s hard Ctrl-C", tag);
    } else {
        a90_console_printf("%s: cancelled by q\r\n", tag);
        a90_logf("cancel", "%s soft q", tag);
    }
    return -ECANCELED;
}

static int ensure_tty_node(void) {
    char devbuf[32];
    unsigned int major_num;
    unsigned int minor_num;

    if (access("/dev/ttyGS0", F_OK) == 0) {
        return 0;
    }
    if (read_text_file("/sys/class/tty/ttyGS0/dev", devbuf, sizeof(devbuf)) < 0) {
        return -1;
    }
    if (sscanf(devbuf, "%u:%u", &major_num, &minor_num) != 2) {
        errno = EINVAL;
        return -1;
    }
    if (mknod("/dev/ttyGS0", S_IFCHR | 0600, makedev(major_num, minor_num)) == 0 ||
        errno == EEXIST) {
        return 0;
    }
    return -1;
}

int a90_console_wait_tty(void) {
    int attempt;

    for (attempt = 0; attempt < 50; ++attempt) {
        if (access("/dev/ttyGS0", F_OK) == 0) {
            return 0;
        }
        if (access("/sys/class/tty/ttyGS0/dev", R_OK) == 0 && ensure_tty_node() == 0) {
            return 0;
        }
        usleep(200000);
    }

    errno = ENOENT;
    return -1;
}

int a90_console_attach(void) {
    int fd;
    struct termios tio;

    fd = open("/dev/ttyGS0", O_RDWR | O_NOCTTY);
    if (fd < 0) {
        return -1;
    }

    if (tcgetattr(fd, &tio) == 0) {
        tio.c_iflag = IGNBRK;
        tio.c_oflag = 0;
        tio.c_cflag &= ~(CSIZE | PARENB | CSTOPB | CRTSCTS);
        tio.c_cflag |= CS8 | CREAD | CLOCAL;
        tio.c_lflag = 0;
        tio.c_cc[VMIN] = 1;
        tio.c_cc[VTIME] = 0;
        cfsetispeed(&tio, B115200);
        cfsetospeed(&tio, B115200);
        tcsetattr(fd, TCSANOW, &tio);
        tcflush(fd, TCIOFLUSH);
    }

    console_fd = fd;
    return a90_console_dup_stdio();
}

int a90_console_dup_stdio(void) {
    if (console_fd < 0) {
        errno = ENODEV;
        return -1;
    }
    if (dup2(console_fd, STDIN_FILENO) < 0 ||
        dup2(console_fd, STDOUT_FILENO) < 0 ||
        dup2(console_fd, STDERR_FILENO) < 0) {
        return -1;
    }
    return 0;
}

void a90_console_drain_input(unsigned int quiet_ms, unsigned int max_ms) {
    long started_ms = monotonic_millis();
    long quiet_started_ms = started_ms;

    while (1) {
        struct pollfd pfd;
        long now_ms = monotonic_millis();
        char ch;

        if (now_ms - started_ms >= (long)max_ms) {
            return;
        }
        if (now_ms - quiet_started_ms >= (long)quiet_ms) {
            return;
        }

        pfd.fd = STDIN_FILENO;
        pfd.events = POLLIN;
        pfd.revents = 0;

        if (poll(&pfd, 1, 20) <= 0 || (pfd.revents & POLLIN) == 0) {
            continue;
        }

        if (read(STDIN_FILENO, &ch, 1) == 1) {
            quiet_started_ms = monotonic_millis();
        }
    }
}

int a90_console_reattach(const char *reason, bool announce) {
    int old_fd = console_fd;
    long now_ms = monotonic_millis();
    bool quiet_success = (strcmp(reason, "idle-timeout") == 0);

    if (now_ms > 0 &&
        last_console_reattach_ms > 0 &&
        now_ms - last_console_reattach_ms < 500) {
        return 0;
    }
    last_console_reattach_ms = now_ms;

    if (!quiet_success) {
        a90_logf("console", "reattach requested reason=%s old_fd=%d",
                 reason, old_fd);
        console_klogf("<6>A90%s: console reattach requested reason=%s old_fd=%d\n",
                      INIT_BUILD, reason, old_fd);
    }

    if (old_fd >= 0) {
        close(old_fd);
    }
    console_fd = -1;

    if (a90_console_wait_tty() < 0) {
        int saved_errno = errno;
        a90_logf("console", "reattach wait failed reason=%s errno=%d error=%s",
                 reason, saved_errno, strerror(saved_errno));
        console_klogf("<6>A90%s: console reattach wait failed (%d)\n", INIT_BUILD, saved_errno);
        errno = saved_errno;
        return -1;
    }

    if (a90_console_attach() < 0) {
        int saved_errno = errno;
        a90_logf("console", "reattach open failed reason=%s errno=%d error=%s",
                 reason, saved_errno, strerror(saved_errno));
        console_klogf("<6>A90%s: console reattach open failed (%d)\n", INIT_BUILD, saved_errno);
        errno = saved_errno;
        return -1;
    }

    a90_console_drain_input(50, 200);
    if (!quiet_success) {
        a90_logf("console", "reattach ok reason=%s fd=%d", reason, console_fd);
        console_klogf("<6>A90%s: console reattached reason=%s fd=%d\n", INIT_BUILD, reason, console_fd);
    }
    if (announce) {
        a90_console_printf("\r\n# serial console reattached: %s\r\n", reason);
    }
    return 0;
}

ssize_t a90_console_readline(char *buf, size_t buf_size) {
    static char pending_newline = '\0';
    static long last_idle_reattach_ms = 0;
    size_t pos = 0;

    while (pos + 1 < buf_size) {
        struct pollfd pfd;
        int poll_rc;
        char ch;
        ssize_t rd;

        pfd.fd = STDIN_FILENO;
        pfd.events = POLLIN | POLLHUP | POLLERR | POLLNVAL;
        pfd.revents = 0;

        poll_rc = poll(&pfd, 1, CONSOLE_POLL_TIMEOUT_MS);
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (poll_rc == 0) {
            long now_ms = monotonic_millis();

            if (now_ms > 0 &&
                now_ms - last_idle_reattach_ms >= CONSOLE_IDLE_REATTACH_MS) {
                last_idle_reattach_ms = now_ms;
                if (a90_console_reattach("idle-timeout", false) == 0) {
                    pending_newline = '\0';
                }
            }
            continue;
        }

        if ((pfd.revents & (POLLHUP | POLLERR | POLLNVAL)) != 0) {
            if (a90_console_reattach("poll-fault", true) < 0) {
                return -1;
            }
            pending_newline = '\0';
            continue;
        }
        if ((pfd.revents & POLLIN) == 0) {
            continue;
        }

        rd = read(STDIN_FILENO, &ch, 1);

        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            if (a90_console_reattach("read-error", true) == 0) {
                pending_newline = '\0';
                continue;
            }
            return -1;
        }
        if (rd == 0) {
            if (a90_console_reattach("read-eof", true) == 0) {
                pending_newline = '\0';
            }
            continue;
        }

        if (pending_newline != '\0' && ch == pending_newline) {
            pending_newline = '\0';
            continue;
        }
        pending_newline = '\0';

        if (ch == '\r' || ch == '\n') {
            pending_newline = (ch == '\r') ? '\n' : '\r';
            a90_console_write("\r\n", 2);
            break;
        }

        if (ch == 0x7f || ch == 0x08) {
            if (pos > 0) {
                pos--;
                a90_console_write("\b \b", 3);
            }
            continue;
        }

        if (ch == 0x03) {
            a90_console_write("^C\r\n", 4);
            pos = 0;
            break;
        }

        if (ch == 0x15) {
            while (pos > 0) {
                --pos;
                a90_console_write("\b \b", 3);
            }
            continue;
        }

        if (ch == 0x1b) {
            consume_escape_sequence();
            continue;
        }

        if ((unsigned char)ch < 0x20) {
            continue;
        }

        buf[pos++] = ch;
        a90_console_write(&ch, 1);
    }

    buf[pos] = '\0';
    return (ssize_t)pos;
}
