#include "a90_auto_handoff.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "a90_benchmark.h"
#include "a90_config.h"
#include "a90_console.h"
#include "a90_log.h"
#include "a90_server_distro.h"
#include "a90_timeline.h"
#include "a90_util.h"

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#if A90_AUTO_HANDOFF_BENCHMARK_V1

#define A90_AUTO_HANDOFF_TOKEN "SERVER-DISTRO-D3B-SWITCHROOT"
#define A90_AUTO_HANDOFF_ARM_TOKEN "AUTO-HANDOFF-BENCHMARK-V1-ARM"
#define A90_AUTO_HANDOFF_SCHEMA "a90-auto-handoff-benchmark-v1"
#define A90_AUTO_HANDOFF_STATE_MAX 768U

static int a90_auto_handoff_hex64_valid(const char *value) {
    size_t index;

    if (value == NULL || strlen(value) != 64U) {
        return 0;
    }
    for (index = 0; index < 64U; ++index) {
        if (!((value[index] >= '0' && value[index] <= '9') ||
              (value[index] >= 'a' && value[index] <= 'f'))) {
            return 0;
        }
    }
    return 1;
}

static int a90_auto_handoff_binding_valid(void) {
    return strncmp(A90_AUTO_HANDOFF_IMAGE,
                   "/mnt/sdext/a90/runtime/",
                   strlen("/mnt/sdext/a90/runtime/")) == 0 &&
           a90_auto_handoff_hex64_valid(A90_AUTO_HANDOFF_IMAGE_SHA256);
}

static int a90_auto_handoff_state_path(const char *path) {
    struct stat st;

    if (lstat(path, &st) < 0) {
        return errno == ENOENT ? 0 : -errno;
    }
    if (!S_ISREG(st.st_mode) || S_ISLNK(st.st_mode) || st.st_uid != 0 ||
        st.st_nlink != 1 || (st.st_mode & 0777) != 0600) {
        return -EPERM;
    }
    return 1;
}

