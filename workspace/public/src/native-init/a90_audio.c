#include "a90_audio.h"
#include "a90_audio_chime.h"
#include "a90_audio_profile.h"
#include "a90_audio_query.h"
#include "a90_audio_route.h"
#include "a90_audio_stage.h"

#include "a90_console.h"
#include "a90_helper.h"
#include "a90_util.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>

#include <sound/asound.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#define AUDIO_FW_DIR "/vendor/firmware_mnt/image"
#define AUDIO_FWCLASS_PATH "/sys/module/firmware_class/parameters/path"
#define AUDIO_BOOT_ATTR "/sys/kernel/boot_adsp/boot"
#define AUDIO_SOUND_CLASS_DIR "/sys/class/sound"
#define AUDIO_DEV_SND_DIR "/dev/snd"
#define AUDIO_MAX_LISTED 8
#define AUDIO_SND_MAX_LISTED 64
#define AUDIO_MISSING_LIST_SIZE 192
#define AUDIO_ADSP_SEGMENT_MODEL "stock-sparse-b00-b11-b13-b16"
#define AUDIO_APP_TYPE_CFG_MAX_VALUES 128
#define AUDIO_SETCAL_MANIFEST_VERSION 1
#ifndef AUDIO_SETCAL_RUNTIME_PREFIX
#define AUDIO_SETCAL_RUNTIME_PREFIX "/cache/a90-runtime"
#endif
#ifndef AUDIO_SETCAL_BUNDLED_PREFIX
#define AUDIO_SETCAL_BUNDLED_PREFIX "/a90/audio"
#endif
#define AUDIO_SETCAL_LEGACY_REPLAY_PREFIX "/cache/a90-acdb-setcal-replay-"
#define AUDIO_SETCAL_DEV_MSM_AUDIO_CAL "/dev/msm_audio_cal"
#define AUDIO_SETCAL_DEV_ION "/dev/ion"
#define AUDIO_SETCAL_SYSFS_MSM_AUDIO_CAL_DEV "/sys/class/misc/msm_audio_cal/dev"
#define AUDIO_SETCAL_SYSFS_ION_DEV "/sys/class/misc/ion/dev"
#define AUDIO_PROC_MISC "/proc/misc"
#define AUDIO_MISC_MAJOR 10U
#define AUDIO_CAL_IOCTL_MAGIC 'a'
#define AUDIO_SETCAL_IOCTL_ALLOCATE_CALIBRATION _IOWR(AUDIO_CAL_IOCTL_MAGIC, 200, void *)
#define AUDIO_SETCAL_IOCTL_DEALLOCATE_CALIBRATION _IOWR(AUDIO_CAL_IOCTL_MAGIC, 201, void *)
#define AUDIO_SETCAL_IOCTL_SET_CALIBRATION _IOWR(AUDIO_CAL_IOCTL_MAGIC, 203, void *)
#define AUDIO_ION_FLAG_CACHED 1U
#define AUDIO_ION_SYSTEM_HEAP_ID 25U
#define AUDIO_ION_SYSTEM_HEAP_MASK (1U << AUDIO_ION_SYSTEM_HEAP_ID)
#define AUDIO_SETCAL_MANIFEST_PROFILE_SIZE 96
#define AUDIO_SETCAL_MANIFEST_ROLE_SIZE 64
#define AUDIO_SETCAL_MANIFEST_SHA256_SIZE 65
#define AUDIO_SETCAL_ARG_MAX_BYTES 512U
#define AUDIO_SETCAL_PAYLOAD_MAX_BYTES (256U * 1024U)
#define AUDIO_SETCAL_CAL_BASIC_SIZE 32U
#define AUDIO_SETCAL_OFF_DATA_SIZE 0U
#define AUDIO_SETCAL_OFF_CAL_TYPE 8U
#define AUDIO_SETCAL_OFF_BUFFER_NUMBER 20U
#define AUDIO_SETCAL_OFF_CAL_SIZE 24U
#define AUDIO_SETCAL_OFF_MEM_HANDLE 28U
#define AUDIO_ION_IOC_MAGIC 'I'
#define AUDIO_PCM_PERIOD_SIZE 1024
#define AUDIO_PCM_PERIOD_COUNT 4
#define AUDIO_PCM_MAX_CHANNELS 8
#define AUDIO_PCM_TONE_HZ 440
#define AUDIO_PLAY_ASYNC_DIR "/cache/a90-audio-play"
#define AUDIO_PLAY_ASYNC_STATUS_PATH AUDIO_PLAY_ASYNC_DIR "/status.txt"
#define AUDIO_PLAY_ASYNC_LOG_PATH AUDIO_PLAY_ASYNC_DIR "/worker.log"
#define AUDIO_PLAY_MANIFEST_WAIT_TIMEOUT_MS 90000
#define AUDIO_PLAY_MANIFEST_WAIT_SLEEP_MS 250

struct audio_ion_allocation_data {
    uint64_t len;
    uint32_t heap_id_mask;
    uint32_t flags;
    uint32_t fd;
    uint32_t unused;
};

#define AUDIO_ION_IOC_ALLOC _IOWR(AUDIO_ION_IOC_MAGIC, 0, struct audio_ion_allocation_data)

static const char *const AUDIO_ADSP_SEGMENTS[] = {
    "adsp.b00",
    "adsp.b01",
    "adsp.b02",
    "adsp.b03",
    "adsp.b04",
    "adsp.b05",
    "adsp.b06",
    "adsp.b07",
    "adsp.b08",
    "adsp.b09",
    "adsp.b10",
    "adsp.b11",
    "adsp.b13",
    "adsp.b14",
    "adsp.b15",
    "adsp.b16",
};

static int audio_materialize_ion_devnode_once(void);
static int audio_materialize_msm_audio_cal_devnode_once(void);

struct adsp_firmware_status {
    bool dir_exists;
    bool mdt_present;
    bool adspr_jsn_present;
    bool adspua_jsn_present;
    int present_segments;
    char missing_segments[AUDIO_MISSING_LIST_SIZE];
};

struct audio_snd_scan_stats {
    int entries;
    int allowed;
    int with_dev;
    int listed;
    int created;
    int already_ok;
    int missing;
    int invalid;
    int refused;
    int failed;
};

struct audio_setcal_entry {
    int cal_type;
    const char *role;
    bool dmabuf_expected;
};

struct audio_setcal_manifest_totals {
    int entries;
    int arg_entries;
    int payload_entries;
    int files_opened;
    long long arg_bytes;
    long long payload_bytes;
};

struct audio_setcal_manifest_plan_entry {
    bool present;
    int sequence;
    int cal_type;
    bool dmabuf_expected;
    char role[AUDIO_SETCAL_MANIFEST_ROLE_SIZE];
    char arg_path[PATH_MAX];
    long long arg_size;
    char arg_sha256[AUDIO_SETCAL_MANIFEST_SHA256_SIZE];
    char payload_path[PATH_MAX];
    long long payload_size;
    char payload_sha256[AUDIO_SETCAL_MANIFEST_SHA256_SIZE];
    long long arg_loaded;
    long long payload_loaded;
};

struct audio_setcal_manifest_plan {
    int version;
    char profile[AUDIO_SETCAL_MANIFEST_PROFILE_SIZE];
    int declared_entry_count;
    struct audio_setcal_manifest_totals totals;
    struct audio_setcal_manifest_totals load_totals;
    struct audio_setcal_manifest_plan_entry entries[AUDIO_PROFILE_ACDB_SET_COUNT];
    bool valid;
};

struct audio_setcal_allocation_slot {
    bool active;
    int sequence;
    int cal_type;
    long long payload_size;
    long long payload_loaded;
    char role[AUDIO_SETCAL_MANIFEST_ROLE_SIZE];
};

struct audio_setcal_allocation_plan {
    int slot_count;
    long long total_payload_bytes;
    struct audio_setcal_allocation_slot slots[AUDIO_PROFILE_ACDB_SET_COUNT];
};

struct audio_setcal_ion_request_slot {
    bool active;
    int sequence;
    int cal_type;
    uint64_t len;
    uint32_t heap_id_mask;
    uint32_t flags;
    int dmabuf_fd;
    int mem_handle;
    char role[AUDIO_SETCAL_MANIFEST_ROLE_SIZE];
};

struct audio_setcal_ion_request_plan {
    int request_count;
    uint32_t heap_id_mask;
    uint32_t flags;
    uint64_t total_len;
    struct audio_setcal_ion_request_slot requests[AUDIO_PROFILE_ACDB_SET_COUNT];
};

struct audio_setcal_execute_state {
    bool active;
    bool has_payload;
    bool allocated;
    int sequence;
    int cal_type;
    int buffer_number;
    int ion_fd;
    int dmabuf_fd;
    void *mapped;
    unsigned char *arg;
    unsigned char *set_arg;
    unsigned char *alloc_arg;
    unsigned char *dealloc_arg;
    unsigned char *payload;
    size_t arg_len;
    size_t payload_len;
};

struct audio_setcal_execute_session {
    struct audio_setcal_execute_state states[AUDIO_PROFILE_ACDB_SET_COUNT];
    int cal_fd;
    int prepared_count;
    int allocated_count;
    int set_count;
    int deallocated_count;
    int ioctl_sequence;
    bool initialized;
};

static int audio_adsp_boot_once(char **argv, int argc);
static int audio_snd_materialize_once(char **argv, int argc);
static int audio_app_type_cmd(char **argv, int argc);
static int audio_route_cmd(char **argv, int argc);
static int count_dir_entries_matching(const char *path, const char *needle);

static const struct audio_setcal_entry AUDIO_INTERNAL_SPEAKER_SETCAL_PLAN[] = {
    {.cal_type = 39, .role = "CORE_CUSTOM_TOPOLOGIES_BYTE_EXACT_SET", .dmabuf_expected = true},
    {.cal_type = 20, .role = "AFE_FB_SPKR_PROT_HEADER_REAL_HAL_1", .dmabuf_expected = false},
    {.cal_type = 20, .role = "AFE_FB_SPKR_PROT_HEADER_REAL_HAL_2", .dmabuf_expected = false},
    {.cal_type = 13, .role = "APP_META_HEADER", .dmabuf_expected = false},
    {.cal_type = 9, .role = "AFE_TOPOLOGY_HEADER", .dmabuf_expected = false},
    {.cal_type = 11, .role = "AUDPROC_COMMON_PAYLOAD", .dmabuf_expected = true},
    {.cal_type = 12, .role = "VOL_HEADER_NO_PAYLOAD", .dmabuf_expected = false},
    {.cal_type = 15, .role = "ASM_STREAM_PAYLOAD", .dmabuf_expected = true},
    {.cal_type = 23, .role = "AFE_TOPOLOGY_ID_HEADER", .dmabuf_expected = false},
    {.cal_type = 16, .role = "AFE_COMMON_PAYLOAD", .dmabuf_expected = true},
    {.cal_type = 21, .role = "SPEAKER_VI_HEADER", .dmabuf_expected = false},
};

static int audio_setcal_entry_count(void) {
    return (int)(sizeof(AUDIO_INTERNAL_SPEAKER_SETCAL_PLAN) /
                 sizeof(AUDIO_INTERNAL_SPEAKER_SETCAL_PLAN[0]));
}

static const char *yesno(bool value) {
    return value ? "yes" : "no";
}

static void print_int_list(const char *prefix, const int *values, int count) {
    int index;

    a90_console_printf("%s=", prefix);
    for (index = 0; index < count; ++index) {
        a90_console_printf("%s%d", index == 0 ? "" : ",", values[index]);
    }
    a90_console_printf("\r\n");
}

static bool audio_setcal_plan_matches_profile(const struct audio_speaker_profile *profile) {
    int index;

    if (profile == NULL || audio_setcal_entry_count() != AUDIO_PROFILE_ACDB_SET_COUNT) {
        return false;
    }
    for (index = 0; index < audio_setcal_entry_count(); ++index) {
        if (AUDIO_INTERNAL_SPEAKER_SETCAL_PLAN[index].cal_type != profile->acdb_set_order[index]) {
            return false;
        }
    }
    return true;
}

static int audio_setcal_payload_entry_count(void) {
    int index;
    int count = 0;

    for (index = 0; index < audio_setcal_entry_count(); ++index) {
        if (AUDIO_INTERNAL_SPEAKER_SETCAL_PLAN[index].dmabuf_expected) {
            ++count;
        }
    }
    return count;
}

static bool audio_text_is_sha256(const char *text) {
    size_t index;

    if (text == NULL || strlen(text) != 64) {
        return false;
    }
    for (index = 0; index < 64; ++index) {
        char ch = text[index];

        if (!((ch >= '0' && ch <= '9') ||
              (ch >= 'a' && ch <= 'f') ||
              (ch >= 'A' && ch <= 'F'))) {
            return false;
        }
    }
    return true;
}

static bool audio_setcal_path_has_prefix(const char *path, const char *prefix) {
    size_t prefix_len;

    if (path == NULL || prefix == NULL || path[0] == '\0' || prefix[0] == '\0') {
        return false;
    }
    prefix_len = strlen(prefix);
    return strncmp(path, prefix, prefix_len) == 0 &&
           (path[prefix_len] == '\0' || path[prefix_len] == '/' || prefix[prefix_len - 1] == '-');
}

static bool audio_setcal_path_has_dotdot(const char *path) {
    const char *cursor = path;

    if (path == NULL) {
        return true;
    }
    while ((cursor = strstr(cursor, "..")) != NULL) {
        if ((cursor == path || cursor[-1] == '/') &&
            (cursor[2] == '\0' || cursor[2] == '/')) {
            return true;
        }
        cursor += 2;
    }
    return false;
}

static bool audio_setcal_manifest_path_allowed(const char *path) {
    if (path == NULL || path[0] != '/' || audio_setcal_path_has_dotdot(path)) {
        return false;
    }
    return audio_setcal_path_has_prefix(path, AUDIO_SETCAL_RUNTIME_PREFIX) ||
           audio_setcal_path_has_prefix(path, AUDIO_SETCAL_BUNDLED_PREFIX) ||
           audio_setcal_path_has_prefix(path, AUDIO_SETCAL_LEGACY_REPLAY_PREFIX);
}

static bool audio_setcal_payload_path_allowed(const char *path) {
    if (path == NULL || path[0] != '/' || audio_setcal_path_has_dotdot(path)) {
        return false;
    }
    return audio_setcal_path_has_prefix(path, AUDIO_SETCAL_RUNTIME_PREFIX) ||
           audio_setcal_path_has_prefix(path, AUDIO_SETCAL_BUNDLED_PREFIX) ||
           audio_setcal_path_has_prefix(path, AUDIO_SETCAL_LEGACY_REPLAY_PREFIX);
}

static int audio_setcal_verify_regular_file(const char *prefix,
                                            const char *path,
                                            long long expected_size,
                                            const char *expected_sha256,
                                            bool path_required) {
    struct stat st;
    char actual_sha256[65];
    bool path_allowed;
    bool present = false;
    bool size_match = false;
    bool sha_valid = false;
    bool sha_checked = false;
    bool sha_match = false;
    int rc = 0;

    if (!path_required) {
        if (path != NULL && strcmp(path, "-") == 0 && expected_size == 0 &&
            expected_sha256 != NULL && strcmp(expected_sha256, "-") == 0) {
            a90_console_printf("%s.required=0\r\n", prefix);
            a90_console_printf("%s.ok=1\r\n", prefix);
            return 0;
        }
        a90_console_printf("%s.error=unexpected-nonempty-optional-payload\r\n", prefix);
        a90_console_printf("%s.ok=0\r\n", prefix);
        return -EINVAL;
    }
    if (path == NULL || strcmp(path, "-") == 0 || expected_size <= 0 ||
        expected_sha256 == NULL || strcmp(expected_sha256, "-") == 0) {
        a90_console_printf("%s.error=missing-path-size-or-sha\r\n", prefix);
        a90_console_printf("%s.ok=0\r\n", prefix);
        return -EINVAL;
    }

    path_allowed = audio_setcal_payload_path_allowed(path);
    sha_valid = audio_text_is_sha256(expected_sha256);
    a90_console_printf("%s.path_allowed=%d\r\n", prefix, path_allowed ? 1 : 0);
    a90_console_printf("%s.expected_size=%lld\r\n", prefix, expected_size);
    a90_console_printf("%s.expected_sha256=%s\r\n", prefix, expected_sha256);
    a90_console_printf("%s.sha256_valid=%d\r\n", prefix, sha_valid ? 1 : 0);
    if (!path_allowed || !sha_valid) {
        a90_console_printf("%s.ok=0\r\n", prefix);
        return -EINVAL;
    }

    if (lstat(path, &st) == 0 && S_ISREG(st.st_mode) && !S_ISLNK(st.st_mode)) {
        present = true;
        size_match = (long long)st.st_size == expected_size;
    }
    a90_console_printf("%s.present=%d\r\n", prefix, present ? 1 : 0);
    a90_console_printf("%s.actual_size=%lld\r\n", prefix, present ? (long long)st.st_size : 0LL);
    a90_console_printf("%s.size_match=%d\r\n", prefix, size_match ? 1 : 0);
    if (!present || !size_match) {
        a90_console_printf("%s.ok=0\r\n", prefix);
        return -ENOENT;
    }

    if (a90_helper_sha256_file(path, actual_sha256, sizeof(actual_sha256)) == 0) {
        sha_checked = true;
        sha_match = strcasecmp(actual_sha256, expected_sha256) == 0;
    } else {
        rc = negative_errno_or(EIO);
        snprintf(actual_sha256, sizeof(actual_sha256), "hash-error:%d", -rc);
    }
    a90_console_printf("%s.actual_sha256=%s\r\n", prefix, actual_sha256);
    a90_console_printf("%s.sha256_checked=%d\r\n", prefix, sha_checked ? 1 : 0);
    a90_console_printf("%s.sha256_match=%d\r\n", prefix, sha_match ? 1 : 0);
    a90_console_printf("%s.ok=%d\r\n", prefix, sha_match ? 1 : 0);
    return sha_match ? 0 : (rc < 0 ? rc : -EIO);
}

static int audio_setcal_load_regular_file(const char *prefix,
                                          const char *path,
                                          long long expected_size,
                                          bool path_required,
                                          long long *bytes_read) {
    struct stat st;
    char buffer[4096];
    long long total_read = 0;
    int fd;

    if (bytes_read != NULL) {
        *bytes_read = 0;
    }
    if (!path_required) {
        a90_console_printf("%s.required=0\r\n", prefix);
        a90_console_printf("%s.open_ok=0\r\n", prefix);
        a90_console_printf("%s.bytes_read=0\r\n", prefix);
        a90_console_printf("%s.ok=1\r\n", prefix);
        return 0;
    }
    if (path == NULL || strcmp(path, "-") == 0 || expected_size <= 0) {
        a90_console_printf("%s.error=missing-path-or-size\r\n", prefix);
        a90_console_printf("%s.ok=0\r\n", prefix);
        return -EINVAL;
    }
    a90_console_printf("%s.path=%s\r\n", prefix, path);
    a90_console_printf("%s.expected_size=%lld\r\n", prefix, expected_size);
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        int saved_errno = errno;

        a90_console_printf("%s.open_ok=0 errno=%d\r\n", prefix, saved_errno);
        a90_console_printf("%s.ok=0\r\n", prefix);
        return -saved_errno;
    }
    a90_console_printf("%s.open_ok=1\r\n", prefix);
    if (fstat(fd, &st) < 0) {
        int saved_errno = errno;

        close(fd);
        a90_console_printf("%s.regular_file=0 errno=%d\r\n", prefix, saved_errno);
        a90_console_printf("%s.ok=0\r\n", prefix);
        return -saved_errno;
    }
    if (!S_ISREG(st.st_mode)) {
        close(fd);
        a90_console_printf("%s.regular_file=0 errno=%d\r\n", prefix, EINVAL);
        a90_console_printf("%s.ok=0\r\n", prefix);
        return -EINVAL;
    }
    a90_console_printf("%s.regular_file=1\r\n", prefix);
    for (;;) {
        ssize_t chunk = read(fd, buffer, sizeof(buffer));

        if (chunk < 0) {
            int saved_errno = errno;

            close(fd);
            a90_console_printf("%s.read_error=%d\r\n", prefix, saved_errno);
            a90_console_printf("%s.ok=0\r\n", prefix);
            return -saved_errno;
        }
        if (chunk == 0) {
            break;
        }
        total_read += chunk;
    }
    close(fd);
    if (bytes_read != NULL) {
        *bytes_read = total_read;
    }
    a90_console_printf("%s.bytes_read=%lld\r\n", prefix, total_read);
    a90_console_printf("%s.size_match=%d\r\n", total_read == expected_size ? 1 : 0);
    a90_console_printf("%s.ok=%d\r\n", total_read == expected_size ? 1 : 0);
    return total_read == expected_size ? 0 : -EIO;
}

static void audio_copy_string(char *dst, size_t dst_size, const char *src) {
    size_t index;

    if (dst == NULL || dst_size == 0) {
        return;
    }
    if (src == NULL) {
        src = "";
    }
    for (index = 0; index + 1 < dst_size && src[index] != '\0'; ++index) {
        dst[index] = src[index];
    }
    dst[index] = '\0';
}

static void audio_setcal_manifest_plan_reset(struct audio_setcal_manifest_plan *plan) {
    if (plan == NULL) {
        return;
    }
    memset(plan, 0, sizeof(*plan));
    plan->version = -1;
    plan->declared_entry_count = -1;
}

static void audio_setcal_manifest_plan_store_entry(struct audio_setcal_manifest_plan *plan,
                                                   int sequence,
                                                   int cal_type,
                                                   const char *role,
                                                   bool dmabuf_expected,
                                                   const char *arg_path,
                                                   long long arg_size,
                                                   const char *arg_sha256,
                                                   const char *payload_path,
                                                   long long payload_size,
                                                   const char *payload_sha256,
                                                   long long arg_loaded,
                                                   long long payload_loaded) {
    struct audio_setcal_manifest_plan_entry *entry;

    if (plan == NULL || sequence < 0 || sequence >= AUDIO_PROFILE_ACDB_SET_COUNT) {
        return;
    }
    entry = &plan->entries[sequence];
    memset(entry, 0, sizeof(*entry));
    entry->present = true;
    entry->sequence = sequence;
    entry->cal_type = cal_type;
    entry->dmabuf_expected = dmabuf_expected;
    audio_copy_string(entry->role, sizeof(entry->role), role);
    audio_copy_string(entry->arg_path, sizeof(entry->arg_path), arg_path);
    entry->arg_size = arg_size;
    audio_copy_string(entry->arg_sha256, sizeof(entry->arg_sha256), arg_sha256);
    audio_copy_string(entry->payload_path, sizeof(entry->payload_path), payload_path);
    entry->payload_size = payload_size;
    audio_copy_string(entry->payload_sha256, sizeof(entry->payload_sha256), payload_sha256);
    entry->arg_loaded = arg_loaded;
    entry->payload_loaded = payload_loaded;
}

