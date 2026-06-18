#ifndef A90_AUDIO_STAGE_H
#define A90_AUDIO_STAGE_H

#include <stdbool.h>

#define AUDIO_STAGE_CONTRACT_VERSION 1
#define AUDIO_STAGE_CONTRACT_COUNT 14
#define AUDIO_ADSP_BOOT_ONCE_TOKEN "AUD2_ONE_SHOT_ADSP_BOOT"
#define AUDIO_SND_MATERIALIZE_TOKEN "AUD3_DEV_SND_MATERIALIZE_ONLY"
#define AUDIO_SETCAL_DEFAULT_MANIFEST_PATH "/cache/a90-runtime/pkg/manifests/audio-setcal-internal-speaker-safe.manifest"

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

extern const struct audio_stage_contract AUDIO_STAGE_CONTRACTS[AUDIO_STAGE_CONTRACT_COUNT];

#endif
