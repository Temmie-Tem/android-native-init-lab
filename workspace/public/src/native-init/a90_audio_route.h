#ifndef A90_AUDIO_ROUTE_H
#define A90_AUDIO_ROUTE_H

#include <stdbool.h>

#include "a90_audio_profile.h"

#define AUDIO_ROUTE_API_VERSION 1
#define AUDIO_ROUTE_LAYER_ALL "all"
#define AUDIO_ROUTE_LAYER_CORE "core"
#define AUDIO_ROUTE_LAYER_FEEDBACK "feedback"
#define AUDIO_ROUTE_LAYER_ENDPOINT "endpoint"
#define AUDIO_ROUTE_LAYER_BLOCKED "blocked"

int a90_audio_route_control_count(void);
int a90_audio_route_reset_count(void);
int a90_audio_route_value_total_count(const struct audio_route_value *value);
const char *a90_audio_route_value_kind_name(const struct audio_route_value *value);
bool a90_audio_route_has_smart_amp_boost(void);
bool a90_audio_route_layer_valid(const char *layer);
bool a90_audio_route_control_matches_layer(const struct audio_route_control *control, const char *layer);
int a90_audio_route_selected_count(const char *layer, bool reset_mode);
bool a90_audio_route_selected_has_smart_amp_boost(const char *layer);
bool a90_audio_route_layer_write_allowed(const char *layer);
int a90_audio_observer_count_for_prefix(const struct audio_speaker_profile *profile, const char *prefix);
int a90_audio_route_count_for_speaker(const char *speaker);
int a90_audio_route_layer_count_for_speaker(const char *speaker, const char *layer);
int a90_audio_route_boost_count_for_speaker(const char *speaker);
int a90_audio_speaker_map_count(void);
const char *a90_audio_speaker_map_id(int index);

#endif
