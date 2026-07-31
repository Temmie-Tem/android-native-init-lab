#include <stdbool.h>
#include <stddef.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdint.h>
#include <pthread.h>
#include <arpa/inet.h>
#include <time.h>
#include <netinet/in.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif
#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#include "doomgeneric.h"
#include "doomkeys.h"

extern int I_GetTime(void);
extern int gametic;

#define A90_DG_KEY_QUEUE_MAX 64U
#define A90_DG_RUNTIME_WAD_PATH "/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD"

const char a90_doomgeneric_v3024_marker[] =
    "a90.doomgeneric.v3024.private_source_integration=1";
const char a90_doomgeneric_v3024_wad_policy[] =
    "a90.doomgeneric.v3024.wad_policy=runtime-private-not-boot";
const char a90_doomgeneric_v3024_input_policy[] =
    "a90.doomgeneric.v3024.input=serial-doompad-to-DG_GetKey";
const char a90_doomgeneric_v3029_marker[] =
    "a90.doomgeneric.v3045.continuous_loop=33ms-loop-start-zero-continuous";
const char a90_doomgeneric_v3029_wad_smoke_policy[] =
    "a90.doomgeneric.v3031.wad_smoke=bounded";
const char a90_doomgeneric_v3031_frame_dump_policy[] =
    "a90.doomgeneric.v3031.frame_dump=raw-xbgr8888-file";
const char a90_doomgeneric_v3033_loop_policy[] =
    "a90.doomgeneric.v3045.loop=input-state-file-to-DG_GetKey-33ms-continuous";
const char a90_doomgeneric_v3042_color_policy[] =
    "a90.doomgeneric.v3045.frame_color=rb-swap-to-xbgr8888";
const char a90_doomgeneric_v3045_continuous_policy[] =
    "a90.doomgeneric.v3045.loop_frames_zero=continuous";
const char a90_doomgeneric_v3049_autostart_policy[] =
    "a90.doomgeneric.v3049.autostart=warp-e1m1-skill2";
const char a90_doomgeneric_v3051_probe_policy[] =
    "a90.doomgeneric.v3051.probe=autostart-argv12";
const char a90_doomgeneric_v3053_audio_policy[] =
    "a90.doomgeneric.v3053.audio=native-audio-corun-tone-real-sfx-disabled";
const char a90_doomgeneric_v3057_input_policy[] =
    "a90.doomgeneric.v3057.input=unix-dgram-state-with-file-fallback";
const char a90_doomgeneric_v3059_udp_input_policy[] =
    "a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback";
const char a90_doomgeneric_v3079_pace_policy[] =
    "a90.doomgeneric.v3079.pace=presenter-pageflip-token";
const char a90_doomgeneric_v3081_frame_ipc_policy[] =
    "a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq";
const char a90_doomgeneric_v3096_tick_telemetry_policy[] =
    "a90.doomgeneric.v3404.tick_telemetry=smooth-demo-paced-time-direct-blit";
const char a90_doomgeneric_v3096_scale_policy[] =
    "a90.doomgeneric.v3404.scale=producer-960x600-1to1-demo-hud-large-groups";
const char a90_doomgeneric_v3098_gametic_frame_policy[] =
    "a90.doomgeneric.v3404.gametic_frame_telemetry=loop-dump-gametic-summary-smooth-demo";
const char a90_doomgeneric_v3100_phase_policy[] =
    "a90.doomgeneric.v3404.phase_telemetry=tick-draw-dump-split-smooth-demo";
const char a90_doomgeneric_v3404_paced_time_policy[] =
    "a90.doomgeneric.v3404.paced_time=smooth-demo-presenter-token-doom-tic-quantum";
const char a90_doomgeneric_v3404_mode_label[] =
    "non-original-smooth-demo";
const char a90_doomgeneric_v3404_input_thread_policy[] =
    "a90.doomgeneric.v3404.input_thread=background-drain-udp-unix-dgram";
const char a90_doomgeneric_v3404_time_policy[] =
    "a90.doomgeneric.v3404.time_model=clock-monotonic-while-loop-active";
const char a90_doomgeneric_v3404_demo_hud_policy[] =
    "a90.doomgeneric.v3404.demo_hud=large-grouped-hw-doom-input";
const char a90_doomgeneric_v3404_audio_policy[] =
    "a90.doomgeneric.v3404.audio=real-sfx-pcm-stream-softap-s4-transfer-server";

struct a90_doompad_snapshot {
    bool forward;
    bool back;
    bool left;
    bool right;
    bool fire;
    bool use;
    bool menu;
    bool run;
    unsigned int seq;
};

struct a90_dg_key_event {
    int pressed;
    unsigned char key;
};

static struct a90_dg_key_event key_queue[A90_DG_KEY_QUEUE_MAX];
static unsigned int key_head;
static unsigned int key_tail;
static bool last_forward;
static bool last_back;
static bool last_left;
static bool last_right;
static bool last_fire;
static bool last_use;
static bool last_menu;
static bool last_run;
static unsigned int last_seq;
static unsigned int presented_frames;
static uint32_t fake_ticks_ms;
static uint32_t paced_ticks_ms;
static uint32_t paced_tick_remainder_us;
static uint32_t paced_time_advance_calls;
static uint64_t paced_time_advance_us_total;
static int paced_time_active;
static uint32_t monotonic_time_base_ms;
static int monotonic_time_base_set;
static uint32_t monotonic_time_last_ticks_ms;
static uint32_t tick_telemetry_sleep_calls;
static uint64_t tick_telemetry_sleep_ms_total;
static uint32_t tick_telemetry_getticks_calls;
static uint32_t frame_gametic_samples;
static uint32_t frame_gametic_changed_transitions;
static uint32_t frame_gametic_repeated_transitions;
static uint32_t frame_gametic_positive_delta_total;
static uint32_t frame_gametic_max_delta;
static uint32_t frame_gametic_reset_transitions;
static uint32_t frame_gametic_same_run_current;
static uint32_t frame_gametic_max_same_run;
static int frame_gametic_first;
static int frame_gametic_last;
static int frame_gametic_previous;
static uint32_t draw_gametic_samples;
static uint32_t draw_gametic_changed_transitions;
static uint32_t draw_gametic_repeated_transitions;
static uint32_t draw_gametic_positive_delta_total;
static uint32_t draw_gametic_max_delta;
static uint32_t draw_gametic_reset_transitions;
static uint32_t draw_gametic_same_run_current;
static uint32_t draw_gametic_max_same_run;
static int draw_gametic_first;
static int draw_gametic_last;
static int draw_gametic_previous;
static uint32_t loop_tick_samples;
static uint32_t loop_tick_gametic_changed;
static uint32_t loop_tick_gametic_repeated;
static uint32_t loop_tick_gametic_positive_delta_total;
static uint32_t loop_tick_gametic_max_delta;
static uint32_t loop_tick_gametic_reset;
static uint32_t loop_tick_draw_changed_iterations;
static uint32_t loop_tick_draw_unchanged_iterations;
static uint32_t loop_tick_draw_delta_total;
static uint32_t loop_tick_draw_max_delta;
static uint32_t frame_checksum;
static pthread_mutex_t a90_dg_key_lock = PTHREAD_MUTEX_INITIALIZER;
static pixel_t frame_sink[DOOMGENERIC_RESX * DOOMGENERIC_RESY];

static uint32_t a90_doomgeneric_monotonic_ms(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
        return fake_ticks_ms;
    }
    return (uint32_t)(((uint64_t)ts.tv_sec * 1000ULL) +
                      ((uint64_t)ts.tv_nsec / 1000000ULL));
}

static uint32_t marker_checksum(const volatile char *value) {
    uint32_t checksum = 5381U;

    while (value != NULL && *value != '\0') {
        checksum = (checksum * 33U) ^ (uint32_t)(unsigned char)*value;
        ++value;
    }
    return checksum;
}

