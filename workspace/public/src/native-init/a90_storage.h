#ifndef A90_STORAGE_H
#define A90_STORAGE_H

#include <stdbool.h>
#include <limits.h>

struct a90_storage_status {
    bool probed;
    bool sd_present;
    bool sd_mounted;
    bool sd_expected;
    bool sd_rw_ok;
    bool fallback;
    char backend[16];
    char root[PATH_MAX];
    char sd_uuid[40];
    char warning[128];
    char detail[160];
};

struct a90_storage_boot_hooks {
    void (*set_line)(void *ctx, int line, const char *text);
    void (*draw_frame)(void *ctx);
};

int a90_storage_mount_cache(void);
void a90_storage_set_cache_ready(bool ready);
int a90_storage_probe_boot(const struct a90_storage_boot_hooks *hooks, void *ctx);
int a90_storage_get_status(struct a90_storage_status *out);
const char *a90_storage_root(void);
const char *a90_storage_backend(void);
const char *a90_storage_warning(void);
bool a90_storage_using_fallback(void);
int a90_storage_cmd_storage(void);
int a90_storage_cmd_mountsd(char **argv, int argc);

#endif
