#define _DEFAULT_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#define O3_MAGIC "S2O0"
#define O3_VERSION 1U
#define O3_REQUEST 1U
#define O3_RESPONSE 2U
#define O3_HEADER_SIZE 16U
#define O3_MAX_PAYLOAD 1024U
#define O3_STATUS_QUERY "O3 STATUS"
#define O3_STATUS_QUERY_LEN 9U
#define O3_MARKER "S22_O3_CONTROL"

static volatile sig_atomic_t g_stop;

static void on_signal(int signum) {
    (void)signum;
    g_stop = 1;
}

static uint16_t load_le16(const uint8_t *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint32_t load_le32(const uint8_t *p) {
    return (uint32_t)p[0] |
           ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static void store_le16(uint8_t *p, uint16_t value) {
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
}

static void store_le32(uint8_t *p, uint32_t value) {
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
    p[2] = (uint8_t)(value >> 16);
    p[3] = (uint8_t)(value >> 24);
}

static uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t len) {
    size_t index;
    crc = ~crc;
    for (index = 0; index < len; ++index) {
        unsigned int bit;
        crc ^= data[index];
        for (bit = 0; bit < 8U; ++bit) {
            uint32_t mask = (uint32_t)-(int32_t)(crc & 1U);
            crc = (crc >> 1) ^ (0xedb88320U & mask);
        }
    }
    return ~crc;
}

static uint32_t frame_crc(const uint8_t header[O3_HEADER_SIZE], const uint8_t *payload, size_t len) {
    uint32_t crc = crc32_update(0U, header, 12U);
    return crc32_update(crc, payload, len);
}

static int64_t monotonic_ms(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
        return 0;
    }
    return (int64_t)ts.tv_sec * 1000LL + (int64_t)ts.tv_nsec / 1000000LL;
}

