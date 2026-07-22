// SPDX-License-Identifier: MIT
/* P2.33 E1A/E1B wrapper over the pinned R4W1-E runtime primitives. */

#ifndef S22PLUS_FYG8_P233_PROFILE
#error "S22PLUS_FYG8_P233_PROFILE must select E1A=1 or E1B=2"
#endif

#if S22PLUS_FYG8_P233_PROFILE != 1 && S22PLUS_FYG8_P233_PROFILE != 2
#error "S22PLUS_FYG8_P233_PROFILE must select E1A=1 or E1B=2"
#endif

#ifndef S22PLUS_FYG8_P233_RUN_ID_BYTES
#error "S22PLUS_FYG8_P233_RUN_ID_BYTES must be supplied by the host build"
#endif

#define S22_R4W1E_E1_RUN_ID_BYTES S22PLUS_FYG8_P233_RUN_ID_BYTES
#define e1_run s22_p233_included_e1b_run
#define _start s22_p233_included_start
#include "s22plus_r4w1e_e1_runtime.c"
#undef _start
#undef e1_run

#define S22_P233_STAGE_E1A_SUCCESS 0x2fU

#if S22PLUS_FYG8_P233_PROFILE == 1
__attribute__((noreturn)) static void s22_p233_run(void) {
    struct child_session child = {.pid = -1, .token_fd = -1, .exec_fd = -1};
    E1_REQUIRE(S22_R4W1E_STAGE_PROC_MOUNTED, 0U, mount_proc());
    E1_REQUIRE(S22_R4W1E_STAGE_SYS_MOUNTED, 0U, mount_sys());
    E1_REQUIRE(S22_R4W1E_STAGE_DEV_TMPFS_MOUNTED, 0U, mount_dev());
    E1_REQUIRE(S22_R4W1E_STAGE_RUN_TMPFS_MOUNTED, 0U, mount_run());
    E1_REQUIRE(
        S22_R4W1E_STAGE_DEV_NODES_VERIFIED,
        0U,
        setup_and_verify_dev_null());
    E1_REQUIRE(
        S22_R4W1E_STAGE_CHILD_EXEC_STARTED, 0U, child_start(&child));
    E1_REQUIRE(
        S22_R4W1E_STAGE_CHILD_TOKEN_VERIFIED,
        0U,
        child_verify_token(&child));
    E1_REQUIRE(S22_R4W1E_STAGE_CHILD_REAPED, 0U, child_reap(&child));
    if (s22_r4w1e_checkpoint_success(&g_checkpoint) != 0) {
        quiet_park();
    }
    quiet_park();
}
#else
__attribute__((noreturn)) static void s22_p233_run(void) {
    s22_p233_included_e1b_run();
}
#endif

__attribute__((noreturn)) void _start(void) {
    if (sys_getpid() != 1) {
        quiet_park();
    }
    if (s22_r4w1e_checkpoint_client_init(&g_checkpoint, k_run_id) != 0) {
        quiet_park();
    }
    s22_p233_run();
}
