#ifndef A90_RUNTIME_H
#define A90_RUNTIME_H

#include <stdbool.h>
#include <limits.h>

#include "a90_storage.h"

struct a90_runtime_status {
    bool initialized;
    bool fallback;
    bool writable;
    char backend[16];
    char root[PATH_MAX];
    char bin[PATH_MAX];
    char etc[PATH_MAX];
    char logs[PATH_MAX];
    char tmp[PATH_MAX];
    char state[PATH_MAX];
    char pkg[PATH_MAX];
    char run[PATH_MAX];
    char pkg_bin[PATH_MAX];
    char pkg_helpers[PATH_MAX];
    char pkg_services[PATH_MAX];
    char pkg_manifests[PATH_MAX];
    char state_services[PATH_MAX];
    char helper_manifest[PATH_MAX];
    char helper_state[PATH_MAX];
    char helper_deploy_log[PATH_MAX];
    char warning[160];
    char detail[192];
};

int a90_runtime_init(const struct a90_storage_status *storage);
int a90_runtime_get_status(struct a90_runtime_status *out);
const char *a90_runtime_root(void);
const char *a90_runtime_bin_dir(void);
const char *a90_runtime_log_dir(void);
const char *a90_runtime_tmp_dir(void);
const char *a90_runtime_state_dir(void);
const char *a90_runtime_warning(void);
bool a90_runtime_using_fallback(void);
int a90_runtime_cmd_runtime(void);

#endif
