#ifndef A90_TIMELINE_H
#define A90_TIMELINE_H

#include <stddef.h>

struct a90_timeline_entry {
    long ms;
    char step[32];
    int code;
    int saved_errno;
    char detail[128];
};

void a90_timeline_record(int code, int saved_errno, const char *step, const char *fmt, ...);
void a90_timeline_replay_to_log(const char *reason);
void a90_timeline_probe_path(const char *step, const char *path);
void a90_timeline_probe_boot_resources(void);
void a90_timeline_boot_summary(char *out, size_t out_size);
size_t a90_timeline_count(void);
const struct a90_timeline_entry *a90_timeline_entry_at(size_t index);

#endif
