#define _GNU_SOURCE

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define FWPATHCTL_VERSION "a90_fwpathctl v1"
#define FIRMWARE_CLASS_PATH "/sys/module/firmware_class/parameters/path"
#define MAX_FWPATH_LEN 255

static bool is_safe_path_value(const char *value) {
    size_t len;

    if (value == NULL || value[0] != '/') {
        return false;
    }
    len = strlen(value);
    if (len == 0 || len > MAX_FWPATH_LEN) {
        return false;
    }
    for (size_t i = 0; i < len; i++) {
        unsigned char ch = (unsigned char)value[i];

        if (isalnum(ch) || ch == '_' || ch == '.' || ch == '/' ||
            ch == '+' || ch == '-') {
            continue;
        }
        return false;
    }
    return true;
}

static int read_fwpath(void) {
    char buf[MAX_FWPATH_LEN + 2];
    ssize_t nread;
    int fd;

    fd = open(FIRMWARE_CLASS_PATH, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        perror("open read firmware_class.path");
        return 1;
    }
    nread = read(fd, buf, sizeof(buf) - 1);
    if (nread < 0) {
        perror("read firmware_class.path");
        close(fd);
        return 1;
    }
    close(fd);
    buf[nread] = '\0';
    fputs(buf, stdout);
    if (nread == 0 || buf[nread - 1] != '\n') {
        fputc('\n', stdout);
    }
    return 0;
}

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

static int write_fwpath(const char *value) {
    int fd;

    if (!is_safe_path_value(value)) {
        fprintf(stderr, "unsafe firmware path value\n");
        return 2;
    }
    fd = open(FIRMWARE_CLASS_PATH, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        perror("open write firmware_class.path");
        return 1;
    }
    if (write_all(fd, value, strlen(value)) < 0) {
        perror("write firmware_class.path");
        close(fd);
        return 1;
    }
    if (close(fd) < 0) {
        perror("close firmware_class.path");
        return 1;
    }
    return read_fwpath();
}

static void usage(FILE *out) {
    fprintf(out, "%s\n", FWPATHCTL_VERSION);
    fprintf(out, "usage: a90_fwpathctl read|write <absolute-path>\n");
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "read") == 0) {
        return read_fwpath();
    }
    if (argc == 3 && strcmp(argv[1], "write") == 0) {
        return write_fwpath(argv[2]);
    }
    usage(argc == 1 ? stdout : stderr);
    return argc == 1 ? 0 : 2;
}