static int a90_auto_handoff_fsync_cache_dir(void) {
    int fd;
    int rc = 0;

    fd = open("/cache", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    if (fsync(fd) < 0) {
        rc = -errno;
    }
    if (close(fd) < 0 && rc == 0) {
        rc = -errno;
    }
    return rc;
}

static int a90_auto_handoff_create_state(const char *path,
                                         const char *content,
                                         size_t content_size) {
    int fd;
    int rc = 0;

    fd = open(path,
              O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return -errno;
    }
    if (fchown(fd, 0, 0) < 0 ||
        fchmod(fd, 0600) < 0 ||
        write_all_checked(fd, content, content_size) < 0 ||
        fsync(fd) < 0) {
        rc = errno != 0 ? -errno : -EIO;
    }
    if (close(fd) < 0 && rc == 0) {
        rc = -errno;
    }
    if (rc < 0) {
        (void)unlink(path);
        (void)a90_auto_handoff_fsync_cache_dir();
        return rc;
    }
    rc = a90_auto_handoff_fsync_cache_dir();
    if (rc < 0) {
        (void)unlink(path);
        (void)a90_auto_handoff_fsync_cache_dir();
        return rc;
    }
    return 0;
}

static int a90_auto_handoff_format_state(char *out,
                                         size_t out_size,
                                         const char *intent_sha256,
                                         const char *state) {
    int length;

    length = snprintf(out,
                      out_size,
                      "schema=%s\n"
                      "build=%s\n"
                      "image=%s\n"
                      "image_sha256=%s\n"
                      "intent_sha256=%s\n"
                      "state=%s\n",
                      A90_AUTO_HANDOFF_SCHEMA,
                      INIT_BUILD,
                      A90_AUTO_HANDOFF_IMAGE,
                      A90_AUTO_HANDOFF_IMAGE_SHA256,
                      intent_sha256,
                      state);
    if (length < 0 || (size_t)length >= out_size) {
        return -EOVERFLOW;
    }
    return length;
}

static int a90_auto_handoff_create_enable(const char *intent_sha256) {
    char content[A90_AUTO_HANDOFF_STATE_MAX];
    int length;

    length = a90_auto_handoff_format_state(content,
                                           sizeof(content),
                                           intent_sha256,
                                           "armed-after-native-health");
    if (length < 0) {
        return length;
    }
    return a90_auto_handoff_create_state(A90_AUTO_HANDOFF_ENABLE_PATH,
                                         content,
                                         (size_t)length);
}

static int a90_auto_handoff_create_latch(const char *intent_sha256) {
    char content[A90_AUTO_HANDOFF_STATE_MAX];
    int length;

    length = a90_auto_handoff_format_state(
        content,
        sizeof(content),
        intent_sha256,
        "automatic-handoff-dispatched-no-replay");
    if (length < 0) {
        return length;
    }
    return a90_auto_handoff_create_state(A90_AUTO_HANDOFF_LATCH_PATH,
                                         content,
                                         (size_t)length);
}

static int a90_auto_handoff_read_enable(char *intent_sha256,
                                        size_t intent_size) {
    struct stat before;
    struct stat opened;
    char content[A90_AUTO_HANDOFF_STATE_MAX];
    char expected[A90_AUTO_HANDOFF_STATE_MAX];
    const char *prefix = "intent_sha256=";
    char *intent;
    char *newline;
    ssize_t count;
    ssize_t extra;
    int expected_size;
    int fd;

    if (intent_sha256 == NULL || intent_size < 65U) {
        return -EINVAL;
    }
    if (lstat(A90_AUTO_HANDOFF_ENABLE_PATH, &before) < 0) {
        return errno == ENOENT ? 0 : -errno;
    }
    if (!S_ISREG(before.st_mode) || S_ISLNK(before.st_mode) || before.st_uid != 0 ||
        before.st_nlink != 1 || (before.st_mode & 0777) != 0600 ||
        before.st_size <= 0 || before.st_size >= (off_t)sizeof(content)) {
        return -EPERM;
    }
    fd = open(A90_AUTO_HANDOFF_ENABLE_PATH, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    if (fstat(fd, &opened) < 0 ||
        opened.st_dev != before.st_dev ||
        opened.st_ino != before.st_ino ||
        opened.st_size != before.st_size ||
        !S_ISREG(opened.st_mode)) {
        int saved_errno = errno != 0 ? errno : ESTALE;

        close(fd);
        return -saved_errno;
    }
    count = read(fd, content, sizeof(content) - 1U);
    if (count < 0) {
        int saved_errno = errno;

        close(fd);
        return -saved_errno;
    }
    extra = read(fd, content + count, 1U);
    if (close(fd) < 0 && extra == 0) {
        return -errno;
    }
    if (count != before.st_size || extra != 0) {
        return -EOVERFLOW;
    }
    content[count] = '\0';
    intent = strstr(content, prefix);
    if (intent == NULL) {
        return -EINVAL;
    }
    intent += strlen(prefix);
    newline = strchr(intent, '\n');
    if (newline == NULL || (size_t)(newline - intent) != 64U) {
        return -EINVAL;
    }
    memcpy(intent_sha256, intent, 64U);
    intent_sha256[64] = '\0';
    if (!a90_auto_handoff_hex64_valid(intent_sha256)) {
        return -EINVAL;
    }
    expected_size = a90_auto_handoff_format_state(expected,
                                                  sizeof(expected),
                                                  intent_sha256,
                                                  "armed-after-native-health");
    if (expected_size < 0 || strcmp(content, expected) != 0) {
        return -EINVAL;
    }
    return 1;
}

int a90_auto_handoff_status_cmd(char **argv, int argc) {
    char intent_sha256[65];
    int enable_state;
    int latch_state;

    if (argc != 1) {
        a90_console_printf("usage: auto-handoff-status\r\n");
        return -EINVAL;
    }
    (void)argv;
    enable_state = a90_auto_handoff_read_enable(intent_sha256, sizeof(intent_sha256));
    latch_state = a90_auto_handoff_state_path(A90_AUTO_HANDOFF_LATCH_PATH);
    a90_console_printf("A90AUTO_STATUS binding=%d enable=%d latch=%d build=%s\r\n",
                       a90_auto_handoff_binding_valid() ? 1 : 0,
                       enable_state,
                       latch_state,
                       INIT_BUILD);
    return enable_state < 0 ? enable_state : (latch_state < 0 ? latch_state : 0);
}

int a90_auto_handoff_arm_cmd(char **argv, int argc) {
    const char *intent_sha256;
    int enable_state;
    int latch_state;
    int rc;

    if (argc != 3 || strcmp(argv[1], A90_AUTO_HANDOFF_ARM_TOKEN) != 0) {
        a90_console_printf("usage: auto-handoff-arm %s <intent-sha256>\r\n",
                           A90_AUTO_HANDOFF_ARM_TOKEN);
        return -EPERM;
    }
    intent_sha256 = argv[2];
    if (!a90_auto_handoff_binding_valid() ||
        !a90_auto_handoff_hex64_valid(intent_sha256)) {
        return -EINVAL;
    }
    latch_state = a90_auto_handoff_state_path(A90_AUTO_HANDOFF_LATCH_PATH);
    if (latch_state != 0) {
        return latch_state > 0 ? -EALREADY : latch_state;
    }
    enable_state = a90_auto_handoff_state_path(A90_AUTO_HANDOFF_ENABLE_PATH);
    if (enable_state != 0) {
        return enable_state > 0 ? -EEXIST : enable_state;
    }
    rc = a90_auto_handoff_create_enable(intent_sha256);
    if (rc < 0) {
        a90_console_printf("A90AUTO_ARM armed=0 rc=%d\r\n", rc);
        return rc;
    }
    a90_console_printf("A90AUTO_ARM armed=1 intent_sha256=%s build=%s\r\n",
                       intent_sha256,
                       INIT_BUILD);
    a90_logf("auto-handoff", "armed after native health intent_sha256=%s",
             intent_sha256);
    a90_timeline_record(0,
                        0,
                        "auto-handoff-arm",
                        "durable enable created after native health");
    return 0;
}

int a90_auto_handoff_run_once(void) {
    char *argv[] = {
        (char *)"switch-root-to-distro",
        (char *)A90_AUTO_HANDOFF_TOKEN,
        (char *)A90_AUTO_HANDOFF_IMAGE,
        (char *)A90_AUTO_HANDOFF_IMAGE_SHA256,
        NULL,
    };
    char intent_sha256[65];
    int enable_state;
    int latch_state;
    int rc;

    a90_benchmark_mark("auto_handoff_check");
    if (!a90_auto_handoff_binding_valid()) {
        a90_console_printf("A90AUTO refused=invalid-compiled-binding\r\n");
        a90_logf("auto-handoff", "refused invalid compiled binding");
        a90_timeline_record(-EINVAL,
                            EINVAL,
                            "auto-handoff",
                            "invalid compiled binding");
        a90_benchmark_mark("auto_handoff_binding_refused");
        return -EINVAL;
    }
    latch_state = a90_auto_handoff_state_path(A90_AUTO_HANDOFF_LATCH_PATH);
    if (latch_state > 0) {
        a90_console_printf("A90AUTO state=latched-stay-native latch=%s\r\n",
                           A90_AUTO_HANDOFF_LATCH_PATH);
        a90_logf("auto-handoff", "latched stay native path=%s",
                 A90_AUTO_HANDOFF_LATCH_PATH);
        a90_timeline_record(0, 0, "auto-handoff", "latched stay native");
        a90_benchmark_mark("auto_handoff_latched_native");
        return 1;
    }
    if (latch_state < 0) {
        a90_console_printf("A90AUTO refused=latch-inspection rc=%d\r\n", latch_state);
        a90_logf("auto-handoff", "latch inspection failed rc=%d", latch_state);
        a90_timeline_record(latch_state,
                            -latch_state,
                            "auto-handoff",
                            "latch inspection failed");
        a90_benchmark_mark("auto_handoff_latch_refused");
        return latch_state;
    }
    enable_state = a90_auto_handoff_read_enable(intent_sha256, sizeof(intent_sha256));
    if (enable_state == 0) {
        a90_console_printf("A90AUTO state=unarmed-stay-native enable=%s\r\n",
                           A90_AUTO_HANDOFF_ENABLE_PATH);
        a90_logf(
            "auto-handoff",
            "A90AUTO state=unarmed-stay-native"
        );
        a90_timeline_record(0, 0, "auto-handoff", "unarmed stay native");
        a90_benchmark_mark("auto_handoff_unarmed_native");
        return 2;
    }
    if (enable_state < 0) {
        a90_console_printf("A90AUTO refused=enable-invalid rc=%d\r\n", enable_state);
        a90_logf("auto-handoff", "enable invalid rc=%d", enable_state);
        a90_timeline_record(enable_state,
                            -enable_state,
                            "auto-handoff",
                            "enable invalid");
        a90_benchmark_mark("auto_handoff_enable_refused");
        return enable_state;
    }
    rc = a90_auto_handoff_create_latch(intent_sha256);
    if (rc < 0) {
        a90_console_printf("A90AUTO refused=latch-create rc=%d\r\n", rc);
        a90_logf("auto-handoff", "latch create failed rc=%d", rc);
        a90_timeline_record(rc,
                            -rc,
                            "auto-handoff",
                            "durable latch create failed");
        a90_benchmark_mark("auto_handoff_latch_refused");
        return rc;
    }

    a90_console_printf("A90AUTO state=dispatch-once latch=%s image=%s\r\n",
                       A90_AUTO_HANDOFF_LATCH_PATH,
                       A90_AUTO_HANDOFF_IMAGE);
    a90_logf("auto-handoff", "dispatch once latch=%s image=%s",
             A90_AUTO_HANDOFF_LATCH_PATH,
             A90_AUTO_HANDOFF_IMAGE);
    a90_timeline_record(0,
                        0,
                        "auto-handoff",
                        "durable enable and latch exact; dispatch once");
    a90_benchmark_mark("auto_handoff_dispatched");
    rc = a90_server_distro_switch_root_cmd(argv, 4);

    a90_console_printf("A90AUTO state=handoff-returned-no-replay rc=%d\r\n", rc);
    a90_logf("auto-handoff", "handoff returned no replay rc=%d", rc);
    a90_timeline_record(rc,
                        rc < 0 ? -rc : EIO,
                        "auto-handoff",
                        "handoff returned; latch retained; no replay");
    a90_benchmark_emit("auto_handoff_returned_native");
    return rc < 0 ? rc : -EIO;
}

#else

int a90_auto_handoff_status_cmd(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return -ENOTSUP;
}

int a90_auto_handoff_arm_cmd(char **argv, int argc) {
    (void)argv;
    (void)argc;
    return -ENOTSUP;
}

int a90_auto_handoff_run_once(void) {
    return 0;
}

#endif
