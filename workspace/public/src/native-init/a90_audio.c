#include "a90_audio.h"

#include "a90_console.h"
#include "a90_helper.h"
#include "a90_util.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/ioctl.h>
#include <unistd.h>

#include <sound/asound.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#define AUDIO_FW_DIR "/vendor/firmware_mnt/image"
#define AUDIO_FWCLASS_PATH "/sys/module/firmware_class/parameters/path"
#define AUDIO_BOOT_ATTR "/sys/kernel/boot_adsp/boot"
#define AUDIO_ADSP_BOOT_ONCE_TOKEN "AUD2_ONE_SHOT_ADSP_BOOT"
#define AUDIO_SND_MATERIALIZE_TOKEN "AUD3_DEV_SND_MATERIALIZE_ONLY"
#define AUDIO_SOUND_CLASS_DIR "/sys/class/sound"
#define AUDIO_DEV_SND_DIR "/dev/snd"
#define AUDIO_MAX_LISTED 8
#define AUDIO_SND_MAX_LISTED 64
#define AUDIO_MISSING_LIST_SIZE 192
#define AUDIO_ADSP_SEGMENT_MODEL "stock-sparse-b00-b11-b13-b16"
#define AUDIO_PROFILE_VERSION 1
#define AUDIO_DEFAULT_PROFILE_ID "internal-speaker-safe"
#define AUDIO_PROFILE_ACDB_SET_COUNT 11
#define AUDIO_PROFILE_FORBIDDEN_CAL_COUNT 3
#define AUDIO_PROFILE_OBSERVER_COUNT 8
#define AUDIO_APP_TYPE_CFG_MAX_VALUES 128
#define AUDIO_ROUTE_APPLY_COUNT 13
#define AUDIO_ROUTE_RESET_COUNT 12
#define AUDIO_SETCAL_MANIFEST_VERSION 1
#define AUDIO_SETCAL_DEFAULT_MANIFEST_PATH "/cache/a90-runtime/pkg/manifests/audio-setcal-internal-speaker-safe.manifest"
#define AUDIO_SETCAL_RUNTIME_PREFIX "/cache/a90-runtime"
#define AUDIO_SETCAL_LEGACY_REPLAY_PREFIX "/cache/a90-acdb-setcal-replay-"
#define AUDIO_SETCAL_DEV_MSM_AUDIO_CAL "/dev/msm_audio_cal"
#define AUDIO_SETCAL_DEV_ION "/dev/ion"
#define AUDIO_SETCAL_IOCTL_ALLOCATE_CALIBRATION 0xC00461C8u
#define AUDIO_SETCAL_IOCTL_DEALLOCATE_CALIBRATION 0xC00461C9u
#define AUDIO_SETCAL_IOCTL_SET_CALIBRATION 0xC00461CBu
#define AUDIO_SETCAL_MANIFEST_PROFILE_SIZE 96
#define AUDIO_SETCAL_MANIFEST_ROLE_SIZE 64
#define AUDIO_SETCAL_MANIFEST_SHA256_SIZE 65
#define AUDIO_PCM_PERIOD_SIZE 1024
#define AUDIO_PCM_PERIOD_COUNT 4

enum audio_route_value_kind {
    AUDIO_ROUTE_VALUE_INTS = 1,
    AUDIO_ROUTE_VALUE_ENUM = 2,
};

struct audio_route_value {
    enum audio_route_value_kind kind;
    const char *enum_value;
    int ints[4];
    int int_count;
    int zero_fill;
};

struct audio_route_control {
    const char *name;
    const char *role;
    const char *layer;
    const char *speaker;
    const char *policy;
    int order;
    bool resettable;
    bool smart_amp_boost;
    struct audio_route_value apply;
    struct audio_route_value reset;
};

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

struct audio_speaker_profile {
    const char *id;
    const char *endpoint;
    const char *speaker_map;
    int card;
    int pcm_device;
    int channels;
    int sample_rate;
    int bit_width;
    int app_type;
    int acdb_id;
    int stream_control_width;
    const char *global_app_type_config;
    const char *stream_app_type_config;
    const int acdb_set_order[AUDIO_PROFILE_ACDB_SET_COUNT];
    const int forbidden_cal_types[AUDIO_PROFILE_FORBIDDEN_CAL_COUNT];
    const char *const *observer_controls;
    int observer_control_count;
    int probe_amplitude_milli;
    int probe_duration_ms;
    int listen_amplitude_milli;
    int listen_duration_ms;
    int amplitude_cap_milli;
    int duration_cap_ms;
};

