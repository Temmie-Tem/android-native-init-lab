#include "a90_kernelinv.h"

#include "a90_console.h"
#include "a90_usb_gadget.h"
#include "a90_util.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

static const char *yesno(bool value) {
    return value ? "yes" : "no";
}

static bool path_exists_lstat(const char *path) {
    struct stat st;

    return lstat(path, &st) == 0;
}

static bool path_is_dir(const char *path) {
    struct stat st;

    return lstat(path, &st) == 0 && S_ISDIR(st.st_mode);
}

static int count_dir_entries_with_prefix(const char *path, const char *prefix) {
    DIR *dir;
    struct dirent *entry;
    int count = 0;
    size_t prefix_len = strlen(prefix);

    dir = opendir(path);
    if (dir == NULL) {
        return 0;
    }

    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        if (prefix_len == 0 || strncmp(entry->d_name, prefix, prefix_len) == 0) {
            ++count;
        }
    }

    closedir(dir);
    return count;
}

static int count_dir_entries(const char *path) {
    return count_dir_entries_with_prefix(path, "");
}

static bool text_file_contains_word(const char *path, const char *needle) {
    char buf[4096];

    if (read_text_file(path, buf, sizeof(buf)) < 0) {
        return false;
    }
    return strstr(buf, needle) != NULL;
}

static bool proc_filesystems_has(const char *name) {
    char needle[64];

    snprintf(needle, sizeof(needle), "%s", name);
    needle[sizeof(needle) - 1] = '\0';
    return text_file_contains_word("/proc/filesystems", needle);
}

static bool proc_mounts_has_type(const char *type) {
    char buf[4096];
    char needle[96];

    if (read_text_file("/proc/mounts", buf, sizeof(buf)) < 0) {
        return false;
    }
    snprintf(needle, sizeof(needle), " %s ", type);
    needle[sizeof(needle) - 1] = '\0';
    return strstr(buf, needle) != NULL;
}

static void read_proc_config(struct a90_kernelinv_snapshot *out) {
    struct stat st;
    unsigned char magic[2] = { 0, 0 };
    int fd;

    if (stat("/proc/config.gz", &st) < 0) {
        return;
    }

    out->proc_config_present = true;
    out->proc_config_mode = st.st_mode & 0777;
    out->proc_config_size = (long)st.st_size;

    fd = open("/proc/config.gz", O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return;
    }
    if (read(fd, magic, sizeof(magic)) == (ssize_t)sizeof(magic)) {
        out->proc_config_gzip_magic = magic[0] == 0x1f && magic[1] == 0x8b;
    }
    close(fd);
}

static void read_proc_cmdline(struct a90_kernelinv_snapshot *out) {
    int fd;
    ssize_t rd;

    snprintf(out->proc_cmdline, sizeof(out->proc_cmdline), "unreadable");
    fd = open("/proc/cmdline", O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return;
    }
    rd = read(fd, out->proc_cmdline, sizeof(out->proc_cmdline) - 1);
    if (rd < 0) {
        close(fd);
        snprintf(out->proc_cmdline, sizeof(out->proc_cmdline), "unreadable");
        return;
    }
    out->proc_cmdline[rd] = '\0';
    trim_newline(out->proc_cmdline);
    if ((size_t)rd == sizeof(out->proc_cmdline) - 1) {
        char extra;

        if (read(fd, &extra, 1) == 1) {
            out->proc_cmdline_truncated = true;
        }
    }
    close(fd);
}

static void read_cgroups(struct a90_kernelinv_snapshot *out) {
    char buf[4096];
    char *line;
    char *saveptr = NULL;

    if (read_text_file("/proc/cgroups", buf, sizeof(buf)) < 0) {
        return;
    }

    line = strtok_r(buf, "\n", &saveptr);
    while (line != NULL) {
        char name[64];
        int hierarchy;
        int num_cgroups;
        int enabled;

        if (line[0] != '#' &&
            sscanf(line, "%63s %d %d %d", name, &hierarchy, &num_cgroups, &enabled) == 4) {
            (void)hierarchy;
            (void)num_cgroups;
            ++out->cgroup_controllers;
            if (enabled != 0) {
                ++out->cgroup_enabled;
            }
        }
        line = strtok_r(NULL, "\n", &saveptr);
    }
}

