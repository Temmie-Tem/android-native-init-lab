#include "a90_pstore.h"

#include "a90_console.h"
#include "a90_util.h"

#include <dirent.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

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

static bool text_file_contains(const char *path, const char *needle) {
    char buf[4096];

    if (read_text_file(path, buf, sizeof(buf)) < 0) {
        return false;
    }
    return strstr(buf, needle) != NULL;
}

static bool proc_filesystems_has(const char *name) {
    return text_file_contains("/proc/filesystems", name);
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

static bool proc_cmdline_has(const char *needle) {
    return text_file_contains("/proc/cmdline", needle);
}

static void count_pstore_entries(struct a90_pstore_snapshot *out) {
    DIR *dir;
    struct dirent *entry;

    dir = opendir("/sys/fs/pstore");
    if (dir == NULL) {
        return;
    }

    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        ++out->entry_count;
        if (strncmp(entry->d_name, "dmesg", 5) == 0) {
            ++out->dmesg_entries;
        } else if (strncmp(entry->d_name, "console", 7) == 0) {
            ++out->console_entries;
        } else if (strncmp(entry->d_name, "ftrace", 6) == 0) {
            ++out->ftrace_entries;
        } else if (strncmp(entry->d_name, "pmsg", 4) == 0) {
            ++out->pmsg_entries;
        }
    }

    closedir(dir);
}

static int count_dir_entries(const char *path) {
    DIR *dir;
    struct dirent *entry;
    int count = 0;

    dir = opendir(path);
    if (dir == NULL) {
        return 0;
    }

    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") != 0 && strcmp(entry->d_name, "..") != 0) {
            ++count;
        }
    }

    closedir(dir);
    return count;
}

int a90_pstore_collect(struct a90_pstore_snapshot *out) {
    if (out == NULL) {
        return -EINVAL;
    }

    memset(out, 0, sizeof(*out));
    out->fs_pstore = proc_filesystems_has("pstore");
    out->mount_pstore = proc_mounts_has_type("pstore");
    out->pstore_dir = path_is_dir("/sys/fs/pstore");
    count_pstore_entries(out);
    out->cmdline_pstore = proc_cmdline_has("pstore");
    out->cmdline_ramoops = proc_cmdline_has("ramoops");
    out->cmdline_sec_debug = proc_cmdline_has("sec_debug") || proc_cmdline_has("sec_log");
    out->ramoops_module_dir = path_is_dir("/sys/module/ramoops");
    out->ramoops_parameters = count_dir_entries("/sys/module/ramoops/parameters");
    return 0;
}

void a90_pstore_summary(char *out, size_t out_size) {
    struct a90_pstore_snapshot snapshot;

    if (out == NULL || out_size == 0) {
        return;
    }
    if (a90_pstore_collect(&snapshot) < 0) {
        snprintf(out, out_size, "pstore=error");
        return;
    }
    snprintf(out, out_size,
             "pstore=fs=%s mounted=%s dir=%s entries=%d ramoops_cmdline=%s module=%s params=%d",
             yesno(snapshot.fs_pstore),
             yesno(snapshot.mount_pstore),
             yesno(snapshot.pstore_dir),
             snapshot.entry_count,
             yesno(snapshot.cmdline_ramoops),
             yesno(snapshot.ramoops_module_dir),
             snapshot.ramoops_parameters);
    out[out_size - 1] = '\0';
}

int a90_pstore_print_summary(void) {
    char summary[192];

    a90_pstore_summary(summary, sizeof(summary));
    a90_console_printf("%s\r\n", summary);
    return 0;
}

int a90_pstore_print_full(void) {
    struct a90_pstore_snapshot snapshot;

    if (a90_pstore_collect(&snapshot) < 0) {
        a90_console_printf("pstore: collect failed\r\n");
        return negative_errno_or(EIO);
    }

    a90_console_printf("[pstore feasibility]\r\n");
    a90_console_printf("policy: read-only; no pstore mount, no reboot persistence test\r\n");
    a90_console_printf("support: fs_pstore=%s mounted=%s dir=%s entries=%d\r\n",
                       yesno(snapshot.fs_pstore),
                       yesno(snapshot.mount_pstore),
                       yesno(snapshot.pstore_dir),
                       snapshot.entry_count);
    a90_console_printf("entries: dmesg=%d console=%d ftrace=%d pmsg=%d other=%d\r\n",
                       snapshot.dmesg_entries,
                       snapshot.console_entries,
                       snapshot.ftrace_entries,
                       snapshot.pmsg_entries,
                       snapshot.entry_count - snapshot.dmesg_entries - snapshot.console_entries -
                               snapshot.ftrace_entries - snapshot.pmsg_entries);
    a90_console_printf("cmdline: pstore=%s ramoops=%s sec_debug_or_sec_log=%s\r\n",
                       yesno(snapshot.cmdline_pstore),
                       yesno(snapshot.cmdline_ramoops),
                       yesno(snapshot.cmdline_sec_debug));
    a90_console_printf("ramoops: module_dir=%s parameters=%d\r\n",
                       yesno(snapshot.ramoops_module_dir),
                       snapshot.ramoops_parameters);
    a90_console_printf("next: reboot-survival test requires explicit opt-in later\r\n");
    return 0;
}

int a90_pstore_print_paths(void) {
    static const char *const paths[] = {
        "/proc/filesystems",
        "/proc/mounts",
        "/proc/cmdline",
        "/sys/fs/pstore",
        "/sys/module/ramoops",
        "/sys/module/ramoops/parameters",
    };
    size_t index;

    a90_console_printf("[pstore paths]\r\n");
    for (index = 0; index < sizeof(paths) / sizeof(paths[0]); ++index) {
        a90_console_printf("%s: %s\r\n", paths[index], yesno(path_exists_lstat(paths[index])));
    }
    return 0;
}

int a90_pstore_cmd(char **argv, int argc) {
    const char *mode = argc > 1 ? argv[1] : "summary";

    if (argc > 2) {
        a90_console_printf("usage: pstore [summary|full|paths]\r\n");
        return -EINVAL;
    }
    if (strcmp(mode, "summary") == 0 || strcmp(mode, "status") == 0) {
        return a90_pstore_print_summary();
    }
    if (strcmp(mode, "full") == 0) {
        return a90_pstore_print_full();
    }
    if (strcmp(mode, "paths") == 0) {
        return a90_pstore_print_paths();
    }

    a90_console_printf("usage: pstore [summary|full|paths]\r\n");
    return -EINVAL;
}