static int audio_setcal_verify_manifest_entry(char *line,
                                              const struct audio_speaker_profile *profile,
                                              bool *seen_entry,
                                              struct audio_setcal_manifest_totals *totals,
                                              bool load_files,
                                              struct audio_setcal_manifest_totals *load_totals,
                                              struct audio_setcal_manifest_plan *plan) {
    int sequence = -1;
    int cal_type = -1;
    int dmabuf_expected = -1;
    char role[64];
    char arg_path[PATH_MAX];
    char arg_sha256[65];
    char payload_path[PATH_MAX];
    char payload_sha256[65];
    long long arg_size = 0;
    long long payload_size = 0;
    const struct audio_setcal_entry *expected;
    char prefix[80];
    char arg_prefix[96];
    char payload_prefix[96];
    char load_arg_prefix[96];
    char load_payload_prefix[96];
    long long arg_loaded = 0;
    long long payload_loaded = 0;
    int fields;
    int rc = 0;

    memset(role, 0, sizeof(role));
    memset(arg_path, 0, sizeof(arg_path));
    memset(arg_sha256, 0, sizeof(arg_sha256));
    memset(payload_path, 0, sizeof(payload_path));
    memset(payload_sha256, 0, sizeof(payload_sha256));
    fields = sscanf(line,
                    "entry %d %d %63s %d %4095s %lld %64s %4095s %lld %64s",
                    &sequence,
                    &cal_type,
                    role,
                    &dmabuf_expected,
                    arg_path,
                    &arg_size,
                    arg_sha256,
                    payload_path,
                    &payload_size,
                    payload_sha256);
    if (fields != 10 || sequence < 0 || sequence >= audio_setcal_entry_count()) {
        a90_console_printf("audio.setcal.verify.error=bad-entry-line\r\n");
        return -EINVAL;
    }
    if (seen_entry[sequence]) {
        a90_console_printf("audio.setcal.verify.entry.%d.error=duplicate\r\n", sequence);
        return -EINVAL;
    }
    seen_entry[sequence] = true;
    expected = &AUDIO_INTERNAL_SPEAKER_SETCAL_PLAN[sequence];
    snprintf(prefix, sizeof(prefix), "audio.setcal.verify.entry.%d", sequence);
    a90_console_printf("%s.cal_type=%d\r\n", prefix, cal_type);
    a90_console_printf("%s.role=%s\r\n", prefix, role);
    a90_console_printf("%s.dmabuf_expected=%d\r\n", prefix, dmabuf_expected);
    a90_console_printf("%s.plan_cal_type=%d\r\n", prefix, expected->cal_type);
    a90_console_printf("%s.plan_role=%s\r\n", prefix, expected->role);
    if (profile == NULL || cal_type != expected->cal_type ||
        strcmp(role, expected->role) != 0 ||
        dmabuf_expected != (expected->dmabuf_expected ? 1 : 0)) {
        a90_console_printf("%s.error=plan-mismatch\r\n", prefix);
        a90_console_printf("%s.ok=0\r\n", prefix);
        return -EINVAL;
    }
    if (totals != NULL) {
        totals->entries += 1;
        totals->arg_entries += 1;
        totals->arg_bytes += arg_size > 0 ? arg_size : 0;
        if (expected->dmabuf_expected) {
            totals->payload_entries += 1;
            totals->payload_bytes += payload_size > 0 ? payload_size : 0;
        }
    }
    snprintf(arg_prefix, sizeof(arg_prefix), "%s.arg", prefix);
    if (audio_setcal_verify_regular_file(arg_prefix, arg_path, arg_size, arg_sha256, true) < 0) {
        rc = -EINVAL;
    }
    snprintf(payload_prefix, sizeof(payload_prefix), "%s.payload", prefix);
    if (audio_setcal_verify_regular_file(payload_prefix,
                                         payload_path,
                                         payload_size,
                                         payload_sha256,
                                         expected->dmabuf_expected) < 0) {
        rc = -EINVAL;
    }
    if (load_files && rc == 0) {
        snprintf(load_arg_prefix, sizeof(load_arg_prefix), "audio.setcal.load.entry.%d.arg", sequence);
        if (audio_setcal_load_regular_file(load_arg_prefix, arg_path, arg_size, true, &arg_loaded) < 0) {
            rc = -EINVAL;
        }
        snprintf(load_payload_prefix, sizeof(load_payload_prefix), "audio.setcal.load.entry.%d.payload", sequence);
        if (audio_setcal_load_regular_file(load_payload_prefix,
                                           payload_path,
                                           payload_size,
                                           expected->dmabuf_expected,
                                           &payload_loaded) < 0) {
            rc = -EINVAL;
        }
        if (load_totals != NULL && rc == 0) {
            load_totals->entries += 1;
            load_totals->arg_entries += 1;
            load_totals->files_opened += 1;
            load_totals->arg_bytes += arg_loaded;
            if (expected->dmabuf_expected) {
                load_totals->payload_entries += 1;
                load_totals->files_opened += 1;
                load_totals->payload_bytes += payload_loaded;
            }
        }
        a90_console_printf("audio.setcal.load.entry.%d.ok=%d\r\n", sequence, rc == 0 ? 1 : 0);
    }
    if (rc == 0) {
        audio_setcal_manifest_plan_store_entry(plan,
                                               sequence,
                                               cal_type,
                                               role,
                                               dmabuf_expected != 0,
                                               arg_path,
                                               arg_size,
                                               arg_sha256,
                                               payload_path,
                                               payload_size,
                                               payload_sha256,
                                               arg_loaded,
                                               payload_loaded);
    }
    a90_console_printf("%s.ok=%d\r\n", prefix, rc == 0 ? 1 : 0);
    return rc;
}

static int audio_setcal_verify_manifest(const struct audio_speaker_profile *profile,
                                        const char *manifest_path,
                                        struct audio_setcal_manifest_totals *totals,
                                        bool load_files,
                                        struct audio_setcal_manifest_totals *load_totals,
                                        struct audio_setcal_manifest_plan *plan) {
    FILE *fp;
    int fd;
    char line[1024];
    char manifest_profile[96] = "";
    bool seen_entry[AUDIO_PROFILE_ACDB_SET_COUNT];
    int manifest_version = -1;
    int manifest_entry_count = -1;
    int parsed_entries = 0;
    int rc = 0;
    int line_no = 0;
    int index;

    memset(seen_entry, 0, sizeof(seen_entry));
    if (totals != NULL) {
        memset(totals, 0, sizeof(*totals));
    }
    if (load_totals != NULL) {
        memset(load_totals, 0, sizeof(*load_totals));
    }
    audio_setcal_manifest_plan_reset(plan);
    a90_console_printf("audio.setcal.verify.manifest=%s\r\n", manifest_path != NULL ? manifest_path : "-");
    a90_console_printf("audio.setcal.verify.path_allowed=%d\r\n",
                       audio_setcal_manifest_path_allowed(manifest_path) ? 1 : 0);
    a90_console_printf("audio.setcal.verify.ioctl_attempted=0\r\n");
    a90_console_printf("audio.setcal.load.requested=%d\r\n", load_files ? 1 : 0);
    if (!audio_setcal_manifest_path_allowed(manifest_path)) {
        a90_console_printf("audio.setcal.verify.error=manifest-path-not-allowed\r\n");
        a90_console_printf("audio.setcal.verify.ok=0\r\n");
        return -EINVAL;
    }
    fd = open(manifest_path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        int saved_errno = errno;

        a90_console_printf("audio.setcal.verify.open_ok=0 errno=%d\r\n", saved_errno);
        a90_console_printf("audio.setcal.verify.ok=0\r\n");
        return -saved_errno;
    }
    fp = fdopen(fd, "r");
    if (fp == NULL) {
        int saved_errno = errno;

        close(fd);
        a90_console_printf("audio.setcal.verify.open_ok=0 errno=%d\r\n", saved_errno);
        a90_console_printf("audio.setcal.verify.ok=0\r\n");
        return -saved_errno;
    }
    a90_console_printf("audio.setcal.verify.open_ok=1\r\n");
    while (fgets(line, sizeof(line), fp) != NULL) {
        char *cursor = line;

        ++line_no;
        trim_newline(line);
        while (*cursor == ' ' || *cursor == '\t') {
            ++cursor;
        }
        if (*cursor == '\0' || *cursor == '#') {
            continue;
        }
        if (sscanf(cursor, "version %d", &manifest_version) == 1) {
            if (plan != NULL) {
                plan->version = manifest_version;
            }
            continue;
        }
        if (sscanf(cursor, "profile %95s", manifest_profile) == 1) {
            if (plan != NULL) {
                audio_copy_string(plan->profile, sizeof(plan->profile), manifest_profile);
            }
            continue;
        }
        if (sscanf(cursor, "entry_count %d", &manifest_entry_count) == 1) {
            if (plan != NULL) {
                plan->declared_entry_count = manifest_entry_count;
            }
            continue;
        }
        if (strncmp(cursor, "entry ", 6) == 0) {
            if (audio_setcal_verify_manifest_entry(cursor,
                                                   profile,
                                                   seen_entry,
                                                   totals,
                                                   load_files,
                                                   load_totals,
                                                   plan) < 0) {
                rc = -EINVAL;
            }
            ++parsed_entries;
            continue;
        }
        a90_console_printf("audio.setcal.verify.line.%d.error=unknown-token\r\n", line_no);
        rc = -EINVAL;
    }
    if (ferror(fp)) {
        rc = -EIO;
    }
    fclose(fp);

    a90_console_printf("audio.setcal.verify.version=%d\r\n", manifest_version);
    a90_console_printf("audio.setcal.verify.profile=%s\r\n", manifest_profile[0] != '\0' ? manifest_profile : "-");
    a90_console_printf("audio.setcal.verify.entry_count=%d\r\n", manifest_entry_count);
    a90_console_printf("audio.setcal.verify.parsed_entries=%d\r\n", parsed_entries);
    if (totals != NULL) {
        a90_console_printf("audio.setcal.verify.arg_entries=%d\r\n", totals->arg_entries);
        a90_console_printf("audio.setcal.verify.payload_entries=%d\r\n", totals->payload_entries);
        a90_console_printf("audio.setcal.verify.arg_bytes=%lld\r\n", totals->arg_bytes);
        a90_console_printf("audio.setcal.verify.payload_bytes=%lld\r\n", totals->payload_bytes);
    }
    if (manifest_version != AUDIO_SETCAL_MANIFEST_VERSION) {
        a90_console_printf("audio.setcal.verify.error=bad-version\r\n");
        rc = -EINVAL;
    }
    if (profile == NULL || strcmp(manifest_profile, profile->id) != 0) {
        a90_console_printf("audio.setcal.verify.error=profile-mismatch\r\n");
        rc = -EINVAL;
    }
    if (manifest_entry_count != audio_setcal_entry_count() ||
        parsed_entries != audio_setcal_entry_count()) {
        a90_console_printf("audio.setcal.verify.error=entry-count-mismatch\r\n");
        rc = -EINVAL;
    }
    for (index = 0; index < audio_setcal_entry_count(); ++index) {
        if (!seen_entry[index]) {
            a90_console_printf("audio.setcal.verify.entry.%d.error=missing\r\n", index);
            rc = -EINVAL;
        }
    }
    a90_console_printf("audio.setcal.verify.ok=%d\r\n", rc == 0 ? 1 : 0);
    if (plan != NULL && rc == 0) {
        if (totals != NULL) {
            plan->totals = *totals;
        }
        if (load_totals != NULL) {
            plan->load_totals = *load_totals;
        }
        plan->valid = true;
    }
    return rc;
}

static void audio_setcal_print_execute_plan(const struct audio_speaker_profile *profile,
                                            const struct audio_setcal_manifest_plan *plan) {
    int index;

    if (profile == NULL || plan == NULL) {
        return;
    }
    a90_console_printf("audio.setcal.execute.plan.version=1\r\n");
    a90_console_printf("audio.setcal.execute.plan.profile=%s\r\n", profile->id);
    a90_console_printf("audio.setcal.execute.plan.manifest.valid=%d\r\n", plan->valid ? 1 : 0);
    a90_console_printf("audio.setcal.execute.plan.manifest.version=%d\r\n", plan->version);
    a90_console_printf("audio.setcal.execute.plan.manifest.profile=%s\r\n",
                       plan->profile[0] != '\0' ? plan->profile : "-");
    a90_console_printf("audio.setcal.execute.plan.manifest.entry_count=%d\r\n",
                       plan->declared_entry_count);
    a90_console_printf("audio.setcal.execute.plan.device.msm_audio_cal=%s\r\n", AUDIO_SETCAL_DEV_MSM_AUDIO_CAL);
    a90_console_printf("audio.setcal.execute.plan.device.ion=%s\r\n", AUDIO_SETCAL_DEV_ION);
    a90_console_printf("audio.setcal.execute.plan.ioctl.allocate=0x%08x\r\n",
                       AUDIO_SETCAL_IOCTL_ALLOCATE_CALIBRATION);
    a90_console_printf("audio.setcal.execute.plan.ioctl.set=0x%08x\r\n",
                       AUDIO_SETCAL_IOCTL_SET_CALIBRATION);
    a90_console_printf("audio.setcal.execute.plan.ioctl.deallocate=0x%08x\r\n",
                       AUDIO_SETCAL_IOCTL_DEALLOCATE_CALIBRATION);
    a90_console_printf("audio.setcal.execute.plan.entry.count=%d\r\n", plan->totals.entries);
    a90_console_printf("audio.setcal.execute.plan.arg_entries=%d\r\n", plan->totals.arg_entries);
    a90_console_printf("audio.setcal.execute.plan.payload_entries=%d\r\n", plan->totals.payload_entries);
    a90_console_printf("audio.setcal.execute.plan.arg_bytes=%lld\r\n", plan->totals.arg_bytes);
    a90_console_printf("audio.setcal.execute.plan.payload_bytes=%lld\r\n", plan->totals.payload_bytes);
    a90_console_printf("audio.setcal.execute.plan.loaded_files=%d\r\n", plan->load_totals.files_opened);
    a90_console_printf("audio.setcal.execute.plan.loaded_arg_bytes=%lld\r\n", plan->load_totals.arg_bytes);
    a90_console_printf("audio.setcal.execute.plan.loaded_payload_bytes=%lld\r\n", plan->load_totals.payload_bytes);
    a90_console_printf("audio.setcal.execute.plan.executor_input=manifest-plan-entries\r\n");
    for (index = 0; index < AUDIO_PROFILE_ACDB_SET_COUNT; ++index) {
        const struct audio_setcal_manifest_plan_entry *entry = &plan->entries[index];
        char prefix[80];

        snprintf(prefix, sizeof(prefix), "audio.setcal.execute.plan.entry.%d", index);
        a90_console_printf("%s.present=%d\r\n", prefix, entry->present ? 1 : 0);
        a90_console_printf("%s.sequence=%d\r\n", prefix, entry->sequence);
        a90_console_printf("%s.cal_type=%d\r\n", prefix, entry->cal_type);
        a90_console_printf("%s.role=%s\r\n", prefix, entry->role[0] != '\0' ? entry->role : "-");
        a90_console_printf("%s.dmabuf_expected=%d\r\n", prefix, entry->dmabuf_expected ? 1 : 0);
        a90_console_printf("%s.arg_size=%lld\r\n", prefix, entry->arg_size);
        a90_console_printf("%s.payload_size=%lld\r\n", prefix, entry->payload_size);
        a90_console_printf("%s.arg_loaded=%lld\r\n", prefix, entry->arg_loaded);
        a90_console_printf("%s.payload_loaded=%lld\r\n", prefix, entry->payload_loaded);
    }
    a90_console_printf("audio.setcal.execute.plan.sequence=open_ion,open_msm_audio_cal,allocate_payload_entries,set_entries_in_order,hold_fds,deallocate_payload_entries_reverse,close_fds\r\n");
    a90_console_printf("audio.setcal.execute.plan.devices_opened=0\r\n");
    a90_console_printf("audio.setcal.execute.plan.ioctl_attempted=0\r\n");
}

static void audio_setcal_allocation_plan_build(const struct audio_setcal_manifest_plan *manifest_plan,
                                               struct audio_setcal_allocation_plan *allocation_plan) {
    int index;

    if (allocation_plan == NULL) {
        return;
    }
    memset(allocation_plan, 0, sizeof(*allocation_plan));
    if (manifest_plan == NULL || !manifest_plan->valid) {
        return;
    }
    for (index = 0; index < AUDIO_PROFILE_ACDB_SET_COUNT; ++index) {
        const struct audio_setcal_manifest_plan_entry *entry = &manifest_plan->entries[index];
        struct audio_setcal_allocation_slot *slot;

        if (!entry->present || !entry->dmabuf_expected) {
            continue;
        }
        slot = &allocation_plan->slots[allocation_plan->slot_count];
        slot->active = true;
        slot->sequence = entry->sequence;
        slot->cal_type = entry->cal_type;
        slot->payload_size = entry->payload_size;
        slot->payload_loaded = entry->payload_loaded;
        audio_copy_string(slot->role, sizeof(slot->role), entry->role);
        allocation_plan->slot_count += 1;
        allocation_plan->total_payload_bytes += entry->payload_size > 0 ? entry->payload_size : 0;
    }
}

static void audio_setcal_print_allocation_plan(const struct audio_setcal_allocation_plan *allocation_plan) {
    int index;

    if (allocation_plan == NULL) {
        return;
    }
    a90_console_printf("audio.setcal.execute.allocate.plan.version=1\r\n");
    a90_console_printf("audio.setcal.execute.allocate.plan.slot.count=%d\r\n",
                       allocation_plan->slot_count);
    a90_console_printf("audio.setcal.execute.allocate.plan.total_payload_bytes=%lld\r\n",
                       allocation_plan->total_payload_bytes);
    a90_console_printf("audio.setcal.execute.allocate.plan.ioctl.allocate=0x%08x\r\n",
                       AUDIO_SETCAL_IOCTL_ALLOCATE_CALIBRATION);
    a90_console_printf("audio.setcal.execute.allocate.plan.ioctl.deallocate=0x%08x\r\n",
                       AUDIO_SETCAL_IOCTL_DEALLOCATE_CALIBRATION);
    a90_console_printf("audio.setcal.execute.allocate.plan.allocate_attempted=0\r\n");
    a90_console_printf("audio.setcal.execute.allocate.plan.ioctl_attempted=0\r\n");
    for (index = 0; index < allocation_plan->slot_count; ++index) {
        const struct audio_setcal_allocation_slot *slot = &allocation_plan->slots[index];
        char prefix[96];

        snprintf(prefix, sizeof(prefix), "audio.setcal.execute.allocate.plan.slot.%d", index);
        a90_console_printf("%s.active=%d\r\n", prefix, slot->active ? 1 : 0);
        a90_console_printf("%s.sequence=%d\r\n", prefix, slot->sequence);
        a90_console_printf("%s.cal_type=%d\r\n", prefix, slot->cal_type);
        a90_console_printf("%s.role=%s\r\n", prefix, slot->role[0] != '\0' ? slot->role : "-");
        a90_console_printf("%s.payload_size=%lld\r\n", prefix, slot->payload_size);
        a90_console_printf("%s.payload_loaded=%lld\r\n", prefix, slot->payload_loaded);
    }
}

static void audio_setcal_ion_request_plan_build(const struct audio_setcal_allocation_plan *allocation_plan,
                                                struct audio_setcal_ion_request_plan *request_plan) {
    int index;

    if (request_plan == NULL) {
        return;
    }
    memset(request_plan, 0, sizeof(*request_plan));
    request_plan->heap_id_mask = AUDIO_ION_SYSTEM_HEAP_MASK;
    request_plan->flags = AUDIO_ION_FLAG_CACHED;
    if (allocation_plan == NULL) {
        return;
    }
    for (index = 0; index < allocation_plan->slot_count; ++index) {
        const struct audio_setcal_allocation_slot *slot = &allocation_plan->slots[index];
        struct audio_setcal_ion_request_slot *request;

        if (!slot->active || slot->payload_size <= 0) {
            continue;
        }
        request = &request_plan->requests[request_plan->request_count];
        request->active = true;
        request->sequence = slot->sequence;
        request->cal_type = slot->cal_type;
        request->len = (uint64_t)slot->payload_size;
        request->heap_id_mask = request_plan->heap_id_mask;
        request->flags = request_plan->flags;
        request->dmabuf_fd = -1;
        request->mem_handle = -1;
        audio_copy_string(request->role, sizeof(request->role), slot->role);
        request_plan->request_count += 1;
        request_plan->total_len += request->len;
    }
}

static void audio_setcal_print_ion_request_plan(const struct audio_setcal_ion_request_plan *request_plan) {
    int index;

    if (request_plan == NULL) {
        return;
    }
    a90_console_printf("audio.setcal.execute.ion.plan.version=1\r\n");
    a90_console_printf("audio.setcal.execute.ion.plan.request.count=%d\r\n",
                       request_plan->request_count);
    a90_console_printf("audio.setcal.execute.ion.plan.total_len=%llu\r\n",
                       (unsigned long long)request_plan->total_len);
    a90_console_printf("audio.setcal.execute.ion.plan.heap_id_mask=0x%08x\r\n",
                       request_plan->heap_id_mask);
    a90_console_printf("audio.setcal.execute.ion.plan.flags=0x%08x\r\n", request_plan->flags);
    a90_console_printf("audio.setcal.execute.ion.plan.alloc_attempted=0\r\n");
    a90_console_printf("audio.setcal.execute.ion.plan.ioctl_attempted=0\r\n");
    for (index = 0; index < request_plan->request_count; ++index) {
        const struct audio_setcal_ion_request_slot *request = &request_plan->requests[index];
        char prefix[96];

        snprintf(prefix, sizeof(prefix), "audio.setcal.execute.ion.plan.request.%d", index);
        a90_console_printf("%s.active=%d\r\n", prefix, request->active ? 1 : 0);
        a90_console_printf("%s.sequence=%d\r\n", prefix, request->sequence);
        a90_console_printf("%s.cal_type=%d\r\n", prefix, request->cal_type);
        a90_console_printf("%s.role=%s\r\n", prefix, request->role[0] != '\0' ? request->role : "-");
        a90_console_printf("%s.len=%llu\r\n", prefix, (unsigned long long)request->len);
        a90_console_printf("%s.heap_id_mask=0x%08x\r\n", prefix, request->heap_id_mask);
        a90_console_printf("%s.flags=0x%08x\r\n", prefix, request->flags);
        a90_console_printf("%s.dmabuf_fd=%d\r\n", prefix, request->dmabuf_fd);
        a90_console_printf("%s.mem_handle=%d\r\n", prefix, request->mem_handle);
    }
}

static int32_t audio_setcal_read_le_i32(const unsigned char *data, size_t len, size_t off) {
    uint32_t raw;

    if (data == NULL || off + sizeof(raw) > len) {
        return INT32_MIN;
    }
    memcpy(&raw, data + off, sizeof(raw));
    return (int32_t)raw;
}

static void audio_setcal_write_le_i32(unsigned char *data, size_t len, size_t off, int32_t value) {
    uint32_t raw = (uint32_t)value;

    if (data == NULL || off + sizeof(raw) > len) {
        return;
    }
    memcpy(data + off, &raw, sizeof(raw));
}

static bool audio_setcal_buffer_is_all_zero(const unsigned char *data, size_t len) {
    size_t offset;

    if (data == NULL || len == 0) {
        return true;
    }
    for (offset = 0; offset < len; ++offset) {
        if (data[offset] != 0) {
            return false;
        }
    }
    return true;
}

static int audio_setcal_read_file_bytes(const char *prefix,
                                        const char *path,
                                        size_t max_len,
                                        unsigned char **data_out,
                                        size_t *size_out) {
    int fd;
    struct stat st;
    unsigned char *data = NULL;
    size_t done = 0;

    if (data_out != NULL) {
        *data_out = NULL;
    }
    if (size_out != NULL) {
        *size_out = 0;
    }
    if (prefix == NULL) {
        prefix = "audio.setcal.execute.input";
    }
    a90_console_printf("%s.path=%s\r\n", prefix, path != NULL ? path : "-");
    if (!audio_setcal_payload_path_allowed(path)) {
        a90_console_printf("%s.error=path-not-allowed\r\n", prefix);
        return -EINVAL;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        int saved_errno = errno;

        a90_console_printf("%s.open_ok=0 errno=%d\r\n", prefix, saved_errno);
        return -saved_errno;
    }
    if (fstat(fd, &st) < 0) {
        int saved_errno = errno;

        a90_console_printf("%s.fstat_ok=0 errno=%d\r\n", prefix, saved_errno);
        close(fd);
        return -saved_errno;
    }
    if (!S_ISREG(st.st_mode) || st.st_size <= 0 || st.st_size > (off_t)max_len) {
        a90_console_printf("%s.error=bad-size-or-type size=%lld max=%llu\r\n",
                           prefix,
                           (long long)st.st_size,
                           (unsigned long long)max_len);
        close(fd);
        return -EINVAL;
    }
    data = (unsigned char *)calloc(1, (size_t)st.st_size);
    if (data == NULL) {
        close(fd);
        a90_console_printf("%s.error=alloc-failed\r\n", prefix);
        return -ENOMEM;
    }
    while (done < (size_t)st.st_size) {
        ssize_t rc = read(fd, data + done, (size_t)st.st_size - done);

        if (rc < 0) {
            int saved_errno = errno;

            if (saved_errno == EINTR) {
                continue;
            }
            a90_console_printf("%s.read_ok=0 errno=%d\r\n", prefix, saved_errno);
            free(data);
            close(fd);
            return -saved_errno;
        }
        if (rc == 0) {
            a90_console_printf("%s.error=short-read\r\n", prefix);
            free(data);
            close(fd);
            return -EIO;
        }
        done += (size_t)rc;
    }
    close(fd);
    if (audio_setcal_buffer_is_all_zero(data, (size_t)st.st_size)) {
        a90_console_printf("%s.error=all-zero\r\n", prefix);
        free(data);
        return -EINVAL;
    }
    a90_console_printf("%s.open_ok=1\r\n", prefix);
    a90_console_printf("%s.bytes=%llu\r\n", prefix, (unsigned long long)done);
    if (data_out != NULL) {
        *data_out = data;
    } else {
        free(data);
    }
    if (size_out != NULL) {
        *size_out = done;
    }
    return 0;
}