struct audio_stage_contract {
    const char *id;
    const char *owner;
    const char *phase;
    const char *command_template;
    const char *speaker_scope;
    const char *note;
    int order;
    bool uses_profile;
    bool native_implemented;
    bool writes_runtime_state;
    bool rollback_boundary;
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

static const char *const AUDIO_INTERNAL_SPEAKER_OBSERVER_CONTROLS[] = {
    "SpkrLeft COMP Switch",
    "SpkrRight COMP Switch",
    "SpkrLeft BOOST Switch",
    "SpkrRight BOOST Switch",
    "SpkrLeft VISENSE Switch",
    "SpkrRight VISENSE Switch",
    "Get RMS",
    "App Type Config",
};

static const struct audio_speaker_profile AUDIO_SPEAKER_PROFILES[] = {
    {
        .id = AUDIO_DEFAULT_PROFILE_ID,
        .endpoint = "internal-speaker",
        .speaker_map = "SpkrLeft/SpkrRight WSA881x via WSA_CDC_DMA_RX",
        .card = 0,
        .pcm_device = 0,
        .channels = 2,
        .sample_rate = 48000,
        .bit_width = 16,
        .app_type = 69941,
        .acdb_id = 15,
        .stream_control_width = 2,
        .global_app_type_config = "1 69941 48000 16",
        .stream_app_type_config = "69941 15 48000 2",
        .acdb_set_order = {39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21},
        .forbidden_cal_types = {10, 14, 24},
        .observer_controls = AUDIO_INTERNAL_SPEAKER_OBSERVER_CONTROLS,
        .observer_control_count = AUDIO_PROFILE_OBSERVER_COUNT,
        .probe_amplitude_milli = 20,
        .probe_duration_ms = 1000,
        .listen_amplitude_milli = 150,
        .listen_duration_ms = 8000,
        .amplitude_cap_milli = 200,
        .duration_cap_ms = 10000,
    },
};

static const struct audio_route_control AUDIO_INTERNAL_SPEAKER_ROUTE[] = {
    {
        .name = "Audio Stream 0 App Type Cfg",
        .role = "stream_cfg",
        .layer = "core",
        .speaker = "shared",
        .policy = "safe-observed",
        .order = 10,
        .resettable = false,
        .apply = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {69941, 15, 48000, 2}, .int_count = 4, .zero_fill = 124},
        .reset = {.kind = AUDIO_ROUTE_VALUE_INTS, .int_count = 0, .zero_fill = 0},
    },
    {
        .name = "Playback Channel Map0",
        .role = "stream_cfg",
        .layer = "core",
        .speaker = "shared",
        .policy = "safe-observed",
        .order = 20,
        .resettable = true,
        .apply = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {1, 2}, .int_count = 2, .zero_fill = 30},
        .reset = {.kind = AUDIO_ROUTE_VALUE_INTS, .int_count = 0, .zero_fill = 32},
    },
    {
        .name = "SLIMBUS_0_RX Audio Mixer MultiMedia1",
        .role = "route",
        .layer = "core",
        .speaker = "shared",
        .policy = "safe-observed",
        .order = 30,
        .resettable = true,
        .apply = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {1, 0}, .int_count = 2, .zero_fill = 0},
        .reset = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {0, 0}, .int_count = 2, .zero_fill = 0},
    },
    {
        .name = "SLIM RX0 MUX",
        .role = "route",
        .layer = "core",
        .speaker = "shared",
        .policy = "safe-observed",
        .order = 40,
        .resettable = true,
        .apply = {.kind = AUDIO_ROUTE_VALUE_ENUM, .enum_value = "AIF1_PB"},
        .reset = {.kind = AUDIO_ROUTE_VALUE_ENUM, .enum_value = "ZERO"},
    },
    {
        .name = "RX INT7_1 MIX1 INP0",
        .role = "route",
        .layer = "core",
        .speaker = "shared",
        .policy = "safe-observed",
        .order = 50,
        .resettable = true,
        .apply = {.kind = AUDIO_ROUTE_VALUE_ENUM, .enum_value = "RX0"},
        .reset = {.kind = AUDIO_ROUTE_VALUE_ENUM, .enum_value = "ZERO"},
    },
    {
        .name = "COMP7 Switch",
        .role = "route",
        .layer = "core",
        .speaker = "shared",
        .policy = "safe-observed",
        .order = 60,
        .resettable = true,
        .apply = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {1}, .int_count = 1, .zero_fill = 0},
        .reset = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {0}, .int_count = 1, .zero_fill = 0},
    },
    {
        .name = "AIF4_VI Mixer SPKR_VI_1",
        .role = "speaker_feedback",
        .layer = "feedback",
        .speaker = "SPKR_VI_1",
        .policy = "speaker-protection-observed",
        .order = 70,
        .resettable = true,
        .apply = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {1}, .int_count = 1, .zero_fill = 0},
        .reset = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {0}, .int_count = 1, .zero_fill = 0},
    },
    {
        .name = "AIF4_VI Mixer SPKR_VI_2",
        .role = "speaker_feedback",
        .layer = "feedback",
        .speaker = "SPKR_VI_2",
        .policy = "speaker-protection-observed",
        .order = 80,
        .resettable = true,
        .apply = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {1}, .int_count = 1, .zero_fill = 0},
        .reset = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {0}, .int_count = 1, .zero_fill = 0},
    },
    {
        .name = "SLIM_4_TX Format",
        .role = "speaker_feedback",
        .layer = "feedback",
        .speaker = "SPKR_VI",
        .policy = "speaker-protection-observed",
        .order = 90,
        .resettable = true,
        .apply = {.kind = AUDIO_ROUTE_VALUE_ENUM, .enum_value = "PACKED_16B"},
        .reset = {.kind = AUDIO_ROUTE_VALUE_ENUM, .enum_value = "UNPACKED"},
    },
    {
        .name = "SpkrLeft VISENSE Switch",
        .role = "speaker_endpoint",
        .layer = "endpoint",
        .speaker = "SpkrLeft",
        .policy = "speaker-protection-observed",
        .order = 100,
        .resettable = true,
        .apply = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {1}, .int_count = 1, .zero_fill = 0},
        .reset = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {0}, .int_count = 1, .zero_fill = 0},
    },
    {
        .name = "SpkrLeft COMP Switch",
        .role = "speaker_endpoint",
        .layer = "endpoint",
        .speaker = "SpkrLeft",
        .policy = "speaker-endpoint-review",
        .order = 110,
        .resettable = true,
        .apply = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {1}, .int_count = 1, .zero_fill = 0},
        .reset = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {0}, .int_count = 1, .zero_fill = 0},
    },
    {
        .name = "SpkrLeft BOOST Switch",
        .role = "speaker_endpoint",
        .layer = "endpoint",
        .speaker = "SpkrLeft",
        .policy = "blocked-smart-amp-boost",
        .order = 120,
        .resettable = true,
        .smart_amp_boost = true,
        .apply = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {1}, .int_count = 1, .zero_fill = 0},
        .reset = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {0}, .int_count = 1, .zero_fill = 0},
    },
    {
        .name = "SpkrLeft SWR DAC_Port Switch",
        .role = "speaker_endpoint",
        .layer = "endpoint",
        .speaker = "SpkrLeft",
        .policy = "safe-observed",
        .order = 130,
        .resettable = true,
        .apply = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {1}, .int_count = 1, .zero_fill = 0},
        .reset = {.kind = AUDIO_ROUTE_VALUE_INTS, .ints = {0}, .int_count = 1, .zero_fill = 0},
    },
};

