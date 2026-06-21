#ifndef A90_DOOMGENERIC_BRIDGE_H
#define A90_DOOMGENERIC_BRIDGE_H

#include <stdbool.h>
#include <stdint.h>
#include <sys/types.h>

struct a90_run_result;

struct a90_doomgeneric_bridge_status {
    const char *candidate;
    const char *engine;
    const char *helper_path;
    const char *runtime_wad_root;
    const char *runtime_wad_path;
    const char *expected_wad_sha256;
    const char *frame_path;
    const char *input_state_path;
    const char *input_path;
    const char *sound_mode;
    long long runtime_wad_max_bytes;
    long long runtime_wad_bytes;
    uint32_t frame_width;
    uint32_t frame_height;
    uint32_t frame_stride;
    uint32_t frame_bytes;
    uint32_t loop_frame_ms;
    bool helper_present;
    bool helper_executable;
    bool runtime_wad_present;
    bool runtime_wad_regular;
    bool runtime_wad_size_ok;
    bool wad_embedded_in_boot;
    bool visible_loop;
};

struct a90_doomgeneric_input_state {
    bool forward;
    bool back;
    bool left;
    bool right;
    bool fire;
    bool use;
    bool menu;
    bool run;
    bool active;
    unsigned int seq;
};

struct a90_doomgeneric_wad_check {
    const char *path;
    const char *expected_sha256;
    char actual_sha256[65];
    char magic[5];
    long long bytes;
    int stat_errno;
    bool present;
    bool regular;
    bool size_ok;
    bool magic_ok;
    bool expected_sha256_valid;
    bool sha256_checked;
    bool sha256_match;
    bool ok;
};

struct a90_doomgeneric_frame_render {
    const char *path;
    uint32_t width;
    uint32_t height;
    uint32_t stride;
    uint32_t expected_bytes;
    long long bytes;
    int stat_errno;
    bool present;
    bool regular;
    bool size_ok;
    bool geometry_ok;
    bool ok;
};

void a90_doomgeneric_bridge_get_status(struct a90_doomgeneric_bridge_status *status);
int a90_doomgeneric_bridge_probe(int timeout_ms, struct a90_run_result *result);
int a90_doomgeneric_bridge_verify_wad(const char *expected_sha256,
                                      struct a90_doomgeneric_wad_check *check);
int a90_doomgeneric_bridge_play(int frames,
                                const char *expected_sha256,
                                int timeout_ms,
                                struct a90_doomgeneric_wad_check *check,
                                struct a90_run_result *result);
int a90_doomgeneric_bridge_render_frame(int frames,
                                        const char *expected_sha256,
                                        int timeout_ms,
                                        struct a90_doomgeneric_wad_check *check,
                                        struct a90_doomgeneric_frame_render *render,
                                        struct a90_run_result *result);
int a90_doomgeneric_bridge_read_frame_render(struct a90_doomgeneric_frame_render *render);
int a90_doomgeneric_bridge_write_input_state(const struct a90_doomgeneric_input_state *input);
int a90_doomgeneric_bridge_start_frame_loop_helper(int frames,
                                                   const char *expected_sha256,
                                                   int frame_ms,
                                                   struct a90_doomgeneric_wad_check *check,
                                                   pid_t *pid_out);

#endif
