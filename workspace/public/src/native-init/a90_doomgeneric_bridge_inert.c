#include "a90_doomgeneric_bridge.h"

#include "a90_run.h"

#include <errno.h>
#include <string.h>


static void inert_run_result(struct a90_run_result *result) {
    if (result == NULL) {
        return;
    }
    memset(result, 0, sizeof(*result));
    result->pid = -1;
    result->rc = -ENOTSUP;
    result->saved_errno = ENOTSUP;
}


static void inert_wad_check(const char *expected_sha256,
                            struct a90_doomgeneric_wad_check *check) {
    if (check == NULL) {
        return;
    }
    memset(check, 0, sizeof(*check));
    check->path = "";
    check->expected_sha256 = expected_sha256 != NULL ? expected_sha256 : "";
    check->stat_errno = ENOTSUP;
}


static void inert_frame_render(struct a90_doomgeneric_frame_render *render) {
    if (render == NULL) {
        return;
    }
    memset(render, 0, sizeof(*render));
    render->path = "";
    render->stat_errno = ENOTSUP;
}


void a90_doomgeneric_bridge_get_status(
        struct a90_doomgeneric_bridge_status *status) {
    if (status == NULL) {
        return;
    }
    memset(status, 0, sizeof(*status));
    status->candidate = "phase3-minimal-b-inert-doom-surface";
    status->engine = "disabled-no-runtime";
    status->helper_path = "";
    status->runtime_wad_root = "";
    status->runtime_wad_path = "";
    status->expected_wad_sha256 = "";
    status->frame_path = "";
    status->shared_frame_path = "";
    status->input_state_path = "";
    status->input_socket_path = "";
    status->pace_socket_path = "";
    status->input_path = "disabled";
    status->sound_mode = "disabled";
}


int a90_doomgeneric_bridge_probe(int timeout_ms,
                                 struct a90_run_result *result) {
    (void)timeout_ms;
    inert_run_result(result);
    return -ENOTSUP;
}


int a90_doomgeneric_bridge_verify_wad(
        const char *expected_sha256,
        struct a90_doomgeneric_wad_check *check) {
    inert_wad_check(expected_sha256, check);
    return -ENOTSUP;
}


int a90_doomgeneric_bridge_play(int frames,
                                const char *expected_sha256,
                                int timeout_ms,
                                struct a90_doomgeneric_wad_check *check,
                                struct a90_run_result *result) {
    (void)frames;
    (void)timeout_ms;
    inert_wad_check(expected_sha256, check);
    inert_run_result(result);
    return -ENOTSUP;
}


int a90_doomgeneric_bridge_render_frame(
        int frames,
        const char *expected_sha256,
        int timeout_ms,
        struct a90_doomgeneric_wad_check *check,
        struct a90_doomgeneric_frame_render *render,
        struct a90_run_result *result) {
    (void)frames;
    (void)timeout_ms;
    inert_wad_check(expected_sha256, check);
    inert_frame_render(render);
    inert_run_result(result);
    return -ENOTSUP;
}


int a90_doomgeneric_bridge_read_frame_render(
        struct a90_doomgeneric_frame_render *render) {
    inert_frame_render(render);
    return -ENOTSUP;
}


int a90_doomgeneric_bridge_write_input_state(
        const struct a90_doomgeneric_input_state *input) {
    (void)input;
    return -ENOTSUP;
}


int a90_doomgeneric_bridge_send_input_socket(
        const struct a90_doomgeneric_input_state *input) {
    (void)input;
    return -ENOTSUP;
}


int a90_doomgeneric_bridge_start_frame_loop_helper(
        int frames,
        const char *expected_sha256,
        int frame_ms,
        struct a90_doomgeneric_wad_check *check,
        pid_t *pid_out) {
    (void)frames;
    (void)frame_ms;
    inert_wad_check(expected_sha256, check);
    if (pid_out != NULL) {
        *pid_out = -1;
    }
    return -ENOTSUP;
}