static int wait_fd(int fd, short events, int timeout_ms) {
    struct pollfd pfd = {.fd = fd, .events = events, .revents = 0};
    int rc;
    do {
        rc = poll(&pfd, 1, timeout_ms);
    } while (rc < 0 && errno == EINTR && !g_stop);
    if (rc <= 0) {
        return rc;
    }
    if ((pfd.revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
        return -1;
    }
    return (pfd.revents & events) != 0 ? 1 : 0;
}

static int read_exact(int fd, uint8_t *buf, size_t len, int timeout_ms) {
    size_t done = 0;
    int64_t deadline = monotonic_ms() + timeout_ms;
    while (done < len && !g_stop) {
        int64_t remaining = deadline - monotonic_ms();
        int ready;
        ssize_t rc;
        if (remaining <= 0) {
            return 0;
        }
        ready = wait_fd(fd, POLLIN, (int)remaining);
        if (ready <= 0) {
            return ready;
        }
        rc = read(fd, buf + done, len - done);
        if (rc > 0) {
            done += (size_t)rc;
            continue;
        }
        if (rc < 0 && (errno == EINTR || errno == EAGAIN)) {
            continue;
        }
        return -1;
    }
    return done == len ? 1 : -1;
}

static int write_all(int fd, const uint8_t *buf, size_t len, int timeout_ms) {
    size_t done = 0;
    int64_t deadline = monotonic_ms() + timeout_ms;
    while (done < len && !g_stop) {
        int64_t remaining = deadline - monotonic_ms();
        int ready;
        ssize_t rc;
        if (remaining <= 0) {
            return 0;
        }
        ready = wait_fd(fd, POLLOUT, (int)remaining);
        if (ready <= 0) {
            return ready;
        }
        rc = write(fd, buf + done, len - done);
        if (rc > 0) {
            done += (size_t)rc;
            continue;
        }
        if (rc < 0 && (errno == EINTR || errno == EAGAIN)) {
            continue;
        }
        return -1;
    }
    return done == len ? 1 : -1;
}

static int open_tty(const char *path, int flush_input, struct termios *saved, int *have_saved) {
    struct termios tio;
    int fd = open(path, O_RDWR | O_NOCTTY | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    if (tcgetattr(fd, saved) != 0) {
        close(fd);
        return -1;
    }
    *have_saved = 1;
    tio = *saved;
    cfmakeraw(&tio);
    tio.c_cflag |= CLOCAL | CREAD;
    tio.c_cc[VMIN] = 0;
    tio.c_cc[VTIME] = 0;
    if (tcsetattr(fd, TCSANOW, &tio) != 0) {
        close(fd);
        *have_saved = 0;
        return -1;
    }
    if (flush_input) {
        (void)tcflush(fd, TCIOFLUSH);
    }
    return fd;
}

static void close_tty(int fd, const struct termios *saved, int have_saved) {
    if (have_saved) {
        (void)tcsetattr(fd, TCSANOW, saved);
    }
    (void)close(fd);
}

static int parse_uint(const char *text, unsigned int *out) {
    char *end = NULL;
    unsigned long value;
    errno = 0;
    value = strtoul(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value > 0xffffffffUL) {
        return -1;
    }
    *out = (unsigned int)value;
    return 0;
}

static void write_best_effort_path(const char *path, const char *text) {
    size_t length = strlen(text);
    size_t offset = 0;
    int fd = open(path, O_WRONLY | O_CLOEXEC | O_NONBLOCK);
    if (fd < 0) {
        return;
    }
    while (offset < length) {
        ssize_t amount = write(fd, text + offset, length - offset);
        if (amount > 0) {
            offset += (size_t)amount;
            continue;
        }
        if (amount < 0 && errno == EINTR) {
            continue;
        }
        break;
    }
    (void)close(fd);
}

static void emit_retained(const char *text) {
    write_best_effort_path("/dev/kmsg", text);
    write_best_effort_path("/dev/pmsg0", text);
    fputs(text, stderr);
}

static void append_status(const char *path, const char *text) {
    int fd = open(path, O_WRONLY | O_APPEND | O_CLOEXEC);
    if (fd >= 0) {
        size_t length = strlen(text);
        size_t offset = 0;
        while (offset < length) {
            ssize_t amount = write(fd, text + offset, length - offset);
            if (amount > 0) {
                offset += (size_t)amount;
                continue;
            }
            if (amount < 0 && errno == EINTR) {
                continue;
            }
            break;
        }
        (void)fsync(fd);
        (void)close(fd);
    }
}

static size_t read_status(const char *path, uint8_t *payload, size_t size) {
    ssize_t amount;
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        const char fallback[] = "result=status-open-fail\n";
        memcpy(payload, fallback, sizeof(fallback) - 1);
        return sizeof(fallback) - 1;
    }
    do {
        amount = read(fd, payload, size);
    } while (amount < 0 && errno == EINTR);
    (void)close(fd);
    if (amount <= 0) {
        const char fallback[] = "result=status-read-fail\n";
        memcpy(payload, fallback, sizeof(fallback) - 1);
        return sizeof(fallback) - 1;
    }
    return (size_t)amount;
}

__attribute__((noreturn)) static void park_forever(void) {
    struct timespec delay = {.tv_sec = 10, .tv_nsec = 0};
    for (;;) {
        (void)nanosleep(&delay, NULL);
    }
}

static void usage(const char *argv0) {
    fprintf(
        stderr,
        "usage: %s --device PATH --status-file PATH --max-requests N --idle-timeout-ms N\n",
        argv0
    );
}

int main(int argc, char **argv) {
    const char *device = NULL;
    const char *status_file = NULL;
    unsigned int max_requests = 0;
    unsigned int idle_timeout_ms = 0;
    unsigned int handled = 0;
    unsigned int status_queries = 0;
    unsigned int invalid = 0;
    unsigned int crc_errors = 0;
    unsigned int seq_errors = 0;
    unsigned int io_reopens = 0;
    uint32_t expected_seq = 0;
    int have_seq = 0;
    int first_open = 1;
    int protocol_recorded = 0;
    int64_t last_activity;
    int index;

    for (index = 1; index < argc; ++index) {
        if (strcmp(argv[index], "--device") == 0 && index + 1 < argc) {
            device = argv[++index];
        } else if (strcmp(argv[index], "--status-file") == 0 && index + 1 < argc) {
            status_file = argv[++index];
        } else if (strcmp(argv[index], "--max-requests") == 0 && index + 1 < argc) {
            if (parse_uint(argv[++index], &max_requests) != 0) {
                usage(argv[0]);
                return 2;
            }
        } else if (strcmp(argv[index], "--idle-timeout-ms") == 0 && index + 1 < argc) {
            if (parse_uint(argv[++index], &idle_timeout_ms) != 0) {
                usage(argv[0]);
                return 2;
            }
        } else {
            usage(argv[0]);
            return 2;
        }
    }
    if (device == NULL || status_file == NULL || max_requests == 0 || idle_timeout_ms < 1000U) {
        usage(argv[0]);
        return 2;
    }

    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);
    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);
    signal(SIGHUP, SIG_IGN);
    last_activity = monotonic_ms();
    append_status(status_file, "control_daemon=running\nprotocol=O0-compatible-with-O3-STATUS\n");
    emit_retained(O3_MARKER " phase=ready\n");

    while (!g_stop) {
        struct termios saved;
        int have_saved = 0;
        int fd;
        if (!protocol_recorded && (uint64_t)(monotonic_ms() - last_activity) >= idle_timeout_ms) {
            append_status(status_file, "protocol_result=timeout\n");
            emit_retained(O3_MARKER " phase=protocol_timeout\n");
            park_forever();
        }
        fd = open_tty(device, first_open, &saved, &have_saved);
        first_open = 0;
        if (fd < 0) {
            ++io_reopens;
            usleep(50000U);
            continue;
        }
        while (!g_stop) {
            uint8_t header[O3_HEADER_SIZE];
            uint8_t payload[O3_MAX_PAYLOAD];
            uint8_t response[O3_MAX_PAYLOAD];
            uint16_t payload_len;
            uint16_t response_len;
            uint32_t seq;
            uint32_t received_crc;
            int rc = read_exact(fd, header, sizeof(header), 1000);
            if (rc == 0) {
                if (!protocol_recorded &&
                    (uint64_t)(monotonic_ms() - last_activity) >= idle_timeout_ms) {
                    break;
                }
                continue;
            }
            if (rc < 0) {
                ++io_reopens;
                break;
            }
            last_activity = monotonic_ms();
            payload_len = load_le16(&header[6]);
            seq = load_le32(&header[8]);
            received_crc = load_le32(&header[12]);
            if (memcmp(header, O3_MAGIC, 4) != 0 || header[4] != O3_VERSION ||
                header[5] != O3_REQUEST || payload_len > O3_MAX_PAYLOAD) {
                ++invalid;
                break;
            }
            rc = read_exact(fd, payload, payload_len, 2000);
            if (rc <= 0) {
                ++io_reopens;
                break;
            }
            if (frame_crc(header, payload, payload_len) != received_crc) {
                ++crc_errors;
                continue;
            }
            if (have_seq && seq != expected_seq) {
                ++seq_errors;
            }
            expected_seq = seq + 1U;
            have_seq = 1;

            if (payload_len == O3_STATUS_QUERY_LEN &&
                memcmp(payload, O3_STATUS_QUERY, O3_STATUS_QUERY_LEN) == 0) {
                response_len = (uint16_t)read_status(status_file, response, sizeof(response));
                ++status_queries;
            } else if (handled < max_requests) {
                memcpy(response, payload, payload_len);
                response_len = payload_len;
                ++handled;
            } else {
                const char limit[] = "result=echo-limit\n";
                memcpy(response, limit, sizeof(limit) - 1);
                response_len = (uint16_t)(sizeof(limit) - 1);
                ++invalid;
            }

            header[5] = O3_RESPONSE;
            store_le16(&header[6], response_len);
            store_le32(&header[8], seq);
            store_le32(&header[12], 0U);
            store_le32(&header[12], frame_crc(header, response, response_len));
            if (write_all(fd, header, sizeof(header), 2000) <= 0 ||
                write_all(fd, response, response_len, 2000) <= 0) {
                ++io_reopens;
                break;
            }
            last_activity = monotonic_ms();

            if (!protocol_recorded && handled == max_requests) {
                char result[256];
                const char *verdict = invalid == 0 && crc_errors == 0 && seq_errors == 0 ? "pass" : "fail";
                (void)snprintf(
                    result,
                    sizeof(result),
                    "protocol_result=%s\nprotocol_handled=%u\nprotocol_invalid=%u\n"
                    "protocol_crc_errors=%u\nprotocol_seq_errors=%u\nprotocol_io_reopens=%u\n",
                    verdict,
                    handled,
                    invalid,
                    crc_errors,
                    seq_errors,
                    io_reopens
                );
                append_status(status_file, result);
                emit_retained(
                    invalid == 0 && crc_errors == 0 && seq_errors == 0
                        ? O3_MARKER " phase=protocol_pass\n"
                        : O3_MARKER " phase=protocol_fail\n"
                );
                protocol_recorded = 1;
            }
        }
        close_tty(fd, &saved, have_saved);
    }

    append_status(status_file, "control_signal_stop=1\n");
    emit_retained(O3_MARKER " phase=signal_park\n");
    (void)status_queries;
    park_forever();
}
