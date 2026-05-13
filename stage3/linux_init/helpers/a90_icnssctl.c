#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define ICNSSCTL_VERSION "a90_icnssctl v1"
#define ICNSS_DEVICE_ID "18800000.qcom,icnss"
#define ICNSS_BIND_PATH "/sys/bus/platform/drivers/icnss/bind"
#define ICNSS_UNBIND_PATH "/sys/bus/platform/drivers/icnss/unbind"
#define ICNSS_UEVENT_PATH "/sys/devices/platform/soc/18800000.qcom,icnss/uevent"

static int write_all(int fd, const char *buf, size_t len) {
    size_t off = 0;

    while (off < len) {
        ssize_t nwritten = write(fd, buf + off, len - off);

        if (nwritten < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (nwritten == 0) {
            errno = EIO;
            return -1;
        }
        off += (size_t)nwritten;
    }
    return 0;
}

static int write_fixed(const char *target) {
    int fd;

    fd = open(target, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        perror("open icnss control");
        return 1;
    }
    if (write_all(fd, ICNSS_DEVICE_ID, strlen(ICNSS_DEVICE_ID)) < 0) {
        perror("write icnss control");
        close(fd);
        return 1;
    }
    if (close(fd) < 0) {
        perror("close icnss control");
        return 1;
    }
    return 0;
}

static int cat_file(const char *path) {
    char buf[4096];
    ssize_t nread;
    int fd;

    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        perror("open status");
        return 1;
    }
    while ((nread = read(fd, buf, sizeof(buf))) > 0) {
        if (write_all(STDOUT_FILENO, buf, (size_t)nread) < 0) {
            perror("write status");
            close(fd);
            return 1;
        }
    }
    if (nread < 0) {
        perror("read status");
        close(fd);
        return 1;
    }
    close(fd);
    return 0;
}

static void usage(FILE *out) {
    fprintf(out, "%s\n", ICNSSCTL_VERSION);
    fprintf(out, "usage: a90_icnssctl status|unbind|bind\n");
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "status") == 0) {
        return cat_file(ICNSS_UEVENT_PATH);
    }
    if (argc == 2 && strcmp(argv[1], "unbind") == 0) {
        return write_fixed(ICNSS_UNBIND_PATH);
    }
    if (argc == 2 && strcmp(argv[1], "bind") == 0) {
        return write_fixed(ICNSS_BIND_PATH);
    }
    usage(argc == 1 ? stdout : stderr);
    return argc == 1 ? 0 : 2;
}