static unsigned int next_index(unsigned int index) {
    return (index + 1U) % A90_DG_KEY_QUEUE_MAX;
}

static void queue_key_event(int pressed, unsigned char key) {
    unsigned int next_tail = next_index(key_tail);

    if (next_tail == key_head) {
        return;
    }
    key_queue[key_tail].pressed = pressed ? 1 : 0;
    key_queue[key_tail].key = key;
    key_tail = next_tail;
}

static void queue_edge(bool current, bool *previous, unsigned char key) {
    if (previous == NULL) {
        return;
    }
    if (current != *previous) {
        queue_key_event(current ? 1 : 0, key);
        *previous = current;
    }
}

void a90_doomgeneric_feed_snapshot(const struct a90_doompad_snapshot *snapshot) {
    if (snapshot == NULL) {
        return;
    }

    pthread_mutex_lock(&a90_dg_key_lock);
    queue_edge(snapshot->forward, &last_forward, KEY_UPARROW);
    queue_edge(snapshot->back, &last_back, KEY_DOWNARROW);
    queue_edge(snapshot->left, &last_left, KEY_LEFTARROW);
    queue_edge(snapshot->right, &last_right, KEY_RIGHTARROW);
    queue_edge(snapshot->fire, &last_fire, KEY_FIRE);
    queue_edge(snapshot->use, &last_use, KEY_USE);
    queue_edge(snapshot->menu, &last_menu, KEY_ESCAPE);
    queue_edge(snapshot->run, &last_run, KEY_RSHIFT);
    last_seq = snapshot->seq;
    pthread_mutex_unlock(&a90_dg_key_lock);
}

int a90_doomgeneric_prepare_argv(char **argv, int max_args) {
    static char arg0[] = "doomgeneric";
    static char arg_iwad[] = "-iwad";
    static char arg_wad[] = A90_DG_RUNTIME_WAD_PATH;
    static char arg_nosound[] = "-nosound";
    static char arg_nomusic[] = "-nomusic";
    static char arg_mb[] = "-mb";
    static char arg_mb_value[] = "6";
    static char arg_warp[] = "-warp";
    static char arg_episode[] = "1";
    static char arg_map[] = "1";
    static char arg_skill[] = "-skill";
    static char arg_skill_value[] = "2";

    if (argv == NULL || max_args < 12) {
        return 0;
    }
    argv[0] = arg0;
    argv[1] = arg_iwad;
    argv[2] = arg_wad;
    argv[3] = arg_nosound;
    argv[4] = arg_nomusic;
    argv[5] = arg_mb;
    argv[6] = arg_mb_value;
    argv[7] = arg_warp;
    argv[8] = arg_episode;
    argv[9] = arg_map;
    argv[10] = arg_skill;
    argv[11] = arg_skill_value;
    return 12;
}

unsigned int a90_doomgeneric_last_seq(void) {
    unsigned int seq;

    pthread_mutex_lock(&a90_dg_key_lock);
    seq = last_seq;
    pthread_mutex_unlock(&a90_dg_key_lock);
    return seq;
}

unsigned int a90_doomgeneric_pending_keys(void) {
    unsigned int pending;

    pthread_mutex_lock(&a90_dg_key_lock);
    if (key_tail >= key_head) {
        pending = key_tail - key_head;
    } else {
        pending = A90_DG_KEY_QUEUE_MAX - key_head + key_tail;
    }
    pthread_mutex_unlock(&a90_dg_key_lock);
    return pending;
}

unsigned int a90_doomgeneric_presented_frames(void) {
    return presented_frames;
}

uint32_t a90_doomgeneric_frame_checksum(void) {
    return frame_checksum;
}

void DG_Init(void) {
    memset(frame_sink, 0, sizeof(frame_sink));
    key_head = 0;
    key_tail = 0;
    presented_frames = 0;
    fake_ticks_ms = 0;
    paced_ticks_ms = 0;
    paced_tick_remainder_us = 0;
    paced_time_advance_calls = 0;
    paced_time_advance_us_total = 0;
    paced_time_active = 0;
    monotonic_time_base_ms = a90_doomgeneric_monotonic_ms();
    monotonic_time_base_set = 1;
    monotonic_time_last_ticks_ms = 0;
    tick_telemetry_sleep_calls = 0;
    tick_telemetry_sleep_ms_total = 0;
    tick_telemetry_getticks_calls = 0;
    frame_gametic_samples = 0;
    frame_gametic_changed_transitions = 0;
    frame_gametic_repeated_transitions = 0;
    frame_gametic_positive_delta_total = 0;
    frame_gametic_max_delta = 0;
    frame_gametic_reset_transitions = 0;
    frame_gametic_same_run_current = 0;
    frame_gametic_max_same_run = 0;
    frame_gametic_first = -1;
    frame_gametic_last = -1;
    frame_gametic_previous = -1;
    draw_gametic_samples = 0;
    draw_gametic_changed_transitions = 0;
    draw_gametic_repeated_transitions = 0;
    draw_gametic_positive_delta_total = 0;
    draw_gametic_max_delta = 0;
    draw_gametic_reset_transitions = 0;
    draw_gametic_same_run_current = 0;
    draw_gametic_max_same_run = 0;
    draw_gametic_first = -1;
    draw_gametic_last = -1;
    draw_gametic_previous = -1;
    loop_tick_samples = 0;
    loop_tick_gametic_changed = 0;
    loop_tick_gametic_repeated = 0;
    loop_tick_gametic_positive_delta_total = 0;
    loop_tick_gametic_max_delta = 0;
    loop_tick_gametic_reset = 0;
    loop_tick_draw_changed_iterations = 0;
    loop_tick_draw_unchanged_iterations = 0;
    loop_tick_draw_delta_total = 0;
    loop_tick_draw_max_delta = 0;
    frame_checksum = 0;
}

static pixel_t a90_doomgeneric_swap_rb_to_xbgr8888(pixel_t pixel) {
    return (pixel & (pixel_t)0xff00ff00U) |
        ((pixel & (pixel_t)0x00ff0000U) >> 16) |
        ((pixel & (pixel_t)0x000000ffU) << 16);
}

static void a90_doomgeneric_record_phase_gametic(
        const char *label,
        uint32_t *samples,
        uint32_t *changed_transitions,
        uint32_t *repeated_transitions,
        uint32_t *positive_delta_total,
        uint32_t *max_delta,
        uint32_t *reset_transitions,
        uint32_t *same_run_current,
        uint32_t *max_same_run,
        int *first,
        int *last,
        int *previous,
        int current);

void DG_DrawFrame(void) {
    const size_t count = (size_t)DOOMGENERIC_RESX * (size_t)DOOMGENERIC_RESY;
    size_t i;

    if (DG_ScreenBuffer != NULL) {
        for (i = 0; i < count; ++i) {
            frame_sink[i] = a90_doomgeneric_swap_rb_to_xbgr8888(DG_ScreenBuffer[i]);
        }
        for (i = 0; i < count; i += 257U) {
            frame_checksum = frame_checksum * 33U + (uint32_t)frame_sink[i];
        }
    }
    ++presented_frames;
    a90_doomgeneric_record_phase_gametic(
        "draw_gametic",
        &draw_gametic_samples,
        &draw_gametic_changed_transitions,
        &draw_gametic_repeated_transitions,
        &draw_gametic_positive_delta_total,
        &draw_gametic_max_delta,
        &draw_gametic_reset_transitions,
        &draw_gametic_same_run_current,
        &draw_gametic_max_same_run,
        &draw_gametic_first,
        &draw_gametic_last,
        &draw_gametic_previous,
        gametic);
}

#define A90_DG_PACED_TICK_QUANTUM_US 28571U

void DG_SleepMs(uint32_t ms) {
    ++tick_telemetry_sleep_calls;
    tick_telemetry_sleep_ms_total += ms;
    fake_ticks_ms += ms;
}