static void audio_setcal_execute_state_init(struct audio_setcal_execute_state *state,
                                            const struct audio_setcal_manifest_plan_entry *entry) {
    memset(state, 0, sizeof(*state));
    state->sequence = entry != NULL ? entry->sequence : -1;
    state->cal_type = entry != NULL ? entry->cal_type : 0;
    state->buffer_number = -1;
    state->has_payload = entry != NULL && entry->dmabuf_expected;
    state->mapped = MAP_FAILED;
    state->ion_fd = -1;
    state->dmabuf_fd = -1;
}

static void audio_setcal_execute_state_release(struct audio_setcal_execute_state *state) {
    if (state == NULL) {
        return;
    }
    if (state->mapped != MAP_FAILED) {
        munmap(state->mapped, state->payload_len);
        state->mapped = MAP_FAILED;
    }
    if (state->dmabuf_fd >= 0) {
        close(state->dmabuf_fd);
        state->dmabuf_fd = -1;
    }
    if (state->ion_fd >= 0) {
        close(state->ion_fd);
        state->ion_fd = -1;
    }
    free(state->arg);
    free(state->set_arg);
    free(state->alloc_arg);
    free(state->dealloc_arg);
    free(state->payload);
    state->arg = NULL;
    state->set_arg = NULL;
    state->alloc_arg = NULL;
    state->dealloc_arg = NULL;
    state->payload = NULL;
}

