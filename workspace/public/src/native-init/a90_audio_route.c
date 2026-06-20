#include "a90_audio_route.h"

#include <stddef.h>
#include <string.h>

static const struct audio_speaker_map_entry AUDIO_SPEAKER_MAP_ENTRIES[] = {
    {
        .id = "shared",
        .role = "stream-route",
        .channel = "both",
        .hardware = "SLIMBUS_0_RX shared speaker path",
        .safety = "safe-observed-core",
    },
    {
        .id = "SPKR_VI_1",
        .role = "feedback",
        .channel = "left",
        .hardware = "AIF4_VI speaker feedback input 1",
        .safety = "speaker-protection-observed",
    },
    {
        .id = "SPKR_VI_2",
        .role = "feedback",
        .channel = "right",
        .hardware = "AIF4_VI speaker feedback input 2",
        .safety = "speaker-protection-observed",
    },
    {
        .id = "SPKR_VI",
        .role = "feedback-format",
        .channel = "both",
        .hardware = "SLIM_4_TX VI feedback format",
        .safety = "speaker-protection-observed",
    },
    {
        .id = "SpkrLeft",
        .role = "endpoint",
        .channel = "left",
        .hardware = "left WSA881x speaker endpoint",
        .safety = "boost-write-blocked",
    },
    {
        .id = "SpkrRight",
        .role = "endpoint",
        .channel = "right",
        .hardware = "right WSA881x speaker endpoint",
        .safety = "boost-write-blocked",
    },
};


static bool audio_string_starts_with(const char *text, const char *prefix) {
    size_t prefix_len;

    if (text == NULL || prefix == NULL) {
        return false;
    }
    prefix_len = strlen(prefix);
    return strncmp(text, prefix, prefix_len) == 0;
}

int a90_audio_route_control_count(void) {
    return AUDIO_ROUTE_APPLY_COUNT;
}

int a90_audio_route_reset_count(void) {
    int count = 0;
    int index;

    for (index = 0; index < a90_audio_route_control_count(); ++index) {
        if (AUDIO_INTERNAL_SPEAKER_ROUTE[index].resettable) {
            ++count;
        }
    }
    return count;
}

int a90_audio_route_value_total_count(const struct audio_route_value *value) {
    if (value == NULL) {
        return 0;
    }
    return value->int_count + value->zero_fill;
}

