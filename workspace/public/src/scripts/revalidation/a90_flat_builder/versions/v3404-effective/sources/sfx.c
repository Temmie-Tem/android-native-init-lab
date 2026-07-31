#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "i_sound.h"
#include "w_wad.h"
#include "z_zone.h"

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif
#ifndef O_NONBLOCK
#define O_NONBLOCK 0
#endif

#define A90_SFX_STREAM_PATH "/cache/a90-runtime/a90-doomgeneric-v3404-sfx.pcmstream"
#define A90_SFX_RATE 48000
#define A90_SFX_CHANNELS 8
#define A90_SFX_FRAMES_MAX 1600
#define A90_SFX_MASTER_PERCENT 80

int use_libsamplerate = 0;
float libsamplerate_scale = 0.0f;

struct a90_sfx_data {
    int16_t *samples;
    unsigned int frames;
};

struct a90_sfx_channel {
    const struct a90_sfx_data *data;
    unsigned int pos;
    int vol;
    int sep;
    int active;
};

static int stream_fd = -1;
static int use_prefix = 1;
static unsigned int frame_remainder;
static struct a90_sfx_channel channels[A90_SFX_CHANNELS];

static snddevice_t sound_devices[] = { SNDDEVICE_SB };

static int open_stream_once(void) {
    return open(A90_SFX_STREAM_PATH, O_WRONLY | O_NONBLOCK | O_CLOEXEC);
}

static int write_best_effort(int fd, const void *data, size_t bytes) {
    size_t done = 0;
    unsigned int writes = 0;

    while (done < bytes && writes < 4U) {
        ssize_t wr = write(fd, (const char *)data + done, bytes - done);

        if (wr < 0) {
            if (errno == EINTR) {
                continue;
            }
            if (errno == EAGAIN
#ifdef EWOULDBLOCK
                || errno == EWOULDBLOCK
#endif
            ) {
                return 0;
            }
            return -errno;
        }
        if (wr == 0) {
            return 0;
        }
        done += (size_t)wr;
        ++writes;
    }
    return 0;
}

static int open_stream(void) {
    return open_stream_once();
}

static int get_sfx_lump_num(sfxinfo_t *sfx) {
    char name[16];

    if (sfx == NULL) {
        return -1;
    }
    if (sfx->link != NULL) {
        sfx = sfx->link;
    }
    if (use_prefix) {
        snprintf(name, sizeof(name), "ds%s", sfx->name);
    } else {
        snprintf(name, sizeof(name), "%s", sfx->name);
    }
    return W_GetNumForName(name);
}

static struct a90_sfx_data *load_sfx(sfxinfo_t *sfx) {
    byte *lump;
    unsigned int lumplen;
    unsigned int lump_samples;
    unsigned int source_samples;
    unsigned int out_frames;
    unsigned int index;
    int samplerate;
    struct a90_sfx_data *out;

    if (sfx == NULL || sfx->lumpnum < 0) {
        return NULL;
    }
    if (sfx->driver_data != NULL) {
        return (struct a90_sfx_data *)sfx->driver_data;
    }
    lumplen = (unsigned int)W_LumpLength(sfx->lumpnum);
    lump = (byte *)W_CacheLumpNum(sfx->lumpnum, PU_STATIC);
    if (lump == NULL || lumplen < 40U || lump[0] != 0x03U || lump[1] != 0x00U) {
        return NULL;
    }
    samplerate = ((int)lump[3] << 8) | (int)lump[2];
    lump_samples = ((unsigned int)lump[7] << 24) |
                   ((unsigned int)lump[6] << 16) |
                   ((unsigned int)lump[5] << 8) |
                   (unsigned int)lump[4];
    if (samplerate <= 0 || lump_samples > lumplen - 8U || lump_samples <= 48U) {
        return NULL;
    }
    source_samples = lump_samples - 32U;
    out_frames = (unsigned int)((((uint64_t)source_samples * A90_SFX_RATE) + (unsigned int)samplerate - 1U) /
                                (unsigned int)samplerate);
    if (out_frames == 0U) {
        return NULL;
    }
    out = (struct a90_sfx_data *)calloc(1, sizeof(*out));
    if (out == NULL) {
        return NULL;
    }
    out->samples = (int16_t *)calloc(out_frames, sizeof(out->samples[0]));
    if (out->samples == NULL) {
        free(out);
        return NULL;
    }
    out->frames = out_frames;
    for (index = 0; index < out_frames; ++index) {
        unsigned int src = (unsigned int)(((uint64_t)index * (unsigned int)samplerate) / A90_SFX_RATE);
        int sample;

        if (src >= source_samples) {
            src = source_samples - 1U;
        }
        sample = ((int)lump[24U + src] - 128) * 256;
        if (sample > 32767) {
            sample = 32767;
        } else if (sample < -32768) {
            sample = -32768;
        }
        out->samples[index] = (int16_t)sample;
    }
    sfx->driver_data = out;
    return out;
}

