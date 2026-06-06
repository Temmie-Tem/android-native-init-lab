#include "a90_util.h"

#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

long monotonic_millis(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0) {
        return 0;
    }

    return (long)(ts.tv_sec * 1000L) + (long)(ts.tv_nsec / 1000000L);
}

int ensure_dir(const char *path, mode_t mode) {
    struct stat st;

    if (mkdir(path, mode) == 0) {
        return 0;
    }
    if (errno == EEXIST) {
        if (lstat(path, &st) == 0 && S_ISDIR(st.st_mode) && !S_ISLNK(st.st_mode)) {
            return 0;
        }
        errno = ENOTDIR;
    }
    return -1;
}

int negative_errno_or(int fallback_errno) {
    int saved_errno = errno;

    if (saved_errno == 0) {
        saved_errno = fallback_errno;
    }
    return -saved_errno;
}

int write_all_checked(int fd, const char *buf, size_t len) {
    while (len > 0) {
        ssize_t written = write(fd, buf, len);
        if (written <= 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        buf += written;
        len -= (size_t)written;
    }
    return 0;
}

void write_all(int fd, const char *buf, size_t len) {
    (void)write_all_checked(fd, buf, len);
}

int read_text_file(const char *path, char *buf, size_t buf_size) {
    int fd;
    ssize_t rd;

    if (buf_size == 0) {
        errno = EINVAL;
        return -1;
    }

    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }

    rd = read(fd, buf, buf_size - 1);
    close(fd);
    if (rd < 0) {
        return -1;
    }

    buf[rd] = '\0';
    return 0;
}

void trim_newline(char *buf) {
    size_t len = strlen(buf);

    while (len > 0 && (buf[len - 1] == '\n' || buf[len - 1] == '\r')) {
        buf[len - 1] = '\0';
        --len;
    }
}

void flatten_inline_text(char *buf) {
    size_t i;
    bool last_was_space = false;

    for (i = 0; buf[i] != '\0'; ++i) {
        if (buf[i] == '\r' || buf[i] == '\n' || buf[i] == '\t') {
            buf[i] = ' ';
        }

        if (buf[i] == ' ') {
            if (last_was_space) {
                buf[i] = '\a';
            } else {
                last_was_space = true;
            }
        } else {
            last_was_space = false;
        }
    }

    {
        size_t rd = 0;
        size_t wr = 0;

        while (buf[rd] != '\0') {
            if (buf[rd] != '\a') {
                buf[wr++] = buf[rd];
            }
            ++rd;
        }
        buf[wr] = '\0';
    }

    trim_newline(buf);
}

int read_trimmed_text_file(const char *path, char *buf, size_t buf_size) {
    if (read_text_file(path, buf, buf_size) < 0) {
        return -1;
    }
    trim_newline(buf);
    return 0;
}