static const struct audio_stage_contract AUDIO_STAGE_CONTRACTS[] = {
    {
        .id = "preflight-v2321-health",
        .owner = "host",
        .phase = "boot",
        .command_template = "a90ctl version/status/selftest",
        .speaker_scope = "host",
        .note = "confirm rollback baseline health before flashing or playback work",
        .order = 10,
        .native_implemented = false,
        .writes_runtime_state = false,
        .rollback_boundary = true,
    },
    {
        .id = "adsp-boot-once",
        .owner = "native-init",
        .phase = "adsp",
        .command_template = "audio adsp-boot-once AUD2_ONE_SHOT_ADSP_BOOT",
        .speaker_scope = "shared",
        .note = "bounded ADSP boot write; retry is forbidden in one boot",
        .order = 20,
        .native_implemented = true,
        .writes_runtime_state = true,
        .rollback_boundary = false,
    },
    {
        .id = "snd-materialize-once",
        .owner = "native-init",
        .phase = "snd",
        .command_template = "audio snd-materialize-once AUD3_DEV_SND_MATERIALIZE_ONLY",
        .speaker_scope = "shared",
        .note = "materialize ALSA /dev/snd nodes from sysfs only",
        .order = 30,
        .native_implemented = true,
        .writes_runtime_state = true,
        .rollback_boundary = false,
    },
    {
        .id = "write-global-app-type-config",
        .owner = "native-init",
        .phase = "app_type",
        .command_template = "audio app-type %s --write",
        .speaker_scope = "shared",
        .note = "writes App Type Config with the V2735 proven tuple",
        .order = 40,
        .uses_profile = true,
        .native_implemented = true,
        .writes_runtime_state = true,
        .rollback_boundary = false,
    },
    {
        .id = "verify-private-acdb-manifest",
        .owner = "native-init",
        .phase = "acdb",
        .command_template = "audio setcal %s --manifest " AUDIO_SETCAL_DEFAULT_MANIFEST_PATH " --verify --dry-run",
        .speaker_scope = "shared",
        .note = "verifies private SET arg/payload files by path, size, and sha256 without issuing audio calibration ioctls",
        .order = 45,
        .uses_profile = true,
        .native_implemented = true,
        .writes_runtime_state = false,
        .rollback_boundary = false,
    },
    {
        .id = "prepare-acdb-payload-bundle",
        .owner = "native-init",
        .phase = "acdb",
        .command_template = "audio setcal %s --manifest " AUDIO_SETCAL_DEFAULT_MANIFEST_PATH " --prepare --dry-run",
        .speaker_scope = "shared",
        .note = "summarizes verified private SET arg/payload byte plan without opening audio devices",
        .order = 47,
        .uses_profile = true,
        .native_implemented = true,
        .writes_runtime_state = false,
        .rollback_boundary = false,
    },
    {
        .id = "load-acdb-payload-files",
        .owner = "native-init",
        .phase = "acdb",
        .command_template = "audio setcal %s --manifest " AUDIO_SETCAL_DEFAULT_MANIFEST_PATH " --load --dry-run",
        .speaker_scope = "shared",
        .note = "opens and drains verified private SET arg/payload files without opening audio devices or issuing ioctls",
        .order = 48,
        .uses_profile = true,
        .native_implemented = true,
        .writes_runtime_state = false,
        .rollback_boundary = false,
    },
    {
        .id = "replay-acdb-setcal-sequence",
        .owner = "native-init",
        .phase = "acdb",
        .command_template = "audio setcal %s --manifest " AUDIO_SETCAL_DEFAULT_MANIFEST_PATH " --execute",
        .speaker_scope = "shared",
        .note = "SET replay remains blocked until the private manifest verifier is followed by a native ioctl implementation",
        .order = 50,
        .uses_profile = true,
        .native_implemented = false,
        .writes_runtime_state = true,
        .rollback_boundary = false,
    },
    {
        .id = "apply-core-speaker-route",
        .owner = "native-init",
        .phase = "route",
        .command_template = "audio route %s --apply --layer core",
        .speaker_scope = "shared",
        .note = "applies only core route controls; endpoint/boost layers remain blocked",
        .order = 60,
        .uses_profile = true,
        .native_implemented = true,
        .writes_runtime_state = true,
        .rollback_boundary = false,
    },
    {
        .id = "plan-bounded-pcm-playback",
        .owner = "native-init",
        .phase = "pcm",
        .command_template = "audio play %s --mode probe --dry-run",
        .speaker_scope = "internal-speaker",
        .note = "plans bounded PCM playback from profile defaults and enforces amplitude/duration caps without opening ALSA",
        .order = 68,
        .uses_profile = true,
        .native_implemented = true,
        .writes_runtime_state = false,
        .rollback_boundary = false,
    },
    {
        .id = "bounded-pcm-playback",
        .owner = "native-init",
        .phase = "pcm",
        .command_template = "audio play %s --mode probe --execute",
        .speaker_scope = "internal-speaker",
        .note = "planned bounded tone API; amplitude stays capped by the profile",
        .order = 70,
        .uses_profile = true,
        .native_implemented = false,
        .writes_runtime_state = true,
        .rollback_boundary = false,
    },
    {
        .id = "plan-audio-stop-cleanup",
        .owner = "native-init",
        .phase = "cleanup",
        .command_template = "audio stop %s --dry-run",
        .speaker_scope = "internal-speaker",
        .note = "plans PCM stop, reverse ACDB deallocation, and core route reset without touching ALSA or calibration ioctls",
        .order = 78,
        .uses_profile = true,
        .native_implemented = true,
        .writes_runtime_state = false,
        .rollback_boundary = false,
    },
    {
        .id = "reset-core-speaker-route",
        .owner = "native-init",
        .phase = "cleanup",
        .command_template = "audio route %s --reset --layer core",
        .speaker_scope = "shared",
        .note = "resets the same core controls in reverse order",
        .order = 80,
        .uses_profile = true,
        .native_implemented = true,
        .writes_runtime_state = true,
        .rollback_boundary = false,
    },
    {
        .id = "rollback-v2321",
        .owner = "host",
        .phase = "rollback",
        .command_template = "native_init_flash.py boot_linux_v2321_usb_clean_identity_rodata.img",
        .speaker_scope = "host",
        .note = "checked boot-partition rollback target for live audio tests",
        .order = 90,
        .native_implemented = false,
        .writes_runtime_state = true,
        .rollback_boundary = true,
    },
};

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

