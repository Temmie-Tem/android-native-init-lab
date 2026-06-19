#ifndef A90_AUDIO_PROFILE_H
#define A90_AUDIO_PROFILE_H

#include <stdbool.h>

#define AUDIO_PROFILE_VERSION 1
#define AUDIO_CORE_PROMOTION_RUN "V2815"
#define AUDIO_CORE_PROMOTION_VERSION "0.10.0"
#define AUDIO_CORE_PROMOTION_TAG "v2812-audio-core-promotion-candidate"
#define AUDIO_CORE_VALIDATION_RUN "V2814"
#define AUDIO_PRODUCTIZATION_LATEST_RUN "V2848"
#define AUDIO_PRODUCTIZATION_LATEST_VERSION "0.10.14"
#define AUDIO_PRODUCTIZATION_LATEST_TAG "v2847-audio-stop-execute"
#define AUDIO_BOOT_CHIME_VALIDATION_RUN "V2846"
#define AUDIO_STOP_EXECUTE_VALIDATION_RUN "V2848"
#define AUDIO_STOP_EXECUTE_SCOPE "core-route-reset"
#define AUDIO_DEFAULT_PROFILE_ID "internal-speaker-safe"
#define AUDIO_SPEAKER_PROFILE_COUNT 1
#define AUDIO_PROFILE_ACDB_SET_COUNT 11
#define AUDIO_PROFILE_FORBIDDEN_CAL_COUNT 3
#define AUDIO_PROFILE_OBSERVER_COUNT 8
#define AUDIO_ROUTE_APPLY_COUNT 13
#define AUDIO_ROUTE_RESET_COUNT 12

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

extern const struct audio_speaker_profile AUDIO_SPEAKER_PROFILES[AUDIO_SPEAKER_PROFILE_COUNT];
extern const struct audio_route_control AUDIO_INTERNAL_SPEAKER_ROUTE[AUDIO_ROUTE_APPLY_COUNT];

int a90_audio_profile_count(void);
const struct audio_speaker_profile *a90_audio_find_profile(const char *id);

#endif
