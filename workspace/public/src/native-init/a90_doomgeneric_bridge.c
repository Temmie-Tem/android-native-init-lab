#include "a90_doomgeneric_bridge.h"

#include "a90_run.h"

#include <errno.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef A90_DOOMGENERIC_BRIDGE_CANDIDATE
#define A90_DOOMGENERIC_BRIDGE_CANDIDATE "v3025-doomgeneric-command-bridge"
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_ENGINE
#define A90_DOOMGENERIC_BRIDGE_ENGINE "doomgeneric-private-link-v3025"
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_HELPER_PATH
#define A90_DOOMGENERIC_BRIDGE_HELPER_PATH "/bin/a90_doomgeneric_private_engine_v3024"
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT
#define A90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT "/cache/a90-runtime/pkg/doom/v3024/"
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_INPUT
#define A90_DOOMGENERIC_BRIDGE_INPUT "serial-doompad-to-DG_GetKey"
#endif

#ifndef A90_DOOMGENERIC_BRIDGE_SOUND
#define A90_DOOMGENERIC_BRIDGE_SOUND "disabled-nosound-nomusic"
#endif

static bool doomgeneric_helper_present(const char *path) {
    struct stat st;

    if (path == NULL || path[0] == '\0') {
        return false;
    }
    if (lstat(path, &st) < 0) {
        return false;
    }
    return S_ISREG(st.st_mode);
}

static bool doomgeneric_helper_executable(const char *path) {
    if (!doomgeneric_helper_present(path)) {
        return false;
    }
    return access(path, X_OK) == 0;
}

void a90_doomgeneric_bridge_get_status(struct a90_doomgeneric_bridge_status *status) {
    if (status == NULL) {
        return;
    }
    memset(status, 0, sizeof(*status));
    status->candidate = A90_DOOMGENERIC_BRIDGE_CANDIDATE;
    status->engine = A90_DOOMGENERIC_BRIDGE_ENGINE;
    status->helper_path = A90_DOOMGENERIC_BRIDGE_HELPER_PATH;
    status->runtime_wad_root = A90_DOOMGENERIC_BRIDGE_RUNTIME_WAD_ROOT;
    status->input_path = A90_DOOMGENERIC_BRIDGE_INPUT;
    status->sound_mode = A90_DOOMGENERIC_BRIDGE_SOUND;
    status->helper_present = doomgeneric_helper_present(status->helper_path);
    status->helper_executable = doomgeneric_helper_executable(status->helper_path);
    status->wad_embedded_in_boot = false;
}

int a90_doomgeneric_bridge_probe(int timeout_ms, struct a90_run_result *result) {
    struct a90_run_result local_result;
    struct a90_doomgeneric_bridge_status status;
    struct a90_run_config config;
    char *const argv[] = {
        (char *)A90_DOOMGENERIC_BRIDGE_HELPER_PATH,
        NULL,
    };
    pid_t pid = -1;
    int rc;

    if (result == NULL) {
        result = &local_result;
    }
    memset(result, 0, sizeof(*result));
    a90_doomgeneric_bridge_get_status(&status);
    if (!status.helper_executable) {
        if (result != NULL) {
            result->rc = -ENOENT;
            result->saved_errno = ENOENT;
        }
        return -ENOENT;
    }
    if (timeout_ms <= 0) {
        timeout_ms = 3000;
    }

    memset(&config, 0, sizeof(config));
    config.tag = "doomgeneric-probe";
    config.argv = argv;
    config.stdio_mode = A90_RUN_STDIO_NULL;
    config.setsid = true;
    config.kill_process_group = true;
    config.timeout_ms = timeout_ms;
    config.stop_timeout_ms = 1000;

    rc = a90_run_spawn(&config, &pid);
    if (rc < 0) {
        if (result != NULL) {
            result->rc = rc;
            result->saved_errno = -rc;
        }
        return rc;
    }
    rc = a90_run_wait(pid, &config, result);
    if (rc < 0) {
        return rc;
    }
    return result->rc;
}
