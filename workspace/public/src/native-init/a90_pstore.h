#ifndef A90_PSTORE_H
#define A90_PSTORE_H

#include <stdbool.h>
#include <stddef.h>

struct a90_pstore_snapshot {
    bool fs_pstore;
    bool mount_pstore;
    bool pstore_dir;
    int entry_count;
    int dmesg_entries;
    int console_entries;
    int ftrace_entries;
    int pmsg_entries;
    bool cmdline_pstore;
    bool cmdline_ramoops;
    bool cmdline_sec_debug;
    bool ramoops_module_dir;
    int ramoops_parameters;
};

int a90_pstore_collect(struct a90_pstore_snapshot *out);
void a90_pstore_summary(char *out, size_t out_size);
int a90_pstore_print_summary(void);
int a90_pstore_print_full(void);
int a90_pstore_print_paths(void);
int a90_pstore_cmd(char **argv, int argc);

#endif