static const char *const AUDIO_SPEAKER_MAP_IDS[] = {
    "shared",
    "SPKR_VI_1",
    "SPKR_VI_2",
    "SPKR_VI",
    "SpkrLeft",
    "SpkrRight",
};

static const char *yesno(bool value) {
    return value ? "yes" : "no";
}

static int audio_profile_count(void) {
    return (int)(sizeof(AUDIO_SPEAKER_PROFILES) / sizeof(AUDIO_SPEAKER_PROFILES[0]));
}

static int audio_stage_count(void) {
    return (int)(sizeof(AUDIO_STAGE_CONTRACTS) / sizeof(AUDIO_STAGE_CONTRACTS[0]));
}

static int audio_setcal_entry_count(void) {
    return (int)(sizeof(AUDIO_INTERNAL_SPEAKER_SETCAL_PLAN) / sizeof(AUDIO_INTERNAL_SPEAKER_SETCAL_PLAN[0]));
}

static const struct audio_speaker_profile *audio_find_profile(const char *id) {
    int index;

    if (id == NULL || id[0] == '\0') {
        id = AUDIO_DEFAULT_PROFILE_ID;
    }
    for (index = 0; index < audio_profile_count(); ++index) {
        if (strcmp(AUDIO_SPEAKER_PROFILES[index].id, id) == 0) {
            return &AUDIO_SPEAKER_PROFILES[index];
        }
    }
    return NULL;
}

static void print_int_list(const char *prefix, const int *values, int count) {
    int index;

    a90_console_printf("%s=", prefix);
    for (index = 0; index < count; ++index) {
        a90_console_printf("%s%d", index == 0 ? "" : ",", values[index]);
    }
    a90_console_printf("\r\n");
}

static void print_str_list(const char *prefix, const char *const *values, int count) {
    int index;

    a90_console_printf("%s=", prefix);
    for (index = 0; index < count; ++index) {
        a90_console_printf("%s%s", index == 0 ? "" : "|", values[index]);
    }
    a90_console_printf("\r\n");
}

static int audio_print_profiles(void) {
    int index;

    a90_console_printf("audio.profiles.version=%d\r\n", AUDIO_PROFILE_VERSION);
    a90_console_printf("audio.profiles.count=%d\r\n", audio_profile_count());
    a90_console_printf("audio.profiles.default=%s\r\n", AUDIO_DEFAULT_PROFILE_ID);
    for (index = 0; index < audio_profile_count(); ++index) {
        a90_console_printf("audio.profiles.%d.id=%s endpoint=%s card=%d pcm=%d\r\n",
                           index,
                           AUDIO_SPEAKER_PROFILES[index].id,
                           AUDIO_SPEAKER_PROFILES[index].endpoint,
                           AUDIO_SPEAKER_PROFILES[index].card,
                           AUDIO_SPEAKER_PROFILES[index].pcm_device);
    }
    return 0;
}

static int audio_print_profile(char **argv, int argc) {
    const struct audio_speaker_profile *profile;
    const char *id = AUDIO_DEFAULT_PROFILE_ID;

    if (argc > 3) {
        a90_console_printf("usage: audio profile [%s]\r\n", AUDIO_DEFAULT_PROFILE_ID);
        return -EINVAL;
    }
    if (argc == 3 && argv != NULL && argv[2] != NULL) {
        id = argv[2];
    }
    profile = audio_find_profile(id);
    if (profile == NULL) {
        a90_console_printf("audio.profile.error=unknown-profile id=%s\r\n", id);
        return -ENOENT;
    }

    a90_console_printf("audio.profile.version=%d\r\n", AUDIO_PROFILE_VERSION);
    a90_console_printf("audio.profile.id=%s\r\n", profile->id);
    a90_console_printf("audio.profile.endpoint=%s\r\n", profile->endpoint);
    a90_console_printf("audio.profile.speaker_map=%s\r\n", profile->speaker_map);
    a90_console_printf("audio.profile.card=%d\r\n", profile->card);
    a90_console_printf("audio.profile.pcm_device=%d\r\n", profile->pcm_device);
    a90_console_printf("audio.profile.channels=%d\r\n", profile->channels);
    a90_console_printf("audio.profile.sample_rate=%d\r\n", profile->sample_rate);
    a90_console_printf("audio.profile.bit_width=%d\r\n", profile->bit_width);
    a90_console_printf("audio.profile.app_type=%d\r\n", profile->app_type);
    a90_console_printf("audio.profile.acdb_id=%d\r\n", profile->acdb_id);
    a90_console_printf("audio.profile.stream_control_width=%d\r\n", profile->stream_control_width);
    a90_console_printf("audio.profile.global_app_type_config=%s\r\n", profile->global_app_type_config);
    a90_console_printf("audio.profile.stream_app_type_config=%s\r\n", profile->stream_app_type_config);
    print_int_list("audio.profile.acdb_set_order", profile->acdb_set_order, AUDIO_PROFILE_ACDB_SET_COUNT);
    print_int_list("audio.profile.forbidden_cal_types", profile->forbidden_cal_types, AUDIO_PROFILE_FORBIDDEN_CAL_COUNT);
    print_str_list("audio.profile.observer_controls", profile->observer_controls, profile->observer_control_count);
    a90_console_printf("audio.profile.probe_defaults.amplitude_milli=%d duration_ms=%d\r\n",
                       profile->probe_amplitude_milli,
                       profile->probe_duration_ms);
    a90_console_printf("audio.profile.listen_defaults.amplitude_milli=%d duration_ms=%d\r\n",
                       profile->listen_amplitude_milli,
                       profile->listen_duration_ms);
    a90_console_printf("audio.profile.safety.amplitude_cap_milli=%d duration_cap_ms=%d\r\n",
                       profile->amplitude_cap_milli,
                       profile->duration_cap_ms);
    a90_console_printf("audio.profile.safety.no_smart_amp_gain_boost_changes=1\r\n");
    a90_console_printf("audio.profile.read_only=1\r\n");
    return 0;
}

