#ifndef A90_KERNELINV_H
#define A90_KERNELINV_H

#include <stdbool.h>
#include <stddef.h>
#include <sys/types.h>

struct a90_kernelinv_snapshot {
    bool proc_config_present;
    bool proc_config_gzip_magic;
    mode_t proc_config_mode;
    long proc_config_size;

    bool fs_pstore;
    bool fs_tracefs;
    bool fs_debugfs;
    bool fs_cgroup;
    bool fs_cgroup2;
    bool fs_bpf;

    bool mount_pstore;
    bool mount_tracefs;
    bool mount_debugfs;
    bool mount_configfs;
    bool mount_cgroup;
    bool mount_cgroup2;

    int cgroup_controllers;
    int cgroup_enabled;

    bool pstore_dir;
    int pstore_entries;

    bool tracefs_dir;
    int tracefs_entries;

    int thermal_zones;
    int cooling_devices;
    int power_supply_total;
    bool power_supply_battery;
    bool power_supply_usb;
    bool power_supply_wireless;
    int power_supply_chargers;

    int watchdog_class_devices;
    bool dev_watchdog;
    bool dev_watchdog0;

    bool usb_configfs;
    bool usb_gadget_dir;
    bool usb_acm_function;
    bool usb_acm_link;
    bool usb_adb_link;
    bool usb_udc_bound;
    char usb_udc[64];

    char kernel_release[256];
    char proc_cmdline[2048];
    bool proc_cmdline_truncated;
};

int a90_kernelinv_collect(struct a90_kernelinv_snapshot *out);
void a90_kernelinv_summary(char *out, size_t out_size);
int a90_kernelinv_print_summary(void);
int a90_kernelinv_print_full(void);
int a90_kernelinv_print_paths(void);
int a90_kernelinv_cmd(char **argv, int argc);

#endif