static void a90_doomgeneric_advance_paced_time(void) {
    uint32_t total_us = paced_tick_remainder_us + A90_DG_PACED_TICK_QUANTUM_US;
    uint32_t step_ms = total_us / 1000U;

    paced_tick_remainder_us = total_us % 1000U;
    paced_ticks_ms += step_ms;
    ++paced_time_advance_calls;
    paced_time_advance_us_total += A90_DG_PACED_TICK_QUANTUM_US;
}

uint32_t DG_GetTicksMs(void) {
    uint32_t now;

    ++tick_telemetry_getticks_calls;
    if (!paced_time_active) {
        return fake_ticks_ms;
    }
    now = a90_doomgeneric_monotonic_ms();
    if (!monotonic_time_base_set) {
        monotonic_time_base_ms = now;
        monotonic_time_base_set = 1;
    }
    monotonic_time_last_ticks_ms = now - monotonic_time_base_ms;
    return monotonic_time_last_ticks_ms;
}

int DG_GetKey(int *pressed, unsigned char *key) {
    if (pressed == NULL || key == NULL) {
        return 0;
    }

    pthread_mutex_lock(&a90_dg_key_lock);
    if (key_head == key_tail) {
        pthread_mutex_unlock(&a90_dg_key_lock);
        return 0;
    }
    *pressed = key_queue[key_head].pressed;
    *key = key_queue[key_head].key;
    key_head = next_index(key_head);
    pthread_mutex_unlock(&a90_dg_key_lock);
    return 1;
}

void DG_SetWindowTitle(const char *title) {
    (void)title;
}


static int a90_doomgeneric_parse_positive_int(const char *text, int max_value) {
    char *end = NULL;
    long value;

    if (text == NULL || text[0] == '\0') {
        return -1;
    }
    value = strtol(text, &end, 10);
    if (end == NULL || *end != '\0' || value <= 0 || value > max_value) {
        return -1;
    }
    return (int)value;
}

int a90_doomgeneric_run_wad_smoke(const char *wad_path, int frames) {
    static char arg0[] = "doomgeneric";
    static char arg_iwad[] = "-iwad";
    static char arg_nosound[] = "-nosound";
    static char arg_nomusic[] = "-nomusic";
    static char arg_mb[] = "-mb";
    static char arg_mb_value[] = "6";
    static char arg_warp[] = "-warp";
    static char arg_episode[] = "1";
    static char arg_map[] = "1";
    static char arg_skill[] = "-skill";
    static char arg_skill_value[] = "2";
    char *argv[13];
    int index;

    if (wad_path == NULL || wad_path[0] == '\0' || frames <= 0 || frames > 300) {
        return 30;
    }
    argv[0] = arg0;
    argv[1] = arg_iwad;
    argv[2] = (char *)wad_path;
    argv[3] = arg_nosound;
    argv[4] = arg_nomusic;
    argv[5] = arg_mb;
    argv[6] = arg_mb_value;
    argv[7] = arg_warp;
    argv[8] = arg_episode;
    argv[9] = arg_map;
    argv[10] = arg_skill;
    argv[11] = arg_skill_value;
    argv[12] = NULL;

    doomgeneric_Create(12, argv);
    for (index = 0; frames == 0 || index < frames; ++index) {
        doomgeneric_Tick();
    }
    return a90_doomgeneric_presented_frames() > 0U ? 0 : 31;
}

int a90_doomgeneric_native_probe_entry(void) {
    struct a90_doompad_snapshot snapshot = {
        .forward = true,
        .fire = true,
        .run = true,
        .seq = 24U,
    };
    char *argv[13] = {0};
    int argc = a90_doomgeneric_prepare_argv(argv, 13);
    int pressed = 0;
    unsigned char key = 0;

    DG_Init();
    if (marker_checksum(a90_doomgeneric_v3024_marker) == 0U ||
        marker_checksum(a90_doomgeneric_v3024_wad_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3024_input_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3029_marker) == 0U ||
        marker_checksum(a90_doomgeneric_v3029_wad_smoke_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3031_frame_dump_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3033_loop_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3042_color_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3045_continuous_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3049_autostart_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3051_probe_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3053_audio_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3057_input_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3059_udp_input_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3079_pace_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3081_frame_ipc_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3096_tick_telemetry_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3096_scale_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3098_gametic_frame_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3100_phase_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3404_paced_time_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3404_mode_label) == 0U ||
        marker_checksum(a90_doomgeneric_v3404_input_thread_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3404_time_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3404_demo_hud_policy) == 0U ||
        marker_checksum(a90_doomgeneric_v3404_audio_policy) == 0U) {
        return 19;
    }
    if (argc != 12 || strcmp(argv[1], "-iwad") != 0 ||
        strcmp(argv[2], A90_DG_RUNTIME_WAD_PATH) != 0 ||
        strcmp(argv[3], "-nosound") != 0 ||
        strcmp(argv[4], "-nomusic") != 0 ||
        strcmp(argv[7], "-warp") != 0 ||
        strcmp(argv[8], "1") != 0 ||
        strcmp(argv[9], "1") != 0 ||
        strcmp(argv[10], "-skill") != 0 ||
        strcmp(argv[11], "2") != 0) {
        return 20;
    }
    a90_doomgeneric_feed_snapshot(&snapshot);
    if (a90_doomgeneric_pending_keys() != 3U) {
        return 21;
    }
    if (!DG_GetKey(&pressed, &key) || pressed != 1 || key != KEY_UPARROW) {
        return 22;
    }
    if (!DG_GetKey(&pressed, &key) || pressed != 1 || key != KEY_FIRE) {
        return 23;
    }
    if (!DG_GetKey(&pressed, &key) || pressed != 1 || key != KEY_RSHIFT) {
        return 24;
    }
    DG_SleepMs(16U);
    DG_DrawFrame();
    if (DG_GetTicksMs() != 16U || a90_doomgeneric_presented_frames() != 1U) {
        return 25;
    }
    return a90_doomgeneric_last_seq() == 24U ? 0 : 26;
}


static int a90_doomgeneric_write_full(int fd, const void *data, size_t bytes) {
    size_t done = 0;

    while (done < bytes) {
        ssize_t wr = write(fd, (const char *)data + done, bytes - done);

        if (wr < 0) {
            if (errno == EINTR) {
                continue;
            }
            return 40;
        }
        if (wr == 0) {
            return 41;
        }
        done += (size_t)wr;
    }
    return 0;
}

int a90_doomgeneric_dump_frame_xbgr8888(const char *output_path) {
    const size_t bytes = (size_t)DOOMGENERIC_RESX * (size_t)DOOMGENERIC_RESY * sizeof(frame_sink[0]);
    int fd;
    int rc;

    if (output_path == NULL || output_path[0] == '\0' || sizeof(frame_sink[0]) != 4U) {
        return 42;
    }
    fd = open(output_path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        return 43;
    }
    rc = a90_doomgeneric_write_full(fd, frame_sink, bytes);
    if (close(fd) < 0 && rc == 0) {
        rc = 44;
    }
    return rc;
}

