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

/*
 * Debian's durable evidence record. It sits beside the rootfs image on the
 * shared medium and never inside it: the work-copy replacement makes the
 * rootfs read-only, and a record inside the image would go read-only with it,
 * killing the instrument exactly when that change most needs grading.
 */
#ifndef A90_AUTO_HANDOFF_EVIDENCE_PATH
#define A90_AUTO_HANDOFF_EVIDENCE_PATH \
    "/mnt/sdext/a90/runtime/evidence/a90-ondevice-evidence-v1.log"
#endif
#ifndef A90_AUTO_HANDOFF_EVIDENCE_RUN_PATH
#define A90_AUTO_HANDOFF_EVIDENCE_RUN_PATH \
    "/mnt/sdext/a90/runtime/evidence/a90-ondevice-evidence-run"
#endif
#define A90_ONDEV_EVIDENCE_MARKER "A90OBSREC "
#define A90_ONDEV_EVIDENCE_TAIL_MAX 65536U
#define A90_ONDEV_EVIDENCE_LINES_MAX 64U

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

/*
 * Publish the run identity Debian stamps its evidence with.
 *
 * Debian cannot see the enable or latch file: those live under /cache, and
 * after switch_root its root is the SD image. So the identity has to be handed
 * across on the shared medium. Using the arming intent_sha256 binds the record
 * to the exact intent that armed this ordinal, which is stronger than any run
 * string invented for the purpose.
 *
 * A failure here is logged and never refuses the dispatch. The instrument must
 * not become one more way for a host-side defect to kill an ordinal -- that is
 * the disease being cured, not a tool to reach for.
 */
static int a90_auto_handoff_publish_evidence_run(const char *intent_sha256) {
    char line[66];
    int fd;
    int length;
    ssize_t written;

    if (!a90_auto_handoff_hex64_valid(intent_sha256)) {
        return -EINVAL;
    }
    length = snprintf(line, sizeof(line), "%s\n", intent_sha256);
    if (length < 0 || (size_t)length >= sizeof(line)) {
        return -EINVAL;
    }
    fd = open(A90_AUTO_HANDOFF_EVIDENCE_RUN_PATH,
              O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW,
              0644);
    if (fd < 0) {
        return -errno;
    }
    written = write(fd, line, (size_t)length);
    if (written != (ssize_t)length) {
        int saved = (written < 0) ? errno : EIO;

        close(fd);
        return -saved;
    }
    if (fsync(fd) < 0) {
        int saved = errno;

        close(fd);
        return -saved;
    }
    if (close(fd) < 0) {
        return -errno;
    }
    return 0;
}

/*
 * Replay Debian's durable on-device evidence into the native log.
 *
 * Debian records PID 1 entry, DRM/display, and Dropbear liveness on the device
 * while it owns the machine, stamped from /proc/uptime. Those are all
 * device-internal facts; confirming them live over the host bridge inside a
 * timeout window is what turned a durable fact into a transient race and cost
 * three automatic-handoff ordinals their proof.
 *
 * This side only transports. It never grades. Selection by run identity and
 * every semantic judgement belong to the host parser, which is tested against
 * the exact defect classes that burned those ordinals. Keeping C to "read the
 * tail, emit the marker lines" keeps the parsing surface where the tests are.
 *
 * Absence is not a failure here: a first boot, or a handoff that never reached
 * Debian, legitimately has no record. The host decides what that means.
 */
static int a90_auto_handoff_replay_ondevice_evidence(void) {
    static char buffer[A90_ONDEV_EVIDENCE_TAIL_MAX + 1U];
    struct stat st;
    off_t start = 0;
    size_t consumed = 0;
    unsigned emitted = 0;
    char *cursor;
    int fd;

    fd = open(A90_AUTO_HANDOFF_EVIDENCE_PATH,
              O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    if (fstat(fd, &st) < 0 || !S_ISREG(st.st_mode)) {
        close(fd);
        return -EINVAL;
    }
    if (st.st_size > (off_t)A90_ONDEV_EVIDENCE_TAIL_MAX) {
        start = st.st_size - (off_t)A90_ONDEV_EVIDENCE_TAIL_MAX;
    }
    if (lseek(fd, start, SEEK_SET) == (off_t)-1) {
        close(fd);
        return -errno;
    }
    while (consumed < A90_ONDEV_EVIDENCE_TAIL_MAX) {
        ssize_t got = read(fd,
                           buffer + consumed,
                           A90_ONDEV_EVIDENCE_TAIL_MAX - consumed);

        if (got < 0) {
            if (errno == EINTR) {
                continue;
            }
            close(fd);
            return -errno;
        }
        if (got == 0) {
            break;
        }
        consumed += (size_t)got;
    }
    close(fd);
    buffer[consumed] = '\0';

    cursor = buffer;
    /* A tail read starts mid-line; that leading fragment is not a record. */
    if (start > 0 && buffer[0] != '\n') {
        char *first = strchr(cursor, '\n');

        cursor = (first == NULL) ? buffer + consumed : first + 1;
    } else if (start > 0) {
        ++cursor;
    }
    while (*cursor != '\0' && emitted < A90_ONDEV_EVIDENCE_LINES_MAX) {
        char *end = strchr(cursor, '\n');
        char *marker;
        size_t length;

        if (end == NULL) {
            /* No terminator: a write truncated by power loss. Drop it rather
             * than emitting half a record. */
            break;
        }
        *end = '\0';
        length = strlen(cursor);
        while (length > 0 && cursor[length - 1] == '\r') {
            cursor[--length] = '\0';
        }
        marker = strstr(cursor, A90_ONDEV_EVIDENCE_MARKER);
        if (marker != NULL) {
            a90_logf("ondev-evidence", "%s", marker);
            ++emitted;
        }
        cursor = end + 1;
    }
    return (int)emitted;
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
        int replayed;

        a90_console_printf("A90AUTO state=latched-stay-native latch=%s\r\n",
                           A90_AUTO_HANDOFF_LATCH_PATH);
        a90_logf("auto-handoff", "latched stay native path=%s",
                 A90_AUTO_HANDOFF_LATCH_PATH);
        a90_timeline_record(0, 0, "auto-handoff", "latched stay native");
        /*
         * This is the boot after Debian handed the machine back, so it is the
         * first moment the durable record is readable from native. Replay it
         * before the latched mark so the evidence and the stage marker land in
         * the same log segment the host reads back.
         */
        replayed = a90_auto_handoff_replay_ondevice_evidence();
        if (replayed >= 0) {
            a90_logf("ondev-evidence", "replayed lines=%d path=%s",
                     replayed, A90_AUTO_HANDOFF_EVIDENCE_PATH);
        } else {
            a90_logf("ondev-evidence", "absent rc=%d path=%s",
                     replayed, A90_AUTO_HANDOFF_EVIDENCE_PATH);
        }
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
    rc = a90_auto_handoff_publish_evidence_run(intent_sha256);
    if (rc < 0) {
        a90_logf("ondev-evidence", "run publish failed rc=%d path=%s", rc,
                 A90_AUTO_HANDOFF_EVIDENCE_RUN_PATH);
    } else {
        a90_logf("ondev-evidence", "run published intent_sha256=%s path=%s",
                 intent_sha256, A90_AUTO_HANDOFF_EVIDENCE_RUN_PATH);
    }
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
