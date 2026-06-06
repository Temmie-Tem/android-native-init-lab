#ifndef A90_HELPER_H
#define A90_HELPER_H

#include <stdbool.h>
#include <stddef.h>
#include <limits.h>

#define A90_HELPER_MAX_ENTRIES 16

struct a90_helper_entry {
    char name[64];
    char path[PATH_MAX];
    char fallback[PATH_MAX];
    char preferred[PATH_MAX];
    char role[64];
    char expected_sha256[65];
    char actual_sha256[65];
    unsigned int expected_mode;
    unsigned int actual_mode;
    long long expected_size;
    long long actual_size;
    bool present;
    bool fallback_present;
    bool executable;
    bool hash_checked;
    bool hash_match;
    bool required;
    bool manifest_entry;
    bool manifest_path_allowed;
    bool manifest_sha_valid;
    char warning[160];
};

int a90_helper_scan(void);
int a90_helper_count(void);
int a90_helper_entry_at(int index, struct a90_helper_entry *out);
int a90_helper_find(const char *name, struct a90_helper_entry *out);
const char *a90_helper_manifest_path(void);
const char *a90_helper_deploy_log_path(void);
const char *a90_helper_preferred_path(const char *name, const char *fallback);
void a90_helper_summary(char *out, size_t out_size);
bool a90_helper_has_failures(void);
bool a90_helper_has_warnings(void);
int a90_helper_print_inventory(bool verbose);
int a90_helper_print_manifest_template(void);
int a90_helper_cmd_helpers(char **argv, int argc);

#endif