static boolean sfx_init(boolean use_sfx_prefix) {
    unsigned int index;

    (void)signal(SIGPIPE, SIG_IGN);
    use_prefix = use_sfx_prefix ? 1 : 0;
    for (index = 0; index < A90_SFX_CHANNELS; ++index) {
        memset(&channels[index], 0, sizeof(channels[index]));
    }
    frame_remainder = 0;
    stream_fd = open_stream();
    return true;
}

static void sfx_shutdown(void) {
    if (stream_fd >= 0) {
        close(stream_fd);
        stream_fd = -1;
    }
}

static int sfx_get_lump_num(sfxinfo_t *sfx) {
    return get_sfx_lump_num(sfx);
}

static unsigned int frames_per_update(void) {
    unsigned int total = A90_SFX_RATE + frame_remainder;
    unsigned int frames = total / 35U;

    frame_remainder = total % 35U;
    if (frames > A90_SFX_FRAMES_MAX) {
        frames = A90_SFX_FRAMES_MAX;
    }
    return frames;
}

static void sfx_update(void) {
    int16_t mix[A90_SFX_FRAMES_MAX * 2U];
    unsigned int frames = frames_per_update();
    unsigned int frame;
    unsigned int chan;

    memset(mix, 0, frames * 2U * sizeof(mix[0]));
    for (chan = 0; chan < A90_SFX_CHANNELS; ++chan) {
        struct a90_sfx_channel *ch = &channels[chan];
        int left_gain;
        int right_gain;

        if (!ch->active || ch->data == NULL || ch->data->samples == NULL) {
            continue;
        }
        left_gain = (254 - ch->sep) * ch->vol * A90_SFX_MASTER_PERCENT;
        right_gain = ch->sep * ch->vol * A90_SFX_MASTER_PERCENT;
        for (frame = 0; frame < frames; ++frame) {
            int sample;
            int left;
            int right;
            int mixed;

            if (ch->pos >= ch->data->frames) {
                ch->active = 0;
                break;
            }
            sample = ch->data->samples[ch->pos++];
            left = (sample * left_gain) / (254 * 127 * 100);
            right = (sample * right_gain) / (254 * 127 * 100);
            mixed = (int)mix[(frame * 2U)] + left;
            if (mixed > 32767) {
                mixed = 32767;
            } else if (mixed < -32768) {
                mixed = -32768;
            }
            mix[(frame * 2U)] = (int16_t)mixed;
            mixed = (int)mix[(frame * 2U) + 1U] + right;
            if (mixed > 32767) {
                mixed = 32767;
            } else if (mixed < -32768) {
                mixed = -32768;
            }
            mix[(frame * 2U) + 1U] = (int16_t)mixed;
        }
    }
    if (stream_fd < 0) {
        stream_fd = open_stream_once();
    }
    if (stream_fd >= 0) {
        int write_rc = write_best_effort(stream_fd, mix, frames * 2U * sizeof(mix[0]));

        if (write_rc < 0) {
            close(stream_fd);
            stream_fd = -1;
        }
    }
}

static void sfx_update_params(int channel, int vol, int sep) {
    if (channel < 0 || channel >= (int)A90_SFX_CHANNELS) {
        return;
    }
    channels[channel].vol = vol;
    channels[channel].sep = sep;
}

static int sfx_start(sfxinfo_t *sfx, int channel, int vol, int sep) {
    struct a90_sfx_data *data;

    if (channel < 0 || channel >= (int)A90_SFX_CHANNELS) {
        return -1;
    }
    data = load_sfx(sfx);
    if (data == NULL) {
        return -1;
    }
    channels[channel].data = data;
    channels[channel].pos = 0;
    channels[channel].vol = vol;
    channels[channel].sep = sep;
    channels[channel].active = 1;
    return channel;
}

static void sfx_stop(int channel) {
    if (channel >= 0 && channel < (int)A90_SFX_CHANNELS) {
        channels[channel].active = 0;
    }
}

static boolean sfx_playing(int channel) {
    if (channel < 0 || channel >= (int)A90_SFX_CHANNELS) {
        return false;
    }
    return channels[channel].active ? true : false;
}

static void sfx_cache(sfxinfo_t *sounds, int num_sounds) {
    (void)sounds;
    (void)num_sounds;
}

sound_module_t DG_sound_module = {
    sound_devices,
    1,
    sfx_init,
    sfx_shutdown,
    sfx_get_lump_num,
    sfx_update,
    sfx_update_params,
    sfx_start,
    sfx_stop,
    sfx_playing,
    sfx_cache,
};

static boolean music_init(void) { return false; }
static void music_shutdown(void) {}
static void music_set_volume(int volume) { (void)volume; }
static void music_pause(void) {}
static void music_resume(void) {}
static void *music_register(void *data, int len) { (void)data; (void)len; return NULL; }
static void music_unregister(void *handle) { (void)handle; }
static void music_play(void *handle, boolean looping) { (void)handle; (void)looping; }
static void music_stop(void) {}
static boolean music_playing(void) { return false; }
static void music_poll(void) {}

music_module_t DG_music_module = {
    sound_devices,
    1,
    music_init,
    music_shutdown,
    music_set_volume,
    music_pause,
    music_resume,
    music_register,
    music_unregister,
    music_play,
    music_stop,
    music_playing,
    music_poll,
};