static int audio_setcal_ion_alloc_dmabuf(size_t len,
                                         int sequence,
                                         int cal_type,
                                         int *ion_fd_out,
                                         int *dmabuf_fd_out) {
    struct audio_ion_allocation_data allocation;
    int ion_fd;

    if (ion_fd_out != NULL) {
        *ion_fd_out = -1;
    }
    if (dmabuf_fd_out != NULL) {
        *dmabuf_fd_out = -1;
    }
    if (len == 0 || len > AUDIO_SETCAL_PAYLOAD_MAX_BYTES) {
        a90_console_printf("audio.setcal.execute.ion.error=bad-len sequence=%d cal_type=%d len=%llu\r\n",
                           sequence,
                           cal_type,
                           (unsigned long long)len);
        return -EINVAL;
    }
    if (audio_materialize_ion_devnode_once() < 0) {
        return negative_errno_or(ENOENT);
    }
    ion_fd = open(AUDIO_SETCAL_DEV_ION, O_RDONLY | O_CLOEXEC);
    if (ion_fd < 0) {
        int saved_errno = errno;

        a90_console_printf("audio.setcal.execute.ion.open_ok=0 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    memset(&allocation, 0, sizeof(allocation));
    allocation.len = (uint64_t)len;
    allocation.heap_id_mask = AUDIO_ION_SYSTEM_HEAP_MASK;
    allocation.flags = AUDIO_ION_FLAG_CACHED;
    a90_console_printf("audio.setcal.execute.ion.alloc.sequence=%d\r\n", sequence);
    a90_console_printf("audio.setcal.execute.ion.alloc.cal_type=%d\r\n", cal_type);
    a90_console_printf("audio.setcal.execute.ion.alloc.len=%llu\r\n", (unsigned long long)len);
    a90_console_printf("audio.setcal.execute.ion.alloc.heap_id_mask=0x%08x\r\n", allocation.heap_id_mask);
    a90_console_printf("audio.setcal.execute.ion.alloc.flags=0x%08x\r\n", allocation.flags);
    if (ioctl(ion_fd, AUDIO_ION_IOC_ALLOC, &allocation) < 0) {
        int saved_errno = errno;

        a90_console_printf("audio.setcal.execute.ion.alloc_ok=0 errno=%d\r\n", saved_errno);
        close(ion_fd);
        return -saved_errno;
    }
    if (ion_fd_out != NULL) {
        *ion_fd_out = ion_fd;
    }
    if (dmabuf_fd_out != NULL) {
        *dmabuf_fd_out = (int)allocation.fd;
    }
    a90_console_printf("audio.setcal.execute.ion.alloc_ok=1 dmabuf_fd=%d\r\n", (int)allocation.fd);
    return 0;
}

static int audio_setcal_prepare_payload_state(struct audio_setcal_execute_state *state,
                                              const struct audio_setcal_manifest_plan_entry *entry) {
    char prefix[96];
    int rc;

    if (state == NULL || entry == NULL) {
        return -EINVAL;
    }
    snprintf(prefix, sizeof(prefix), "audio.setcal.execute.entry.%d.payload", state->sequence);
    rc = audio_setcal_read_file_bytes(prefix,
                                      entry->payload_path,
                                      AUDIO_SETCAL_PAYLOAD_MAX_BYTES,
                                      &state->payload,
                                      &state->payload_len);
    if (rc < 0) {
        return rc;
    }
    rc = audio_setcal_ion_alloc_dmabuf(state->payload_len,
                                       state->sequence,
                                       state->cal_type,
                                       &state->ion_fd,
                                       &state->dmabuf_fd);
    if (rc < 0) {
        return rc;
    }
    state->mapped = mmap(NULL,
                         state->payload_len,
                         PROT_READ | PROT_WRITE,
                         MAP_SHARED,
                         state->dmabuf_fd,
                         0);
    if (state->mapped == MAP_FAILED) {
        int saved_errno = errno;

        a90_console_printf("audio.setcal.execute.entry.%d.mmap_ok=0 errno=%d\r\n",
                           state->sequence,
                           saved_errno);
        return -saved_errno;
    }
    memcpy(state->mapped, state->payload, state->payload_len);
    if (msync(state->mapped, state->payload_len, MS_SYNC) < 0) {
        int saved_errno = errno;

        a90_console_printf("audio.setcal.execute.entry.%d.msync_ok=0 errno=%d\r\n",
                           state->sequence,
                           saved_errno);
        a90_console_printf("audio.setcal.execute.entry.%d.msync_nonfatal=1\r\n",
                           state->sequence);
    } else {
        a90_console_printf("audio.setcal.execute.entry.%d.msync_ok=1\r\n", state->sequence);
    }
    a90_console_printf("audio.setcal.execute.entry.%d.mmap_ok=1\r\n", state->sequence);
    a90_console_printf("audio.setcal.execute.entry.%d.payload_copied=1\r\n", state->sequence);
    return 0;
}

static int audio_setcal_prepare_exact_entry(struct audio_setcal_execute_state *state,
                                            const struct audio_setcal_manifest_plan_entry *entry) {
    char prefix[96];
    int32_t data_size;
    int32_t cal_type;
    int32_t cal_size;
    int32_t mem_handle;
    int rc;

    if (state == NULL || entry == NULL || !entry->present) {
        return -EINVAL;
    }
    snprintf(prefix, sizeof(prefix), "audio.setcal.execute.entry.%d.arg", state->sequence);
    rc = audio_setcal_read_file_bytes(prefix,
                                      entry->arg_path,
                                      AUDIO_SETCAL_ARG_MAX_BYTES,
                                      &state->arg,
                                      &state->arg_len);
    if (rc < 0) {
        return rc;
    }
    if (state->arg_len < AUDIO_SETCAL_CAL_BASIC_SIZE) {
        a90_console_printf("audio.setcal.execute.entry.%d.error=arg-too-short len=%llu\r\n",
                           state->sequence,
                           (unsigned long long)state->arg_len);
        return -EINVAL;
    }
    data_size = audio_setcal_read_le_i32(state->arg, state->arg_len, AUDIO_SETCAL_OFF_DATA_SIZE);
    cal_type = audio_setcal_read_le_i32(state->arg, state->arg_len, AUDIO_SETCAL_OFF_CAL_TYPE);
    cal_size = audio_setcal_read_le_i32(state->arg, state->arg_len, AUDIO_SETCAL_OFF_CAL_SIZE);
    state->buffer_number = audio_setcal_read_le_i32(state->arg,
                                                    state->arg_len,
                                                    AUDIO_SETCAL_OFF_BUFFER_NUMBER);
    if (data_size != (int32_t)state->arg_len || cal_type != entry->cal_type || cal_size < 0) {
        a90_console_printf("audio.setcal.execute.entry.%d.error=bad-arg-header data_size=%d arg_len=%llu cal_type=%d expected_cal_type=%d cal_size=%d\r\n",
                           state->sequence,
                           data_size,
                           (unsigned long long)state->arg_len,
                           cal_type,
                           entry->cal_type,
                           cal_size);
        return -EINVAL;
    }
    state->cal_type = cal_type;
    state->set_arg = (unsigned char *)calloc(1, state->arg_len);
    if (state->set_arg == NULL) {
        return -ENOMEM;
    }
    memcpy(state->set_arg, state->arg, state->arg_len);
    if (!state->has_payload) {
        mem_handle = audio_setcal_read_le_i32(state->set_arg,
                                              state->arg_len,
                                              AUDIO_SETCAL_OFF_MEM_HANDLE);
        if (cal_size == 0 && mem_handle >= 0) {
            audio_setcal_write_le_i32(state->set_arg,
                                      state->arg_len,
                                      AUDIO_SETCAL_OFF_MEM_HANDLE,
                                      -1);
            a90_console_printf("audio.setcal.execute.entry.%d.mem_handle_neutralized=1 original=%d\r\n",
                               state->sequence,
                               mem_handle);
        }
        a90_console_printf("audio.setcal.execute.entry.%d.header_only=1 cal_type=%d buffer=%d cal_size=%d\r\n",
                           state->sequence,
                           state->cal_type,
                           state->buffer_number,
                           audio_setcal_read_le_i32(state->set_arg,
                                                    state->arg_len,
                                                    AUDIO_SETCAL_OFF_CAL_SIZE));
        state->active = true;
        return 0;
    }
    if (cal_size <= 0) {
        a90_console_printf("audio.setcal.execute.entry.%d.error=payload-entry-without-positive-cal-size\r\n",
                           state->sequence);
        return -EINVAL;
    }
    rc = audio_setcal_prepare_payload_state(state, entry);
    if (rc < 0) {
        return rc;
    }
    if ((int32_t)state->payload_len != cal_size) {
        a90_console_printf("audio.setcal.execute.entry.%d.error=payload-size-mismatch payload=%llu cal_size=%d\r\n",
                           state->sequence,
                           (unsigned long long)state->payload_len,
                           cal_size);
        return -EINVAL;
    }
    state->alloc_arg = (unsigned char *)calloc(1, state->arg_len);
    state->dealloc_arg = (unsigned char *)calloc(1, state->arg_len);
    if (state->alloc_arg == NULL || state->dealloc_arg == NULL) {
        return -ENOMEM;
    }
    memcpy(state->alloc_arg, state->arg, state->arg_len);
    memcpy(state->dealloc_arg, state->arg, state->arg_len);
    audio_setcal_write_le_i32(state->set_arg,
                              state->arg_len,
                              AUDIO_SETCAL_OFF_MEM_HANDLE,
                              state->dmabuf_fd);
    audio_setcal_write_le_i32(state->set_arg,
                              state->arg_len,
                              AUDIO_SETCAL_OFF_CAL_SIZE,
                              (int32_t)state->payload_len);
    audio_setcal_write_le_i32(state->alloc_arg,
                              state->arg_len,
                              AUDIO_SETCAL_OFF_MEM_HANDLE,
                              state->dmabuf_fd);
    audio_setcal_write_le_i32(state->alloc_arg, state->arg_len, AUDIO_SETCAL_OFF_CAL_SIZE, 0);
    audio_setcal_write_le_i32(state->dealloc_arg,
                              state->arg_len,
                              AUDIO_SETCAL_OFF_MEM_HANDLE,
                              state->dmabuf_fd);
    audio_setcal_write_le_i32(state->dealloc_arg, state->arg_len, AUDIO_SETCAL_OFF_CAL_SIZE, 0);
    state->active = true;
    a90_console_printf("audio.setcal.execute.entry.%d.payload_ready=1 dmabuf_fd=%d bytes=%llu\r\n",
                       state->sequence,
                       state->dmabuf_fd,
                       (unsigned long long)state->payload_len);
    return 0;
}

static int audio_setcal_ioctl_cal(int fd,
                                  unsigned long request,
                                  const unsigned char *packet,
                                  size_t packet_len,
                                  const char *name,
                                  int sequence) {
    int32_t cal_type = audio_setcal_read_le_i32(packet, packet_len, AUDIO_SETCAL_OFF_CAL_TYPE);
    int32_t buffer_number = audio_setcal_read_le_i32(packet, packet_len, AUDIO_SETCAL_OFF_BUFFER_NUMBER);
    int32_t cal_size = audio_setcal_read_le_i32(packet, packet_len, AUDIO_SETCAL_OFF_CAL_SIZE);
    int32_t mem_handle = audio_setcal_read_le_i32(packet, packet_len, AUDIO_SETCAL_OFF_MEM_HANDLE);
    int rc;
    int saved_errno;

    a90_console_printf("audio.setcal.execute.ioctl.%d.name=%s\r\n", sequence, name);
    a90_console_printf("audio.setcal.execute.ioctl.%d.request=0x%08lx\r\n", sequence, request);
    a90_console_printf("audio.setcal.execute.ioctl.%d.cal_type=%d\r\n", sequence, cal_type);
    a90_console_printf("audio.setcal.execute.ioctl.%d.buffer=%d\r\n", sequence, buffer_number);
    a90_console_printf("audio.setcal.execute.ioctl.%d.cal_size=%d\r\n", sequence, cal_size);
    a90_console_printf("audio.setcal.execute.ioctl.%d.mem_handle=%d\r\n", sequence, mem_handle);
    a90_console_printf("audio.setcal.execute.ioctl.%d.arg_len=%llu\r\n",
                       sequence,
                       (unsigned long long)packet_len);
    rc = ioctl(fd, request, (void *)packet);
    saved_errno = rc == 0 ? 0 : errno;
    a90_console_printf("audio.setcal.execute.ioctl.%d.rc=%d errno=%d\r\n", sequence, rc, saved_errno);
    if (rc < 0) {
        return -saved_errno;
    }
    return 0;
}

static void audio_setcal_execute_session_init(struct audio_setcal_execute_session *session) {
    if (session == NULL) {
        return;
    }
    memset(session, 0, sizeof(*session));
    session->cal_fd = -1;
}

static int audio_setcal_execute_session_start(struct audio_setcal_execute_session *session,
                                              const struct audio_setcal_manifest_plan *plan) {
    int rc = 0;
    int index;

    if (session == NULL) {
        return -EINVAL;
    }
    audio_setcal_execute_session_init(session);
    if (plan == NULL || !plan->valid || plan->declared_entry_count != AUDIO_PROFILE_ACDB_SET_COUNT) {
        a90_console_printf("audio.setcal.execute.error=bad-manifest-plan\r\n");
        return -EINVAL;
    }
    for (index = 0; index < AUDIO_PROFILE_ACDB_SET_COUNT; ++index) {
        audio_setcal_execute_state_init(&session->states[index], &plan->entries[index]);
    }
    session->initialized = true;
    a90_console_printf("audio.setcal.execute.start=1\r\n");
    for (index = 0; index < AUDIO_PROFILE_ACDB_SET_COUNT; ++index) {
        rc = audio_setcal_prepare_exact_entry(&session->states[index], &plan->entries[index]);
        if (rc < 0) {
            a90_console_printf("audio.setcal.execute.prepare_failed.index=%d errno=%d\r\n", index, -rc);
            return rc;
        }
        ++session->prepared_count;
    }
    rc = audio_materialize_msm_audio_cal_devnode_once();
    if (rc < 0) {
        return rc;
    }
    session->cal_fd = open(AUDIO_SETCAL_DEV_MSM_AUDIO_CAL, O_RDWR | O_CLOEXEC);
    if (session->cal_fd < 0) {
        int saved_errno = errno;

        a90_console_printf("audio.setcal.execute.open.msm_audio_cal.open_ok=0 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    a90_console_printf("audio.setcal.execute.open.msm_audio_cal.open_ok=1\r\n");
    for (index = 0; index < AUDIO_PROFILE_ACDB_SET_COUNT; ++index) {
        if (session->states[index].has_payload) {
            rc = audio_setcal_ioctl_cal(session->cal_fd,
                                        AUDIO_SETCAL_IOCTL_ALLOCATE_CALIBRATION,
                                        session->states[index].alloc_arg,
                                        session->states[index].arg_len,
                                        "AUDIO_ALLOCATE_CALIBRATION",
                                        session->ioctl_sequence++);
            if (rc < 0) {
                a90_console_printf("audio.setcal.execute.allocate_failed.index=%d errno=%d\r\n",
                                   index,
                                   -rc);
                return rc;
            }
            session->states[index].allocated = true;
            ++session->allocated_count;
        }
        rc = audio_setcal_ioctl_cal(session->cal_fd,
                                    AUDIO_SETCAL_IOCTL_SET_CALIBRATION,
                                    session->states[index].set_arg,
                                    session->states[index].arg_len,
                                    "AUDIO_SET_CALIBRATION",
                                    session->ioctl_sequence++);
        if (rc < 0) {
            a90_console_printf("audio.setcal.execute.set_failed.index=%d errno=%d\r\n", index, -rc);
            return rc;
        }
        ++session->set_count;
    }
    a90_console_printf("audio.setcal.execute.hold_active=1\r\n");
    return 0;
}

static int audio_setcal_execute_session_cleanup(struct audio_setcal_execute_session *session,
                                                int prior_rc,
                                                int *ioctl_count_out) {
    int rc = prior_rc;
    int index;

    if (ioctl_count_out != NULL) {
        *ioctl_count_out = 0;
    }
    if (session == NULL) {
        return rc < 0 ? rc : -EINVAL;
    }
    if (session->cal_fd >= 0) {
        for (index = session->prepared_count; index > 0; --index) {
            int reverse_index = index - 1;
            int cleanup_rc;

            if (!session->states[reverse_index].allocated) {
                continue;
            }
            cleanup_rc = audio_setcal_ioctl_cal(session->cal_fd,
                                                AUDIO_SETCAL_IOCTL_DEALLOCATE_CALIBRATION,
                                                session->states[reverse_index].dealloc_arg,
                                                session->states[reverse_index].arg_len,
                                                "AUDIO_DEALLOCATE_CALIBRATION",
                                                session->ioctl_sequence++);
            if (cleanup_rc == 0) {
                session->states[reverse_index].allocated = false;
                ++session->deallocated_count;
            } else if (rc == 0) {
                rc = cleanup_rc;
            }
        }
        close(session->cal_fd);
        session->cal_fd = -1;
    }
    if (session->initialized) {
        for (index = 0; index < AUDIO_PROFILE_ACDB_SET_COUNT; ++index) {
            audio_setcal_execute_state_release(&session->states[index]);
        }
        session->initialized = false;
    }
    a90_console_printf("audio.setcal.execute.prepared_count=%d\r\n", session->prepared_count);
    a90_console_printf("audio.setcal.execute.allocated_count=%d\r\n", session->allocated_count);
    a90_console_printf("audio.setcal.execute.set_count=%d\r\n", session->set_count);
    a90_console_printf("audio.setcal.execute.deallocated_count=%d\r\n", session->deallocated_count);
    a90_console_printf("audio.setcal.execute.ioctl_count=%d\r\n", session->ioctl_sequence);
    a90_console_printf("audio.setcal.execute.ioctl_attempted=%d\r\n", session->ioctl_sequence > 0 ? 1 : 0);
    a90_console_printf("audio.setcal.execute.ok=%d\r\n", rc == 0 ? 1 : 0);
    if (ioctl_count_out != NULL) {
        *ioctl_count_out = session->ioctl_sequence;
    }
    return rc;
}

static int audio_setcal_execute_manifest_plan(const struct audio_setcal_manifest_plan *plan,
                                              int *ioctl_count_out) {
    struct audio_setcal_execute_session session;
    int rc;

    if (ioctl_count_out != NULL) {
        *ioctl_count_out = 0;
    }
    rc = audio_setcal_execute_session_start(&session, plan);
    return audio_setcal_execute_session_cleanup(&session, rc, ioctl_count_out);
}

static int audio_setcal_cmd(char **argv, int argc) {
    const char *profile_id = AUDIO_DEFAULT_PROFILE_ID;
    const char *manifest_path = NULL;
    const struct audio_speaker_profile *profile;
    struct audio_setcal_manifest_plan *manifest_plan = NULL;
    struct audio_setcal_allocation_plan allocation_plan;
    struct audio_setcal_ion_request_plan ion_request_plan;
    struct audio_setcal_manifest_totals totals;
    struct audio_setcal_manifest_totals load_totals;
    bool seen_profile = false;
    bool execute_mode = false;
    bool verify_manifest = false;
    bool prepare_manifest = false;
    bool load_manifest = false;
    bool manifest_action_requested;
    bool load_files;
    int argi;
    int index;

    memset(&totals, 0, sizeof(totals));
    memset(&load_totals, 0, sizeof(load_totals));
    memset(&allocation_plan, 0, sizeof(allocation_plan));
    memset(&ion_request_plan, 0, sizeof(ion_request_plan));
    for (argi = 2; argi < argc; ++argi) {
        if (argv == NULL || argv[argi] == NULL) {
            a90_console_printf("usage: audio setcal [profile] [--dry-run|--execute] [--manifest PATH --verify|--prepare|--load]\r\n");
            return -EINVAL;
        }
        if (strcmp(argv[argi], "--dry-run") == 0) {
            execute_mode = false;
        } else if (strcmp(argv[argi], "--execute") == 0) {
            execute_mode = true;
        } else if (strcmp(argv[argi], "--verify") == 0) {
            verify_manifest = true;
        } else if (strcmp(argv[argi], "--prepare") == 0) {
            prepare_manifest = true;
        } else if (strcmp(argv[argi], "--load") == 0) {
            load_manifest = true;
        } else if (strcmp(argv[argi], "--manifest") == 0) {
            if (argi + 1 >= argc || argv[argi + 1] == NULL) {
                a90_console_printf("usage: audio setcal [profile] [--dry-run|--execute] [--manifest PATH --verify|--prepare|--load]\r\n");
                return -EINVAL;
            }
            manifest_path = argv[++argi];
        } else if (!seen_profile) {
            profile_id = argv[argi];
            seen_profile = true;
        } else {
            a90_console_printf("usage: audio setcal [profile] [--dry-run|--execute] [--manifest PATH --verify|--prepare|--load]\r\n");
            return -EINVAL;
        }
    }

    profile = a90_audio_find_profile(profile_id);
    a90_console_printf("audio.setcal.version=1\r\n");
    a90_console_printf("audio.setcal.profile=%s\r\n", profile_id);
    a90_console_printf("audio.setcal.mode=%s\r\n", execute_mode ? "execute" : "dry-run");
    a90_console_printf("audio.setcal.ioctl_attempted=0\r\n");
    a90_console_printf("audio.setcal.execute_supported=1\r\n");
    a90_console_printf("audio.setcal.verify_requested=%d\r\n", verify_manifest ? 1 : 0);
    a90_console_printf("audio.setcal.prepare_requested=%d\r\n", prepare_manifest ? 1 : 0);
    a90_console_printf("audio.setcal.load_requested=%d\r\n", load_manifest ? 1 : 0);
    a90_console_printf("audio.setcal.execute_manifest_required=%d\r\n", execute_mode ? 1 : 0);
    a90_console_printf("audio.setcal.execute_auto_load=%d\r\n", execute_mode ? 1 : 0);
    a90_console_printf("audio.setcal.execute_native_replay_supported=%d\r\n", execute_mode ? 1 : 0);
    a90_console_printf("audio.setcal.manifest_path=%s\r\n", manifest_path != NULL ? manifest_path : "-");
    if (profile == NULL) {
        a90_console_printf("audio.setcal.error=unknown-profile\r\n");
        return -ENOENT;
    }
    if (!audio_setcal_plan_matches_profile(profile)) {
        a90_console_printf("audio.setcal.error=plan-order-mismatch entries=%d expected=%d\r\n",
                           audio_setcal_entry_count(),
                           AUDIO_PROFILE_ACDB_SET_COUNT);
        return -EINVAL;
    }

    a90_console_printf("audio.setcal.endpoint=%s\r\n", profile->endpoint);
    a90_console_printf("audio.setcal.private_payloads_required=1\r\n");
    a90_console_printf("audio.setcal.exact_set_arg_replay=1\r\n");
    a90_console_printf("audio.setcal.header_only_set_arg_replay=1\r\n");
    a90_console_printf("audio.setcal.devices.msm_audio_cal=%s\r\n", AUDIO_SETCAL_DEV_MSM_AUDIO_CAL);
    a90_console_printf("audio.setcal.devices.ion=%s\r\n", AUDIO_SETCAL_DEV_ION);
    a90_console_printf("audio.setcal.sequence=prepare_payloads,set_each,hold,deallocate_payload_entries_reverse\r\n");
    a90_console_printf("audio.setcal.entry.count=%d\r\n", audio_setcal_entry_count());
    a90_console_printf("audio.setcal.entry.payload.count=%d\r\n", audio_setcal_payload_entry_count());
    a90_console_printf("audio.setcal.helper.max_entries=16\r\n");
    print_int_list("audio.setcal.replay_order", profile->acdb_set_order, AUDIO_PROFILE_ACDB_SET_COUNT);
    print_int_list("audio.setcal.forbidden_stale_cal_types",
                   profile->forbidden_cal_types,
                   AUDIO_PROFILE_FORBIDDEN_CAL_COUNT);
    for (index = 0; index < audio_setcal_entry_count(); ++index) {
        char prefix[64];
        const struct audio_setcal_entry *entry = &AUDIO_INTERNAL_SPEAKER_SETCAL_PLAN[index];

        snprintf(prefix, sizeof(prefix), "audio.setcal.entry.%d", index);
        a90_console_printf("%s.sequence=%d\r\n", prefix, index);
        a90_console_printf("%s.kind=exact-set\r\n", prefix);
        a90_console_printf("%s.cal_type=%d\r\n", prefix, entry->cal_type);
        a90_console_printf("%s.role=%s\r\n", prefix, entry->role);
        a90_console_printf("%s.arg_required=1\r\n", prefix);
        a90_console_printf("%s.dmabuf_expected=%d\r\n", prefix, entry->dmabuf_expected ? 1 : 0);
        a90_console_printf("%s.payload_required=%d\r\n", prefix, entry->dmabuf_expected ? 1 : 0);
    }

    manifest_action_requested = verify_manifest || prepare_manifest || load_manifest || execute_mode;
    load_files = load_manifest || execute_mode;
    if (manifest_action_requested) {
        int verify_rc;

        if (manifest_path == NULL) {
            if (execute_mode) {
                a90_console_printf("audio.setcal.error=manifest-required-for-execute\r\n");
            } else {
                a90_console_printf("audio.setcal.error=manifest-required-for-verify-prepare-or-load\r\n");
            }
            a90_console_printf("audio.setcal.ioctl_attempted=0\r\n");
            return -EINVAL;
        }
        manifest_plan = calloc(1, sizeof(*manifest_plan));
        if (manifest_plan == NULL) {
            a90_console_printf("audio.setcal.error=manifest-plan-alloc-failed\r\n");
            a90_console_printf("audio.setcal.ioctl_attempted=0\r\n");
            return -ENOMEM;
        }
        verify_rc = audio_setcal_verify_manifest(profile,
                                                 manifest_path,
                                                 &totals,
                                                 load_files,
                                                 load_files ? &load_totals : NULL,
                                                 manifest_plan);
        if (verify_rc < 0) {
            a90_console_printf("audio.setcal.verify_failed=%d\r\n", -verify_rc);
            a90_console_printf("audio.setcal.ioctl_attempted=0\r\n");
            free(manifest_plan);
            return verify_rc;
        }
        a90_console_printf("audio.setcal.verify_ok=1\r\n");
        a90_console_printf("audio.setcal.manifest_plan.valid=%d\r\n", manifest_plan->valid ? 1 : 0);
        if (prepare_manifest) {
            a90_console_printf("audio.setcal.prepare.entry.count=%d\r\n", totals.entries);
            a90_console_printf("audio.setcal.prepare.arg_entries=%d\r\n", totals.arg_entries);
            a90_console_printf("audio.setcal.prepare.payload_entries=%d\r\n", totals.payload_entries);
            a90_console_printf("audio.setcal.prepare.arg_bytes=%lld\r\n", totals.arg_bytes);
            a90_console_printf("audio.setcal.prepare.payload_bytes=%lld\r\n", totals.payload_bytes);
            a90_console_printf("audio.setcal.prepare.devices_opened=0\r\n");
            a90_console_printf("audio.setcal.prepare.ioctl_attempted=0\r\n");
            a90_console_printf("audio.setcal.prepare_ok=1\r\n");
        }
        if (load_files) {
            a90_console_printf("audio.setcal.load.entry.count=%d\r\n", load_totals.entries);
            a90_console_printf("audio.setcal.load.arg_entries=%d\r\n", load_totals.arg_entries);
            a90_console_printf("audio.setcal.load.payload_entries=%d\r\n", load_totals.payload_entries);
            a90_console_printf("audio.setcal.load.files_opened=%d\r\n", load_totals.files_opened);
            a90_console_printf("audio.setcal.load.arg_bytes=%lld\r\n", load_totals.arg_bytes);
            a90_console_printf("audio.setcal.load.payload_bytes=%lld\r\n", load_totals.payload_bytes);
            a90_console_printf("audio.setcal.load.devices_opened=0\r\n");
            a90_console_printf("audio.setcal.load.ioctl_attempted=0\r\n");
            a90_console_printf("audio.setcal.load_ok=1\r\n");
        }
    }

    if (execute_mode) {
        int execute_rc;
        int ioctl_count = 0;

        audio_setcal_print_execute_plan(profile, manifest_plan);
        audio_setcal_allocation_plan_build(manifest_plan, &allocation_plan);
        audio_setcal_print_allocation_plan(&allocation_plan);
        audio_setcal_ion_request_plan_build(&allocation_plan, &ion_request_plan);
        audio_setcal_print_ion_request_plan(&ion_request_plan);
        execute_rc = audio_setcal_execute_manifest_plan(manifest_plan, &ioctl_count);
        a90_console_printf("audio.setcal.execute_rc=%d\r\n", execute_rc);
        a90_console_printf("audio.setcal.ioctl_attempted=%d\r\n", ioctl_count > 0 ? 1 : 0);
        free(manifest_plan);
        return execute_rc;
    }
    free(manifest_plan);
    a90_console_printf("audio.setcal.dry_run_ok=1\r\n");
    return 0;
}

static bool audio_parse_nonnegative_int(const char *text, int *value) {
    char *endptr = NULL;
    long parsed;

    if (text == NULL || text[0] == '\0' || value == NULL) {
        return false;
    }
    errno = 0;
    parsed = strtol(text, &endptr, 10);
    if (errno != 0 || endptr == text || *endptr != '\0' || parsed < 0 || parsed > INT_MAX) {
        return false;
    }
    *value = (int)parsed;
    return true;
}

static bool audio_play_mode_defaults(const struct audio_speaker_profile *profile,
                                     const char *mode,
                                     int *amplitude_milli,
                                     int *duration_ms) {
    if (profile == NULL || mode == NULL || amplitude_milli == NULL || duration_ms == NULL) {
        return false;
    }
    if (strcmp(mode, "probe") == 0) {
        *amplitude_milli = profile->probe_amplitude_milli;
        *duration_ms = profile->probe_duration_ms;
        return true;
    }
    if (strcmp(mode, "listen") == 0) {
        *amplitude_milli = profile->listen_amplitude_milli;
        *duration_ms = profile->listen_duration_ms;
        return true;
    }
    return false;
}

static long long audio_play_frame_bytes(const struct audio_speaker_profile *profile) {
    if (profile == NULL || profile->channels <= 0 || profile->bit_width <= 0 ||
        (profile->bit_width % 8) != 0) {
        return 0;
    }
    return (long long)profile->channels * (long long)(profile->bit_width / 8);
}

static long long audio_play_data_bytes(const struct audio_speaker_profile *profile, int duration_ms) {
    long long frame_bytes = audio_play_frame_bytes(profile);

    if (profile == NULL || duration_ms <= 0 || frame_bytes <= 0 || profile->sample_rate <= 0) {
        return 0;
    }
    return ((long long)profile->sample_rate * (long long)duration_ms * frame_bytes) / 1000LL;
}

static void audio_play_pcm_path(const struct audio_speaker_profile *profile,
                                char *path,
                                size_t path_size) {
    if (path == NULL || path_size == 0) {
        return;
    }
    if (profile == NULL) {
        path[0] = '\0';
        return;
    }
    snprintf(path, path_size, "/dev/snd/pcmC%dD%dp", profile->card, profile->pcm_device);
}

static const char *audio_play_pcm_node_state(const char *path, bool *ready) {
    struct stat st;

    if (ready != NULL) {
        *ready = false;
    }
    if (path == NULL || path[0] == '\0') {
        return "bad-path";
    }
    if (lstat(path, &st) < 0) {
        return errno == ENOENT ? "missing" : "stat-failed";
    }
    if (!S_ISCHR(st.st_mode)) {
        return "not-char";
    }
    if (ready != NULL) {
        *ready = true;
    }
    return "ok";
}

static bool audio_print_pcm_prereq(const char *prefix,
                                   const struct audio_speaker_profile *profile,
                                   char *pcm_path,
                                   size_t pcm_path_size) {
    bool ready = false;
    const char *state;

    if (prefix == NULL || prefix[0] == '\0') {
        prefix = "audio.prereq.snd";
    }
    audio_play_pcm_path(profile, pcm_path, pcm_path_size);
    state = audio_play_pcm_node_state(pcm_path, &ready);
    a90_console_printf("%s.pcm_path=%s\r\n", prefix, pcm_path);
    a90_console_printf("%s.pcm_node.state=%s\r\n", prefix, state);
    a90_console_printf("%s.pcm_node.ready=%d\r\n", prefix, ready ? 1 : 0);
    a90_console_printf("%s.snd_materialize_command=audio snd-materialize-once %s\r\n",
                       prefix,
                       AUDIO_SND_MATERIALIZE_TOKEN);
    return ready;
}

static bool audio_play_print_pcm_prereq(const struct audio_speaker_profile *profile,
                                        char *pcm_path,
                                        size_t pcm_path_size) {
    return audio_print_pcm_prereq("audio.play.prereq", profile, pcm_path, pcm_path_size);
}

static int audio_prereq_cmd(char **argv, int argc) {
    const struct audio_speaker_profile *profile;
    const char *profile_id = AUDIO_DEFAULT_PROFILE_ID;
    char pcm_path[64];
    bool snd_ready;

    if (argc > 3) {
        a90_console_printf("usage: audio prereq [%s]\r\n", AUDIO_DEFAULT_PROFILE_ID);
        return -EINVAL;
    }
    if (argc == 3 && argv != NULL && argv[2] != NULL) {
        profile_id = argv[2];
    }
    profile = a90_audio_find_profile(profile_id);
    a90_console_printf("audio.prereq.version=1\r\n");
    a90_console_printf("audio.prereq.profile=%s\r\n", profile_id);
    a90_console_printf("audio.prereq.read_only=1\r\n");
    a90_console_printf("audio.prereq.write_attempted=0\r\n");
    a90_console_printf("audio.prereq.playback_attempted=0\r\n");
    if (profile == NULL) {
        a90_console_printf("audio.prereq.error=unknown-profile\r\n");
        return -ENOENT;
    }
    a90_console_printf("audio.prereq.endpoint=%s\r\n", profile->endpoint);
    a90_console_printf("audio.prereq.card=%d\r\n", profile->card);
    a90_console_printf("audio.prereq.pcm_device=%d\r\n", profile->pcm_device);
    a90_console_printf("audio.prereq.stage_order=boot,adsp,snd,app_type,setcal,route,pcm,cleanup,rollback\r\n");
    a90_console_printf("audio.prereq.adsp.required=1\r\n");
    a90_console_printf("audio.prereq.adsp.command=audio adsp-boot-once %s\r\n", AUDIO_ADSP_BOOT_ONCE_TOKEN);
    a90_console_printf("audio.prereq.snd.required=1\r\n");
    snd_ready = audio_print_pcm_prereq("audio.prereq.snd", profile, pcm_path, sizeof(pcm_path));
    a90_console_printf("audio.prereq.app_type.required=1\r\n");
    a90_console_printf("audio.prereq.app_type.command=audio app-type %s --write\r\n", profile->id);
    a90_console_printf("audio.prereq.app_type.global_config=%s\r\n", profile->global_app_type_config);
    a90_console_printf("audio.prereq.setcal.required=1\r\n");
    a90_console_printf("audio.prereq.setcal.manifest=%s\r\n", AUDIO_SETCAL_DEFAULT_MANIFEST_PATH);
    a90_console_printf("audio.prereq.setcal.command=audio setcal %s --manifest %s --execute\r\n",
                       profile->id,
                       AUDIO_SETCAL_DEFAULT_MANIFEST_PATH);
    print_int_list("audio.prereq.setcal.order", profile->acdb_set_order, AUDIO_PROFILE_ACDB_SET_COUNT);
    a90_console_printf("audio.prereq.route.required=1\r\n");
    a90_console_printf("audio.prereq.route.command=audio route %s --apply --layer core\r\n", profile->id);
    a90_console_printf("audio.prereq.play.required=1\r\n");
    a90_console_printf("audio.prereq.play.command=audio play %s --mode probe --execute\r\n", profile->id);
    a90_console_printf("audio.prereq.ready.snd=%d\r\n", snd_ready ? 1 : 0);
    a90_console_printf("audio.prereq.ready.runtime_state_verified=0\r\n");
    a90_console_printf("audio.prereq.ready.play=0\r\n");
    return 0;
}

static bool audio_pcm_param_is_mask(int parameter) {
    return parameter >= SNDRV_PCM_HW_PARAM_FIRST_MASK && parameter <= SNDRV_PCM_HW_PARAM_LAST_MASK;
}

static bool audio_pcm_param_is_interval(int parameter) {
    return parameter >= SNDRV_PCM_HW_PARAM_FIRST_INTERVAL && parameter <= SNDRV_PCM_HW_PARAM_LAST_INTERVAL;
}

static struct snd_mask *audio_pcm_param_to_mask(struct snd_pcm_hw_params *params, int parameter) {
    return &params->masks[parameter - SNDRV_PCM_HW_PARAM_FIRST_MASK];
}

static struct snd_interval *audio_pcm_param_to_interval(struct snd_pcm_hw_params *params, int parameter) {
    return &params->intervals[parameter - SNDRV_PCM_HW_PARAM_FIRST_INTERVAL];
}

static void audio_pcm_param_init(struct snd_pcm_hw_params *params) {
    int parameter;

    memset(params, 0, sizeof(*params));
    for (parameter = SNDRV_PCM_HW_PARAM_FIRST_MASK; parameter <= SNDRV_PCM_HW_PARAM_LAST_MASK; ++parameter) {
        struct snd_mask *mask = audio_pcm_param_to_mask(params, parameter);
        mask->bits[0] = ~0U;
        mask->bits[1] = ~0U;
    }
    for (parameter = SNDRV_PCM_HW_PARAM_FIRST_INTERVAL; parameter <= SNDRV_PCM_HW_PARAM_LAST_INTERVAL; ++parameter) {
        struct snd_interval *interval = audio_pcm_param_to_interval(params, parameter);
        interval->min = 0;
        interval->max = ~0U;
    }
    params->rmask = ~0U;
    params->cmask = 0;
    params->info = ~0U;
}

static void audio_pcm_param_set_mask(struct snd_pcm_hw_params *params, int parameter, unsigned int bit) {
    struct snd_mask *mask;

    if (params == NULL || !audio_pcm_param_is_mask(parameter) || bit >= SNDRV_MASK_MAX) {
        return;
    }
    mask = audio_pcm_param_to_mask(params, parameter);
    memset(mask, 0, sizeof(*mask));
    mask->bits[bit >> 5] |= (uint32_t)(1U << (bit & 31U));
}

static void audio_pcm_param_set_int(struct snd_pcm_hw_params *params, int parameter, unsigned int value) {
    struct snd_interval *interval;

    if (params == NULL || !audio_pcm_param_is_interval(parameter)) {
        return;
    }
    interval = audio_pcm_param_to_interval(params, parameter);
    interval->min = value;
    interval->max = value;
    interval->integer = 1;
}

static void audio_pcm_param_set_min(struct snd_pcm_hw_params *params, int parameter, unsigned int value) {
    struct snd_interval *interval;

    if (params == NULL || !audio_pcm_param_is_interval(parameter)) {
        return;
    }
    interval = audio_pcm_param_to_interval(params, parameter);
    interval->min = value;
}

static int audio_pcm_configure_fd(int fd, const struct audio_speaker_profile *profile) {
    struct snd_pcm_hw_params hw_params;
    struct snd_pcm_sw_params sw_params;
    int rc;

    if (fd < 0 || profile == NULL || profile->channels <= 0 || profile->channels > AUDIO_PCM_MAX_CHANNELS ||
        profile->sample_rate <= 0 || profile->bit_width != 16) {
        a90_console_printf("audio.play.execute.error=bad-pcm-profile\r\n");
        return -EINVAL;
    }

    audio_pcm_param_init(&hw_params);
    audio_pcm_param_set_mask(&hw_params, SNDRV_PCM_HW_PARAM_FORMAT, SNDRV_PCM_FORMAT_S16_LE);
    audio_pcm_param_set_mask(&hw_params, SNDRV_PCM_HW_PARAM_SUBFORMAT, SNDRV_PCM_SUBFORMAT_STD);
    audio_pcm_param_set_mask(&hw_params, SNDRV_PCM_HW_PARAM_ACCESS, SNDRV_PCM_ACCESS_RW_INTERLEAVED);
    audio_pcm_param_set_min(&hw_params, SNDRV_PCM_HW_PARAM_PERIOD_SIZE, AUDIO_PCM_PERIOD_SIZE);
    audio_pcm_param_set_int(&hw_params, SNDRV_PCM_HW_PARAM_SAMPLE_BITS, (unsigned int)profile->bit_width);
    audio_pcm_param_set_int(&hw_params,
                            SNDRV_PCM_HW_PARAM_FRAME_BITS,
                            (unsigned int)(profile->bit_width * profile->channels));
    audio_pcm_param_set_int(&hw_params, SNDRV_PCM_HW_PARAM_CHANNELS, (unsigned int)profile->channels);
    audio_pcm_param_set_int(&hw_params, SNDRV_PCM_HW_PARAM_PERIODS, AUDIO_PCM_PERIOD_COUNT);
    audio_pcm_param_set_int(&hw_params, SNDRV_PCM_HW_PARAM_RATE, (unsigned int)profile->sample_rate);

    errno = 0;
    rc = ioctl(fd, SNDRV_PCM_IOCTL_HW_PARAMS, &hw_params);
    a90_console_printf("audio.play.execute.hw_params.rc=%d errno=%d\r\n", rc, rc < 0 ? errno : 0);
    if (rc < 0) {
        return -errno;
    }

    memset(&sw_params, 0, sizeof(sw_params));
    sw_params.tstamp_mode = SNDRV_PCM_TSTAMP_ENABLE;
    sw_params.period_step = 1;
    sw_params.avail_min = 1;
    sw_params.xfer_align = AUDIO_PCM_PERIOD_SIZE / 2;
    sw_params.start_threshold = (AUDIO_PCM_PERIOD_COUNT * AUDIO_PCM_PERIOD_SIZE) / 2;
    sw_params.stop_threshold = AUDIO_PCM_PERIOD_COUNT * AUDIO_PCM_PERIOD_SIZE;
    sw_params.silence_threshold = 0;
    sw_params.silence_size = 0;

    errno = 0;
    rc = ioctl(fd, SNDRV_PCM_IOCTL_SW_PARAMS, &sw_params);
    a90_console_printf("audio.play.execute.sw_params.rc=%d errno=%d\r\n", rc, rc < 0 ? errno : 0);
    if (rc < 0) {
        return -errno;
    }

    errno = 0;
    rc = ioctl(fd, SNDRV_PCM_IOCTL_PREPARE);
    a90_console_printf("audio.play.execute.prepare.rc=%d errno=%d\r\n", rc, rc < 0 ? errno : 0);
    if (rc < 0) {
        return -errno;
    }

    return 0;
}

static int16_t audio_pcm_triangle_sample(int64_t frame_index,
                                         int sample_rate,
                                         int amplitude_milli) {
    int amplitude = (32767 * amplitude_milli) / 1000;
    int tone_period = sample_rate / AUDIO_PCM_TONE_HZ;
    int phase;
    int half_period;
    int ramp;

    if (amplitude <= 0 || tone_period < 4) {
        return 0;
    }
    phase = (int)(frame_index % tone_period);
    half_period = tone_period / 2;
    ramp = phase < half_period ? phase : tone_period - phase;
    return (int16_t)(((ramp * 4 * amplitude) / tone_period) - amplitude);
}

static void audio_pcm_fill_tone(int16_t *buffer,
                                int frames,
                                const struct audio_speaker_profile *profile,
                                int amplitude_milli,
                                int64_t start_frame) {
    int frame_index;
    int channel_index;

    if (buffer == NULL || profile == NULL || frames <= 0) {
        return;
    }
    for (frame_index = 0; frame_index < frames; ++frame_index) {
        int16_t sample = audio_pcm_triangle_sample(start_frame + frame_index,
                                                  profile->sample_rate,
                                                  amplitude_milli);
        for (channel_index = 0; channel_index < profile->channels; ++channel_index) {
            buffer[(frame_index * profile->channels) + channel_index] = sample;
        }
    }
}

static int audio_pcm_write_frames(int fd,
                                  const int16_t *buffer,
                                  int frames) {
    struct snd_xferi transfer;
    int rc;

    memset(&transfer, 0, sizeof(transfer));
    transfer.buf = (void *)buffer;
    transfer.frames = (snd_pcm_uframes_t)frames;

    errno = 0;
    rc = ioctl(fd, SNDRV_PCM_IOCTL_WRITEI_FRAMES, &transfer);
    if (rc < 0) {
        a90_console_printf("audio.play.execute.write.rc=%d errno=%d frames=%d\r\n", rc, errno, frames);
        return -errno;
    }
    if (transfer.result < 0) {
        a90_console_printf("audio.play.execute.write.result=%ld frames=%d\r\n",
                           (long)transfer.result,
                           frames);
        return (int)transfer.result;
    }
    if (transfer.result != frames) {
        a90_console_printf("audio.play.execute.write.short=%ld frames=%d\r\n",
                           (long)transfer.result,
                           frames);
        return -EIO;
    }
    return 0;
}

static int audio_play_execute_pcm(const struct audio_speaker_profile *profile,
                                  const char *mode,
                                  int amplitude_milli,
                                  int duration_ms) {
    char pcm_path[64];
    int16_t *buffer;
    int fd;
    int total_frames;
    int frames_done = 0;
    int chunk_count = 0;
    int frame_bytes;
    int buffer_bytes;
    int rc = 0;

    if (profile == NULL || mode == NULL) {
        return -EINVAL;
    }
    frame_bytes = (int)audio_play_frame_bytes(profile);
    total_frames = (profile->sample_rate * duration_ms) / 1000;
    buffer_bytes = AUDIO_PCM_PERIOD_SIZE * frame_bytes;
    if (total_frames <= 0 || frame_bytes <= 0 || buffer_bytes <= 0 ||
        profile->channels <= 0 || profile->channels > AUDIO_PCM_MAX_CHANNELS ||
        profile->bit_width != 16) {
        a90_console_printf("audio.play.execute.error=bad-pcm-geometry\r\n");
        return -EINVAL;
    }

    audio_play_pcm_path(profile, pcm_path, sizeof(pcm_path));
    a90_console_printf("audio.play.execute.version=1\r\n");
    a90_console_printf("audio.play.execute.profile=%s\r\n", profile->id);
    a90_console_printf("audio.play.execute.mode=%s\r\n", mode);
    a90_console_printf("audio.play.execute.pcm_path=%s\r\n", pcm_path);
    a90_console_printf("audio.play.execute.tone_hz=%d\r\n", AUDIO_PCM_TONE_HZ);
    a90_console_printf("audio.play.execute.total_frames=%d\r\n", total_frames);
    a90_console_printf("audio.play.execute.buffer_bytes=%d\r\n", buffer_bytes);

    buffer = malloc((size_t)buffer_bytes);
    if (buffer == NULL) {
        a90_console_printf("audio.play.execute.error=alloc-failed errno=%d bytes=%d\r\n", errno, buffer_bytes);
        return -ENOMEM;
    }

    a90_console_printf("audio.play.execute.alsa_open_attempted=1\r\n");
    errno = 0;
    fd = open(pcm_path, O_WRONLY | O_CLOEXEC);
    a90_console_printf("audio.play.execute.open.rc=%d errno=%d\r\n", fd >= 0 ? 0 : -1, fd < 0 ? errno : 0);
    if (fd < 0) {
        rc = -errno;
        free(buffer);
        return rc;
    }

    a90_console_printf("audio.play.execute.ioctl_attempted=1\r\n");
    rc = audio_pcm_configure_fd(fd, profile);
    if (rc < 0) {
        close(fd);
        free(buffer);
        return rc;
    }

    a90_console_printf("audio.play.playback_attempted=1\r\n");
    a90_console_printf("audio.play.execute.pcm_write_attempted=1\r\n");
    a90_console_printf("A90_LISTEN_WINDOW_BEGIN profile=%s mode=%s amplitude_milli=%d duration_ms=%d\r\n",
                       profile->id,
                       mode,
                       amplitude_milli,
                       duration_ms);
    while (frames_done < total_frames) {
        int frames_this_chunk = total_frames - frames_done;
        if (frames_this_chunk > AUDIO_PCM_PERIOD_SIZE) {
            frames_this_chunk = AUDIO_PCM_PERIOD_SIZE;
        }
        audio_pcm_fill_tone(buffer, frames_this_chunk, profile, amplitude_milli, frames_done);
        rc = audio_pcm_write_frames(fd, buffer, frames_this_chunk);
        if (rc < 0) {
            a90_console_printf("A90_LISTEN_WINDOW_END rc=%d chunks=%d frames=%d bytes=%lld\r\n",
                               rc,
                               chunk_count,
                               frames_done,
                               (long long)frames_done * (long long)frame_bytes);
            ioctl(fd, SNDRV_PCM_IOCTL_DROP);
            close(fd);
            free(buffer);
            return rc;
        }
        frames_done += frames_this_chunk;
        ++chunk_count;
    }

    errno = 0;
    rc = ioctl(fd, SNDRV_PCM_IOCTL_DRAIN);
    a90_console_printf("audio.play.execute.drain.rc=%d errno=%d\r\n", rc, rc < 0 ? errno : 0);
    if (rc < 0) {
        rc = -errno;
    }

    close(fd);
    free(buffer);
    a90_console_printf("A90_LISTEN_WINDOW_END rc=%d chunks=%d frames=%d bytes=%lld\r\n",
                       rc,
                       chunk_count,
                       frames_done,
                       (long long)frames_done * (long long)frame_bytes);
    a90_console_printf("audio.play.execute.done=%d chunks=%d frames=%d bytes=%lld\r\n",
                       rc == 0 ? 1 : 0,
                       chunk_count,
                       frames_done,
                       (long long)frames_done * (long long)frame_bytes);
    return rc;
}

static void audio_play_print_execute_plan(const struct audio_speaker_profile *profile,
                                          const char *mode,
                                          int amplitude_milli,
                                          int duration_ms) {
    long long frame_bytes = audio_play_frame_bytes(profile);
    long long data_bytes = audio_play_data_bytes(profile, duration_ms);
    long long period_bytes = frame_bytes * AUDIO_PCM_PERIOD_SIZE;
    long long chunks = period_bytes > 0 ? (data_bytes + period_bytes - 1) / period_bytes : 0;
    char pcm_path[64];

    if (profile == NULL) {
        return;
    }
    audio_play_pcm_path(profile, pcm_path, sizeof(pcm_path));
    a90_console_printf("audio.play.execute.plan.version=1\r\n");
    a90_console_printf("audio.play.execute.plan.profile=%s\r\n", profile->id);
    a90_console_printf("audio.play.execute.plan.mode=%s\r\n", mode);
    a90_console_printf("audio.play.execute.plan.pcm_path=%s\r\n", pcm_path);
    a90_console_printf("audio.play.execute.plan.period_size=%d\r\n", AUDIO_PCM_PERIOD_SIZE);
    a90_console_printf("audio.play.execute.plan.period_count=%d\r\n", AUDIO_PCM_PERIOD_COUNT);
    a90_console_printf("audio.play.execute.plan.frame_bytes=%lld\r\n", frame_bytes);
    a90_console_printf("audio.play.execute.plan.period_bytes=%lld\r\n", period_bytes);
    a90_console_printf("audio.play.execute.plan.data_bytes=%lld\r\n", data_bytes);
    a90_console_printf("audio.play.execute.plan.chunks=%lld\r\n", chunks);
    a90_console_printf("audio.play.execute.plan.amplitude_milli=%d\r\n", amplitude_milli);
    a90_console_printf("audio.play.execute.plan.duration_ms=%d\r\n", duration_ms);
    a90_console_printf("audio.play.execute.plan.waveform=s16le-stereo-bounded-tone\r\n");
    a90_console_printf("audio.play.execute.plan.sequence=open_pcm,configure_hw_params,write_bounded_tone,drain,close_pcm\r\n");
    a90_console_printf("audio.play.execute.plan.foreground_prime_adsp=1\r\n");
    a90_console_printf("audio.play.execute.plan.foreground_prime_adsp_wait=0\r\n");
    a90_console_printf("audio.play.execute.plan.alsa_open_attempted=0\r\n");
    a90_console_printf("audio.play.execute.plan.ioctl_attempted=0\r\n");
    a90_console_printf("audio.play.execute.plan.pcm_write_attempted=0\r\n");
}

static int audio_play_async_open_status(int flags) {
    if (ensure_dir(AUDIO_PLAY_ASYNC_DIR, 0700) < 0) {
        return -1;
    }
    return open(AUDIO_PLAY_ASYNC_STATUS_PATH, flags | O_CLOEXEC | O_NOFOLLOW, 0600);
}

static void audio_play_async_statusf(const char *fmt, ...) {
    char line[512];
    va_list ap;
    int fd;
    int len;

    fd = audio_play_async_open_status(O_WRONLY | O_CREAT | O_APPEND);
    if (fd < 0) {
        return;
    }
    va_start(ap, fmt);
    len = vsnprintf(line, sizeof(line), fmt, ap);
    va_end(ap);
    if (len > 0) {
        if ((size_t)len >= sizeof(line)) {
            len = (int)sizeof(line) - 1;
        }
        write_all(fd, line, (size_t)len);
    }
    close(fd);
}

static void audio_play_async_reset_status(const struct audio_speaker_profile *profile,
                                          const char *mode,
                                          int amplitude_milli,
                                          int duration_ms,
                                          const char *manifest_path) {
    (void)ensure_dir(AUDIO_PLAY_ASYNC_DIR, 0700);
    (void)unlink(AUDIO_PLAY_ASYNC_STATUS_PATH);
    (void)unlink(AUDIO_PLAY_ASYNC_LOG_PATH);
    audio_play_async_statusf("audio.play.worker.status.version=1\n");
    audio_play_async_statusf("audio.play.worker.profile=%s\n", profile != NULL ? profile->id : "-");
    audio_play_async_statusf("audio.play.worker.mode=%s\n", mode != NULL ? mode : "-");
    audio_play_async_statusf("audio.play.worker.amplitude_milli=%d\n", amplitude_milli);
    audio_play_async_statusf("audio.play.worker.duration_ms=%d\n", duration_ms);
    audio_play_async_statusf("audio.play.worker.manifest=%s\n",
                             manifest_path != NULL ? manifest_path : "-");
    audio_play_async_statusf("audio.play.worker.done=0\n");
}

static int audio_play_status_cmd(void) {
    int fd;
    char buffer[512];
    ssize_t rd;

    a90_console_printf("audio.play_status.version=1\r\n");
    a90_console_printf("audio.play_status.path=%s\r\n", AUDIO_PLAY_ASYNC_STATUS_PATH);
    a90_console_printf("audio.play_status.log_path=%s\r\n", AUDIO_PLAY_ASYNC_LOG_PATH);
    fd = open(AUDIO_PLAY_ASYNC_STATUS_PATH, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        a90_console_printf("audio.play_status.present=0 errno=%d\r\n", errno);
        return 0;
    }
    a90_console_printf("audio.play_status.present=1\r\n");
    while ((rd = read(fd, buffer, sizeof(buffer))) > 0) {
        size_t index;

        for (index = 0; index < (size_t)rd; ++index) {
            if (buffer[index] == '\n') {
                a90_console_write("\r\n", 2);
            } else {
                a90_console_write(&buffer[index], 1);
            }
        }
    }
    close(fd);
    a90_console_printf("audio.play_status.read_complete=1\r\n");
    return 0;
}

static bool audio_wait_for_audio_condition(const char *label,
                                           int timeout_ms,
                                           int sleep_ms,
                                           bool (*predicate)(const struct audio_speaker_profile *),
                                           const struct audio_speaker_profile *profile) {
    int elapsed_ms = 0;

    if (label == NULL || predicate == NULL || sleep_ms <= 0 || timeout_ms < 0) {
        return false;
    }
    while (elapsed_ms <= timeout_ms) {
        if (predicate(profile)) {
            a90_console_printf("audio.play.integrated.wait.%s.ready=1 elapsed_ms=%d\r\n", label, elapsed_ms);
            return true;
        }
        usleep((useconds_t)sleep_ms * 1000U);
        elapsed_ms += sleep_ms;
    }
    a90_console_printf("audio.play.integrated.wait.%s.ready=0 elapsed_ms=%d\r\n", label, elapsed_ms);
    return false;
}

static bool audio_wait_for_manifest_ready(const char *manifest_path) {
    int elapsed_ms = 0;

    a90_console_printf("audio.play.integrated.wait.manifest.path=%s\r\n",
                       manifest_path != NULL ? manifest_path : "-");
    audio_play_async_statusf("audio.play.worker.manifest_wait_started=1\n");
    audio_play_async_statusf("audio.play.worker.manifest_wait_path=%s\n",
                             manifest_path != NULL ? manifest_path : "-");
    if (manifest_path == NULL || manifest_path[0] == '\0') {
        a90_console_printf("audio.play.integrated.wait.manifest.ready=0 elapsed_ms=0 errno=%d\r\n",
                           EINVAL);
        audio_play_async_statusf("audio.play.worker.manifest_ready=0 elapsed_ms=0 errno=%d\n",
                                 EINVAL);
        return false;
    }
    while (elapsed_ms <= AUDIO_PLAY_MANIFEST_WAIT_TIMEOUT_MS) {
        if (access(manifest_path, R_OK) == 0) {
            a90_console_printf("audio.play.integrated.wait.manifest.ready=1 elapsed_ms=%d\r\n",
                               elapsed_ms);
            audio_play_async_statusf("audio.play.worker.manifest_ready=1 elapsed_ms=%d\n",
                                     elapsed_ms);
            return true;
        }
        usleep((useconds_t)AUDIO_PLAY_MANIFEST_WAIT_SLEEP_MS * 1000U);
        elapsed_ms += AUDIO_PLAY_MANIFEST_WAIT_SLEEP_MS;
    }
    a90_console_printf("audio.play.integrated.wait.manifest.ready=0 elapsed_ms=%d errno=%d\r\n",
                       elapsed_ms,
                       ENOENT);
    audio_play_async_statusf("audio.play.worker.manifest_ready=0 elapsed_ms=%d errno=%d\n",
                             elapsed_ms,
                             ENOENT);
    return false;
}

static bool audio_condition_sound_control_ready(const struct audio_speaker_profile *profile) {
    (void)profile;
    return count_dir_entries_matching(AUDIO_SOUND_CLASS_DIR, "control") > 0;
}

static bool audio_condition_pcm_ready(const struct audio_speaker_profile *profile) {
    char pcm_path[64];
    bool ready = false;

    if (profile == NULL) {
        return false;
    }
    audio_play_pcm_path(profile, pcm_path, sizeof(pcm_path));
    (void)audio_play_pcm_node_state(pcm_path, &ready);
    return ready;
}

static int audio_play_run_adsp_stage(const struct audio_speaker_profile *profile, bool boot_allowed) {
    char *adsp_argv[] = {"audio", "adsp-boot-once", AUDIO_ADSP_BOOT_ONCE_TOKEN};
    int rc = 0;

    (void)profile;
    a90_console_printf("audio.play.integrated.stage=adsp\r\n");
    a90_console_printf("audio.play.integrated.adsp.boot_allowed=%d\r\n", boot_allowed ? 1 : 0);
    if (boot_allowed) {
        rc = audio_adsp_boot_once(adsp_argv, 3);
        a90_console_printf("audio.play.integrated.adsp.rc=%d\r\n", rc);
        if (rc == -EALREADY) {
            a90_console_printf("audio.play.integrated.adsp.already_ready=1\r\n");
            rc = 0;
        }
        if (rc < 0) {
            return rc;
        }
    } else {
        a90_console_printf("audio.play.integrated.adsp.boot_skipped=1 reason=foreground_prime_no_wait\r\n");
    }
    if (!audio_wait_for_audio_condition("sound_control", 70000, 250, audio_condition_sound_control_ready, profile)) {
        return -ETIMEDOUT;
    }
    return 0;
}

static int audio_play_kick_adsp_stage_no_wait(const struct audio_speaker_profile *profile) {
    char *adsp_argv[] = {"audio", "adsp-boot-once", AUDIO_ADSP_BOOT_ONCE_TOKEN};
    int rc;

    (void)profile;
    a90_console_printf("audio.play.execute.foreground_prime_adsp=1\r\n");
    a90_console_printf("audio.play.execute.foreground_prime_adsp.wait=0\r\n");
    rc = audio_adsp_boot_once(adsp_argv, 3);
    a90_console_printf("audio.play.execute.foreground_prime_adsp.rc=%d\r\n", rc);
    if (rc == -EALREADY) {
        a90_console_printf("audio.play.execute.foreground_prime_adsp.already_ready=1\r\n");
        rc = 0;
    }
    return rc;
}

static int audio_play_run_snd_stage(const struct audio_speaker_profile *profile) {
    char *snd_argv[] = {"audio", "snd-materialize-once", AUDIO_SND_MATERIALIZE_TOKEN};
    int rc;

    a90_console_printf("audio.play.integrated.stage=snd\r\n");
    rc = audio_snd_materialize_once(snd_argv, 3);
    a90_console_printf("audio.play.integrated.snd.rc=%d\r\n", rc);
    if (rc < 0) {
        return rc;
    }
    if (!audio_wait_for_audio_condition("pcm_node", 10000, 250, audio_condition_pcm_ready, profile)) {
        return -ETIMEDOUT;
    }
    return 0;
}

static int audio_play_run_app_type_stage(const struct audio_speaker_profile *profile) {
    char *app_argv[] = {"audio", "app-type", NULL, "--write"};
    int rc;

    if (profile == NULL) {
        return -EINVAL;
    }
    app_argv[2] = (char *)profile->id;
    a90_console_printf("audio.play.integrated.stage=app_type\r\n");
    rc = audio_app_type_cmd(app_argv, 4);
    a90_console_printf("audio.play.integrated.app_type.rc=%d\r\n", rc);
    return rc;
}

static int audio_play_load_setcal_session(const struct audio_speaker_profile *profile,
                                          const char *manifest_path,
                                          struct audio_setcal_execute_session *session) {
    struct audio_setcal_manifest_plan plan;
    struct audio_setcal_manifest_totals totals;
    int rc;

    if (profile == NULL || manifest_path == NULL || session == NULL) {
        return -EINVAL;
    }
    memset(&plan, 0, sizeof(plan));
    memset(&totals, 0, sizeof(totals));
    a90_console_printf("audio.play.integrated.stage=setcal\r\n");
    a90_console_printf("audio.play.integrated.setcal.manifest=%s\r\n", manifest_path);
    if (!audio_wait_for_manifest_ready(manifest_path)) {
        return -ETIMEDOUT;
    }
    a90_console_printf("audio.play.integrated.setcal.verify_load_files=0\r\n");
    rc = audio_setcal_verify_manifest(profile, manifest_path, &totals, false, NULL, &plan);
    a90_console_printf("audio.play.integrated.setcal.verify_rc=%d\r\n", rc);
    if (rc < 0) {
        return rc;
    }
    rc = audio_setcal_execute_session_start(session, &plan);
    a90_console_printf("audio.play.integrated.setcal.start_rc=%d\r\n", rc);
    return rc;
}

static int audio_play_run_route_stage(const struct audio_speaker_profile *profile, bool reset) {
    char *route_argv[] = {"audio", "route", NULL, NULL, "--layer", "core"};
    int rc;

    if (profile == NULL) {
        return -EINVAL;
    }
    route_argv[2] = (char *)profile->id;
    route_argv[3] = reset ? "--reset" : "--apply";
    a90_console_printf("audio.play.integrated.stage=%s\r\n", reset ? "route_reset" : "route_apply");
    rc = audio_route_cmd(route_argv, 6);
    a90_console_printf("audio.play.integrated.%s.rc=%d\r\n", reset ? "route_reset" : "route_apply", rc);
    return rc;
}

static int audio_play_execute_integrated(const struct audio_speaker_profile *profile,
                                         const char *mode,
                                         int amplitude_milli,
                                         int duration_ms,
                                         const char *manifest_path,
                                         bool adsp_prebooted) {
    struct audio_setcal_execute_session setcal_session;
    bool setcal_started = false;
    bool route_apply_attempted = false;
    int rc;
    int cleanup_rc;
    int ioctl_count = 0;

    audio_setcal_execute_session_init(&setcal_session);
    if (manifest_path == NULL || manifest_path[0] == '\0') {
        manifest_path = AUDIO_SETCAL_DEFAULT_MANIFEST_PATH;
    }
    a90_console_printf("audio.play.integrated.version=1\r\n");
    a90_console_printf("audio.play.integrated.profile=%s\r\n", profile != NULL ? profile->id : "-");
    a90_console_printf("audio.play.integrated.manifest=%s\r\n", manifest_path);
    a90_console_printf("audio.play.integrated.adsp_prebooted=%d\r\n", adsp_prebooted ? 1 : 0);
    a90_console_printf("audio.play.integrated.sequence=adsp,snd,app_type,manifest_wait,setcal_hold,route_core,pcm,route_core_reset,setcal_deallocate\r\n");
    rc = audio_play_run_adsp_stage(profile, !adsp_prebooted);
    if (rc < 0) {
        goto done;
    }
    rc = audio_play_run_snd_stage(profile);
    if (rc < 0) {
        goto done;
    }
    rc = audio_play_run_app_type_stage(profile);
    if (rc < 0) {
        goto done;
    }
    rc = audio_play_load_setcal_session(profile, manifest_path, &setcal_session);
    if (rc < 0) {
        goto done;
    }
    setcal_started = true;
    route_apply_attempted = true;
    rc = audio_play_run_route_stage(profile, false);
    if (rc < 0) {
        goto done;
    }
    rc = audio_play_execute_pcm(profile, mode, amplitude_milli, duration_ms);

done:
    if (route_apply_attempted) {
        cleanup_rc = audio_play_run_route_stage(profile, true);
        if (cleanup_rc < 0 && rc == 0) {
            rc = cleanup_rc;
        }
    }
    if (setcal_started || setcal_session.initialized || setcal_session.cal_fd >= 0) {
        cleanup_rc = audio_setcal_execute_session_cleanup(&setcal_session, rc, &ioctl_count);
        if (cleanup_rc < 0) {
            rc = cleanup_rc;
        }
    }
    a90_console_printf("audio.play.integrated.setcal_ioctl_count=%d\r\n", ioctl_count);
    a90_console_printf("audio.play.integrated.done=%d rc=%d\r\n", rc == 0 ? 1 : 0, rc);
    return rc;
}

static int audio_play_start_worker(const struct audio_speaker_profile *profile,
                                   const char *mode,
                                   int amplitude_milli,
                                   int duration_ms,
                                   const char *manifest_path,
                                   bool adsp_prebooted) {
    pid_t pid;

    if (manifest_path == NULL || manifest_path[0] == '\0') {
        manifest_path = AUDIO_SETCAL_DEFAULT_MANIFEST_PATH;
    }
    audio_play_async_reset_status(profile, mode, amplitude_milli, duration_ms, manifest_path);
    audio_play_async_statusf("audio.play.worker.adsp_prebooted=%d\n", adsp_prebooted ? 1 : 0);
    pid = fork();
    if (pid < 0) {
        a90_console_printf("audio.play.worker.spawn_failed errno=%d\r\n", errno);
        audio_play_async_statusf("audio.play.worker.spawn_failed=1 errno=%d\n", errno);
        audio_play_async_statusf("audio.play.worker.done=1 rc=%d\n", -errno);
        return negative_errno_or(EIO);
    }
    if (pid == 0) {
        int rc;

        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        if (a90_console_redirect_child_to_file(AUDIO_PLAY_ASYNC_LOG_PATH) < 0) {
            a90_console_silence_child();
        }
        audio_play_async_statusf("audio.play.worker.child_started=1 pid=%ld\n", (long)getpid());
        audio_play_async_statusf("audio.play.worker.log_path=%s\n", AUDIO_PLAY_ASYNC_LOG_PATH);
        rc = audio_play_execute_integrated(profile, mode, amplitude_milli, duration_ms, manifest_path, adsp_prebooted);
        audio_play_async_statusf("audio.play.worker.done=1 rc=%d\n", rc);
        audio_play_async_statusf("audio.play.worker.exit_code=%d\n", rc == 0 ? 0 : 1);
        _exit(rc == 0 ? 0 : 1);
    }

    a90_console_printf("audio.play.worker.version=1\r\n");
    a90_console_printf("audio.play.worker.started=1\r\n");
    a90_console_printf("audio.play.worker.pid=%ld\r\n", (long)pid);
    a90_console_printf("audio.play.worker.adsp_prebooted=%d\r\n", adsp_prebooted ? 1 : 0);
    a90_console_printf("audio.play.worker.status_path=%s\r\n", AUDIO_PLAY_ASYNC_STATUS_PATH);
    a90_console_printf("audio.play.worker.log_path=%s\r\n", AUDIO_PLAY_ASYNC_LOG_PATH);
    a90_console_printf("audio.play.worker.parent_returns=1\r\n");
    audio_play_async_statusf("audio.play.worker.started=1\n");
    audio_play_async_statusf("audio.play.worker.pid=%ld\n", (long)pid);
    return 0;
}

static int audio_play_cmd(char **argv, int argc) {
    const char *profile_id = AUDIO_DEFAULT_PROFILE_ID;
    const char *mode = "probe";
    const char *manifest_path = AUDIO_SETCAL_DEFAULT_MANIFEST_PATH;
    const struct audio_speaker_profile *profile;
    bool seen_profile = false;
    bool execute_mode = false;
    bool amplitude_override = false;
    bool duration_override = false;
    int requested_amplitude_milli = 0;
    int requested_duration_ms = 0;
    int amplitude_milli = 0;
    int duration_ms = 0;
    char pcm_path[64];
    bool pcm_node_ready;
    int argi;

    for (argi = 2; argi < argc; ++argi) {
        if (argv == NULL || argv[argi] == NULL) {
            a90_console_printf("usage: audio play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--manifest PATH] [--dry-run|--execute]\r\n");
            return -EINVAL;
        }
        if (strcmp(argv[argi], "--dry-run") == 0) {
            execute_mode = false;
        } else if (strcmp(argv[argi], "--execute") == 0) {
            execute_mode = true;
        } else if (strcmp(argv[argi], "--mode") == 0) {
            if (argi + 1 >= argc || argv[argi + 1] == NULL) {
                a90_console_printf("usage: audio play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--manifest PATH] [--dry-run|--execute]\r\n");
                return -EINVAL;
            }
            mode = argv[++argi];
        } else if (strcmp(argv[argi], "--amplitude-milli") == 0) {
            if (argi + 1 >= argc || !audio_parse_nonnegative_int(argv[argi + 1], &requested_amplitude_milli)) {
                a90_console_printf("usage: audio play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--manifest PATH] [--dry-run|--execute]\r\n");
                return -EINVAL;
            }
            amplitude_override = true;
            ++argi;
        } else if (strcmp(argv[argi], "--duration-ms") == 0) {
            if (argi + 1 >= argc || !audio_parse_nonnegative_int(argv[argi + 1], &requested_duration_ms)) {
                a90_console_printf("usage: audio play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--manifest PATH] [--dry-run|--execute]\r\n");
                return -EINVAL;
            }
            duration_override = true;
            ++argi;
        } else if (strcmp(argv[argi], "--manifest") == 0) {
            if (argi + 1 >= argc || argv[argi + 1] == NULL) {
                a90_console_printf("usage: audio play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--manifest PATH] [--dry-run|--execute]\r\n");
                return -EINVAL;
            }
            manifest_path = argv[++argi];
        } else if (!seen_profile) {
            profile_id = argv[argi];
            seen_profile = true;
        } else {
            a90_console_printf("usage: audio play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--manifest PATH] [--dry-run|--execute]\r\n");
            return -EINVAL;
        }
    }

    profile = a90_audio_find_profile(profile_id);
    a90_console_printf("audio.play.version=1\r\n");
    a90_console_printf("audio.play.profile=%s\r\n", profile_id);
    a90_console_printf("audio.play.mode=%s\r\n", mode);
    a90_console_printf("audio.play.execute_requested=%d\r\n", execute_mode ? 1 : 0);
    a90_console_printf("audio.play.execute_supported=1\r\n");
    a90_console_printf("audio.play.execute_plan_supported=%d\r\n", execute_mode ? 1 : 0);
    a90_console_printf("audio.play.integrated_execute_supported=1\r\n");
    a90_console_printf("audio.play.setcal_manifest=%s\r\n", manifest_path != NULL ? manifest_path : "-");
    a90_console_printf("audio.play.playback_attempted=0\r\n");
    if (profile == NULL) {
        a90_console_printf("audio.play.error=unknown-profile\r\n");
        return -ENOENT;
    }
    if (!audio_play_mode_defaults(profile, mode, &amplitude_milli, &duration_ms)) {
        a90_console_printf("audio.play.error=unknown-mode\r\n");
        return -EINVAL;
    }
    if (amplitude_override) {
        amplitude_milli = requested_amplitude_milli;
        a90_console_printf("audio.play.amplitude_override=1\r\n");
    }
    if (duration_override) {
        duration_ms = requested_duration_ms;
        a90_console_printf("audio.play.duration_override=1\r\n");
    }
    a90_console_printf("audio.play.endpoint=%s\r\n", profile->endpoint);
    a90_console_printf("audio.play.card=%d\r\n", profile->card);
    a90_console_printf("audio.play.pcm_device=%d\r\n", profile->pcm_device);
    a90_console_printf("audio.play.channels=%d\r\n", profile->channels);
    a90_console_printf("audio.play.sample_rate=%d\r\n", profile->sample_rate);
    a90_console_printf("audio.play.bit_width=%d\r\n", profile->bit_width);
    a90_console_printf("audio.play.format=s16le\r\n");
    a90_console_printf("audio.play.amplitude_milli=%d\r\n", amplitude_milli);
    a90_console_printf("audio.play.duration_ms=%d\r\n", duration_ms);
    a90_console_printf("audio.play.cap.amplitude_milli=%d\r\n", profile->amplitude_cap_milli);
    a90_console_printf("audio.play.cap.duration_ms=%d\r\n", profile->duration_cap_ms);
    a90_console_printf("audio.play.safety.no_smart_amp_gain_boost_changes=1\r\n");
    a90_console_printf("audio.play.safety.amplitude_within_cap=%d\r\n",
                       amplitude_milli <= profile->amplitude_cap_milli ? 1 : 0);
    a90_console_printf("audio.play.safety.duration_within_cap=%d\r\n",
                       duration_ms <= profile->duration_cap_ms ? 1 : 0);
    a90_console_printf("audio.play.requires.adsp=1\r\n");
    a90_console_printf("audio.play.requires.snd=1\r\n");
    a90_console_printf("audio.play.requires.app_type=1\r\n");
    a90_console_printf("audio.play.requires.setcal=1\r\n");
    a90_console_printf("audio.play.requires.route=1\r\n");
    a90_console_printf("audio.play.execute.sequence=adsp,snd,app_type,setcal_hold,route_core,pcm,route_core_reset,setcal_deallocate\r\n");
    a90_console_printf("audio.play.alsa_open_attempted=0\r\n");
    a90_console_printf("audio.play.ioctl_attempted=0\r\n");
    pcm_node_ready = audio_play_print_pcm_prereq(profile, pcm_path, sizeof(pcm_path));
    if (amplitude_milli > profile->amplitude_cap_milli || duration_ms > profile->duration_cap_ms) {
        a90_console_printf("audio.play.refused=safety-cap-exceeded\r\n");
        return -EPERM;
    }
    if (execute_mode) {
        int prime_rc;

        audio_play_print_execute_plan(profile, mode, amplitude_milli, duration_ms);
        a90_console_printf("audio.play.initial_pcm_node_ready=%d\r\n", pcm_node_ready ? 1 : 0);
        prime_rc = audio_play_kick_adsp_stage_no_wait(profile);
        if (prime_rc < 0) {
            a90_console_printf("audio.play.execute.foreground_prime_adsp.failed=1\r\n");
            return prime_rc;
        }
        a90_console_printf("audio.play.execute.async_worker=1\r\n");
        return audio_play_start_worker(profile, mode, amplitude_milli, duration_ms, manifest_path, true);
    }
    a90_console_printf("audio.play.dry_run_ok=1\r\n");
    return 0;
}

static int audio_chime_cmd(char **argv, int argc) {
    const char *profile_id = AUDIO_DEFAULT_PROFILE_ID;
    const char *manifest_path = AUDIO_SETCAL_DEFAULT_MANIFEST_PATH;
    bool execute_mode = false;
    int amplitude_milli = AUDIO_CHIME_DEFAULT_AMPLITUDE_MILLI;
    int duration_ms = AUDIO_CHIME_DEFAULT_DURATION_MS;
    char amplitude_text[16];
    char duration_text[16];
    char *play_argv[13];
    int play_argc = 0;
    int argi;

    for (argi = 2; argi < argc; ++argi) {
        if (argv == NULL || argv[argi] == NULL) {
            a90_console_printf("usage: audio chime [--dry-run|--execute] [--amplitude-milli N] [--duration-ms N] [--manifest PATH]\r\n");
            return -EINVAL;
        }
        if (strcmp(argv[argi], "--dry-run") == 0) {
            execute_mode = false;
        } else if (strcmp(argv[argi], "--execute") == 0) {
            execute_mode = true;
        } else if (strcmp(argv[argi], "--amplitude-milli") == 0) {
            if (argi + 1 >= argc || !audio_parse_nonnegative_int(argv[argi + 1], &amplitude_milli)) {
                a90_console_printf("usage: audio chime [--dry-run|--execute] [--amplitude-milli N] [--duration-ms N] [--manifest PATH]\r\n");
                return -EINVAL;
            }
            ++argi;
        } else if (strcmp(argv[argi], "--duration-ms") == 0) {
            if (argi + 1 >= argc || !audio_parse_nonnegative_int(argv[argi + 1], &duration_ms)) {
                a90_console_printf("usage: audio chime [--dry-run|--execute] [--amplitude-milli N] [--duration-ms N] [--manifest PATH]\r\n");
                return -EINVAL;
            }
            ++argi;
        } else if (strcmp(argv[argi], "--manifest") == 0) {
            if (argi + 1 >= argc || argv[argi + 1] == NULL) {
                a90_console_printf("usage: audio chime [--dry-run|--execute] [--amplitude-milli N] [--duration-ms N] [--manifest PATH]\r\n");
                return -EINVAL;
            }
            manifest_path = argv[++argi];
        } else {
            a90_console_printf("usage: audio chime [--dry-run|--execute] [--amplitude-milli N] [--duration-ms N] [--manifest PATH]\r\n");
            return -EINVAL;
        }
    }

    snprintf(amplitude_text, sizeof(amplitude_text), "%d", amplitude_milli);
    snprintf(duration_text, sizeof(duration_text), "%d", duration_ms);

    a90_console_printf("audio.chime.version=1\r\n");
    a90_console_printf("audio.chime.profile=%s\r\n", profile_id);
    a90_console_printf("audio.chime.mode=listen\r\n");
    a90_console_printf("audio.chime.execute_requested=%d\r\n", execute_mode ? 1 : 0);
    a90_console_printf("audio.chime.amplitude_milli=%d\r\n", amplitude_milli);
    a90_console_printf("audio.chime.duration_ms=%d\r\n", duration_ms);
    a90_console_printf("audio.chime.manifest=%s\r\n", manifest_path != NULL ? manifest_path : "-");
    a90_console_printf("audio.chime.boot_autoplay_default=0\r\n");
    a90_console_printf("audio.chime.best_effort=1\r\n");
    a90_console_printf("audio.chime.blocks_boot=0\r\n");
    a90_console_printf("audio.chime.delegates=audio-play\r\n");

    play_argv[play_argc++] = "audio";
    play_argv[play_argc++] = "play";
    play_argv[play_argc++] = (char *)profile_id;
    play_argv[play_argc++] = "--mode";
    play_argv[play_argc++] = "listen";
    play_argv[play_argc++] = "--amplitude-milli";
    play_argv[play_argc++] = amplitude_text;
    play_argv[play_argc++] = "--duration-ms";
    play_argv[play_argc++] = duration_text;
    play_argv[play_argc++] = "--manifest";
    play_argv[play_argc++] = (char *)manifest_path;
    play_argv[play_argc++] = execute_mode ? "--execute" : "--dry-run";
    play_argv[play_argc] = NULL;
    return audio_play_cmd(play_argv, play_argc);
}

static int audio_stop_cmd(char **argv, int argc) {
    const char *profile_id = AUDIO_DEFAULT_PROFILE_ID;
    const struct audio_speaker_profile *profile;
    bool seen_profile = false;
    bool execute_mode = false;
    int reverse_order[AUDIO_PROFILE_ACDB_SET_COUNT];
    int argi;
    int index;

    for (argi = 2; argi < argc; ++argi) {
        if (argv == NULL || argv[argi] == NULL) {
            a90_console_printf("usage: audio stop [profile] [--dry-run|--execute]\r\n");
            return -EINVAL;
        }
        if (strcmp(argv[argi], "--dry-run") == 0) {
            execute_mode = false;
        } else if (strcmp(argv[argi], "--execute") == 0) {
            execute_mode = true;
        } else if (!seen_profile) {
            profile_id = argv[argi];
            seen_profile = true;
        } else {
            a90_console_printf("usage: audio stop [profile] [--dry-run|--execute]\r\n");
            return -EINVAL;
        }
    }

    profile = a90_audio_find_profile(profile_id);
    a90_console_printf("audio.stop.version=1\r\n");
    a90_console_printf("audio.stop.profile=%s\r\n", profile_id);
    a90_console_printf("audio.stop.execute_requested=%d\r\n", execute_mode ? 1 : 0);
    a90_console_printf("audio.stop.execute_supported=0\r\n");
    a90_console_printf("audio.stop.playback_stop_attempted=0\r\n");
    a90_console_printf("audio.stop.setcal_deallocate_attempted=0\r\n");
    a90_console_printf("audio.stop.route_write_attempted=0\r\n");
    a90_console_printf("audio.stop.ioctl_attempted=0\r\n");
    if (profile == NULL) {
        a90_console_printf("audio.stop.error=unknown-profile\r\n");
        return -ENOENT;
    }
    for (index = 0; index < AUDIO_PROFILE_ACDB_SET_COUNT; ++index) {
        reverse_order[index] = profile->acdb_set_order[AUDIO_PROFILE_ACDB_SET_COUNT - 1 - index];
    }
    a90_console_printf("audio.stop.endpoint=%s\r\n", profile->endpoint);
    a90_console_printf("audio.stop.requires.pcm_stop=1\r\n");
    a90_console_printf("audio.stop.requires.setcal_deallocate_reverse=1\r\n");
    a90_console_printf("audio.stop.requires.route_reset_core=1\r\n");
    a90_console_printf("audio.stop.route_reset_command=audio route %s --reset --layer core\r\n", profile->id);
    print_int_list("audio.stop.setcal_deallocate_order", reverse_order, AUDIO_PROFILE_ACDB_SET_COUNT);
    if (execute_mode) {
        a90_console_printf("audio.stop.refused=execute-not-implemented-native-cleanup\r\n");
        return -EPERM;
    }
    a90_console_printf("audio.stop.dry_run_ok=1\r\n");
    return 0;
}

static int audio_open_control_device(int card) {
    char path[64];
    int fd;

    snprintf(path, sizeof(path), "/dev/snd/controlC%d", card);
    fd = open(path, O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        a90_console_printf("audio.app_type.open_failed path=%s errno=%d\r\n", path, errno);
    }
    return fd;
}

static int audio_resolve_control_by_name(int fd, const char *name, struct snd_ctl_elem_id *id) {
    struct snd_ctl_elem_list list;
    struct snd_ctl_elem_id *ids;
    unsigned int count;
    unsigned int index;

    memset(&list, 0, sizeof(list));
    if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_LIST, &list) < 0) {
        a90_console_printf("audio.app_type.list_count_failed errno=%d\r\n", errno);
        return -1;
    }
    count = list.count;
    if (count == 0 || count > 8192) {
        a90_console_printf("audio.app_type.list_bad_count count=%u\r\n", list.count);
        errno = ERANGE;
        return -1;
    }
    ids = calloc(count, sizeof(*ids));
    if (ids == NULL) {
        a90_console_printf("audio.app_type.alloc_failed count=%u errno=%d\r\n", count, errno);
        return -1;
    }
    memset(&list, 0, sizeof(list));
    list.space = count;
    list.pids = ids;
    if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_LIST, &list) < 0) {
        a90_console_printf("audio.app_type.list_ids_failed errno=%d\r\n", errno);
        free(ids);
        return -1;
    }
    for (index = 0; index < list.used; ++index) {
        if (strncmp((const char *)ids[index].name, name, sizeof(ids[index].name)) == 0) {
            *id = ids[index];
            free(ids);
            return 0;
        }
    }
    a90_console_printf("audio.app_type.resolve_failed name=%s used=%u\r\n", name, list.used);
    free(ids);
    errno = ENOENT;
    return -1;
}