static void audio_print_stage_command(const char *prefix,
                                      const struct audio_stage_contract *stage,
                                      const struct audio_speaker_profile *profile) {
    a90_console_printf("%s.command=", prefix);
    if (stage->uses_profile) {
        a90_console_printf(stage->command_template, profile->id);
    } else {
        a90_console_printf("%s", stage->command_template);
    }
    a90_console_printf("\r\n");
}

static int audio_print_stages(char **argv, int argc) {
    const struct audio_speaker_profile *profile;
    const char *id = AUDIO_DEFAULT_PROFILE_ID;
    int index;
    int native_count = 0;
    int runtime_write_count = 0;
    char prefix[64];

    if (argc > 3) {
        a90_console_printf("usage: audio stages [%s]\r\n", AUDIO_DEFAULT_PROFILE_ID);
        return -EINVAL;
    }
    if (argc == 3 && argv != NULL && argv[2] != NULL) {
        id = argv[2];
    }
    profile = audio_find_profile(id);
    a90_console_printf("audio.stages.version=1\r\n");
    a90_console_printf("audio.stages.profile=%s\r\n", id);
    if (profile == NULL) {
        a90_console_printf("audio.stages.error=unknown-profile\r\n");
        return -ENOENT;
    }
    for (index = 0; index < audio_stage_count(); ++index) {
        if (AUDIO_STAGE_CONTRACTS[index].native_implemented) {
            ++native_count;
        }
        if (AUDIO_STAGE_CONTRACTS[index].writes_runtime_state) {
            ++runtime_write_count;
        }
    }
    a90_console_printf("audio.stages.endpoint=%s\r\n", profile->endpoint);
    a90_console_printf("audio.stages.count=%d\r\n", audio_stage_count());
    a90_console_printf("audio.stages.native_implemented.count=%d\r\n", native_count);
    a90_console_printf("audio.stages.runtime_write.count=%d\r\n", runtime_write_count);
    a90_console_printf("audio.stages.all_native_ready=0\r\n");
    a90_console_printf("audio.stages.read_only=1\r\n");
    for (index = 0; index < audio_stage_count(); ++index) {
        const struct audio_stage_contract *stage = &AUDIO_STAGE_CONTRACTS[index];

        snprintf(prefix, sizeof(prefix), "audio.stages.%d", index);
        a90_console_printf("%s.id=%s\r\n", prefix, stage->id);
        a90_console_printf("%s.order=%d\r\n", prefix, stage->order);
        a90_console_printf("%s.owner=%s\r\n", prefix, stage->owner);
        a90_console_printf("%s.phase=%s\r\n", prefix, stage->phase);
        a90_console_printf("%s.native_implemented=%d\r\n", prefix, stage->native_implemented ? 1 : 0);
        a90_console_printf("%s.writes_runtime_state=%d\r\n", prefix, stage->writes_runtime_state ? 1 : 0);
        a90_console_printf("%s.rollback_boundary=%d\r\n", prefix, stage->rollback_boundary ? 1 : 0);
        a90_console_printf("%s.speaker_scope=%s\r\n", prefix, stage->speaker_scope);
        audio_print_stage_command(prefix, stage, profile);
        a90_console_printf("%s.note=%s\r\n", prefix, stage->note);
    }
    return 0;
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
    return audio_setcal_path_has_prefix(path, AUDIO_SETCAL_RUNTIME_PREFIX);
}

