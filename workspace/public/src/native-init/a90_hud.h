#ifndef A90_HUD_H
#define A90_HUD_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "a90_kms.h"
#include "a90_metrics.h"

/*
 * Compatibility for retained v88/v89 source snapshots. New code should use
 * a90_metrics_* directly.
 */
#define a90_hud_status_snapshot a90_metrics_snapshot
static inline int a90_hud_read_sysfs_long(const char *path, long *value_out) {
    return a90_metrics_read_sysfs_long(path, value_out);
}
static inline void a90_hud_read_status_snapshot(struct a90_hud_status_snapshot *snapshot) {
    a90_metrics_read_snapshot(snapshot);
}

struct a90_hud_storage_status {
    const char *backend;
    const char *root;
    const char *warning;
};

void a90_hud_boot_splash_set_line(size_t index, const char *fmt, ...);
void a90_hud_draw_boot_splash(struct a90_fb *fb);
void a90_hud_draw_status_overlay(struct a90_fb *fb,
                                 const struct a90_hud_storage_status *storage,
                                 unsigned int refresh_sec,
                                 unsigned int sequence);
int a90_hud_draw_status_frame(const struct a90_hud_storage_status *storage,
                              const char *label,
                              bool verbose);
void a90_hud_draw_log_tail_panel(struct a90_fb *fb,
                                 uint32_t x,
                                 uint32_t y,
                                 uint32_t width,
                                 uint32_t bottom,
                                 int max_lines,
                                 const char *title,
                                 uint32_t scale);
void a90_hud_draw_hud_log_tail(struct a90_fb *fb);
bool a90_hud_log_tail_enabled(void);
int a90_hud_set_log_tail_enabled(bool enabled);

#endif