static int audio_validate_app_type_control(int fd,
                                           struct snd_ctl_elem_id *id,
                                           struct snd_ctl_elem_info *info) {
    memset(info, 0, sizeof(*info));
    info->id = *id;
    if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_INFO, info) < 0) {
        a90_console_printf("audio.app_type.info_failed errno=%d numid=%u\r\n", errno, id->numid);
        return -1;
    }
    *id = info->id;
    if (info->type != SNDRV_CTL_ELEM_TYPE_INTEGER) {
        a90_console_printf("audio.app_type.bad_type type=%u\r\n", info->type);
        errno = EINVAL;
        return -1;
    }
    if (info->count < AUDIO_APP_TYPE_CFG_MAX_VALUES) {
        a90_console_printf("audio.app_type.bad_count count=%u required=%d\r\n",
                           info->count,
                           AUDIO_APP_TYPE_CFG_MAX_VALUES);
        errno = EINVAL;
        return -1;
    }
    return 0;
}

static void audio_fill_app_type_value(struct snd_ctl_elem_value *value,
                                      const struct snd_ctl_elem_id *id,
                                      const struct audio_speaker_profile *profile) {
    memset(value, 0, sizeof(*value));
    value->id = *id;
    value->value.integer.value[0] = 1;
    value->value.integer.value[1] = profile->app_type;
    value->value.integer.value[2] = profile->sample_rate;
    value->value.integer.value[3] = profile->bit_width;
}