static bool name_contains(const char *name, const char *needle) {
    size_t name_len = strlen(name);
    size_t needle_len = strlen(needle);
    size_t offset;

    if (needle_len == 0 || needle_len > name_len) {
        return false;
    }
    for (offset = 0; offset + needle_len <= name_len; ++offset) {
        size_t index;
        bool matched = true;

        for (index = 0; index < needle_len; ++index) {
            char lhs = name[offset + index];
            char rhs = needle[index];

            if (lhs >= 'A' && lhs <= 'Z') {
                lhs = (char)(lhs - 'A' + 'a');
            }
            if (rhs >= 'A' && rhs <= 'Z') {
                rhs = (char)(rhs - 'A' + 'a');
            }
            if (lhs != rhs) {
                matched = false;
                break;
            }
        }
        if (matched) {
            return true;
        }
    }
    return false;
}

static void read_power_supply(struct a90_kernelinv_snapshot *out) {
    DIR *dir;
    struct dirent *entry;

    dir = opendir("/sys/class/power_supply");
    if (dir == NULL) {
        return;
    }

    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        ++out->power_supply_total;
        if (strcmp(entry->d_name, "battery") == 0) {
            out->power_supply_battery = true;
        }
        if (strcmp(entry->d_name, "usb") == 0) {
            out->power_supply_usb = true;
        }
        if (strcmp(entry->d_name, "wireless") == 0) {
            out->power_supply_wireless = true;
        }
        if (name_contains(entry->d_name, "charger") || strcmp(entry->d_name, "ac") == 0) {
            ++out->power_supply_chargers;
        }
    }

    closedir(dir);
}

static void read_usb_status(struct a90_kernelinv_snapshot *out) {
    struct a90_usb_gadget_status status;

    if (a90_usb_gadget_status(&status) < 0) {
        return;
    }

    out->usb_configfs = status.configfs_mounted;
    out->usb_gadget_dir = status.gadget_dir;
    out->usb_acm_function = status.acm_function;
    out->usb_acm_link = status.acm_link;
    out->usb_adb_link = status.adb_link;
    out->usb_udc_bound = status.udc_bound;
    snprintf(out->usb_udc, sizeof(out->usb_udc), "%s", status.udc);
    out->usb_udc[sizeof(out->usb_udc) - 1] = '\0';
}

static void print_wrapped_value(const char *label, const char *value) {
    size_t offset = 0;
    size_t value_len;

    if (value == NULL || value[0] == '\0') {
        a90_console_printf("%s: -\r\n", label);
        return;
    }

    value_len = strlen(value);
    a90_console_printf("%s:\r\n", label);
    while (offset < value_len) {
        char chunk[161];
        size_t chunk_len = value_len - offset;

        if (chunk_len > sizeof(chunk) - 1) {
            chunk_len = sizeof(chunk) - 1;
        }
        memcpy(chunk, value + offset, chunk_len);
        chunk[chunk_len] = '\0';
        a90_console_printf("  %s\r\n", chunk);
        offset += chunk_len;
    }
}

