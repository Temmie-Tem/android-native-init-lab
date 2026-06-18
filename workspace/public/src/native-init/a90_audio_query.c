#include "a90_audio_query.h"

#include "a90_audio_profile.h"
#include "a90_audio_route.h"
#include "a90_audio_stage.h"

#include "a90_console.h"

#include <errno.h>
#include <stdio.h>

static void audio_query_print_int_list(const char *prefix, const int *values, int count) {
    int index;

    a90_console_printf("%s=", prefix);
    for (index = 0; index < count; ++index) {
        a90_console_printf("%s%d", index == 0 ? "" : ",", values[index]);
    }
    a90_console_printf("\r\n");
}

static void audio_query_print_str_list(const char *prefix, const char *const *values, int count) {
    int index;

    a90_console_printf("%s=", prefix);
    for (index = 0; index < count; ++index) {
        a90_console_printf("%s%s", index == 0 ? "" : "|", values[index]);
    }
    a90_console_printf("\r\n");
}

static int audio_query_stage_count(void) {
    return AUDIO_STAGE_CONTRACT_COUNT;
}

int a90_audio_query_profiles_cmd(void) {
    int index;

    a90_console_printf("audio.profiles.version=%d\r\n", AUDIO_PROFILE_VERSION);
    a90_console_printf("audio.profiles.count=%d\r\n", a90_audio_profile_count());
    a90_console_printf("audio.profiles.default=%s\r\n", AUDIO_DEFAULT_PROFILE_ID);
    for (index = 0; index < a90_audio_profile_count(); ++index) {
        a90_console_printf("audio.profiles.%d.id=%s endpoint=%s card=%d pcm=%d\r\n",
                           index,
                           AUDIO_SPEAKER_PROFILES[index].id,
                           AUDIO_SPEAKER_PROFILES[index].endpoint,
                           AUDIO_SPEAKER_PROFILES[index].card,
                           AUDIO_SPEAKER_PROFILES[index].pcm_device);
    }
    return 0;
}

int a90_audio_query_profile_cmd(char **argv, int argc) {
    const struct audio_speaker_profile *profile;
    const char *id = AUDIO_DEFAULT_PROFILE_ID;

    if (argc > 3) {
        a90_console_printf("usage: audio profile [%s]\r\n", AUDIO_DEFAULT_PROFILE_ID);
        return -EINVAL;
    }
    if (argc == 3 && argv != NULL && argv[2] != NULL) {
        id = argv[2];
    }
    profile = a90_audio_find_profile(id);
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
    audio_query_print_int_list("audio.profile.acdb_set_order", profile->acdb_set_order, AUDIO_PROFILE_ACDB_SET_COUNT);
    audio_query_print_int_list("audio.profile.forbidden_cal_types", profile->forbidden_cal_types, AUDIO_PROFILE_FORBIDDEN_CAL_COUNT);
    audio_query_print_str_list("audio.profile.observer_controls", profile->observer_controls, profile->observer_control_count);
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

static void audio_query_print_stage_command(const char *prefix,
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

int a90_audio_query_stages_cmd(char **argv, int argc) {
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
    profile = a90_audio_find_profile(id);
    a90_console_printf("audio.stages.version=1\r\n");
    a90_console_printf("audio.stages.profile=%s\r\n", id);
    if (profile == NULL) {
        a90_console_printf("audio.stages.error=unknown-profile\r\n");
        return -ENOENT;
    }
    for (index = 0; index < audio_query_stage_count(); ++index) {
        if (AUDIO_STAGE_CONTRACTS[index].native_implemented) {
            ++native_count;
        }
        if (AUDIO_STAGE_CONTRACTS[index].writes_runtime_state) {
            ++runtime_write_count;
        }
    }
    a90_console_printf("audio.stages.endpoint=%s\r\n", profile->endpoint);
    a90_console_printf("audio.stages.count=%d\r\n", audio_query_stage_count());
    a90_console_printf("audio.stages.native_implemented.count=%d\r\n", native_count);
    a90_console_printf("audio.stages.runtime_write.count=%d\r\n", runtime_write_count);
    a90_console_printf("audio.stages.all_native_ready=0\r\n");
    a90_console_printf("audio.stages.read_only=1\r\n");
    for (index = 0; index < audio_query_stage_count(); ++index) {
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
        audio_query_print_stage_command(prefix, stage, profile);
        a90_console_printf("%s.note=%s\r\n", prefix, stage->note);
    }
    return 0;
}

static void audio_query_speaker_map_print_speaker(const struct audio_speaker_profile *profile,
                                                  int output_index,
                                                  const struct audio_speaker_map_entry *entry) {
    char prefix[64];
    const char *speaker = entry == NULL ? NULL : entry->id;

    snprintf(prefix, sizeof(prefix), "audio.speaker_map.speaker.%d", output_index);
    a90_console_printf("%s.id=%s\r\n", prefix, speaker == NULL ? "" : speaker);
    a90_console_printf("%s.role=%s\r\n", prefix, entry == NULL ? "" : entry->role);
    a90_console_printf("%s.channel=%s\r\n", prefix, entry == NULL ? "" : entry->channel);
    a90_console_printf("%s.hardware=%s\r\n", prefix, entry == NULL ? "" : entry->hardware);
    a90_console_printf("%s.safety=%s\r\n", prefix, entry == NULL ? "" : entry->safety);
    a90_console_printf("%s.route_controls=%d\r\n", prefix, a90_audio_route_count_for_speaker(speaker));
    a90_console_printf("%s.route_core_controls=%d\r\n", prefix,
                       a90_audio_route_layer_count_for_speaker(speaker, AUDIO_ROUTE_LAYER_CORE));
    a90_console_printf("%s.route_feedback_controls=%d\r\n", prefix,
                       a90_audio_route_layer_count_for_speaker(speaker, AUDIO_ROUTE_LAYER_FEEDBACK));
    a90_console_printf("%s.route_endpoint_controls=%d\r\n", prefix,
                       a90_audio_route_layer_count_for_speaker(speaker, AUDIO_ROUTE_LAYER_ENDPOINT));
    a90_console_printf("%s.route_blocked_boost_controls=%d\r\n", prefix,
                       a90_audio_route_boost_count_for_speaker(speaker));
    a90_console_printf("%s.observer_controls=%d\r\n", prefix,
                       a90_audio_observer_count_for_prefix(profile, speaker));
}

int a90_audio_query_speaker_map_cmd(char **argv, int argc) {
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
    profile = a90_audio_find_profile(id);
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
    a90_console_printf("audio.speaker_map.route_control.count=%d\r\n", a90_audio_route_control_count());
    a90_console_printf("audio.speaker_map.observer_control.count=%d\r\n", profile->observer_control_count);
    a90_console_printf("audio.speaker_map.speaker.count=%d\r\n", a90_audio_speaker_map_count());
    a90_console_printf("audio.speaker_map.safety.amplitude_cap_milli=%d\r\n", profile->amplitude_cap_milli);
    a90_console_printf("audio.speaker_map.safety.smart_amp_boost_write_allowed=0\r\n");
    a90_console_printf("audio.speaker_map.safety.smart_amp_boost_blocked=%d\r\n",
                       a90_audio_route_has_smart_amp_boost() ? 1 : 0);
    for (index = 0; index < a90_audio_speaker_map_count(); ++index) {
        audio_query_speaker_map_print_speaker(profile, index, a90_audio_speaker_map_entry(index));
    }
    return 0;
}