const char *a90_audio_route_value_kind_name(const struct audio_route_value *value) {
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

bool a90_audio_route_has_smart_amp_boost(void) {
    int index;

    for (index = 0; index < a90_audio_route_control_count(); ++index) {
        if (AUDIO_INTERNAL_SPEAKER_ROUTE[index].smart_amp_boost) {
            return true;
        }
    }
    return false;
}

bool a90_audio_route_layer_valid(const char *layer) {
    return layer != NULL &&
           (strcmp(layer, AUDIO_ROUTE_LAYER_ALL) == 0 ||
            strcmp(layer, AUDIO_ROUTE_LAYER_CORE) == 0 ||
            strcmp(layer, AUDIO_ROUTE_LAYER_FEEDBACK) == 0 ||
            strcmp(layer, AUDIO_ROUTE_LAYER_ENDPOINT) == 0 ||
            strcmp(layer, AUDIO_ROUTE_LAYER_PLAYBACK) == 0 ||
            strcmp(layer, AUDIO_ROUTE_LAYER_BLOCKED) == 0);
}

bool a90_audio_route_control_matches_layer(const struct audio_route_control *control,
                                           const char *layer) {
    if (control == NULL || layer == NULL) {
        return false;
    }
    if (strcmp(layer, AUDIO_ROUTE_LAYER_ALL) == 0) {
        return true;
    }
    if (strcmp(layer, AUDIO_ROUTE_LAYER_BLOCKED) == 0) {
        return control->smart_amp_boost;
    }
    if (strcmp(layer, AUDIO_ROUTE_LAYER_PLAYBACK) == 0) {
        if (strcmp(control->layer, AUDIO_ROUTE_LAYER_CORE) == 0 ||
            strcmp(control->layer, AUDIO_ROUTE_LAYER_FEEDBACK) == 0) {
            return true;
        }
        return strcmp(control->layer, AUDIO_ROUTE_LAYER_ENDPOINT) == 0 && !control->smart_amp_boost;
    }
    return strcmp(control->layer, layer) == 0;
}

int a90_audio_route_selected_count(const char *layer, bool reset_mode) {
    int count = 0;
    int index;

    for (index = 0; index < a90_audio_route_control_count(); ++index) {
        if (!a90_audio_route_control_matches_layer(&AUDIO_INTERNAL_SPEAKER_ROUTE[index], layer)) {
            continue;
        }
        if (reset_mode && !AUDIO_INTERNAL_SPEAKER_ROUTE[index].resettable) {
            continue;
        }
        ++count;
    }
    return count;
}

bool a90_audio_route_selected_has_smart_amp_boost(const char *layer) {
    int index;

    for (index = 0; index < a90_audio_route_control_count(); ++index) {
        if (a90_audio_route_control_matches_layer(&AUDIO_INTERNAL_SPEAKER_ROUTE[index], layer) &&
            AUDIO_INTERNAL_SPEAKER_ROUTE[index].smart_amp_boost) {
            return true;
        }
    }
    return false;
}

bool a90_audio_route_layer_write_allowed(const char *layer) {
    return layer != NULL &&
           (strcmp(layer, AUDIO_ROUTE_LAYER_CORE) == 0 ||
            strcmp(layer, AUDIO_ROUTE_LAYER_PLAYBACK) == 0);
}

int a90_audio_observer_count_for_prefix(const struct audio_speaker_profile *profile,
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

int a90_audio_route_count_for_speaker(const char *speaker) {
    int index;
    int count = 0;

    for (index = 0; index < a90_audio_route_control_count(); ++index) {
        if (speaker != NULL && strcmp(AUDIO_INTERNAL_SPEAKER_ROUTE[index].speaker, speaker) == 0) {
            ++count;
        }
    }
    return count;
}

int a90_audio_route_layer_count_for_speaker(const char *speaker, const char *layer) {
    int index;
    int count = 0;

    for (index = 0; index < a90_audio_route_control_count(); ++index) {
        if (speaker != NULL && layer != NULL &&
            strcmp(AUDIO_INTERNAL_SPEAKER_ROUTE[index].speaker, speaker) == 0 &&
            strcmp(AUDIO_INTERNAL_SPEAKER_ROUTE[index].layer, layer) == 0) {
            ++count;
        }
    }
    return count;
}

int a90_audio_route_boost_count_for_speaker(const char *speaker) {
    int index;
    int count = 0;

    for (index = 0; index < a90_audio_route_control_count(); ++index) {
        if (speaker != NULL &&
            strcmp(AUDIO_INTERNAL_SPEAKER_ROUTE[index].speaker, speaker) == 0 &&
            AUDIO_INTERNAL_SPEAKER_ROUTE[index].smart_amp_boost) {
            ++count;
        }
    }
    return count;
}

int a90_audio_speaker_map_count(void) {
    return (int)(sizeof(AUDIO_SPEAKER_MAP_ENTRIES) / sizeof(AUDIO_SPEAKER_MAP_ENTRIES[0]));
}

const struct audio_speaker_map_entry *a90_audio_speaker_map_entry(int index) {
    if (index < 0 || index >= a90_audio_speaker_map_count()) {
        return NULL;
    }
    return &AUDIO_SPEAKER_MAP_ENTRIES[index];
}

const char *a90_audio_speaker_map_id(int index) {
    const struct audio_speaker_map_entry *entry = a90_audio_speaker_map_entry(index);

    if (entry == NULL) {
        return NULL;
    }
    return entry->id;
}
