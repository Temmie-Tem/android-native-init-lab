/*
 * D-public HUD intent producer.
 *
 * This helper is designed to run as non-root a90hud.  It writes a small,
 * bounded JSON intent file for a separate native/root-owned presenter.  It does
 * not open DRM, does not perform KMS operations, and does not open network
 * sockets.
 */
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

#define DEFAULT_INTENT_PATH "/run/a90-dpublic/hud-intent.json"
#define MAX_INTENT_BYTES 4096U

static void usage(const char *argv0) {
    fprintf(stderr, "usage: %s [--output PATH] [--sequence N]\n", argv0);
}

static int write_all(int fd, const char *buf, size_t len) {
    size_t off = 0;
    while (off < len) {
        ssize_t written = write(fd, buf + off, len - off);
        if (written < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (written == 0) {
            errno = EIO;
            return -1;
        }
        off += (size_t)written;
    }
    return 0;
}

static int parent_dir(const char *path, char *out, size_t out_size) {
    const char *slash = strrchr(path, '/');
    size_t len;
    if (slash == NULL) {
        if (out_size < 2) {
            errno = ENAMETOOLONG;
            return -1;
        }
        strcpy(out, ".");
        return 0;
    }
    len = (size_t)(slash - path);
    if (len == 0) {
        len = 1;
    }
    if (len + 1 > out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    memcpy(out, path, len);
    out[len] = '\0';
    return 0;
}

static int ensure_parent_dir(const char *path) {
    char dir[PATH_MAX];
    if (parent_dir(path, dir, sizeof(dir)) < 0) {
        return -1;
    }
    if (strcmp(dir, ".") == 0 || strcmp(dir, "/") == 0) {
        return 0;
    }
    if (mkdir(dir, 0755) < 0 && errno != EEXIST) {
        return -1;
    }
    return 0;
}

static int fsync_parent_dir(const char *path) {
    char dir[PATH_MAX];
    int fd;
    int rc;
    if (parent_dir(path, dir, sizeof(dir)) < 0) {
        return -1;
    }
    fd = open(dir, O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    rc = fsync(fd);
    close(fd);
    return rc;
}

static uint64_t monotonic_ms(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0) {
        return 0;
    }
    return (uint64_t)ts.tv_sec * 1000ULL + (uint64_t)ts.tv_nsec / 1000000ULL;
}

static int parse_u64(const char *text, uint64_t *out) {
    char *end = NULL;
    unsigned long long value;
    errno = 0;
    value = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0') {
        return -1;
    }
    *out = (uint64_t)value;
    return 0;
}

static int write_atomic(const char *path, const char *json, size_t json_len) {
    char tmp[PATH_MAX];
    int fd;
    if (json_len == 0 || json_len > MAX_INTENT_BYTES) {
        errno = E2BIG;
        return -1;
    }
    if (ensure_parent_dir(path) < 0) {
        return -1;
    }
    if (snprintf(tmp, sizeof(tmp), "%s.tmp.%ld", path, (long)getpid()) >= (int)sizeof(tmp)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    fd = open(tmp, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0640);
    if (fd < 0) {
        return -1;
    }
    if (write_all(fd, json, json_len) < 0 || fchmod(fd, 0640) < 0 || fsync(fd) < 0) {
        int saved = errno;
        close(fd);
        unlink(tmp);
        errno = saved;
        return -1;
    }
    if (close(fd) < 0) {
        int saved = errno;
        unlink(tmp);
        errno = saved;
        return -1;
    }
    if (rename(tmp, path) < 0) {
        int saved = errno;
        unlink(tmp);
        errno = saved;
        return -1;
    }
    if (fsync_parent_dir(path) < 0) {
        return -1;
    }
    return 0;
}

int main(int argc, char **argv) {
    const char *output = DEFAULT_INTENT_PATH;
    uint64_t sequence = 1;
    uint64_t now_ms;
    char json[MAX_INTENT_BYTES];
    int len;
    int i;

    for (i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--output") == 0 && i + 1 < argc) {
            output = argv[++i];
        } else if (strcmp(argv[i], "--sequence") == 0 && i + 1 < argc) {
            if (parse_u64(argv[++i], &sequence) < 0 || sequence == 0) {
                fprintf(stderr, "invalid sequence\n");
                return 2;
            }
        } else {
            usage(argv[0]);
            return 2;
        }
    }

    now_ms = monotonic_ms();
    len = snprintf(json,
                   sizeof(json),
                   "{\"schema\":\"a90-dpublic-hud-intent-v1\","
                   "\"sequence\":%llu,"
                   "\"monotonic_ms\":%llu,"
                   "\"title\":\"A90 SERVER\","
                   "\"public_state\":\"PUBLIC_OFF\","
                   "\"upstream_state\":\"UNKNOWN\","
                   "\"service_state\":\"READY\","
                   "\"packet_filter_state\":\"READY\","
                   "\"lines\":[\"DPUBLIC DEFAULT OFF\","
                   "\"A90HUD INTENT PRODUCER\","
                   "\"NATIVE PRESENTER OWNS KMS\"]}\n",
                   (unsigned long long)sequence,
                   (unsigned long long)now_ms);
    if (len <= 0 || (size_t)len >= sizeof(json)) {
        fprintf(stderr, "intent too large\n");
        return 1;
    }
    if (write_atomic(output, json, (size_t)len) < 0) {
        perror("write intent");
        return 1;
    }
    printf("A90WSTA132_INTENT_WRITTEN=1\n");
    printf("A90WSTA132_INTENT_OUTPUT=%s\n", output);
    printf("A90WSTA132_INTENT_SEQUENCE=%llu\n", (unsigned long long)sequence);
    printf("A90WSTA132_INTENT_BYTES=%d\n", len);
    printf("A90WSTA132_SECRET_VALUES_LOGGED=0\n");
    return 0;
}
