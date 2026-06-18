#include "a90_audio_profile.h"

#include <string.h>

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

const struct audio_speaker_profile AUDIO_SPEAKER_PROFILES[AUDIO_SPEAKER_PROFILE_COUNT] = {
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

int a90_audio_profile_count(void) {
    return AUDIO_SPEAKER_PROFILE_COUNT;
}

const struct audio_speaker_profile *a90_audio_find_profile(const char *id) {
    int index;

    if (id == NULL || id[0] == '\0') {
        id = AUDIO_DEFAULT_PROFILE_ID;
    }
    for (index = 0; index < a90_audio_profile_count(); ++index) {
        if (strcmp(AUDIO_SPEAKER_PROFILES[index].id, id) == 0) {
            return &AUDIO_SPEAKER_PROFILES[index];
        }
    }
    return NULL;
}

const struct audio_route_control AUDIO_INTERNAL_SPEAKER_ROUTE[AUDIO_ROUTE_APPLY_COUNT] = {
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