int a90_doomgeneric_run_wad_frame_dump(const char *wad_path, int frames, const char *output_path) {
    static char arg0[] = "doomgeneric";
    static char arg_iwad[] = "-iwad";
    static char arg_nosound[] = "-nosound";
    static char arg_nomusic[] = "-nomusic";
    static char arg_mb[] = "-mb";
    static char arg_mb_value[] = "6";
    static char arg_warp[] = "-warp";
    static char arg_episode[] = "1";
    static char arg_map[] = "1";
    static char arg_skill[] = "-skill";
    static char arg_skill_value[] = "2";
    char *argv[13];
    int index;

    if (wad_path == NULL || wad_path[0] == '\0' ||
        output_path == NULL || output_path[0] == '\0' ||
        frames <= 0 || frames > 300) {
        return 45;
    }
    argv[0] = arg0;
    argv[1] = arg_iwad;
    argv[2] = (char *)wad_path;
    argv[3] = arg_nosound;
    argv[4] = arg_nomusic;
    argv[5] = arg_mb;
    argv[6] = arg_mb_value;
    argv[7] = arg_warp;
    argv[8] = arg_episode;
    argv[9] = arg_map;
    argv[10] = arg_skill;
    argv[11] = arg_skill_value;
    argv[12] = NULL;

    doomgeneric_Create(12, argv);
    for (index = 0; frames == 0 || index < frames; ++index) {
        doomgeneric_Tick();
    }
    if (a90_doomgeneric_presented_frames() == 0U) {
        return 46;
    }
    return a90_doomgeneric_dump_frame_xbgr8888(output_path);
}



#define A90_DG_INPUT_PACKET_MAGIC 0x41394450U
#define A90_DG_INPUT_PACKET_VERSION 1U

struct a90_dg_input_packet {
    uint32_t magic;
    uint32_t version;
    uint32_t seq;
    uint32_t mask;
    uint32_t active;
};

static void a90_doomgeneric_apply_input_mask(unsigned int seq, unsigned int mask) {
    struct a90_doompad_snapshot snapshot;

    memset(&snapshot, 0, sizeof(snapshot));
    snapshot.seq = seq;
    snapshot.forward = (mask & (1U << 0)) != 0U;
    snapshot.back = (mask & (1U << 1)) != 0U;
    snapshot.left = (mask & (1U << 2)) != 0U;
    snapshot.right = (mask & (1U << 3)) != 0U;
    snapshot.fire = (mask & (1U << 4)) != 0U;
    snapshot.use = (mask & (1U << 5)) != 0U;
    snapshot.menu = (mask & (1U << 6)) != 0U;
    snapshot.run = (mask & (1U << 7)) != 0U;
    a90_doomgeneric_feed_snapshot(&snapshot);
}