static bool audio_setcal_payload_path_allowed(const char *path) {
    if (path == NULL || path[0] != '/' || audio_setcal_path_has_dotdot(path)) {
        return false;
    }
    return audio_setcal_path_has_prefix(path, AUDIO_SETCAL_RUNTIME_PREFIX) ||
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

static int audio_setcal_cmd(char **argv, int argc) {
    const char *profile_id = AUDIO_DEFAULT_PROFILE_ID;
    const char *manifest_path = NULL;
    const struct audio_speaker_profile *profile;
    struct audio_setcal_manifest_plan *manifest_plan = NULL;
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

    profile = audio_find_profile(profile_id);
    a90_console_printf("audio.setcal.version=1\r\n");
    a90_console_printf("audio.setcal.profile=%s\r\n", profile_id);
    a90_console_printf("audio.setcal.mode=%s\r\n", execute_mode ? "execute" : "dry-run");
    a90_console_printf("audio.setcal.ioctl_attempted=0\r\n");
    a90_console_printf("audio.setcal.execute_supported=0\r\n");
    a90_console_printf("audio.setcal.verify_requested=%d\r\n", verify_manifest ? 1 : 0);
    a90_console_printf("audio.setcal.prepare_requested=%d\r\n", prepare_manifest ? 1 : 0);
    a90_console_printf("audio.setcal.load_requested=%d\r\n", load_manifest ? 1 : 0);
    a90_console_printf("audio.setcal.execute_manifest_required=%d\r\n", execute_mode ? 1 : 0);
    a90_console_printf("audio.setcal.execute_auto_load=%d\r\n", execute_mode ? 1 : 0);
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
        audio_setcal_print_execute_plan(profile, manifest_plan);
        a90_console_printf("audio.setcal.refused=execute-not-implemented-native-setcal-ioctl\r\n");
        a90_console_printf("audio.setcal.ioctl_attempted=0\r\n");
        free(manifest_plan);
        return -EPERM;
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
    snprintf(pcm_path, sizeof(pcm_path), "/dev/snd/pcmC%dD%dp", profile->card, profile->pcm_device);
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
    a90_console_printf("audio.play.execute.plan.alsa_open_attempted=0\r\n");
    a90_console_printf("audio.play.execute.plan.ioctl_attempted=0\r\n");
    a90_console_printf("audio.play.execute.plan.pcm_write_attempted=0\r\n");
}

static int audio_play_cmd(char **argv, int argc) {
    const char *profile_id = AUDIO_DEFAULT_PROFILE_ID;
    const char *mode = "probe";
    const struct audio_speaker_profile *profile;
    bool seen_profile = false;
    bool execute_mode = false;
    bool amplitude_override = false;
    bool duration_override = false;
    int requested_amplitude_milli = 0;
    int requested_duration_ms = 0;
    int amplitude_milli = 0;
    int duration_ms = 0;
    int argi;

    for (argi = 2; argi < argc; ++argi) {
        if (argv == NULL || argv[argi] == NULL) {
            a90_console_printf("usage: audio play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--dry-run|--execute]\r\n");
            return -EINVAL;
        }
        if (strcmp(argv[argi], "--dry-run") == 0) {
            execute_mode = false;
        } else if (strcmp(argv[argi], "--execute") == 0) {
            execute_mode = true;
        } else if (strcmp(argv[argi], "--mode") == 0) {
            if (argi + 1 >= argc || argv[argi + 1] == NULL) {
                a90_console_printf("usage: audio play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--dry-run|--execute]\r\n");
                return -EINVAL;
            }
            mode = argv[++argi];
        } else if (strcmp(argv[argi], "--amplitude-milli") == 0) {
            if (argi + 1 >= argc || !audio_parse_nonnegative_int(argv[argi + 1], &requested_amplitude_milli)) {
                a90_console_printf("usage: audio play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--dry-run|--execute]\r\n");
                return -EINVAL;
            }
            amplitude_override = true;
            ++argi;
        } else if (strcmp(argv[argi], "--duration-ms") == 0) {
            if (argi + 1 >= argc || !audio_parse_nonnegative_int(argv[argi + 1], &requested_duration_ms)) {
                a90_console_printf("usage: audio play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--dry-run|--execute]\r\n");
                return -EINVAL;
            }
            duration_override = true;
            ++argi;
        } else if (!seen_profile) {
            profile_id = argv[argi];
            seen_profile = true;
        } else {
            a90_console_printf("usage: audio play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--dry-run|--execute]\r\n");
            return -EINVAL;
        }
    }

    profile = audio_find_profile(profile_id);
    a90_console_printf("audio.play.version=1\r\n");
    a90_console_printf("audio.play.profile=%s\r\n", profile_id);
    a90_console_printf("audio.play.mode=%s\r\n", mode);
    a90_console_printf("audio.play.execute_requested=%d\r\n", execute_mode ? 1 : 0);
    a90_console_printf("audio.play.execute_supported=0\r\n");
    a90_console_printf("audio.play.execute_plan_supported=%d\r\n", execute_mode ? 1 : 0);
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
    a90_console_printf("audio.play.requires.app_type=1\r\n");
    a90_console_printf("audio.play.requires.setcal=1\r\n");
    a90_console_printf("audio.play.requires.route=1\r\n");
    a90_console_printf("audio.play.alsa_open_attempted=0\r\n");
    a90_console_printf("audio.play.ioctl_attempted=0\r\n");
    if (amplitude_milli > profile->amplitude_cap_milli || duration_ms > profile->duration_cap_ms) {
        a90_console_printf("audio.play.refused=safety-cap-exceeded\r\n");
        return -EPERM;
    }
    if (execute_mode) {
        audio_play_print_execute_plan(profile, mode, amplitude_milli, duration_ms);
        a90_console_printf("audio.play.refused=execute-not-implemented-native-pcm\r\n");
        a90_console_printf("audio.play.playback_attempted=0\r\n");
        return -EPERM;
    }
    a90_console_printf("audio.play.dry_run_ok=1\r\n");
    return 0;
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

    profile = audio_find_profile(profile_id);
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

    profile = audio_find_profile(profile_id);
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

static int audio_route_control_count(void) {
    return (int)(sizeof(AUDIO_INTERNAL_SPEAKER_ROUTE) / sizeof(AUDIO_INTERNAL_SPEAKER_ROUTE[0]));
}

static int audio_route_reset_count(void) {
    int count = 0;
    int index;

    for (index = 0; index < audio_route_control_count(); ++index) {
        if (AUDIO_INTERNAL_SPEAKER_ROUTE[index].resettable) {
            ++count;
        }
    }
    return count;
}

static int audio_route_value_total_count(const struct audio_route_value *value) {
    if (value == NULL) {
        return 0;
    }
    return value->int_count + value->zero_fill;
}

static const char *audio_route_value_kind_name(const struct audio_route_value *value) {
    if (value == NULL) {
        return "unknown";
    }
    if (value->kind == AUDIO_ROUTE_VALUE_ENUM) {
        return "enum";
    }
    if (value->kind == AUDIO_ROUTE_VALUE_INTS) {
        return "ints";
    }
    return "unknown";
}

static bool audio_route_has_smart_amp_boost(void) {
    int index;

    for (index = 0; index < audio_route_control_count(); ++index) {
        if (AUDIO_INTERNAL_SPEAKER_ROUTE[index].smart_amp_boost) {
            return true;
        }
    }
    return false;
}

static bool audio_route_layer_valid(const char *layer) {
    return layer != NULL &&
           (strcmp(layer, "all") == 0 ||
            strcmp(layer, "core") == 0 ||
            strcmp(layer, "feedback") == 0 ||
            strcmp(layer, "endpoint") == 0 ||
            strcmp(layer, "blocked") == 0);
}

static bool audio_route_control_matches_layer(const struct audio_route_control *control,
                                              const char *layer) {
    if (control == NULL || layer == NULL) {
        return false;
    }
    if (strcmp(layer, "all") == 0) {
        return true;
    }
    if (strcmp(layer, "blocked") == 0) {
        return control->smart_amp_boost;
    }
    return strcmp(control->layer, layer) == 0;
}

static int audio_route_selected_count(const char *layer, bool reset_mode) {
    int count = 0;
    int index;

    for (index = 0; index < audio_route_control_count(); ++index) {
        if (!audio_route_control_matches_layer(&AUDIO_INTERNAL_SPEAKER_ROUTE[index], layer)) {
            continue;
        }
        if (reset_mode && !AUDIO_INTERNAL_SPEAKER_ROUTE[index].resettable) {
            continue;
        }
        ++count;
    }
    return count;
}

static bool audio_route_selected_has_smart_amp_boost(const char *layer) {
    int index;

    for (index = 0; index < audio_route_control_count(); ++index) {
        if (audio_route_control_matches_layer(&AUDIO_INTERNAL_SPEAKER_ROUTE[index], layer) &&
            AUDIO_INTERNAL_SPEAKER_ROUTE[index].smart_amp_boost) {
            return true;
        }
    }
    return false;
}

static bool audio_route_layer_write_allowed(const char *layer) {
    return layer != NULL && strcmp(layer, "core") == 0;
}

static bool audio_string_starts_with(const char *text, const char *prefix) {
    size_t prefix_len;

    if (text == NULL || prefix == NULL) {
        return false;
    }
    prefix_len = strlen(prefix);
    return strncmp(text, prefix, prefix_len) == 0;
}

static int audio_observer_count_for_prefix(const struct audio_speaker_profile *profile,
                                           const char *prefix) {
    int index;
    int count = 0;

    if (profile == NULL || prefix == NULL) {
        return 0;
    }
    for (index = 0; index < profile->observer_control_count; ++index) {
        if (audio_string_starts_with(profile->observer_controls[index], prefix)) {
            ++count;
        }
    }
    return count;
}

static int audio_route_count_for_speaker(const char *speaker) {
    int index;
    int count = 0;

    for (index = 0; index < audio_route_control_count(); ++index) {
        if (speaker != NULL && strcmp(AUDIO_INTERNAL_SPEAKER_ROUTE[index].speaker, speaker) == 0) {
            ++count;
        }
    }
    return count;
}

static int audio_route_layer_count_for_speaker(const char *speaker, const char *layer) {
    int index;
    int count = 0;

    for (index = 0; index < audio_route_control_count(); ++index) {
        if (speaker != NULL && layer != NULL &&
            strcmp(AUDIO_INTERNAL_SPEAKER_ROUTE[index].speaker, speaker) == 0 &&
            strcmp(AUDIO_INTERNAL_SPEAKER_ROUTE[index].layer, layer) == 0) {
            ++count;
        }
    }
    return count;
}

static int audio_route_boost_count_for_speaker(const char *speaker) {
    int index;
    int count = 0;

    for (index = 0; index < audio_route_control_count(); ++index) {
        if (speaker != NULL &&
            strcmp(AUDIO_INTERNAL_SPEAKER_ROUTE[index].speaker, speaker) == 0 &&
            AUDIO_INTERNAL_SPEAKER_ROUTE[index].smart_amp_boost) {
            ++count;
        }
    }
    return count;
}

static int audio_speaker_map_count(void) {
    return (int)(sizeof(AUDIO_SPEAKER_MAP_IDS) / sizeof(AUDIO_SPEAKER_MAP_IDS[0]));
}

static void audio_speaker_map_print_speaker(const struct audio_speaker_profile *profile,
                                            int output_index,
                                            const char *speaker) {
    char prefix[64];

    snprintf(prefix, sizeof(prefix), "audio.speaker_map.speaker.%d", output_index);
    a90_console_printf("%s.id=%s\r\n", prefix, speaker);
    a90_console_printf("%s.route_controls=%d\r\n", prefix, audio_route_count_for_speaker(speaker));
    a90_console_printf("%s.route_core_controls=%d\r\n", prefix,
                       audio_route_layer_count_for_speaker(speaker, "core"));
    a90_console_printf("%s.route_feedback_controls=%d\r\n", prefix,
                       audio_route_layer_count_for_speaker(speaker, "feedback"));
    a90_console_printf("%s.route_endpoint_controls=%d\r\n", prefix,
                       audio_route_layer_count_for_speaker(speaker, "endpoint"));
    a90_console_printf("%s.route_blocked_boost_controls=%d\r\n", prefix,
                       audio_route_boost_count_for_speaker(speaker));
    a90_console_printf("%s.observer_controls=%d\r\n", prefix,
                       audio_observer_count_for_prefix(profile, speaker));
}

static int audio_speaker_map_cmd(char **argv, int argc) {
    const struct audio_speaker_profile *profile;
    const char *id = AUDIO_DEFAULT_PROFILE_ID;
    int index;

    if (argc > 3) {
        a90_console_printf("usage: audio speaker-map [%s]\r\n", AUDIO_DEFAULT_PROFILE_ID);
        return -EINVAL;
    }
    if (argc == 3 && argv != NULL && argv[2] != NULL) {
        id = argv[2];
    }
    profile = audio_find_profile(id);
    a90_console_printf("audio.speaker_map.version=1\r\n");
    a90_console_printf("audio.speaker_map.profile=%s\r\n", id);
    a90_console_printf("audio.speaker_map.read_only=1\r\n");
    a90_console_printf("audio.speaker_map.route_write_attempted=0\r\n");
    a90_console_printf("audio.speaker_map.playback_attempted=0\r\n");
    if (profile == NULL) {
        a90_console_printf("audio.speaker_map.error=unknown-profile\r\n");
        return -ENOENT;
    }
    a90_console_printf("audio.speaker_map.endpoint=%s\r\n", profile->endpoint);
    a90_console_printf("audio.speaker_map.hardware=%s\r\n", profile->speaker_map);
    a90_console_printf("audio.speaker_map.route_path=SLIMBUS_0_RX_to_WSA_CDC_DMA_RX\r\n");
    a90_console_printf("audio.speaker_map.route_control.count=%d\r\n", audio_route_control_count());
    a90_console_printf("audio.speaker_map.observer_control.count=%d\r\n", profile->observer_control_count);
    a90_console_printf("audio.speaker_map.speaker.count=%d\r\n", audio_speaker_map_count());
    a90_console_printf("audio.speaker_map.safety.amplitude_cap_milli=%d\r\n", profile->amplitude_cap_milli);
    a90_console_printf("audio.speaker_map.safety.smart_amp_boost_write_allowed=0\r\n");
    a90_console_printf("audio.speaker_map.safety.smart_amp_boost_blocked=%d\r\n",
                       audio_route_has_smart_amp_boost() ? 1 : 0);
    for (index = 0; index < audio_speaker_map_count(); ++index) {
        audio_speaker_map_print_speaker(profile, index, AUDIO_SPEAKER_MAP_IDS[index]);
    }
    return 0;
}

static void audio_route_print_value(const char *prefix, const struct audio_route_value *value) {
    int index;

    a90_console_printf("%s.kind=%s\r\n", prefix, audio_route_value_kind_name(value));
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
    a90_console_printf("%s.total_count=%d\r\n", prefix, audio_route_value_total_count(value));
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
        for (index = audio_route_control_count() - 1; index >= 0; --index) {
            if (!audio_route_control_matches_layer(&AUDIO_INTERNAL_SPEAKER_ROUTE[index], layer)) {
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

    for (index = 0; index < audio_route_control_count(); ++index) {
        if (!audio_route_control_matches_layer(&AUDIO_INTERNAL_SPEAKER_ROUTE[index], layer)) {
            continue;
        }
        snprintf(prefix, sizeof(prefix), "audio.route.apply.%d", output_index);
        audio_route_print_control(prefix,
                                  &AUDIO_INTERNAL_SPEAKER_ROUTE[index],
                                  &AUDIO_INTERNAL_SPEAKER_ROUTE[index].apply);
        ++output_index;
    }
}

static int audio_route_validate_integer_control(int fd,
                                                struct snd_ctl_elem_id *id,
                                                struct snd_ctl_elem_info *info,
                                                const struct audio_route_control *control,
                                                const struct audio_route_value *route_value) {
    int required = audio_route_value_total_count(route_value);

    memset(info, 0, sizeof(*info));
    info->id = *id;
    if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_INFO, info) < 0) {
        a90_console_printf("audio.route.info_failed control=%s errno=%d\r\n", control->name, errno);
        return -1;
    }
    *id = info->id;
    if (info->type != SNDRV_CTL_ELEM_TYPE_INTEGER) {
        a90_console_printf("audio.route.bad_type control=%s expected=integer actual=%u\r\n",
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
        if (audio_route_validate_integer_control(fd, &id, &info, control, route_value) < 0) {
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
                       audio_route_value_kind_name(route_value));
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
        for (index = audio_route_control_count() - 1; index >= 0; --index) {
            if (!audio_route_control_matches_layer(&AUDIO_INTERNAL_SPEAKER_ROUTE[index], layer) ||
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
        for (index = 0; index < audio_route_control_count(); ++index) {
            if (!audio_route_control_matches_layer(&AUDIO_INTERNAL_SPEAKER_ROUTE[index], layer)) {
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
            if (argi >= argc || argv[argi] == NULL || !audio_route_layer_valid(argv[argi])) {
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

    profile = audio_find_profile(profile_id);
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
    if (audio_route_control_count() != AUDIO_ROUTE_APPLY_COUNT ||
        audio_route_reset_count() != AUDIO_ROUTE_RESET_COUNT) {
        a90_console_printf("audio.route.error=route-count-mismatch apply=%d/%d reset=%d/%d\r\n",
                           audio_route_control_count(),
                           AUDIO_ROUTE_APPLY_COUNT,
                           audio_route_reset_count(),
                           AUDIO_ROUTE_RESET_COUNT);
        return -EINVAL;
    }

    a90_console_printf("audio.route.endpoint=%s\r\n", profile->endpoint);
    a90_console_printf("audio.route.card=%d\r\n", profile->card);
    a90_console_printf("audio.route.pcm_device=%d\r\n", profile->pcm_device);
    a90_console_printf("audio.route.apply.count=%d\r\n", AUDIO_ROUTE_APPLY_COUNT);
    a90_console_printf("audio.route.reset.count=%d\r\n", AUDIO_ROUTE_RESET_COUNT);
    a90_console_printf("audio.route.selected.apply.count=%d\r\n", audio_route_selected_count(layer, false));
    a90_console_printf("audio.route.selected.reset.count=%d\r\n", audio_route_selected_count(layer, true));
    a90_console_printf("audio.route.requires_global_app_type=1\r\n");
    a90_console_printf("audio.route.global_app_type_primitive=audio app-type %s --write\r\n", profile->id);
    a90_console_printf("audio.route.smart_amp_boost_blocked=%d\r\n",
                       audio_route_has_smart_amp_boost() ? 1 : 0);
    selected_has_boost = audio_route_selected_has_smart_amp_boost(layer);
    a90_console_printf("audio.route.selected.smart_amp_boost_blocked=%d\r\n", selected_has_boost ? 1 : 0);
    a90_console_printf("audio.route.blocked_control=SpkrLeft BOOST Switch\r\n");
    audio_route_print_controls(reset_mode, layer);

    if (write_mode && !audio_route_layer_write_allowed(layer)) {
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

static int audio_print_adsp_status(void) {
    struct audio_snd_scan_stats snd_stats;
    a90_console_printf("audio.status.version=1\r\n");
    a90_console_printf("audio.status.read_only=1\r\n");
    a90_console_printf("audio.status.default_profile=%s\r\n", AUDIO_DEFAULT_PROFILE_ID);
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
        return audio_print_profiles();
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "profile") == 0) {
        return audio_print_profile(argv, argc);
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "speaker-map") == 0) {
        return audio_speaker_map_cmd(argv, argc);
    }
    if (argc >= 2 && argv != NULL && argv[1] != NULL && strcmp(argv[1], "stages") == 0) {
        return audio_print_stages(argv, argc);
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
    a90_console_printf("usage: audio [adsp-status|status|profiles|profile [id]|speaker-map [id]|stages [id]|app-type [profile] [--dry-run|--write]|setcal [profile] [--dry-run|--execute] [--manifest PATH --verify|--prepare|--load]|play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--dry-run|--execute]|stop [profile] [--dry-run|--execute]|route [profile] [--dry-run|--apply|--reset] [--layer all|core|feedback|endpoint|blocked]|snd-status|adsp-boot-once|snd-materialize-once]\r\n");
    return -EINVAL;
}