static int audio_app_type_cmd(char **argv, int argc) {
    const char *profile_id = AUDIO_DEFAULT_PROFILE_ID;
    const struct audio_speaker_profile *profile;
    struct snd_ctl_elem_id id;
    struct snd_ctl_elem_info info;
    struct snd_ctl_elem_value value;
    bool seen_profile = false;
    bool write_mode = false;
    int fd;
    int argi;

    for (argi = 2; argi < argc; ++argi) {
        if (argv == NULL || argv[argi] == NULL) {
            a90_console_printf("usage: audio app-type [profile] [--dry-run|--write]\r\n");
            return -EINVAL;
        }
        if (strcmp(argv[argi], "--dry-run") == 0) {
            write_mode = false;
        } else if (strcmp(argv[argi], "--write") == 0) {
            write_mode = true;
        } else if (!seen_profile) {
            profile_id = argv[argi];
            seen_profile = true;
        } else {
            a90_console_printf("usage: audio app-type [profile] [--dry-run|--write]\r\n");
            return -EINVAL;
        }
    }

    profile = a90_audio_find_profile(profile_id);
    a90_console_printf("audio.app_type.version=1\r\n");
    a90_console_printf("audio.app_type.profile=%s\r\n", profile_id);
    a90_console_printf("audio.app_type.mode=%s\r\n", write_mode ? "write" : "dry-run");
    if (profile == NULL) {
        a90_console_printf("audio.app_type.error=unknown-profile\r\n");
        return -ENOENT;
    }
    a90_console_printf("audio.app_type.control=App Type Config\r\n");
    a90_console_printf("audio.app_type.payload=%s\r\n", profile->global_app_type_config);
    a90_console_printf("audio.app_type.card=%d\r\n", profile->card);
    a90_console_printf("audio.app_type.write_attempted=0\r\n");

    fd = audio_open_control_device(profile->card);
    if (fd < 0) {
        return negative_errno_or(EIO);
    }
    memset(&id, 0, sizeof(id));
    if (audio_resolve_control_by_name(fd, "App Type Config", &id) < 0) {
        close(fd);
        return negative_errno_or(ENOENT);
    }
    if (audio_validate_app_type_control(fd, &id, &info) < 0) {
        close(fd);
        return negative_errno_or(EINVAL);
    }
    a90_console_printf("audio.app_type.numid=%u count=%u name=%s\r\n",
                       id.numid,
                       info.count,
                       (const char *)id.name);
    audio_fill_app_type_value(&value, &id, profile);
    if (!write_mode) {
        close(fd);
        a90_console_printf("audio.app_type.dry_run_ok=1\r\n");
        return 0;
    }

    a90_console_printf("audio.app_type.write_attempted=1\r\n");
    if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_WRITE, &value) < 0) {
        a90_console_printf("audio.app_type.write_failed errno=%d\r\n", errno);
        close(fd);
        return negative_errno_or(EIO);
    }
    if (close(fd) < 0) {
        a90_console_printf("audio.app_type.close_failed errno=%d\r\n", errno);
        return negative_errno_or(EIO);
    }
    a90_console_printf("audio.app_type.write_ok=1\r\n");
    return 0;
}

static void audio_route_print_value(const char *prefix, const struct audio_route_value *value) {
    int index;

    a90_console_printf("%s.kind=%s\r\n", prefix, a90_audio_route_value_kind_name(value));
    if (value == NULL) {
        return;
    }
    if (value->kind == AUDIO_ROUTE_VALUE_ENUM) {
        a90_console_printf("%s.enum=%s\r\n", prefix, value->enum_value == NULL ? "" : value->enum_value);
        return;
    }
    a90_console_printf("%s.ints=", prefix);
    for (index = 0; index < value->int_count; ++index) {
        a90_console_printf("%s%d", index == 0 ? "" : ",", value->ints[index]);
    }
    a90_console_printf("\r\n");
    a90_console_printf("%s.zero_fill=%d\r\n", prefix, value->zero_fill);
    a90_console_printf("%s.total_count=%d\r\n", prefix, a90_audio_route_value_total_count(value));
}

static void audio_route_print_control(const char *prefix,
                                      const struct audio_route_control *control,
                                      const struct audio_route_value *value) {
    char value_prefix[96];

    a90_console_printf("%s.name=%s\r\n", prefix, control->name);
    a90_console_printf("%s.role=%s\r\n", prefix, control->role);
    a90_console_printf("%s.layer=%s\r\n", prefix, control->layer);
    a90_console_printf("%s.speaker=%s\r\n", prefix, control->speaker);
    a90_console_printf("%s.policy=%s\r\n", prefix, control->policy);
    a90_console_printf("%s.order=%d\r\n", prefix, control->order);
    a90_console_printf("%s.resettable=%d\r\n", prefix, control->resettable ? 1 : 0);
    a90_console_printf("%s.smart_amp_boost=%d\r\n", prefix, control->smart_amp_boost ? 1 : 0);
    snprintf(value_prefix, sizeof(value_prefix), "%s.value", prefix);
    audio_route_print_value(value_prefix, value);
}

static void audio_route_print_controls(bool reset_mode, const char *layer) {
    int index;
    int output_index = 0;
    char prefix[64];

    if (reset_mode) {
        for (index = a90_audio_route_control_count() - 1; index >= 0; --index) {
            if (!a90_audio_route_control_matches_layer(&AUDIO_INTERNAL_SPEAKER_ROUTE[index], layer)) {
                continue;
            }
            if (!AUDIO_INTERNAL_SPEAKER_ROUTE[index].resettable) {
                continue;
            }
            snprintf(prefix, sizeof(prefix), "audio.route.reset.%d", output_index);
            audio_route_print_control(prefix,
                                      &AUDIO_INTERNAL_SPEAKER_ROUTE[index],
                                      &AUDIO_INTERNAL_SPEAKER_ROUTE[index].reset);
            ++output_index;
        }
        return;
    }

    for (index = 0; index < a90_audio_route_control_count(); ++index) {
        if (!a90_audio_route_control_matches_layer(&AUDIO_INTERNAL_SPEAKER_ROUTE[index], layer)) {
            continue;
        }
        snprintf(prefix, sizeof(prefix), "audio.route.apply.%d", output_index);
        audio_route_print_control(prefix,
                                  &AUDIO_INTERNAL_SPEAKER_ROUTE[index],
                                  &AUDIO_INTERNAL_SPEAKER_ROUTE[index].apply);
        ++output_index;
    }
}

static int audio_route_validate_numeric_control(int fd,
                                                struct snd_ctl_elem_id *id,
                                                struct snd_ctl_elem_info *info,
                                                const struct audio_route_control *control,
                                                const struct audio_route_value *route_value) {
    int required = a90_audio_route_value_total_count(route_value);

    memset(info, 0, sizeof(*info));
    info->id = *id;
    if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_INFO, info) < 0) {
        a90_console_printf("audio.route.info_failed control=%s errno=%d\r\n", control->name, errno);
        return -1;
    }
    *id = info->id;
    if (info->type != SNDRV_CTL_ELEM_TYPE_INTEGER &&
        info->type != SNDRV_CTL_ELEM_TYPE_BOOLEAN) {
        a90_console_printf("audio.route.bad_type control=%s expected=numeric actual=%u\r\n",
                           control->name,
                           info->type);
        errno = EINVAL;
        return -1;
    }
    if ((int)info->count < required || required > 128) {
        a90_console_printf("audio.route.bad_count control=%s count=%u required=%d\r\n",
                           control->name,
                           info->count,
                           required);
        errno = EINVAL;
        return -1;
    }
    return 0;
}