static int a90_doomgeneric_open_input_socket(const char *path) {
    struct sockaddr_un addr;
    int fd;
    size_t path_len;
    int flags;

    if (path == NULL || path[0] == '\0') {
        return -1;
    }
    memset(&addr, 0, sizeof(addr));
    path_len = strlen(path);
    if (path_len == 0U || path_len >= sizeof(addr.sun_path)) {
        return -1;
    }
    fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (fd < 0) {
        return -1;
    }
    flags = fcntl(fd, F_GETFL, 0);
    if (flags >= 0) {
        (void)fcntl(fd, F_SETFL, flags | O_NONBLOCK);
    }
    (void)fcntl(fd, F_SETFD, FD_CLOEXEC);
    (void)unlink(path);
    addr.sun_family = AF_UNIX;
    snprintf(addr.sun_path, sizeof(addr.sun_path), "%s", path);
    if (bind(fd, (const struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(fd);
        (void)unlink(path);
        return -1;
    }
    return fd;
}



#define A90_DG_PACE_PACKET_MAGIC 0x41395043U
#define A90_DG_PACE_PACKET_VERSION 1U

struct a90_dg_pace_packet {
    uint32_t magic;
    uint32_t version;
    uint32_t seq;
};

static int a90_doomgeneric_open_pace_socket(const char *path) {
    struct sockaddr_un addr;
    int fd;
    size_t path_len;

    if (path == NULL || path[0] == '\0') {
        return -1;
    }
    path_len = strlen(path);
    if (path_len == 0 || path_len >= sizeof(addr.sun_path)) {
        return -1;
    }
    fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (fd < 0) {
        return -1;
    }
    (void)fcntl(fd, F_SETFD, FD_CLOEXEC);
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    memcpy(addr.sun_path, path, path_len + 1U);
    (void)unlink(path);
    if (bind(fd, (const struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(fd);
        (void)unlink(path);
        return -1;
    }
    return fd;
}

static int a90_doomgeneric_wait_pace_fd(int fd) {
    for (;;) {
        struct a90_dg_pace_packet packet;
        ssize_t rd;

        if (fd < 0) {
            return 0;
        }
        rd = recv(fd, &packet, sizeof(packet), 0);
        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            return 53;
        }
        if (rd != (ssize_t)sizeof(packet)) {
            continue;
        }
        if (packet.magic != A90_DG_PACE_PACKET_MAGIC ||
            packet.version != A90_DG_PACE_PACKET_VERSION) {
            continue;
        }
        return 0;
    }
}

static void a90_doomgeneric_close_pace_socket(int fd, const char *path) {
    if (fd >= 0) {
        close(fd);
    }
    if (path != NULL && path[0] != '\0') {
        (void)unlink(path);
    }
}

static int a90_doomgeneric_open_input_udp(unsigned int port) {
    struct sockaddr_in addr;
    int fd;
    int flags;
    int one = 1;

    if (port == 0U || port > 65535U) {
        return -1;
    }
    fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        return -1;
    }
    (void)setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    flags = fcntl(fd, F_GETFL, 0);
    if (flags >= 0) {
        (void)fcntl(fd, F_SETFL, flags | O_NONBLOCK);
    }
    (void)fcntl(fd, F_SETFD, FD_CLOEXEC);
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons((uint16_t)port);
    if (bind(fd, (const struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(fd);
        return -1;
    }
    return fd;
}

static void a90_doomgeneric_close_input_socket(int fd, const char *path) {
    if (fd >= 0) {
        close(fd);
    }
    if (path != NULL && path[0] != '\0') {
        (void)unlink(path);
    }
}

static void a90_doomgeneric_write_input_state_mask(const char *path,
                                                   unsigned int seq,
                                                   unsigned int mask) {
    FILE *fp;

    if (path == NULL || path[0] == '\0') {
        return;
    }
    fp = fopen(path, "w");
    if (fp == NULL) {
        return;
    }
    (void)fprintf(fp,
                  "seq=%u\n"
                  "forward=%d\n"
                  "back=%d\n"
                  "left=%d\n"
                  "right=%d\n"
                  "fire=%d\n"
                  "use=%d\n"
                  "menu=%d\n"
                  "run=%d\n"
                  "active=%d\n",
                  seq,
                  (mask & (1U << 0)) != 0U ? 1 : 0,
                  (mask & (1U << 1)) != 0U ? 1 : 0,
                  (mask & (1U << 2)) != 0U ? 1 : 0,
                  (mask & (1U << 3)) != 0U ? 1 : 0,
                  (mask & (1U << 4)) != 0U ? 1 : 0,
                  (mask & (1U << 5)) != 0U ? 1 : 0,
                  (mask & (1U << 6)) != 0U ? 1 : 0,
                  (mask & (1U << 7)) != 0U ? 1 : 0,
                  mask != 0U ? 1 : 0);
    (void)fclose(fp);
}

static void a90_doomgeneric_drain_input_fd(int fd, const char *input_state_path) {
    for (;;) {
        struct a90_dg_input_packet packet;
        ssize_t rd;

        if (fd < 0) {
            return;
        }
        rd = recv(fd, &packet, sizeof(packet), MSG_DONTWAIT);
        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            return;
        }
        if (rd != (ssize_t)sizeof(packet)) {
            continue;
        }
        if (packet.magic != A90_DG_INPUT_PACKET_MAGIC ||
            packet.version != A90_DG_INPUT_PACKET_VERSION) {
            continue;
        }
        a90_doomgeneric_apply_input_mask(packet.seq, packet.mask);
        a90_doomgeneric_write_input_state_mask(input_state_path, packet.seq, packet.mask);
    }
}


struct a90_dg_input_thread {
    int input_socket_fd;
    int input_udp_fd;
    const char *input_state_path;
    volatile int stop;
    int started;
    pthread_t thread;
};

static void a90_doomgeneric_input_thread_init(struct a90_dg_input_thread *ctx,
                                              int input_socket_fd,
                                              int input_udp_fd,
                                              const char *input_state_path) {
    memset(ctx, 0, sizeof(*ctx));
    ctx->input_socket_fd = input_socket_fd;
    ctx->input_udp_fd = input_udp_fd;
    ctx->input_state_path = input_state_path;
}

static void *a90_doomgeneric_input_thread_main(void *opaque) {
    struct a90_dg_input_thread *ctx = (struct a90_dg_input_thread *)opaque;

    while (ctx != NULL && !ctx->stop) {
        if (ctx->input_socket_fd >= 0) {
            a90_doomgeneric_drain_input_fd(ctx->input_socket_fd, ctx->input_state_path);
        }
        if (ctx->input_udp_fd >= 0) {
            a90_doomgeneric_drain_input_fd(ctx->input_udp_fd, ctx->input_state_path);
        }
        usleep(1000U);
    }
    return NULL;
}

static int a90_doomgeneric_input_thread_start(struct a90_dg_input_thread *ctx) {
    if (ctx == NULL || (ctx->input_socket_fd < 0 && ctx->input_udp_fd < 0)) {
        return 0;
    }
    if (pthread_create(&ctx->thread, NULL, a90_doomgeneric_input_thread_main, ctx) != 0) {
        return -1;
    }
    ctx->started = 1;
    return 0;
}

static void a90_doomgeneric_input_thread_stop(struct a90_dg_input_thread *ctx) {
    if (ctx == NULL || !ctx->started) {
        return;
    }
    ctx->stop = 1;
    pthread_join(ctx->thread, NULL);
    ctx->started = 0;
}

static void a90_doomgeneric_apply_input_state_file(const char *path) {
    struct a90_doompad_snapshot snapshot;
    FILE *fp;
    char line[96];

    if (path == NULL || path[0] == '\0') {
        return;
    }
    memset(&snapshot, 0, sizeof(snapshot));
    fp = fopen(path, "r");
    if (fp == NULL) {
        return;
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        char key[32];
        unsigned int value = 0U;

        if (sscanf(line, "%31[^=]=%u", key, &value) != 2) {
            continue;
        }
        if (strcmp(key, "forward") == 0) {
            snapshot.forward = value != 0U;
        } else if (strcmp(key, "back") == 0) {
            snapshot.back = value != 0U;
        } else if (strcmp(key, "left") == 0) {
            snapshot.left = value != 0U;
        } else if (strcmp(key, "right") == 0) {
            snapshot.right = value != 0U;
        } else if (strcmp(key, "fire") == 0) {
            snapshot.fire = value != 0U;
        } else if (strcmp(key, "use") == 0) {
            snapshot.use = value != 0U;
        } else if (strcmp(key, "menu") == 0) {
            snapshot.menu = value != 0U;
        } else if (strcmp(key, "run") == 0) {
            snapshot.run = value != 0U;
        } else if (strcmp(key, "seq") == 0) {
            snapshot.seq = value;
        }
    }
    fclose(fp);
    a90_doomgeneric_feed_snapshot(&snapshot);
}

static int a90_doomgeneric_dump_frame_xbgr8888_atomic(const char *output_path) {
    char tmp_path[256];
    int rc;

    if (output_path == NULL ||
        snprintf(tmp_path, sizeof(tmp_path), "%s.tmp", output_path) >= (int)sizeof(tmp_path)) {
        return 47;
    }
    rc = a90_doomgeneric_dump_frame_xbgr8888(tmp_path);
    if (rc != 0) {
        (void)unlink(tmp_path);
        return rc;
    }
    if (rename(tmp_path, output_path) < 0) {
        (void)unlink(tmp_path);
        return 48;
    }
    return 0;
}


#define A90_DG_SHARED_FRAME_MAGIC 0x41394652U
#define A90_DG_SHARED_FRAME_VERSION 1U
#define A90_DG_SHARED_FRAME_HEADER_BYTES 64U

struct a90_dg_shared_frame_header {
    uint32_t magic;
    uint32_t version;
    uint32_t header_bytes;
    uint32_t width;
    uint32_t height;
    uint32_t stride;
    uint32_t frame_bytes;
    uint32_t sequence;
    uint32_t flags;
    uint32_t reserved0;
    uint64_t frame_id;
    uint8_t reserved[16];
};

struct a90_dg_shared_frame {
    int fd;
    void *map;
    size_t map_size;
    volatile struct a90_dg_shared_frame_header *header;
    uint8_t *pixels;
    const char *path;
    uint32_t sequence;
};

static void a90_doomgeneric_shared_frame_init(struct a90_dg_shared_frame *shared) {
    if (shared == NULL) {
        return;
    }
    memset(shared, 0, sizeof(*shared));
    shared->fd = -1;
}

static int a90_doomgeneric_shared_frame_requested(const char *path) {
    return path != NULL && path[0] != '\0';
}

static int a90_doomgeneric_open_shared_frame(struct a90_dg_shared_frame *shared,
                                             const char *path) {
    const size_t frame_bytes = (size_t)DOOMGENERIC_RESX *
        (size_t)DOOMGENERIC_RESY * sizeof(frame_sink[0]);
    const size_t map_size = (size_t)A90_DG_SHARED_FRAME_HEADER_BYTES + frame_bytes;
    void *map;
    int fd;

    if (shared == NULL || !a90_doomgeneric_shared_frame_requested(path) ||
        sizeof(struct a90_dg_shared_frame_header) != A90_DG_SHARED_FRAME_HEADER_BYTES ||
        sizeof(frame_sink[0]) != 4U) {
        return 54;
    }
    fd = open(path, O_RDWR | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        return 55;
    }
    if (ftruncate(fd, (off_t)map_size) < 0) {
        close(fd);
        return 56;
    }
    map = mmap(NULL, map_size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (map == MAP_FAILED) {
        close(fd);
        return 57;
    }
    memset(map, 0, map_size);
    shared->fd = fd;
    shared->map = map;
    shared->map_size = map_size;
    shared->header = (volatile struct a90_dg_shared_frame_header *)map;
    shared->pixels = (uint8_t *)map + A90_DG_SHARED_FRAME_HEADER_BYTES;
    shared->path = path;
    shared->sequence = 0U;

    shared->header->magic = A90_DG_SHARED_FRAME_MAGIC;
    shared->header->version = A90_DG_SHARED_FRAME_VERSION;
    shared->header->header_bytes = A90_DG_SHARED_FRAME_HEADER_BYTES;
    shared->header->width = DOOMGENERIC_RESX;
    shared->header->height = DOOMGENERIC_RESY;
    shared->header->stride = DOOMGENERIC_RESX * (uint32_t)sizeof(frame_sink[0]);
    shared->header->frame_bytes = (uint32_t)frame_bytes;
    __sync_synchronize();
    return 0;
}

static int a90_doomgeneric_write_shared_frame(struct a90_dg_shared_frame *shared) {
    const size_t frame_bytes = (size_t)DOOMGENERIC_RESX *
        (size_t)DOOMGENERIC_RESY * sizeof(frame_sink[0]);
    uint32_t sequence;

    if (shared == NULL || shared->header == NULL || shared->pixels == NULL) {
        return 58;
    }
    sequence = shared->sequence + 2U;
    if (sequence == 0U) {
        sequence = 2U;
    }
    shared->sequence = sequence;
    shared->header->sequence = sequence - 1U;
    __sync_synchronize();
    memcpy(shared->pixels, frame_sink, frame_bytes);
    __sync_synchronize();
    shared->header->frame_id = (((uint64_t)sequence) << 32U) ^ (uint64_t)frame_checksum;
    shared->header->sequence = sequence;
    __sync_synchronize();
    return 0;
}

static void a90_doomgeneric_close_shared_frame(struct a90_dg_shared_frame *shared) {
    if (shared == NULL) {
        return;
    }
    if (shared->map != NULL && shared->map != MAP_FAILED) {
        munmap(shared->map, shared->map_size);
    }
    if (shared->fd >= 0) {
        close(shared->fd);
    }
    a90_doomgeneric_shared_frame_init(shared);
}

#define A90_DG_TICK_TELEMETRY_PATH "/tmp/a90-doomgeneric-v3404-tick-telemetry.txt"

static void a90_doomgeneric_record_phase_gametic(
        const char *label,
        uint32_t *samples,
        uint32_t *changed_transitions,
        uint32_t *repeated_transitions,
        uint32_t *positive_delta_total,
        uint32_t *max_delta,
        uint32_t *reset_transitions,
        uint32_t *same_run_current,
        uint32_t *max_same_run,
        int *first,
        int *last,
        int *previous,
        int current) {
    (void)label;
    if (samples == NULL || changed_transitions == NULL || repeated_transitions == NULL ||
        positive_delta_total == NULL || max_delta == NULL || reset_transitions == NULL ||
        same_run_current == NULL || max_same_run == NULL || first == NULL ||
        last == NULL || previous == NULL) {
        return;
    }
    ++*samples;
    if (*samples == 1U) {
        *first = current;
        *last = current;
        *previous = current;
        *same_run_current = 1U;
        *max_same_run = 1U;
        return;
    }
    if (current == *previous) {
        ++*repeated_transitions;
        ++*same_run_current;
    } else {
        ++*changed_transitions;
        if (current > *previous) {
            uint32_t delta = (uint32_t)(current - *previous);

            *positive_delta_total += delta;
            if (delta > *max_delta) {
                *max_delta = delta;
            }
        } else {
            ++*reset_transitions;
        }
        *same_run_current = 1U;
        *previous = current;
    }
    if (*same_run_current > *max_same_run) {
        *max_same_run = *same_run_current;
    }
    *last = current;
}

static void a90_doomgeneric_record_frame_gametic(void) {
    int current = gametic;

    a90_doomgeneric_record_phase_gametic(
        "dump_gametic",
        &frame_gametic_samples,
        &frame_gametic_changed_transitions,
        &frame_gametic_repeated_transitions,
        &frame_gametic_positive_delta_total,
        &frame_gametic_max_delta,
        &frame_gametic_reset_transitions,
        &frame_gametic_same_run_current,
        &frame_gametic_max_same_run,
        &frame_gametic_first,
        &frame_gametic_last,
        &frame_gametic_previous,
        current);
    return;

    ++frame_gametic_samples;
    if (frame_gametic_samples == 1U) {
        frame_gametic_first = current;
        frame_gametic_last = current;
        frame_gametic_previous = current;
        frame_gametic_same_run_current = 1U;
        frame_gametic_max_same_run = 1U;
        return;
    }
    if (current == frame_gametic_previous) {
        ++frame_gametic_repeated_transitions;
        ++frame_gametic_same_run_current;
    } else {
        ++frame_gametic_changed_transitions;
        if (current > frame_gametic_previous) {
            uint32_t delta = (uint32_t)(current - frame_gametic_previous);

            frame_gametic_positive_delta_total += delta;
            if (delta > frame_gametic_max_delta) {
                frame_gametic_max_delta = delta;
            }
        } else {
            ++frame_gametic_reset_transitions;
        }
        frame_gametic_same_run_current = 1U;
        frame_gametic_previous = current;
    }
    if (frame_gametic_same_run_current > frame_gametic_max_same_run) {
        frame_gametic_max_same_run = frame_gametic_same_run_current;
    }
    frame_gametic_last = current;
}

static void a90_doomgeneric_record_loop_tick_phase(
        int before_gametic,
        int after_gametic,
        unsigned int before_draws,
        unsigned int after_draws) {
    ++loop_tick_samples;
    if (after_gametic == before_gametic) {
        ++loop_tick_gametic_repeated;
    } else {
        ++loop_tick_gametic_changed;
        if (after_gametic > before_gametic) {
            uint32_t delta = (uint32_t)(after_gametic - before_gametic);

            loop_tick_gametic_positive_delta_total += delta;
            if (delta > loop_tick_gametic_max_delta) {
                loop_tick_gametic_max_delta = delta;
            }
        } else {
            ++loop_tick_gametic_reset;
        }
    }
    if (after_draws > before_draws) {
        uint32_t delta = after_draws - before_draws;

        ++loop_tick_draw_changed_iterations;
        loop_tick_draw_delta_total += delta;
        if (delta > loop_tick_draw_max_delta) {
            loop_tick_draw_max_delta = delta;
        }
    } else {
        ++loop_tick_draw_unchanged_iterations;
    }
}

static int a90_doomgeneric_write_tick_telemetry(const char *path,
                                                int frames_requested,
                                                int loop_iterations,
                                                int loop_rc) {
    char tmp_path[256];
    FILE *fp;
    int i_time;
    int observed_gametic;
    unsigned int observed_presented;
    int ok = 1;

    if (path == NULL || path[0] == '\0' ||
        snprintf(tmp_path, sizeof(tmp_path), "%s.tmp", path) >= (int)sizeof(tmp_path)) {
        return 62;
    }
    i_time = I_GetTime();
    observed_gametic = gametic;
    observed_presented = a90_doomgeneric_presented_frames();
    fp = fopen(tmp_path, "w");
    if (fp == NULL) {
        return 63;
    }
    ok = ok && fprintf(fp, "version=1\n") >= 0;
    ok = ok && fprintf(fp, "marker=a90.doomgeneric.v3404.tick_telemetry=smooth-demo-paced-time-direct-blit\n") >= 0;
    ok = ok && fprintf(fp, "frames_requested=%d\n", frames_requested) >= 0;
    ok = ok && fprintf(fp, "loop_iterations=%d\n", loop_iterations) >= 0;
    ok = ok && fprintf(fp, "loop_rc=%d\n", loop_rc) >= 0;
    ok = ok && fprintf(fp, "presented_frames=%u\n", observed_presented) >= 0;
    ok = ok && fprintf(fp, "fake_ticks_ms=%u\n", fake_ticks_ms) >= 0;
    ok = ok && fprintf(fp, "sleep_calls=%u\n", tick_telemetry_sleep_calls) >= 0;
    ok = ok && fprintf(fp, "sleep_ms_total=%llu\n",
                      (unsigned long long)tick_telemetry_sleep_ms_total) >= 0;
    ok = ok && fprintf(fp, "getticks_calls=%u\n", tick_telemetry_getticks_calls) >= 0;
    ok = ok && fprintf(fp, "i_get_time=%d\n", i_time) >= 0;
    ok = ok && fprintf(fp, "gametic=%d\n", observed_gametic) >= 0;
    ok = ok && fprintf(fp, "gametic_frame_marker=a90.doomgeneric.v3404.gametic_frame_telemetry=loop-dump-gametic-summary-smooth-demo\n") >= 0;
    ok = ok && fprintf(fp, "phase_marker=a90.doomgeneric.v3404.phase_telemetry=tick-draw-dump-split-smooth-demo\n") >= 0;
    ok = ok && fprintf(fp, "loop_tick.samples=%u\n", loop_tick_samples) >= 0;
    ok = ok && fprintf(fp, "loop_tick.gametic_changed=%u\n", loop_tick_gametic_changed) >= 0;
    ok = ok && fprintf(fp, "loop_tick.gametic_repeated=%u\n", loop_tick_gametic_repeated) >= 0;
    ok = ok && fprintf(fp, "loop_tick.gametic_positive_delta_total=%u\n", loop_tick_gametic_positive_delta_total) >= 0;
    ok = ok && fprintf(fp, "loop_tick.gametic_max_delta=%u\n", loop_tick_gametic_max_delta) >= 0;
    ok = ok && fprintf(fp, "loop_tick.gametic_reset=%u\n", loop_tick_gametic_reset) >= 0;
    ok = ok && fprintf(fp, "loop_tick.draw_changed_iterations=%u\n", loop_tick_draw_changed_iterations) >= 0;
    ok = ok && fprintf(fp, "loop_tick.draw_unchanged_iterations=%u\n", loop_tick_draw_unchanged_iterations) >= 0;
    ok = ok && fprintf(fp, "loop_tick.draw_delta_total=%u\n", loop_tick_draw_delta_total) >= 0;
    ok = ok && fprintf(fp, "loop_tick.draw_max_delta=%u\n", loop_tick_draw_max_delta) >= 0;
    ok = ok && fprintf(fp, "draw_gametic.samples=%u\n", draw_gametic_samples) >= 0;
    ok = ok && fprintf(fp, "draw_gametic.first=%d\n", draw_gametic_first) >= 0;
    ok = ok && fprintf(fp, "draw_gametic.last=%d\n", draw_gametic_last) >= 0;
    ok = ok && fprintf(fp, "draw_gametic.changed_transitions=%u\n", draw_gametic_changed_transitions) >= 0;
    ok = ok && fprintf(fp, "draw_gametic.repeated_transitions=%u\n", draw_gametic_repeated_transitions) >= 0;
    ok = ok && fprintf(fp, "draw_gametic.positive_delta_total=%u\n", draw_gametic_positive_delta_total) >= 0;
    ok = ok && fprintf(fp, "draw_gametic.max_delta=%u\n", draw_gametic_max_delta) >= 0;
    ok = ok && fprintf(fp, "draw_gametic.reset_transitions=%u\n", draw_gametic_reset_transitions) >= 0;
    ok = ok && fprintf(fp, "draw_gametic.max_same_run=%u\n", draw_gametic_max_same_run) >= 0;
    ok = ok && fprintf(fp, "draw_gametic.transition_samples=%u\n",
                      draw_gametic_changed_transitions +
                      draw_gametic_repeated_transitions) >= 0;
    ok = ok && fprintf(fp, "dump_gametic.samples=%u\n", frame_gametic_samples) >= 0;
    ok = ok && fprintf(fp, "dump_gametic.samples=%u\n", frame_gametic_samples) >= 0;
    ok = ok && fprintf(fp, "dump_gametic.first=%d\n", frame_gametic_first) >= 0;
    ok = ok && fprintf(fp, "dump_gametic.last=%d\n", frame_gametic_last) >= 0;
    ok = ok && fprintf(fp, "dump_gametic.changed_transitions=%u\n", frame_gametic_changed_transitions) >= 0;
    ok = ok && fprintf(fp, "dump_gametic.repeated_transitions=%u\n", frame_gametic_repeated_transitions) >= 0;
    ok = ok && fprintf(fp, "dump_gametic.positive_delta_total=%u\n", frame_gametic_positive_delta_total) >= 0;
    ok = ok && fprintf(fp, "dump_gametic.max_delta=%u\n", frame_gametic_max_delta) >= 0;
    ok = ok && fprintf(fp, "dump_gametic.reset_transitions=%u\n", frame_gametic_reset_transitions) >= 0;
    ok = ok && fprintf(fp, "dump_gametic.max_same_run=%u\n", frame_gametic_max_same_run) >= 0;
    ok = ok && fprintf(fp, "dump_gametic.transition_samples=%u\n",
                      frame_gametic_changed_transitions +
                      frame_gametic_repeated_transitions) >= 0;
    ok = ok && fprintf(fp, "ticrate=35\n") >= 0;
    ok = ok && fprintf(fp, "fake_time_model=DG_SleepMs-request-telemetry-only\n") >= 0;
    ok = ok && fprintf(fp, "paced_time_marker=a90.doomgeneric.v3404.paced_time=smooth-demo-presenter-token-doom-tic-quantum\n") >= 0;
    ok = ok && fprintf(fp, "paced_time_model=monotonic-clock-while-loop-active\n") >= 0;
    ok = ok && fprintf(fp, "time_model_marker=a90.doomgeneric.v3404.time_model=clock-monotonic-while-loop-active\n") >= 0;
    ok = ok && fprintf(fp, "demo_hud_marker=a90.doomgeneric.v3404.demo_hud=large-grouped-hw-doom-input\n") >= 0;
    ok = ok && fprintf(fp, "monotonic_time.last_ticks_ms=%u\n", monotonic_time_last_ticks_ms) >= 0;
    ok = ok && fprintf(fp, "smooth_demo_mode=non-original-smooth-demo\n") >= 0;
    ok = ok && fprintf(fp, "paced_time.active=%d\n", paced_time_active) >= 0;
    ok = ok && fprintf(fp, "paced_time.quantum_us=%u\n", A90_DG_PACED_TICK_QUANTUM_US) >= 0;
    ok = ok && fprintf(fp, "paced_time.paced_ticks_ms=%u\n", paced_ticks_ms) >= 0;
    ok = ok && fprintf(fp, "paced_time.remainder_us=%u\n", paced_tick_remainder_us) >= 0;
    ok = ok && fprintf(fp, "paced_time.advance_calls=%u\n", paced_time_advance_calls) >= 0;
    ok = ok && fprintf(fp, "paced_time.advance_us_total=%llu\n",
                      (unsigned long long)paced_time_advance_us_total) >= 0;
    ok = ok && fprintf(fp, "scale_marker=a90.doomgeneric.v3404.scale=producer-960x600-1to1-demo-hud-large-groups\n") >= 0;
    ok = ok && fprintf(fp, "scale_path=producer-pre-scaled-1to1\n") >= 0;
    ok = ok && fprintf(fp, "pacing_model=presenter-pageflip-token\n") >= 0;
    ok = ok && fprintf(fp, "input_model=udp-ncm-unix-dgram-file-fallback\n") >= 0;
    if (!ok || fflush(fp) != 0) {
        (void)fclose(fp);
        (void)unlink(tmp_path);
        return 64;
    }
    if (fclose(fp) != 0) {
        (void)unlink(tmp_path);
        return 65;
    }
    if (rename(tmp_path, path) < 0) {
        (void)unlink(tmp_path);
        return 66;
    }
    return 0;
}

static int a90_doomgeneric_parse_loop_frames(const char *text, int max_value) {
    if (text != NULL && strcmp(text, "0") == 0) {
        return 0;
    }
    return a90_doomgeneric_parse_positive_int(text, max_value);
}


int a90_doomgeneric_run_wad_frame_loop(const char *wad_path,
                                       int frames,
                                       const char *output_path,
                                       const char *input_state_path,
                                       const char *input_socket_path,
                                       unsigned int input_udp_port,
                                       const char *pace_socket_path,
                                       const char *shared_frame_path,
                                       int frame_ms) {
    static char arg0[] = "doomgeneric";
    static char arg_iwad[] = "-iwad";
    static char arg_nomusic[] = "-nomusic";
    static char arg_mb[] = "-mb";
    static char arg_mb_value[] = "6";
    static char arg_warp[] = "-warp";
    static char arg_episode[] = "1";
    static char arg_map[] = "1";
    static char arg_skill[] = "-skill";
    static char arg_skill_value[] = "2";
    char *argv[13];
    int index;
    int input_socket_fd;
    int input_udp_fd;
    int pace_fd;
    struct a90_dg_input_thread input_thread;
    struct a90_dg_shared_frame shared_frame;
    int rc;
    int loop_rc = 0;

    if (wad_path == NULL || wad_path[0] == '\0' ||
        output_path == NULL || output_path[0] == '\0' ||
        input_state_path == NULL || input_state_path[0] == '\0' ||
        frames < 0 || frames > 300 || frame_ms <= 0 || frame_ms > 250) {
        return 49;
    }
    argv[0] = arg0;
    argv[1] = arg_iwad;
    argv[2] = (char *)wad_path;
    argv[3] = arg_nomusic;
    argv[4] = arg_mb;
    argv[5] = arg_mb_value;
    argv[6] = arg_warp;
    argv[7] = arg_episode;
    argv[8] = arg_map;
    argv[9] = arg_skill;
    argv[10] = arg_skill_value;
    argv[11] = NULL;

    a90_doomgeneric_shared_frame_init(&shared_frame);
    a90_doomgeneric_input_thread_init(&input_thread, -1, -1, input_state_path);
    a90_doomgeneric_apply_input_state_file(input_state_path);
    input_socket_fd = a90_doomgeneric_open_input_socket(input_socket_path);
    input_udp_fd = a90_doomgeneric_open_input_udp(input_udp_port);
    a90_doomgeneric_input_thread_init(&input_thread, input_socket_fd, input_udp_fd, input_state_path);
    pace_fd = a90_doomgeneric_open_pace_socket(pace_socket_path);
    if (pace_socket_path != NULL && pace_socket_path[0] != '\0' && pace_fd < 0) {
        if (input_udp_fd >= 0) {
            close(input_udp_fd);
        }
        a90_doomgeneric_close_input_socket(input_socket_fd, input_socket_path);
        return 52;
    }
    if (a90_doomgeneric_shared_frame_requested(shared_frame_path)) {
        rc = a90_doomgeneric_open_shared_frame(&shared_frame, shared_frame_path);
        if (rc != 0) {
            a90_doomgeneric_close_shared_frame(&shared_frame);
    a90_doomgeneric_close_pace_socket(pace_fd, pace_socket_path);
            if (input_udp_fd >= 0) {
                close(input_udp_fd);
            }
            a90_doomgeneric_close_input_socket(input_socket_fd, input_socket_path);
            return rc;
        }
    }

    doomgeneric_Create(11, argv);
    paced_ticks_ms = fake_ticks_ms;
    paced_tick_remainder_us = 0;
    paced_time_active = 1;
    monotonic_time_base_ms = a90_doomgeneric_monotonic_ms();
    monotonic_time_base_set = 1;
    monotonic_time_last_ticks_ms = 0;
    if (a90_doomgeneric_input_thread_start(&input_thread) != 0) {
        loop_rc = 54;
    }
    for (index = 0; loop_rc == 0 && (frames == 0 || index < frames); ++index) {
        int rc;

        if (pace_fd >= 0) {
            rc = a90_doomgeneric_wait_pace_fd(pace_fd);
            if (rc != 0) {
                loop_rc = rc;
                break;
            }
        }
        if (input_socket_fd >= 0) {
            a90_doomgeneric_drain_input_fd(input_socket_fd, input_state_path);
        }
        if (input_udp_fd >= 0) {
            a90_doomgeneric_drain_input_fd(input_udp_fd, input_state_path);
        }
        {
            int before_gametic = gametic;
            unsigned int before_draws = a90_doomgeneric_presented_frames();

            if (input_socket_fd < 0 && input_udp_fd < 0) {
                a90_doomgeneric_apply_input_state_file(input_state_path);
            }
            a90_doomgeneric_advance_paced_time();
            doomgeneric_Tick();
            a90_doomgeneric_record_loop_tick_phase(
                before_gametic,
                gametic,
                before_draws,
                a90_doomgeneric_presented_frames());
        }
        if (a90_doomgeneric_presented_frames() > 0U) {
            a90_doomgeneric_record_frame_gametic();
            if (shared_frame.header != NULL) {
                rc = a90_doomgeneric_write_shared_frame(&shared_frame);
            } else {
                rc = a90_doomgeneric_dump_frame_xbgr8888_atomic(output_path);
            }
            if (rc != 0) {
                loop_rc = rc;
                break;
            }
        }
        if (pace_fd < 0) {
            usleep((useconds_t)frame_ms * 1000U);
        }
    }
    a90_doomgeneric_input_thread_stop(&input_thread);
    a90_doomgeneric_close_shared_frame(&shared_frame);
    paced_time_active = 0;
    a90_doomgeneric_close_pace_socket(pace_fd, pace_socket_path);
    if (input_udp_fd >= 0) {
        close(input_udp_fd);
    }
    a90_doomgeneric_close_input_socket(input_socket_fd, input_socket_path);
    {
        int final_rc = loop_rc != 0 ? loop_rc :
            (a90_doomgeneric_presented_frames() > 0U ? 0 : 50);
        int telemetry_rc = a90_doomgeneric_write_tick_telemetry(
            A90_DG_TICK_TELEMETRY_PATH, frames, index, final_rc);

        if (telemetry_rc != 0 && final_rc == 0) {
            return telemetry_rc;
        }
        return final_rc;
    }
}

int main(int argc, char **argv) {
    int frames;

    if (argc == 1) {
        return a90_doomgeneric_native_probe_entry();
    }
    if (argc == 5 &&
        strcmp(argv[1], "--wad-smoke") == 0 &&
        argv[2] != NULL &&
        strcmp(argv[3], "--frames") == 0) {
        frames = a90_doomgeneric_parse_positive_int(argv[4], 300);
        if (frames <= 0) {
            return 32;
        }
        return a90_doomgeneric_run_wad_smoke(argv[2], frames);
    }
    if (argc == 7 &&
        strcmp(argv[1], "--wad-frame-dump") == 0 &&
        argv[2] != NULL &&
        strcmp(argv[3], "--frames") == 0 &&
        strcmp(argv[5], "--output") == 0 &&
        argv[6] != NULL) {
        frames = a90_doomgeneric_parse_positive_int(argv[4], 300);
        if (frames <= 0) {
            return 34;
        }
        return a90_doomgeneric_run_wad_frame_dump(argv[2], frames, argv[6]);
    }
    if ((argc == 11 || argc == 13 || argc == 15 || argc == 17 || argc == 19) &&
        strcmp(argv[1], "--wad-frame-loop") == 0 &&
        argv[2] != NULL &&
        strcmp(argv[3], "--frames") == 0 &&
        strcmp(argv[5], "--output") == 0 &&
        argv[6] != NULL &&
        strcmp(argv[7], "--input-state") == 0 &&
        argv[8] != NULL &&
        strcmp(argv[9], "--frame-ms") == 0) {
        int frame_ms;
        const char *input_socket_path = NULL;
        const char *pace_socket_path = NULL;
        const char *shared_frame_path = NULL;
        unsigned int input_udp_port = 0U;
        int arg_index = 11;

        while (arg_index < argc) {
            if (arg_index + 1 >= argc) {
                return 37;
            }
            if (strcmp(argv[arg_index], "--input-socket") == 0) {
                input_socket_path = argv[arg_index + 1];
            } else if (strcmp(argv[arg_index], "--input-udp") == 0) {
                input_udp_port = (unsigned int)a90_doomgeneric_parse_positive_int(argv[arg_index + 1], 65535);
                if (input_udp_port == 0U) {
                    return 37;
                }
            } else if (strcmp(argv[arg_index], "--pace-socket") == 0) {
                pace_socket_path = argv[arg_index + 1];
            } else if (strcmp(argv[arg_index], "--shared-frame") == 0) {
                shared_frame_path = argv[arg_index + 1];
            } else {
                return 37;
            }
            arg_index += 2;
        }
        frames = a90_doomgeneric_parse_loop_frames(argv[4], 300);
        frame_ms = a90_doomgeneric_parse_positive_int(argv[10], 250);
        if (frames < 0 || frame_ms <= 0) {
            return 36;
        }
        return a90_doomgeneric_run_wad_frame_loop(argv[2], frames, argv[6], argv[8], input_socket_path, input_udp_port, pace_socket_path, shared_frame_path, frame_ms);
    }
    return 37;
}
