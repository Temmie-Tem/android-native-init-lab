// Host-built diagnostic helper for V2386 AUD-4 PCM write classification.
// Links against the pinned tinyalsa sources; generated binaries stay private.

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <tinyalsa/asoundlib.h>

#define A90_PCM_PROBE_VERSION "V2386"

struct wav_info {
    unsigned int channels;
    unsigned int rate;
    unsigned int bits;
    uint32_t data_size;
    long data_offset;
};

static uint16_t le16(const unsigned char *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint32_t le32(const unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static int read_exact(FILE *file, void *buf, size_t size) {
    return fread(buf, 1, size, file) == size ? 0 : -1;
}

static int parse_wav(FILE *file, struct wav_info *info) {
    unsigned char header[12];
    int saw_fmt = 0;
    int saw_data = 0;
    memset(info, 0, sizeof(*info));
    if (read_exact(file, header, sizeof(header)) != 0) {
        fprintf(stderr, "A90_PCM_PROBE_WAV_ERROR reason=short_header\n");
        return -1;
    }
    if (memcmp(header, "RIFF", 4) != 0 || memcmp(header + 8, "WAVE", 4) != 0) {
        fprintf(stderr, "A90_PCM_PROBE_WAV_ERROR reason=not_riff_wave\n");
        return -1;
    }
    while (!saw_data) {
        unsigned char chunk[8];
        uint32_t chunk_size;
        long payload_offset;
        if (read_exact(file, chunk, sizeof(chunk)) != 0) {
            fprintf(stderr, "A90_PCM_PROBE_WAV_ERROR reason=missing_data_chunk\n");
            return -1;
        }
        chunk_size = le32(chunk + 4);
        payload_offset = ftell(file);
        if (memcmp(chunk, "fmt ", 4) == 0) {
            unsigned char fmt[16];
            if (chunk_size < sizeof(fmt) || read_exact(file, fmt, sizeof(fmt)) != 0) {
                fprintf(stderr, "A90_PCM_PROBE_WAV_ERROR reason=bad_fmt_chunk\n");
                return -1;
            }
            if (le16(fmt) != 1) {
                fprintf(stderr, "A90_PCM_PROBE_WAV_ERROR reason=non_pcm format=%u\n", le16(fmt));
                return -1;
            }
            info->channels = le16(fmt + 2);
            info->rate = le32(fmt + 4);
            info->bits = le16(fmt + 14);
            saw_fmt = 1;
        } else if (memcmp(chunk, "data", 4) == 0) {
            info->data_size = chunk_size;
            info->data_offset = payload_offset;
            saw_data = 1;
            break;
        }
        if (fseek(file, payload_offset + chunk_size + (chunk_size & 1U), SEEK_SET) != 0) {
            fprintf(stderr, "A90_PCM_PROBE_WAV_ERROR reason=chunk_seek_failed\n");
            return -1;
        }
    }
    if (!saw_fmt || !saw_data || info->channels == 0 || info->rate == 0 || info->data_size == 0) {
        fprintf(stderr, "A90_PCM_PROBE_WAV_ERROR reason=incomplete_wav_metadata\n");
        return -1;
    }
    if (fseek(file, info->data_offset, SEEK_SET) != 0) {
        fprintf(stderr, "A90_PCM_PROBE_WAV_ERROR reason=data_seek_failed\n");
        return -1;
    }
    return 0;
}

static enum pcm_format pcm_format_from_bits(unsigned int bits) {
    if (bits == 32)
        return PCM_FORMAT_S32_LE;
    if (bits == 24)
        return PCM_FORMAT_S24_3LE;
    return PCM_FORMAT_S16_LE;
}

static unsigned int bytes_per_frame(const struct wav_info *info) {
    return info->channels * (info->bits / 8U);
}

static void usage(const char *argv0) {
    fprintf(stderr, "Usage: %s file.wav [-D card] [-d device] [-p period_size] [-n n_periods]\n", argv0);
}

int main(int argc, char **argv) {
    const char *filename;
    unsigned int card = 0;
    unsigned int device = 0;
    unsigned int period_size = 1024;
    unsigned int period_count = 4;
    struct wav_info wav;
    struct pcm_config config;
    struct pcm *pcm = NULL;
    FILE *file = NULL;
    void *buffer = NULL;
    unsigned int buffer_bytes;
    uint32_t remaining;
    unsigned int chunk_index = 0;
    unsigned int total_written = 0;

    if (argc < 2) {
        usage(argv[0]);
        return 2;
    }
    filename = argv[1];
    for (int index = 2; index < argc; index++) {
        if (strcmp(argv[index], "-D") == 0 && index + 1 < argc) {
            card = (unsigned int)strtoul(argv[++index], NULL, 10);
        } else if (strcmp(argv[index], "-d") == 0 && index + 1 < argc) {
            device = (unsigned int)strtoul(argv[++index], NULL, 10);
        } else if (strcmp(argv[index], "-p") == 0 && index + 1 < argc) {
            period_size = (unsigned int)strtoul(argv[++index], NULL, 10);
        } else if (strcmp(argv[index], "-n") == 0 && index + 1 < argc) {
            period_count = (unsigned int)strtoul(argv[++index], NULL, 10);
        } else {
            usage(argv[0]);
            return 2;
        }
    }

    file = fopen(filename, "rb");
    if (!file) {
        fprintf(stderr, "A90_PCM_PROBE_OPEN_WAV_ERROR path=%s errno=%d strerror=%s\n", filename, errno, strerror(errno));
        return 10;
    }
    if (parse_wav(file, &wav) != 0) {
        fclose(file);
        return 11;
    }
    if (wav.bits != 16 && wav.bits != 24 && wav.bits != 32) {
        fprintf(stderr, "A90_PCM_PROBE_WAV_ERROR reason=unsupported_bits bits=%u\n", wav.bits);
        fclose(file);
        return 12;
    }

    memset(&config, 0, sizeof(config));
    config.channels = wav.channels;
    config.rate = wav.rate;
    config.period_size = period_size;
    config.period_count = period_count;
    config.format = pcm_format_from_bits(wav.bits);
    config.start_threshold = 0;
    config.stop_threshold = 0;
    config.silence_threshold = 0;

    printf("A90_PCM_PROBE_START version=%s card=%u device=%u channels=%u rate=%u bits=%u data_bytes=%u period_size=%u period_count=%u\n",
           A90_PCM_PROBE_VERSION, card, device, wav.channels, wav.rate, wav.bits, wav.data_size, period_size, period_count);
    fflush(stdout);

    pcm = pcm_open(card, device, PCM_OUT, &config);
    if (!pcm || !pcm_is_ready(pcm)) {
        fprintf(stderr, "A90_PCM_PROBE_PCM_OPEN_ERROR card=%u device=%u pcm_error=\"%s\"\n",
                card, device, pcm ? pcm_get_error(pcm) : "pcm_open returned NULL");
        if (pcm)
            pcm_close(pcm);
        fclose(file);
        return 20;
    }

    buffer_bytes = pcm_frames_to_bytes(pcm, pcm_get_buffer_size(pcm));
    if (buffer_bytes == 0)
        buffer_bytes = period_size * bytes_per_frame(&wav);
    buffer = malloc(buffer_bytes);
    if (!buffer) {
        fprintf(stderr, "A90_PCM_PROBE_ALLOC_ERROR bytes=%u errno=%d strerror=%s\n", buffer_bytes, errno, strerror(errno));
        pcm_close(pcm);
        fclose(file);
        return 21;
    }
    printf("A90_PCM_PROBE_PCM_OPEN_OK buffer_frames=%u buffer_bytes=%u\n", pcm_get_buffer_size(pcm), buffer_bytes);
    fflush(stdout);

    remaining = wav.data_size;
    while (remaining > 0) {
        size_t want = remaining < buffer_bytes ? remaining : buffer_bytes;
        size_t got = fread(buffer, 1, want, file);
        int rc;
        if (got == 0) {
            fprintf(stderr, "A90_PCM_PROBE_READ_ERROR chunk=%u wanted=%zu remaining=%u\n", chunk_index, want, remaining);
            free(buffer);
            pcm_close(pcm);
            fclose(file);
            return 30;
        }
        errno = 0;
        rc = pcm_write(pcm, buffer, (unsigned int)got);
        if (rc != 0) {
            unsigned int frames = bytes_per_frame(&wav) ? (unsigned int)(got / bytes_per_frame(&wav)) : 0;
            fprintf(stderr,
                    "A90_PCM_PROBE_WRITE_ERROR chunk=%u rc=%d errno=%d strerror=\"%s\" pcm_error=\"%s\" bytes=%zu frames=%u\n",
                    chunk_index, rc, errno, strerror(errno), pcm_get_error(pcm), got, frames);
            free(buffer);
            pcm_close(pcm);
            fclose(file);
            return 40;
        }
        printf("A90_PCM_PROBE_WRITE_OK chunk=%u bytes=%zu\n", chunk_index, got);
        fflush(stdout);
        total_written += (unsigned int)got;
        remaining -= (uint32_t)got;
        chunk_index++;
    }

    printf("A90_PCM_PROBE_DONE chunks=%u bytes=%u drain_us=%lu\n",
           chunk_index, total_written,
           (unsigned long)pcm_get_buffer_size(pcm) * 1000UL / ((unsigned long)wav.rate / 1000UL));
    fflush(stdout);
    usleep((unsigned long)pcm_get_buffer_size(pcm) * 1000UL / ((unsigned long)wav.rate / 1000UL));
    free(buffer);
    pcm_close(pcm);
    fclose(file);
    return 0;
}