static int audio_route_find_enum_item(int fd,
                                      struct snd_ctl_elem_id *id,
                                      struct snd_ctl_elem_info *info,
                                      const struct audio_route_control *control,
                                      const char *enum_value) {
    unsigned int item;

    memset(info, 0, sizeof(*info));
    info->id = *id;
    if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_INFO, info) < 0) {
        a90_console_printf("audio.route.info_failed control=%s errno=%d\r\n", control->name, errno);
        return -1;
    }
    *id = info->id;
    if (info->type != SNDRV_CTL_ELEM_TYPE_ENUMERATED) {
        a90_console_printf("audio.route.bad_type control=%s expected=enum actual=%u\r\n",
                           control->name,
                           info->type);
        errno = EINVAL;
        return -1;
    }
    if (info->count == 0 || info->value.enumerated.items == 0) {
        a90_console_printf("audio.route.bad_enum_shape control=%s count=%u items=%u\r\n",
                           control->name,
                           info->count,
                           info->value.enumerated.items);
        errno = EINVAL;
        return -1;
    }

    for (item = 0; item < info->value.enumerated.items; ++item) {
        struct snd_ctl_elem_info item_info;

        memset(&item_info, 0, sizeof(item_info));
        item_info.id = *id;
        item_info.value.enumerated.item = item;
        if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_INFO, &item_info) < 0) {
            a90_console_printf("audio.route.enum_item_failed control=%s item=%u errno=%d\r\n",
                               control->name,
                               item,
                               errno);
            return -1;
        }
        if (strncmp(item_info.value.enumerated.name,
                    enum_value,
                    sizeof(item_info.value.enumerated.name)) == 0) {
            *info = item_info;
            return (int)item;
        }
    }
    a90_console_printf("audio.route.enum_not_found control=%s value=%s items=%u\r\n",
                       control->name,
                       enum_value == NULL ? "" : enum_value,
                       info->value.enumerated.items);
    errno = ENOENT;
    return -1;
}

static void audio_route_fill_integer_value(struct snd_ctl_elem_value *value,
                                           const struct snd_ctl_elem_id *id,
                                           const struct audio_route_value *route_value) {
    int index;

    memset(value, 0, sizeof(*value));
    value->id = *id;
    for (index = 0; index < route_value->int_count; ++index) {
        value->value.integer.value[index] = route_value->ints[index];
    }
}

static void audio_route_fill_enum_value(struct snd_ctl_elem_value *value,
                                        const struct snd_ctl_elem_id *id,
                                        unsigned int item) {
    memset(value, 0, sizeof(*value));
    value->id = *id;
    value->value.enumerated.item[0] = item;
}

static int audio_route_write_one_control(int fd,
                                         const struct audio_route_control *control,
                                         const struct audio_route_value *route_value) {
    struct snd_ctl_elem_id id;
    struct snd_ctl_elem_info info;
    struct snd_ctl_elem_value value;
    int enum_item;

    memset(&id, 0, sizeof(id));
    if (audio_resolve_control_by_name(fd, control->name, &id) < 0) {
        a90_console_printf("audio.route.resolve_failed control=%s errno=%d\r\n", control->name, errno);
        return -1;
    }

    if (route_value->kind == AUDIO_ROUTE_VALUE_INTS) {
        if (audio_route_validate_numeric_control(fd, &id, &info, control, route_value) < 0) {
            return -1;
        }
        audio_route_fill_integer_value(&value, &id, route_value);
    } else if (route_value->kind == AUDIO_ROUTE_VALUE_ENUM) {
        enum_item = audio_route_find_enum_item(fd, &id, &info, control, route_value->enum_value);
        if (enum_item < 0) {
            return -1;
        }
        audio_route_fill_enum_value(&value, &id, (unsigned int)enum_item);
    } else {
        a90_console_printf("audio.route.bad_value_kind control=%s kind=%d\r\n",
                           control->name,
                           route_value->kind);
        errno = EINVAL;
        return -1;
    }

    a90_console_printf("audio.route.write.control=%s kind=%s\r\n",
                       control->name,
                       a90_audio_route_value_kind_name(route_value));
    if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_WRITE, &value) < 0) {
        a90_console_printf("audio.route.write_failed control=%s errno=%d\r\n", control->name, errno);
        return -1;
    }
    a90_console_printf("audio.route.write_ok control=%s\r\n", control->name);
    return 0;
}

static int audio_route_write_selected_controls(const struct audio_speaker_profile *profile,
                                               const char *layer,
                                               bool reset_mode) {
    int fd;
    int index;
    int written = 0;

    fd = audio_open_control_device(profile->card);
    if (fd < 0) {
        return negative_errno_or(EIO);
    }

    if (reset_mode) {
        for (index = a90_audio_route_control_count() - 1; index >= 0; --index) {
            if (!a90_audio_route_control_matches_layer(&AUDIO_INTERNAL_SPEAKER_ROUTE[index], layer) ||
                !AUDIO_INTERNAL_SPEAKER_ROUTE[index].resettable) {
                continue;
            }
            if (audio_route_write_one_control(fd,
                                              &AUDIO_INTERNAL_SPEAKER_ROUTE[index],
                                              &AUDIO_INTERNAL_SPEAKER_ROUTE[index].reset) < 0) {
                close(fd);
                return negative_errno_or(EIO);
            }
            ++written;
        }
    } else {
        for (index = 0; index < a90_audio_route_control_count(); ++index) {
            if (!a90_audio_route_control_matches_layer(&AUDIO_INTERNAL_SPEAKER_ROUTE[index], layer)) {
                continue;
            }
            if (audio_route_write_one_control(fd,
                                              &AUDIO_INTERNAL_SPEAKER_ROUTE[index],
                                              &AUDIO_INTERNAL_SPEAKER_ROUTE[index].apply) < 0) {
                close(fd);
                return negative_errno_or(EIO);
            }
            ++written;
        }
    }

    if (close(fd) < 0) {
        a90_console_printf("audio.route.close_failed errno=%d\r\n", errno);
        return negative_errno_or(EIO);
    }
    a90_console_printf("audio.route.write_done count=%d layer=%s mode=%s\r\n",
                       written,
                       layer,
                       reset_mode ? "reset" : "apply");
    return 0;
}

static int audio_route_cmd(char **argv, int argc) {
    const char *profile_id = AUDIO_DEFAULT_PROFILE_ID;
    const char *layer = "all";
    const struct audio_speaker_profile *profile;
    bool seen_profile = false;
    bool apply_mode = false;
    bool reset_mode = false;
    bool write_mode;
    bool selected_has_boost;
    int argi;

    for (argi = 2; argi < argc; ++argi) {
        if (argv == NULL || argv[argi] == NULL) {
            a90_console_printf("usage: audio route [profile] [--dry-run|--apply|--reset] [--layer all|core|feedback|endpoint|blocked]\r\n");
            return -EINVAL;
        }
        if (strcmp(argv[argi], "--dry-run") == 0) {
            apply_mode = false;
            reset_mode = false;
        } else if (strcmp(argv[argi], "--apply") == 0) {
            apply_mode = true;
            reset_mode = false;
        } else if (strcmp(argv[argi], "--reset") == 0) {
            apply_mode = false;
            reset_mode = true;
        } else if (strcmp(argv[argi], "--layer") == 0) {
            ++argi;
            if (argi >= argc || argv[argi] == NULL || !a90_audio_route_layer_valid(argv[argi])) {
                a90_console_printf("usage: audio route [profile] [--dry-run|--apply|--reset] [--layer all|core|feedback|endpoint|blocked]\r\n");
                return -EINVAL;
            }
            layer = argv[argi];
        } else if (!seen_profile) {
            profile_id = argv[argi];
            seen_profile = true;
        } else {
            a90_console_printf("usage: audio route [profile] [--dry-run|--apply|--reset] [--layer all|core|feedback|endpoint|blocked]\r\n");
            return -EINVAL;
        }
    }

    profile = a90_audio_find_profile(profile_id);
    write_mode = apply_mode || reset_mode;
    a90_console_printf("audio.route.version=1\r\n");
    a90_console_printf("audio.route.profile=%s\r\n", profile_id);
    a90_console_printf("audio.route.mode=%s\r\n", reset_mode ? "reset" : (apply_mode ? "apply" : "dry-run"));
    a90_console_printf("audio.route.layer=%s\r\n", layer);
    a90_console_printf("audio.route.write_attempted=0\r\n");
    if (profile == NULL) {
        a90_console_printf("audio.route.error=unknown-profile\r\n");
        return -ENOENT;
    }
    if (a90_audio_route_control_count() != AUDIO_ROUTE_APPLY_COUNT ||
        a90_audio_route_reset_count() != AUDIO_ROUTE_RESET_COUNT) {
        a90_console_printf("audio.route.error=route-count-mismatch apply=%d/%d reset=%d/%d\r\n",
                           a90_audio_route_control_count(),
                           AUDIO_ROUTE_APPLY_COUNT,
                           a90_audio_route_reset_count(),
                           AUDIO_ROUTE_RESET_COUNT);
        return -EINVAL;
    }

    a90_console_printf("audio.route.endpoint=%s\r\n", profile->endpoint);
    a90_console_printf("audio.route.card=%d\r\n", profile->card);
    a90_console_printf("audio.route.pcm_device=%d\r\n", profile->pcm_device);
    a90_console_printf("audio.route.apply.count=%d\r\n", AUDIO_ROUTE_APPLY_COUNT);
    a90_console_printf("audio.route.reset.count=%d\r\n", AUDIO_ROUTE_RESET_COUNT);
    a90_console_printf("audio.route.selected.apply.count=%d\r\n", a90_audio_route_selected_count(layer, false));
    a90_console_printf("audio.route.selected.reset.count=%d\r\n", a90_audio_route_selected_count(layer, true));
    a90_console_printf("audio.route.requires_global_app_type=1\r\n");
    a90_console_printf("audio.route.global_app_type_primitive=audio app-type %s --write\r\n", profile->id);
    a90_console_printf("audio.route.smart_amp_boost_blocked=%d\r\n",
                       a90_audio_route_has_smart_amp_boost() ? 1 : 0);
    selected_has_boost = a90_audio_route_selected_has_smart_amp_boost(layer);
    a90_console_printf("audio.route.selected.smart_amp_boost_blocked=%d\r\n", selected_has_boost ? 1 : 0);
    a90_console_printf("audio.route.blocked_control=SpkrLeft BOOST Switch\r\n");
    audio_route_print_controls(reset_mode, layer);

    if (write_mode && !a90_audio_route_layer_write_allowed(layer)) {
        if (selected_has_boost) {
            a90_console_printf("audio.route.refused=write-mode-blocked-smart-amp-boost-review\r\n");
        } else {
            a90_console_printf("audio.route.refused=write-mode-blocked-non-core-layer\r\n");
        }
        a90_console_printf("audio.route.write_attempted=0\r\n");
        return -EPERM;
    }
    if (write_mode) {
        a90_console_printf("audio.route.write_attempted=1\r\n");
        return audio_route_write_selected_controls(profile, layer, reset_mode);
    }
    a90_console_printf("audio.route.dry_run_ok=1\r\n");
    return 0;
}

static bool path_lstat(const char *path, struct stat *st) {
    return lstat(path, st) == 0;
}

static bool path_is_dir(const char *path) {
    struct stat st;

    return path_lstat(path, &st) && S_ISDIR(st.st_mode);
}

static int count_dir_entries(const char *path) {
    DIR *dir;
    struct dirent *entry;
    int count = 0;

    dir = opendir(path);
    if (dir == NULL) {
        return 0;
    }
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        ++count;
    }
    closedir(dir);
    return count;
}

static bool name_contains_ci(const char *name, const char *needle) {
    size_t name_len = strlen(name);
    size_t needle_len = strlen(needle);
    size_t offset;

    if (needle_len == 0 || needle_len > name_len) {
        return false;
    }
    for (offset = 0; offset + needle_len <= name_len; ++offset) {
        size_t index;
        bool matched = true;

        for (index = 0; index < needle_len; ++index) {
            char lhs = name[offset + index];
            char rhs = needle[index];

            if (lhs >= 'A' && lhs <= 'Z') {
                lhs = (char)(lhs - 'A' + 'a');
            }
            if (rhs >= 'A' && rhs <= 'Z') {
                rhs = (char)(rhs - 'A' + 'a');
            }
            if (lhs != rhs) {
                matched = false;
                break;
            }
        }
        if (matched) {
            return true;
        }
    }
    return false;
}

static bool make_child_path(char *out, size_t out_size, const char *base, const char *leaf) {
    size_t base_len = strlen(base);
    size_t leaf_len = strlen(leaf);

    if (out_size == 0 || base_len + 1 + leaf_len + 1 > out_size) {
        if (out_size > 0) {
            out[0] = '\0';
        }
        return false;
    }
    memcpy(out, base, base_len);
    out[base_len] = '/';
    memcpy(out + base_len + 1, leaf, leaf_len + 1);
    return true;
}

static bool starts_with(const char *value, const char *prefix) {
    return strncmp(value, prefix, strlen(prefix)) == 0;
}

static bool decimal_tail_nonempty(const char *value) {
    size_t index;

    if (value == NULL || value[0] == '\0') {
        return false;
    }
    for (index = 0; value[index] != '\0'; ++index) {
        if (value[index] < '0' || value[index] > '9') {
            return false;
        }
    }
    return true;
}

static bool allowed_control_name(const char *name) {
    return starts_with(name, "controlC") && decimal_tail_nonempty(name + strlen("controlC"));
}

static bool allowed_pcm_name(const char *name) {
    const char *cursor;

    if (!starts_with(name, "pcmC")) {
        return false;
    }
    cursor = name + strlen("pcmC");
    if (*cursor < '0' || *cursor > '9') {
        return false;
    }
    while (*cursor >= '0' && *cursor <= '9') {
        ++cursor;
    }
    if (*cursor != 'D') {
        return false;
    }
    ++cursor;
    if (*cursor < '0' || *cursor > '9') {
        return false;
    }
    while (*cursor >= '0' && *cursor <= '9') {
        ++cursor;
    }
    if ((*cursor != 'p' && *cursor != 'c') || cursor[1] != '\0') {
        return false;
    }
    return true;
}

static bool allowed_sound_node_name(const char *name) {
    if (name == NULL || name[0] == '\0' ||
        strcmp(name, ".") == 0 || strcmp(name, "..") == 0 ||
        strchr(name, '/') != NULL) {
        return false;
    }
    return allowed_control_name(name) ||
           allowed_pcm_name(name) ||
           strcmp(name, "timer") == 0 ||
           strcmp(name, "seq") == 0;
}

static int parse_dev_numbers(const char *dev_info,
                             unsigned int *major_num,
                             unsigned int *minor_num) {
    char extra;

    if (sscanf(dev_info, "%u:%u%c", major_num, minor_num, &extra) != 2) {
        errno = EINVAL;
        return -1;
    }
    return 0;
}

