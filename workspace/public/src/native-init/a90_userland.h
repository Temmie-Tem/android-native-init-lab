#ifndef A90_USERLAND_H
#define A90_USERLAND_H

#include <stdbool.h>
#include <stddef.h>
#include <limits.h>

#define A90_USERLAND_MAX_ENTRIES 4

enum a90_userland_kind {
    A90_USERLAND_BUSYBOX = 0,
    A90_USERLAND_TOYBOX,
};

struct a90_userland_entry {
    enum a90_userland_kind kind;
    char name[32];
    char selected_path[PATH_MAX];
    char runtime_path[PATH_MAX];
    char fallback_path[PATH_MAX];
    bool present;
    bool executable;
    bool fallback_present;
    long long size;
    char warning[160];
};

int a90_userland_scan(void);
int a90_userland_count(void);
int a90_userland_entry_at(int index, struct a90_userland_entry *out);
int a90_userland_find(const char *name, struct a90_userland_entry *out);
const char *a90_userland_path(const char *name);
void a90_userland_summary(char *out, size_t out_size);
bool a90_userland_has_busybox(void);
bool a90_userland_has_any(void);
int a90_userland_print_inventory(bool verbose);

#endif
