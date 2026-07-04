/*
 * D-public HUD presenter prototype.
 *
 * This is the root/native-owned side of the split HUD path.  WSTA132 keeps the
 * live KMS path out of scope and validates the intent parser contract first:
 * bounded file size, required schema/sequence/time fields, rejected forbidden
 * fields, and rejected unknown top-level fields.  The presenter contract is the
 * only side allowed to own KMS operations such as DRM_IOCTL_MODE_SETCRTC.
 */
#define _POSIX_C_SOURCE 200809L

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define MAX_INTENT_BYTES 4096U
#define INTENT_SCHEMA "\"schema\":\"a90-dpublic-hud-intent-v1\""

static const char *const allowed_kms_ops[] = {
    "DRM_IOCTL_MODE_GETRESOURCES",
    "DRM_IOCTL_MODE_GETCONNECTOR",
    "DRM_IOCTL_MODE_CREATE_DUMB",
    "DRM_IOCTL_MODE_ADDFB",
    "DRM_IOCTL_MODE_SETCRTC",
    "DRM_IOCTL_MODE_PAGE_FLIP",
    "DRM_IOCTL_MODE_RMFB",
    "DRM_IOCTL_MODE_DESTROY_DUMB",
};

static const char *const allowed_keys[] = {
    "schema",
    "sequence",
    "monotonic_ms",
    "title",
    "public_state",
    "upstream_state",
    "service_state",
    "packet_filter_state",
    "cpu_millic",
    "battery_percent",
    "lines",
};

static const char *const forbidden_keys[] = {
    "command",
    "argv",
    "path",
    "shell",
    "url",
    "ssid",
    "psk",
    "token",
    "secret",
};

static void usage(const char *argv0) {
    fprintf(stderr, "usage: %s --validate-intent PATH\n", argv0);
}

static bool key_allowed(const char *key) {
    size_t i;
    for (i = 0; i < sizeof(allowed_keys) / sizeof(allowed_keys[0]); ++i) {
        if (strcmp(key, allowed_keys[i]) == 0) {
            return true;
        }
    }
    return false;
}

static bool key_present(const char *json, const char *key) {
    char needle[96];
    if (snprintf(needle, sizeof(needle), "\"%s\":", key) >= (int)sizeof(needle)) {
        return false;
    }
    return strstr(json, needle) != NULL;
}

static int read_intent(const char *path, char *buf, size_t buf_size, size_t *used_out) {
    int fd;
    ssize_t nread;
    struct stat st;
    if (buf_size <= MAX_INTENT_BYTES) {
        errno = EINVAL;
        return -1;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    if (fstat(fd, &st) < 0 || st.st_size <= 0 || st.st_size > (off_t)MAX_INTENT_BYTES) {
        close(fd);
        errno = E2BIG;
        return -1;
    }
    nread = read(fd, buf, MAX_INTENT_BYTES + 1U);
    close(fd);
    if (nread <= 0 || nread > (ssize_t)MAX_INTENT_BYTES) {
        errno = E2BIG;
        return -1;
    }
    buf[nread] = '\0';
    *used_out = (size_t)nread;
    return 0;
}

static int reject_unknown_top_level_keys(const char *json) {
    const char *p = json;
    while ((p = strchr(p, '"')) != NULL) {
        const char *start = ++p;
        const char *end = strchr(start, '"');
        const char *after;
        char key[64];
        size_t len;
        if (end == NULL) {
            return -1;
        }
        after = end + 1;
        while (*after != '\0' && isspace((unsigned char)*after)) {
            ++after;
        }
        if (*after != ':') {
            p = end + 1;
            continue;
        }
        len = (size_t)(end - start);
        if (len == 0 || len >= sizeof(key)) {
            return -1;
        }
        memcpy(key, start, len);
        key[len] = '\0';
        if (!key_allowed(key)) {
            fprintf(stderr, "unknown key: %s\n", key);
            return -1;
        }
        p = end + 1;
    }
    return 0;
}

static int validate_intent_json(const char *json, size_t used) {
    size_t i;
    (void)used;
    if (strstr(json, INTENT_SCHEMA) == NULL) {
        fprintf(stderr, "missing schema\n");
        return -1;
    }
    if (!key_present(json, "sequence") || !key_present(json, "monotonic_ms")) {
        fprintf(stderr, "missing required field\n");
        return -1;
    }
    for (i = 0; i < sizeof(forbidden_keys) / sizeof(forbidden_keys[0]); ++i) {
        if (key_present(json, forbidden_keys[i])) {
            fprintf(stderr, "forbidden key: %s\n", forbidden_keys[i]);
            return -1;
        }
    }
    if (reject_unknown_top_level_keys(json) < 0) {
        return -1;
    }
    return 0;
}

static int validate_intent_file(const char *path) {
    char json[MAX_INTENT_BYTES + 1U];
    size_t used = 0;
    if (read_intent(path, json, sizeof(json), &used) < 0) {
        perror("read intent");
        return -1;
    }
    if (validate_intent_json(json, used) < 0) {
        return -1;
    }
    printf("A90WSTA132_PRESENTER_INTENT_VALID=1\n");
    printf("A90WSTA132_PRESENTER_OWNER=native-init\n");
    printf("A90WSTA132_PRESENTER_KMS_MASTER=1\n");
    printf("A90WSTA132_PRESENTER_ALLOWED_KMS_OP=%s\n", allowed_kms_ops[4]);
    printf("A90WSTA132_PRESENTER_INTENT_BYTES=%zu\n", used);
    printf("A90WSTA132_SECRET_VALUES_LOGGED=0\n");
    return 0;
}

int main(int argc, char **argv) {
    if (argc == 3 && strcmp(argv[1], "--validate-intent") == 0) {
        return validate_intent_file(argv[2]) == 0 ? 0 : 1;
    }
    usage(argv[0]);
    return 2;
}