int a90_kernelinv_collect(struct a90_kernelinv_snapshot *out) {
    struct utsname uts;

    if (out == NULL) {
        return -EINVAL;
    }

    memset(out, 0, sizeof(*out));

    if (uname(&uts) == 0) {
        snprintf(out->kernel_release, sizeof(out->kernel_release), "%s %s %s",
                 uts.sysname, uts.release, uts.machine);
        out->kernel_release[sizeof(out->kernel_release) - 1] = '\0';
    }
    read_proc_cmdline(out);

    read_proc_config(out);

    out->fs_pstore = proc_filesystems_has("pstore");
    out->fs_tracefs = proc_filesystems_has("tracefs");
    out->fs_debugfs = proc_filesystems_has("debugfs");
    out->fs_cgroup = proc_filesystems_has("cgroup");
    out->fs_cgroup2 = proc_filesystems_has("cgroup2");
    out->fs_bpf = proc_filesystems_has("bpf");

    out->mount_pstore = proc_mounts_has_type("pstore");
    out->mount_tracefs = proc_mounts_has_type("tracefs");
    out->mount_debugfs = proc_mounts_has_type("debugfs");
    out->mount_configfs = proc_mounts_has_type("configfs");
    out->mount_cgroup = proc_mounts_has_type("cgroup");
    out->mount_cgroup2 = proc_mounts_has_type("cgroup2");

    read_cgroups(out);

    out->pstore_dir = path_is_dir("/sys/fs/pstore");
    out->pstore_entries = count_dir_entries("/sys/fs/pstore");
    out->tracefs_dir = path_is_dir("/sys/kernel/tracing");
    out->tracefs_entries = count_dir_entries("/sys/kernel/tracing");

    out->thermal_zones = count_dir_entries_with_prefix("/sys/class/thermal", "thermal_zone");
    out->cooling_devices = count_dir_entries_with_prefix("/sys/class/thermal", "cooling_device");
    read_power_supply(out);

    out->watchdog_class_devices = count_dir_entries_with_prefix("/sys/class/watchdog", "watchdog");
    out->dev_watchdog = path_exists_lstat("/dev/watchdog");
    out->dev_watchdog0 = path_exists_lstat("/dev/watchdog0");

    read_usb_status(out);

    return 0;
}

void a90_kernelinv_summary(char *out, size_t out_size) {
    struct a90_kernelinv_snapshot snapshot;

    if (out == NULL || out_size == 0) {
        return;
    }
    if (a90_kernelinv_collect(&snapshot) < 0) {
        snprintf(out, out_size, "kernelinv=error");
        return;
    }

    snprintf(out, out_size,
             "kernelinv=config=%s pstore=%s/%s tracefs=%s/%s thermal=%d power=%d watchdog=%d usb=%s",
             yesno(snapshot.proc_config_present),
             yesno(snapshot.fs_pstore),
             yesno(snapshot.mount_pstore),
             yesno(snapshot.fs_tracefs),
             yesno(snapshot.mount_tracefs),
             snapshot.thermal_zones,
             snapshot.power_supply_total,
             snapshot.watchdog_class_devices,
             yesno(snapshot.usb_udc_bound));
    out[out_size - 1] = '\0';
}

int a90_kernelinv_print_summary(void) {
    char summary[256];

    a90_kernelinv_summary(summary, sizeof(summary));
    a90_console_printf("%s\r\n", summary);
    return 0;
}