static int sound_node_paths(const char *name,
                            char *sysfs_dev_path,
                            size_t sysfs_dev_path_size,
                            char *dev_node_path,
                            size_t dev_node_path_size) {
    char sysfs_entry_path[PATH_MAX];

    if (!allowed_sound_node_name(name)) {
        errno = EINVAL;
        return -1;
    }
    if (!make_child_path(sysfs_entry_path, sizeof(sysfs_entry_path), AUDIO_SOUND_CLASS_DIR, name) ||
        !make_child_path(sysfs_dev_path, sysfs_dev_path_size, sysfs_entry_path, "dev") ||
        !make_child_path(dev_node_path, dev_node_path_size, AUDIO_DEV_SND_DIR, name)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    return 0;
}

static int read_sound_node_numbers(const char *name,
                                   char *sysfs_dev_path,
                                   size_t sysfs_dev_path_size,
                                   char *dev_node_path,
                                   size_t dev_node_path_size,
                                   unsigned int *major_num,
                                   unsigned int *minor_num,
                                   char *dev_info,
                                   size_t dev_info_size) {
    if (sound_node_paths(name, sysfs_dev_path, sysfs_dev_path_size,
                         dev_node_path, dev_node_path_size) < 0) {
        return -1;
    }
    if (read_trimmed_text_file(sysfs_dev_path, dev_info, dev_info_size) < 0) {
        return -1;
    }
    if (parse_dev_numbers(dev_info, major_num, minor_num) < 0) {
        return -1;
    }
    return 0;
}

static const char *sound_devnode_state(const char *path, dev_t wanted) {
    struct stat st;

    if (lstat(path, &st) < 0) {
        if (errno == ENOENT) {
            return "missing";
        }
        return "stat-failed";
    }
    if (!S_ISCHR(st.st_mode)) {
        return "not-char";
    }
    if (st.st_rdev != wanted) {
        return "mismatch";
    }
    return "ok";
}

static int audio_read_misc_minor_by_name(const char *name, unsigned int *minor_out) {
    FILE *file;
    char line[256];

    if (name == NULL || minor_out == NULL) {
        errno = EINVAL;
        return -1;
    }
    file = fopen(AUDIO_PROC_MISC, "r");
    if (file == NULL) {
        return -1;
    }
    while (fgets(line, sizeof(line), file) != NULL) {
        unsigned int minor_num = 0;
        char entry_name[128];

        if (sscanf(line, " %u %127s", &minor_num, entry_name) != 2) {
            continue;
        }
        if (strcmp(entry_name, name) == 0) {
            *minor_out = minor_num;
            fclose(file);
            return 0;
        }
    }
    fclose(file);
    errno = ENOENT;
    return -1;
}

static int audio_materialize_msm_audio_cal_devnode_once(void) {
    char dev_info[64];
    unsigned int major_num = 0;
    unsigned int minor_num = 0;
    dev_t wanted;
    struct stat st;

    a90_console_printf("audio.msm_audio_cal_materialize.version=1\r\n");
    a90_console_printf("audio.msm_audio_cal_materialize.sysfs=%s\r\n",
                       AUDIO_SETCAL_SYSFS_MSM_AUDIO_CAL_DEV);
    a90_console_printf("audio.msm_audio_cal_materialize.proc_misc=%s\r\n", AUDIO_PROC_MISC);
    a90_console_printf("audio.msm_audio_cal_materialize.devnode=%s\r\n",
                       AUDIO_SETCAL_DEV_MSM_AUDIO_CAL);
    if (read_trimmed_text_file(AUDIO_SETCAL_SYSFS_MSM_AUDIO_CAL_DEV,
                               dev_info,
                               sizeof(dev_info)) == 0 &&
        parse_dev_numbers(dev_info, &major_num, &minor_num) == 0) {
        a90_console_printf("audio.msm_audio_cal_materialize.source=sysfs\r\n");
        a90_console_printf("audio.msm_audio_cal_materialize.sysfs_read_ok=1 value=%s major=%u minor=%u\r\n",
                           dev_info,
                           major_num,
                           minor_num);
    } else {
        int saved_errno = errno;

        a90_console_printf("audio.msm_audio_cal_materialize.sysfs_read_ok=0 errno=%d\r\n",
                           saved_errno);
        if (audio_read_misc_minor_by_name("msm_audio_cal", &minor_num) < 0) {
            saved_errno = errno;
            a90_console_printf("audio.msm_audio_cal_materialize.proc_misc_read_ok=0 errno=%d\r\n",
                               saved_errno);
            return -saved_errno;
        }
        major_num = AUDIO_MISC_MAJOR;
        a90_console_printf("audio.msm_audio_cal_materialize.source=proc_misc\r\n");
        a90_console_printf("audio.msm_audio_cal_materialize.proc_misc_read_ok=1 major=%u minor=%u\r\n",
                           major_num,
                           minor_num);
    }
    wanted = makedev(major_num, minor_num);
    if (lstat(AUDIO_SETCAL_DEV_MSM_AUDIO_CAL, &st) == 0) {
        if (S_ISCHR(st.st_mode) && st.st_rdev == wanted) {
            a90_console_printf("audio.msm_audio_cal_materialize.already_ok=1\r\n");
            return 0;
        }
        a90_console_printf("audio.msm_audio_cal_materialize.refused=existing-node-mismatch mode=0%o\r\n",
                           (unsigned int)st.st_mode);
        return -EINVAL;
    }
    if (errno != ENOENT) {
        int saved_errno = errno;

        a90_console_printf("audio.msm_audio_cal_materialize.stat_ok=0 errno=%d\r\n",
                           saved_errno);
        return -saved_errno;
    }
    if (mknod(AUDIO_SETCAL_DEV_MSM_AUDIO_CAL, S_IFCHR | 0600, wanted) < 0) {
        int saved_errno = errno;

        if (saved_errno == EEXIST &&
            lstat(AUDIO_SETCAL_DEV_MSM_AUDIO_CAL, &st) == 0 &&
            S_ISCHR(st.st_mode) &&
            st.st_rdev == wanted) {
            a90_console_printf("audio.msm_audio_cal_materialize.already_ok=1\r\n");
            return 0;
        }
        a90_console_printf("audio.msm_audio_cal_materialize.created=0 errno=%d\r\n",
                           saved_errno);
        return -saved_errno;
    }
    a90_console_printf("audio.msm_audio_cal_materialize.created=1 major=%u minor=%u\r\n",
                       major_num,
                       minor_num);
    return 0;
}

static int audio_materialize_ion_devnode_once(void) {
    char dev_info[64];
    unsigned int major_num = 0;
    unsigned int minor_num = 0;
    dev_t wanted;
    struct stat st;

    a90_console_printf("audio.ion_materialize.version=1\r\n");
    a90_console_printf("audio.ion_materialize.sysfs=%s\r\n", AUDIO_SETCAL_SYSFS_ION_DEV);
    a90_console_printf("audio.ion_materialize.devnode=%s\r\n", AUDIO_SETCAL_DEV_ION);
    if (read_trimmed_text_file(AUDIO_SETCAL_SYSFS_ION_DEV, dev_info, sizeof(dev_info)) < 0) {
        int saved_errno = errno;

        a90_console_printf("audio.ion_materialize.sysfs_read_ok=0 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (parse_dev_numbers(dev_info, &major_num, &minor_num) < 0) {
        int saved_errno = errno;

        a90_console_printf("audio.ion_materialize.dev_parse_ok=0 errno=%d value=%s\r\n",
                           saved_errno,
                           dev_info);
        return -saved_errno;
    }
    wanted = makedev(major_num, minor_num);
    a90_console_printf("audio.ion_materialize.sysfs_read_ok=1 value=%s major=%u minor=%u\r\n",
                       dev_info,
                       major_num,
                       minor_num);
    if (lstat(AUDIO_SETCAL_DEV_ION, &st) == 0) {
        if (S_ISCHR(st.st_mode) && st.st_rdev == wanted) {
            a90_console_printf("audio.ion_materialize.already_ok=1\r\n");
            return 0;
        }
        a90_console_printf("audio.ion_materialize.refused=existing-node-mismatch mode=0%o\r\n",
                           (unsigned int)st.st_mode);
        return -EINVAL;
    }
    if (errno != ENOENT) {
        int saved_errno = errno;

        a90_console_printf("audio.ion_materialize.stat_ok=0 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    if (mknod(AUDIO_SETCAL_DEV_ION, S_IFCHR | 0600, wanted) < 0) {
        int saved_errno = errno;

        if (saved_errno == EEXIST &&
            lstat(AUDIO_SETCAL_DEV_ION, &st) == 0 &&
            S_ISCHR(st.st_mode) &&
            st.st_rdev == wanted) {
            a90_console_printf("audio.ion_materialize.already_ok=1\r\n");
            return 0;
        }
        a90_console_printf("audio.ion_materialize.created=0 errno=%d\r\n", saved_errno);
        return -saved_errno;
    }
    a90_console_printf("audio.ion_materialize.created=1 major=%u minor=%u\r\n",
                       major_num,
                       minor_num);
    return 0;
}

static int count_dir_entries_matching(const char *path, const char *needle) {
    DIR *dir;
    struct dirent *entry;
    int count = 0;

    dir = opendir(path);
    if (dir == NULL) {
        return 0;
    }
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        if (name_contains_ci(entry->d_name, needle)) {
            ++count;
        }
    }
    closedir(dir);
    return count;
}

static bool firmware_file_exists_ci_at(const char *dir_path, const char *wanted) {
    DIR *dir;
    struct dirent *entry;
    bool found = false;

    dir = opendir(dir_path);
    if (dir == NULL) {
        return false;
    }
    while ((entry = readdir(dir)) != NULL) {
        if (strcasecmp(entry->d_name, wanted) == 0) {
            found = true;
            break;
        }
    }
    closedir(dir);
    return found;
}

static int expected_adsp_segments(void) {
    return (int)(sizeof(AUDIO_ADSP_SEGMENTS) / sizeof(AUDIO_ADSP_SEGMENTS[0]));
}

static void append_missing_segment(char *out, size_t out_size, const char *segment) {
    size_t used;
    size_t segment_len;

    if (out == NULL || out_size == 0 || segment == NULL) {
        return;
    }
    used = strlen(out);
    if (used > 0) {
        if (used + 1 >= out_size) {
            return;
        }
        out[used++] = ',';
        out[used] = '\0';
    }
    segment_len = strlen(segment);
    if (used + segment_len >= out_size) {
        if (used + 3 < out_size) {
            memcpy(out + used, "...", 4);
        }
        return;
    }
    memcpy(out + used, segment, segment_len + 1);
}

static void check_adsp_firmware_dir(const char *dir_path, struct adsp_firmware_status *status) {
    int index;

    if (status == NULL) {
        return;
    }
    memset(status, 0, sizeof(*status));
    status->dir_exists = path_is_dir(dir_path);
    status->mdt_present = firmware_file_exists_ci_at(dir_path, "adsp.mdt");
    status->adspr_jsn_present = firmware_file_exists_ci_at(dir_path, "adspr.jsn");
    status->adspua_jsn_present = firmware_file_exists_ci_at(dir_path, "adspua.jsn");
    strcpy(status->missing_segments, "none");
    for (index = 0; index < expected_adsp_segments(); ++index) {
        if (firmware_file_exists_ci_at(dir_path, AUDIO_ADSP_SEGMENTS[index])) {
            ++status->present_segments;
            continue;
        }
        if (strcmp(status->missing_segments, "none") == 0) {
            status->missing_segments[0] = '\0';
        }
        append_missing_segment(status->missing_segments,
                               sizeof(status->missing_segments),
                               AUDIO_ADSP_SEGMENTS[index]);
    }
    if (status->missing_segments[0] == '\0') {
        strcpy(status->missing_segments, "none");
    }
}

static bool adsp_firmware_complete(const struct adsp_firmware_status *status) {
    return status != NULL &&
           status->dir_exists &&
           status->mdt_present &&
           status->present_segments == expected_adsp_segments();
}

static void print_adsp_firmware_check(const char *prefix,
                                      const char *dir_path,
                                      const struct adsp_firmware_status *status) {
    a90_console_printf("audio.%s_dir=%s exists=%s\r\n",
                       prefix,
                       dir_path,
                       yesno(status != NULL && status->dir_exists));
    a90_console_printf("audio.%s.adsp_mdt=%s\r\n", prefix, yesno(status != NULL && status->mdt_present));
    a90_console_printf("audio.%s.adsp_segments_model=%s\r\n", prefix, AUDIO_ADSP_SEGMENT_MODEL);
    a90_console_printf("audio.%s.adsp_segments_present=%d expected=%d\r\n",
                       prefix,
                       status != NULL ? status->present_segments : 0,
                       expected_adsp_segments());
    a90_console_printf("audio.%s.adsp_segments_missing=%s\r\n",
                       prefix,
                       status != NULL ? status->missing_segments : "unknown");
    a90_console_printf("audio.%s.adspr_jsn=%s\r\n",
                       prefix,
                       yesno(status != NULL && status->adspr_jsn_present));
    a90_console_printf("audio.%s.adspua_jsn=%s\r\n",
                       prefix,
                       yesno(status != NULL && status->adspua_jsn_present));
}

static void print_trimmed_or_missing(const char *key, const char *path) {
    char value[256];

    if (read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        flatten_inline_text(value);
        a90_console_printf("audio.%s=%s\r\n", key, value[0] != '\0' ? value : "empty");
        return;
    }
    a90_console_printf("audio.%s=missing errno=%d\r\n", key, errno);
}

static void print_mode_line(const char *key, const char *path) {
    struct stat st;

    if (path_lstat(path, &st)) {
        a90_console_printf("audio.%s.exists=yes mode=%03o type=%s\r\n",
                           key,
                           (unsigned int)(st.st_mode & 0777),
                           S_ISDIR(st.st_mode) ? "dir" :
                           S_ISREG(st.st_mode) ? "file" :
                           S_ISLNK(st.st_mode) ? "symlink" : "other");
        return;
    }
    a90_console_printf("audio.%s.exists=no errno=%d\r\n", key, errno);
}

static void print_firmware_status(void) {
    struct adsp_firmware_status mounted_status;
    struct adsp_firmware_status class_status;
    char fwclass_path[PATH_MAX];

    check_adsp_firmware_dir(AUDIO_FW_DIR, &mounted_status);
    print_adsp_firmware_check("firmware", AUDIO_FW_DIR, &mounted_status);
    if (read_trimmed_text_file(AUDIO_FWCLASS_PATH, fwclass_path, sizeof(fwclass_path)) == 0 &&
        fwclass_path[0] != '\0') {
        flatten_inline_text(fwclass_path);
        check_adsp_firmware_dir(fwclass_path, &class_status);
        print_adsp_firmware_check("firmware_class", fwclass_path, &class_status);
        a90_console_printf("audio.firmware_class.adsp_complete=%s\r\n",
                           yesno(adsp_firmware_complete(&class_status)));
        return;
    }
    a90_console_printf("audio.firmware_class_dir=unavailable\r\n");
    a90_console_printf("audio.firmware_class.adsp_complete=no\r\n");
}

static void print_remoteproc_status(void) {
    DIR *dir;
    struct dirent *entry;
    int listed = 0;

    a90_console_printf("audio.remoteproc.count=%d\r\n", count_dir_entries("/sys/class/remoteproc"));
    dir = opendir("/sys/class/remoteproc");
    if (dir == NULL) {
        a90_console_printf("audio.remoteproc.open_errno=%d\r\n", errno);
        return;
    }
    while ((entry = readdir(dir)) != NULL && listed < AUDIO_MAX_LISTED) {
        char base[PATH_MAX];
        char name_path[PATH_MAX];
        char state_path[PATH_MAX];
        char name[128] = "missing";
        char state[128] = "missing";

        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        snprintf(base, sizeof(base), "/sys/class/remoteproc/%s", entry->d_name);
        if (!make_child_path(name_path, sizeof(name_path), base, "name") ||
            read_trimmed_text_file(name_path, name, sizeof(name)) < 0) {
            snprintf(name, sizeof(name), "missing");
        }
        if (!make_child_path(state_path, sizeof(state_path), base, "state") ||
            read_trimmed_text_file(state_path, state, sizeof(state)) < 0) {
            snprintf(state, sizeof(state), "missing");
        }
        flatten_inline_text(name);
        flatten_inline_text(state);
        a90_console_printf("audio.remoteproc.%d.node=%s name=%s state=%s\r\n",
                           listed,
                           entry->d_name,
                           name,
                           state);
        ++listed;
    }
    closedir(dir);
}

static void print_class_counts(void) {
    a90_console_printf("audio.rpmsg.count=%d adsp_like=%d cdsp_like=%d\r\n",
                       count_dir_entries("/sys/bus/rpmsg/devices"),
                       count_dir_entries_matching("/sys/bus/rpmsg/devices", "adsp"),
                       count_dir_entries_matching("/sys/bus/rpmsg/devices", "cdsp"));
    a90_console_printf("audio.rpmsg_class.count=%d\r\n", count_dir_entries("/sys/class/rpmsg"));
    a90_console_printf("audio.fastrpc_class.count=%d\r\n", count_dir_entries("/sys/class/fastrpc"));
    a90_console_printf("audio.sound_class.count=%d card_like=%d control_like=%d\r\n",
                       count_dir_entries("/sys/class/sound"),
                       count_dir_entries_matching("/sys/class/sound", "card"),
                       count_dir_entries_matching("/sys/class/sound", "control"));
    a90_console_printf("audio.dev_snd.count=%d control_like=%d pcm_like=%d\r\n",
                       count_dir_entries("/dev/snd"),
                       count_dir_entries_matching("/dev/snd", "controlC"),
                       count_dir_entries_matching("/dev/snd", "pcm"));
}

static void print_proc_asound(void) {
    char cards[512];

    if (read_trimmed_text_file("/proc/asound/cards", cards, sizeof(cards)) == 0) {
        flatten_inline_text(cards);
        a90_console_printf("audio.proc_asound_cards=%s\r\n", cards[0] != '\0' ? cards : "empty");
    } else {
        a90_console_printf("audio.proc_asound_cards=missing errno=%d\r\n", errno);
    }
}

static int audio_scan_snd_nodes(bool materialize, struct audio_snd_scan_stats *stats) {
    DIR *dir;
    struct dirent *entry;

    memset(stats, 0, sizeof(*stats));
    dir = opendir(AUDIO_SOUND_CLASS_DIR);
    if (dir == NULL) {
        a90_console_printf("audio.snd.sysfs_open_errno=%d\r\n", errno);
        return negative_errno_or(ENOENT);
    }

    while ((entry = readdir(dir)) != NULL) {
        char sysfs_dev_path[PATH_MAX];
        char dev_node_path[PATH_MAX];
        char dev_info[64];
        unsigned int major_num = 0;
        unsigned int minor_num = 0;
        dev_t wanted;
        const char *node_state;

        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        ++stats->entries;
        if (!allowed_sound_node_name(entry->d_name)) {
            ++stats->refused;
            continue;
        }
        ++stats->allowed;
        if (read_sound_node_numbers(entry->d_name,
                                    sysfs_dev_path,
                                    sizeof(sysfs_dev_path),
                                    dev_node_path,
                                    sizeof(dev_node_path),
                                    &major_num,
                                    &minor_num,
                                    dev_info,
                                    sizeof(dev_info)) < 0) {
            ++stats->invalid;
            if (stats->listed < AUDIO_SND_MAX_LISTED) {
                a90_console_printf("audio.snd.%d.name=%s dev=invalid errno=%d action=skip\r\n",
                                   stats->listed,
                                   entry->d_name,
                                   errno);
                ++stats->listed;
            }
            continue;
        }
        ++stats->with_dev;
        wanted = makedev(major_num, minor_num);
        node_state = sound_devnode_state(dev_node_path, wanted);
        if (strcmp(node_state, "ok") == 0) {
            ++stats->already_ok;
        } else if (strcmp(node_state, "missing") == 0) {
            ++stats->missing;
        } else {
            ++stats->invalid;
        }

        if (stats->listed < AUDIO_SND_MAX_LISTED) {
            a90_console_printf("audio.snd.%d.name=%s sysfs_dev=%u:%u devnode=%s state=%s\r\n",
                               stats->listed,
                               entry->d_name,
                               major_num,
                               minor_num,
                               dev_node_path,
                               node_state);
            ++stats->listed;
        }

        if (!materialize) {
            continue;
        }
        if (strcmp(node_state, "ok") == 0) {
            continue;
        }
        if (strcmp(node_state, "missing") != 0) {
            a90_console_printf("audio.snd.materialize.refused=%s state=%s\r\n",
                               entry->d_name,
                               node_state);
            continue;
        }
        if (mknod(dev_node_path, S_IFCHR | 0600, wanted) < 0) {
            if (errno == EEXIST && strcmp(sound_devnode_state(dev_node_path, wanted), "ok") == 0) {
                ++stats->already_ok;
                continue;
            }
            a90_console_printf("audio.snd.materialize.failed=%s errno=%d\r\n",
                               entry->d_name,
                               errno);
            ++stats->failed;
            continue;
        }
        ++stats->created;
        a90_console_printf("audio.snd.materialize.created=%s major=%u minor=%u\r\n",
                           entry->d_name,
                           major_num,
                           minor_num);
    }
    closedir(dir);
    return 0;
}

static void audio_print_snd_scan_summary(const char *prefix, const struct audio_snd_scan_stats *stats) {
    a90_console_printf("%s.entries=%d allowed=%d with_dev=%d listed=%d missing=%d already_ok=%d invalid=%d refused=%d created=%d failed=%d\r\n",
                       prefix,
                       stats->entries,
                       stats->allowed,
                       stats->with_dev,
                       stats->listed,
                       stats->missing,
                       stats->already_ok,
                       stats->invalid,
                       stats->refused,
                       stats->created,
                       stats->failed);
}

static int audio_print_snd_status(void) {
    struct audio_snd_scan_stats stats;
    int rc;

    a90_console_printf("audio.snd_status.version=1\r\n");
    a90_console_printf("audio.snd_status.read_only=1\r\n");
    print_class_counts();
    print_proc_asound();
    rc = audio_scan_snd_nodes(false, &stats);
    audio_print_snd_scan_summary("audio.snd_status", &stats);
    a90_console_printf("audio.status.audio_playback_attempted=0\r\n");
    return rc;
}

static int audio_snd_materialize_once(char **argv, int argc) {
    struct audio_snd_scan_stats stats;
    int rc;

    a90_console_printf("audio.snd_materialize.version=1\r\n");
    a90_console_printf("audio.snd_materialize.scope=AUD-3-preflight-node-materialization-only\r\n");
    a90_console_printf("audio.status.audio_playback_attempted=0\r\n");

    if (argc != 3 || argv == NULL || argv[2] == NULL ||
        strcmp(argv[2], AUDIO_SND_MATERIALIZE_TOKEN) != 0) {
        a90_console_printf("audio.snd_materialize.refused=missing-token\r\n");
        a90_console_printf("usage: audio snd-materialize-once %s\r\n", AUDIO_SND_MATERIALIZE_TOKEN);
        return -EPERM;
    }
    if (count_dir_entries_matching(AUDIO_SOUND_CLASS_DIR, "control") <= 0) {
        a90_console_printf("audio.snd_materialize.refused=no-control-sysfs\r\n");
        return -ENOENT;
    }
    if (ensure_dir(AUDIO_DEV_SND_DIR, 0755) < 0) {
        a90_console_printf("audio.snd_materialize.refused=dev-snd-dir errno=%d\r\n", errno);
        return negative_errno_or(EIO);
    }

    rc = audio_scan_snd_nodes(true, &stats);
    audio_print_snd_scan_summary("audio.snd_materialize", &stats);
    a90_console_printf("audio.snd_materialize.open_attempted=0\r\n");
    a90_console_printf("audio.snd_materialize.ioctl_attempted=0\r\n");
    a90_console_printf("audio.snd_materialize.playback_attempted=0\r\n");
    if (rc < 0) {
        return rc;
    }
    if (stats.failed > 0 || stats.invalid > 0) {
        return -EIO;
    }
    if (stats.created == 0 && stats.already_ok == 0) {
        return -ENOENT;
    }
    return 0;
}

static void audio_print_core_promotion_status(const struct audio_speaker_profile *profile) {
    a90_console_printf("audio.status.core.promoted=1\r\n");
    a90_console_printf("audio.status.core.promotion_run=%s\r\n", AUDIO_CORE_PROMOTION_RUN);
    a90_console_printf("audio.status.core.version=%s\r\n", AUDIO_CORE_PROMOTION_VERSION);
    a90_console_printf("audio.status.core.build_tag=%s\r\n", AUDIO_CORE_PROMOTION_TAG);
    a90_console_printf("audio.status.core.validation_run=%s\r\n", AUDIO_CORE_VALIDATION_RUN);
    a90_console_printf("audio.status.core.native_play_gate=closed\r\n");
    if (profile != NULL) {
        a90_console_printf("audio.status.profile.id=%s\r\n", profile->id);
        a90_console_printf("audio.status.profile.endpoint=%s\r\n", profile->endpoint);
        a90_console_printf("audio.status.profile.speaker_map=%s\r\n", profile->speaker_map);
        a90_console_printf("audio.status.profile.app_type=%d\r\n", profile->app_type);
        a90_console_printf("audio.status.profile.acdb_id=%d\r\n", profile->acdb_id);
        a90_console_printf("audio.status.profile.sample_rate=%d\r\n", profile->sample_rate);
        a90_console_printf("audio.status.profile.bit_width=%d\r\n", profile->bit_width);
        a90_console_printf("audio.status.profile.route_control_count=%d\r\n", a90_audio_route_control_count());
        a90_console_printf("audio.status.profile.speaker_count=%d\r\n", a90_audio_speaker_map_count());
        a90_console_printf("audio.status.safety.amplitude_cap_milli=%d\r\n", profile->amplitude_cap_milli);
        a90_console_printf("audio.status.safety.duration_cap_ms=%d\r\n", profile->duration_cap_ms);
    }
    a90_console_printf("audio.status.safety.smart_amp_boost_write_allowed=0\r\n");
    a90_console_printf("audio.status.safety.wsa_speaker_protection_verified=0\r\n");
}

static int audio_print_adsp_status(void) {
    struct audio_snd_scan_stats snd_stats;
    const struct audio_speaker_profile *profile = a90_audio_find_profile(AUDIO_DEFAULT_PROFILE_ID);
    a90_console_printf("audio.status.version=2\r\n");
    a90_console_printf("audio.status.read_only=1\r\n");
    a90_console_printf("audio.status.default_profile=%s\r\n", AUDIO_DEFAULT_PROFILE_ID);
    audio_print_core_promotion_status(profile);
    print_trimmed_or_missing("firmware_class_path", AUDIO_FWCLASS_PATH);
    print_mode_line("boot_adsp_boot", AUDIO_BOOT_ATTR);
    print_firmware_status();
    print_remoteproc_status();
    print_class_counts();
    print_proc_asound();
    if (audio_scan_snd_nodes(false, &snd_stats) == 0) {
        audio_print_snd_scan_summary("audio.snd_status", &snd_stats);
    }
    print_mode_line("dev_subsys_adsp", "/dev/subsys_adsp");
    print_mode_line("dev_adsprpc_smd", "/dev/adsprpc-smd");
    a90_console_printf("audio.status.activation_write_attempted=0\r\n");
    a90_console_printf("audio.status.audio_playback_attempted=0\r\n");
    return 0;
}

static int audio_adsp_boot_once(char **argv, int argc) {
    struct adsp_firmware_status mounted_status;
    struct adsp_firmware_status class_status;
    struct stat st;
    char fwclass_path[PATH_MAX];
    int fwclass_read_rc;
    int fd;

    a90_console_printf("audio.adsp_boot_once.version=1\r\n");
    a90_console_printf("audio.adsp_boot_once.scope=AUD-2-liveness-only\r\n");
    a90_console_printf("audio.status.audio_playback_attempted=0\r\n");

    if (argc != 3 || argv == NULL || argv[2] == NULL ||
        strcmp(argv[2], AUDIO_ADSP_BOOT_ONCE_TOKEN) != 0) {
        a90_console_printf("audio.adsp_boot_once.refused=missing-token\r\n");
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        a90_console_printf("usage: audio adsp-boot-once %s\r\n", AUDIO_ADSP_BOOT_ONCE_TOKEN);
        return -EPERM;
    }

    if (!path_lstat(AUDIO_BOOT_ATTR, &st)) {
        a90_console_printf("audio.adsp_boot_once.refused=no-boot-attr errno=%d\r\n", errno);
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        return negative_errno_or(ENOENT);
    }
    if (!path_is_dir(AUDIO_FW_DIR)) {
        a90_console_printf("audio.adsp_boot_once.refused=no-firmware-dir\r\n");
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        return -ENOENT;
    }
    check_adsp_firmware_dir(AUDIO_FW_DIR, &mounted_status);
    if (!mounted_status.mdt_present) {
        a90_console_printf("audio.adsp_boot_once.refused=no-adsp-mdt\r\n");
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        return -ENOENT;
    }
    if (mounted_status.present_segments != expected_adsp_segments()) {
        a90_console_printf("audio.adsp_boot_once.refused=missing-adsp-segments present=%d expected=%d model=%s missing=%s\r\n",
                           mounted_status.present_segments,
                           expected_adsp_segments(),
                           AUDIO_ADSP_SEGMENT_MODEL,
                           mounted_status.missing_segments);
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        return -ENOENT;
    }
    fwclass_read_rc = read_trimmed_text_file(AUDIO_FWCLASS_PATH, fwclass_path, sizeof(fwclass_path));
    if (fwclass_read_rc < 0) {
        a90_console_printf("audio.adsp_boot_once.refused=firmware-class-path-unreadable errno=%d\r\n",
                           errno);
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        return negative_errno_or(ENOENT);
    }
    if (fwclass_path[0] == '\0') {
        a90_console_printf("audio.adsp_boot_once.refused=firmware-class-path-empty\r\n");
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        return -ENOENT;
    }
    flatten_inline_text(fwclass_path);
    check_adsp_firmware_dir(fwclass_path, &class_status);
    if (!adsp_firmware_complete(&class_status)) {
        a90_console_printf("audio.adsp_boot_once.refused=firmware-class-path-incomplete path=%s mdt=%s present=%d expected=%d model=%s missing=%s\r\n",
                           fwclass_path,
                           yesno(class_status.mdt_present),
                           class_status.present_segments,
                           expected_adsp_segments(),
                           AUDIO_ADSP_SEGMENT_MODEL,
                           class_status.missing_segments);
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        return -ENOENT;
    }
    if (count_dir_entries_matching("/sys/bus/rpmsg/devices", "adsp") > 0 ||
        count_dir_entries_matching("/sys/class/sound", "card") > 0 ||
        count_dir_entries_matching("/dev/snd", "controlC") > 0) {
        a90_console_printf("audio.adsp_boot_once.refused=already-up-or-sound-present\r\n");
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        return -EALREADY;
    }

    fd = open(AUDIO_BOOT_ATTR, O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        a90_console_printf("audio.adsp_boot_once.write=open_failed errno=%d\r\n", errno);
        a90_console_printf("audio.status.activation_write_attempted=0\r\n");
        return negative_errno_or(EIO);
    }

    a90_console_printf("audio.status.activation_write_attempted=1\r\n");
    if (write_all_checked(fd, "1\n", 2) < 0) {
        a90_console_printf("audio.adsp_boot_once.write=failed errno=%d\r\n", errno);
        close(fd);
        return negative_errno_or(EIO);
    }
    if (close(fd) < 0) {
        a90_console_printf("audio.adsp_boot_once.write=close_failed errno=%d\r\n", errno);
        return negative_errno_or(EIO);
    }
    a90_console_printf("audio.adsp_boot_once.write=accepted\r\n");
    a90_console_printf("audio.adsp_boot_once.retry=forbidden\r\n");
    return 0;
}

int a90_audio_cmd(char **argv, int argc) {
    if (argc <= 1 ||
        (argc == 2 && (strcmp(argv[1], "adsp-status") == 0 || strcmp(argv[1], "status") == 0))) {
        return audio_print_adsp_status();
    }
    if (argc == 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "profiles") == 0) {
        return a90_audio_query_profiles_cmd();
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "profile") == 0) {
        return a90_audio_query_profile_cmd(argv, argc);
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "speaker-map") == 0) {
        return a90_audio_query_speaker_map_cmd(argv, argc);
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "stages") == 0) {
        return a90_audio_query_stages_cmd(argv, argc);
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "prereq") == 0) {
        return audio_prereq_cmd(argv, argc);
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "app-type") == 0) {
        return audio_app_type_cmd(argv, argc);
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "setcal") == 0) {
        return audio_setcal_cmd(argv, argc);
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "play") == 0) {
        return audio_play_cmd(argv, argc);
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "chime") == 0) {
        return audio_chime_cmd(argv, argc);
    }
    if (argc == 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "play-status") == 0) {
        return audio_play_status_cmd();
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "stop") == 0) {
        return audio_stop_cmd(argv, argc);
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "route") == 0) {
        return audio_route_cmd(argv, argc);
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "adsp-boot-once") == 0) {
        return audio_adsp_boot_once(argv, argc);
    }
    if (argc == 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "snd-status") == 0) {
        return audio_print_snd_status();
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "snd-materialize-once") == 0) {
        return audio_snd_materialize_once(argv, argc);
    }
    a90_console_printf("usage: audio [adsp-status|status|profiles|profile [id]|speaker-map [id]|stages [id]|prereq [id]|app-type [profile] [--dry-run|--write]|setcal [profile] [--dry-run|--execute] [--manifest PATH --verify|--prepare|--load]|play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--manifest PATH] [--dry-run|--execute]|chime [--dry-run|--execute] [--amplitude-milli N] [--duration-ms N] [--manifest PATH]|play-status|stop [profile] [--dry-run|--execute]|route [profile] [--dry-run|--apply|--reset] [--layer all|core|feedback|endpoint|blocked]|snd-status|adsp-boot-once|snd-materialize-once]\r\n");
    return -EINVAL;
}