int a90_kernelinv_print_full(void) {
    struct a90_kernelinv_snapshot snapshot;

    if (a90_kernelinv_collect(&snapshot) < 0) {
        a90_console_printf("kernelinv: collect failed\r\n");
        return negative_errno_or(EIO);
    }

    a90_console_printf("[kernelinv]\r\n");
    a90_console_printf("kernel: %s\r\n", snapshot.kernel_release[0] ? snapshot.kernel_release : "unknown");
    a90_console_printf("cmdline_truncated: %s\r\n", yesno(snapshot.proc_cmdline_truncated));
    print_wrapped_value("cmdline", snapshot.proc_cmdline);
    a90_console_printf("config.gz: present=%s mode=0%03o size=%ld gzip=%s\r\n",
                       yesno(snapshot.proc_config_present),
                       (unsigned)snapshot.proc_config_mode,
                       snapshot.proc_config_size,
                       yesno(snapshot.proc_config_gzip_magic));
    a90_console_printf("filesystems: pstore=%s tracefs=%s debugfs=%s cgroup=%s cgroup2=%s bpf=%s\r\n",
                       yesno(snapshot.fs_pstore),
                       yesno(snapshot.fs_tracefs),
                       yesno(snapshot.fs_debugfs),
                       yesno(snapshot.fs_cgroup),
                       yesno(snapshot.fs_cgroup2),
                       yesno(snapshot.fs_bpf));
    a90_console_printf("mounts: pstore=%s tracefs=%s debugfs=%s configfs=%s cgroup=%s cgroup2=%s\r\n",
                       yesno(snapshot.mount_pstore),
                       yesno(snapshot.mount_tracefs),
                       yesno(snapshot.mount_debugfs),
                       yesno(snapshot.mount_configfs),
                       yesno(snapshot.mount_cgroup),
                       yesno(snapshot.mount_cgroup2));
    a90_console_printf("cgroup: controllers=%d enabled=%d\r\n",
                       snapshot.cgroup_controllers,
                       snapshot.cgroup_enabled);
    a90_console_printf("pstore: dir=%s entries=%d mounted=%s\r\n",
                       yesno(snapshot.pstore_dir),
                       snapshot.pstore_entries,
                       yesno(snapshot.mount_pstore));
    a90_console_printf("tracefs: dir=%s entries=%d mounted=%s\r\n",
                       yesno(snapshot.tracefs_dir),
                       snapshot.tracefs_entries,
                       yesno(snapshot.mount_tracefs));
    a90_console_printf("thermal: zones=%d cooling=%d\r\n",
                       snapshot.thermal_zones,
                       snapshot.cooling_devices);
    a90_console_printf("power_supply: total=%d battery=%s usb=%s wireless=%s chargers=%d\r\n",
                       snapshot.power_supply_total,
                       yesno(snapshot.power_supply_battery),
                       yesno(snapshot.power_supply_usb),
                       yesno(snapshot.power_supply_wireless),
                       snapshot.power_supply_chargers);
    a90_console_printf("watchdog: class=%d dev_watchdog=%s dev_watchdog0=%s policy=read-only-no-open\r\n",
                       snapshot.watchdog_class_devices,
                       yesno(snapshot.dev_watchdog),
                       yesno(snapshot.dev_watchdog0));
    a90_console_printf("usb_gadget: configfs=%s gadget=%s acm_function=%s acm_link=%s adb_link=%s udc_bound=%s udc=%s\r\n",
                       yesno(snapshot.usb_configfs),
                       yesno(snapshot.usb_gadget_dir),
                       yesno(snapshot.usb_acm_function),
                       yesno(snapshot.usb_acm_link),
                       yesno(snapshot.usb_adb_link),
                       yesno(snapshot.usb_udc_bound),
                       snapshot.usb_udc[0] ? snapshot.usb_udc : "-");
    return 0;
}

int a90_kernelinv_print_paths(void) {
    static const char *const paths[] = {
        "/proc/config.gz",
        "/proc/filesystems",
        "/proc/mounts",
        "/proc/cgroups",
        "/proc/cmdline",
        "/sys/fs/pstore",
        "/sys/kernel/tracing",
        "/sys/class/watchdog",
        "/sys/class/thermal",
        "/sys/class/power_supply",
        "/config/usb_gadget/g1",
        "/config/usb_gadget/g1/functions",
        "/config/usb_gadget/g1/configs/b.1",
    };
    size_t index;

    a90_console_printf("[kernelinv paths]\r\n");
    for (index = 0; index < sizeof(paths) / sizeof(paths[0]); ++index) {
        a90_console_printf("%s: %s\r\n", paths[index], yesno(path_exists_lstat(paths[index])));
    }
    return 0;
}

int a90_kernelinv_cmd(char **argv, int argc) {
    const char *mode = argc > 1 ? argv[1] : "summary";

    if (argc > 2) {
        a90_console_printf("usage: kernelinv [summary|full|paths]\r\n");
        return -EINVAL;
    }
    if (strcmp(mode, "summary") == 0 || strcmp(mode, "status") == 0) {
        return a90_kernelinv_print_summary();
    }
    if (strcmp(mode, "full") == 0) {
        return a90_kernelinv_print_full();
    }
    if (strcmp(mode, "paths") == 0) {
        return a90_kernelinv_print_paths();
    }

    a90_console_printf("usage: kernelinv [summary|full|paths]\r\n");
    return -EINVAL;
}
