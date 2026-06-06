#include "a90_wifiinv.h"

#include "a90_config.h"
#include "a90_console.h"
#include "a90_log.h"
#include "a90_util.h"

#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define WIFIINV_MAX_PATH_SCAN_DEPTH 4
#define WIFIINV_MAX_FILE_MATCHES 180
#define WIFIINV_MAX_LINE 512
#define WIFIINV_BASELINE_NET_TOTAL 8
#define WIFIINV_BASELINE_WLAN_IFACES 0
#define WIFIINV_BASELINE_RFKILL_TOTAL 1
#define WIFIINV_BASELINE_RFKILL_WIFI 0
#define WIFIINV_BASELINE_MODULE_MATCHES 0
#define WIFIINV_BASELINE_DEFAULT_EXISTING_PATHS 6
#define WIFIINV_BASELINE_DEFAULT_FILE_MATCHES 0
#define WIFIINV_BASELINE_MOUNTED_EXISTING_PATHS 7
#define WIFIINV_BASELINE_MOUNTED_FILE_MATCHES 8

struct wifiinv_sink {
    bool console;
    int file_match_limit;
    int file_matches_printed;
};

static const char *const wifi_candidate_paths[] = {
    "/sys/class/net",
    "/sys/class/rfkill",
    "/sys/module",
    "/proc/modules",
    "/proc/cmdline",
    "/proc/device-tree",
    "/vendor",
    "/vendor/firmware",
    "/vendor/firmware_mnt",
    "/vendor/etc/wifi",
    "/vendor/bin",
    "/vendor/lib",
    "/vendor/lib64",
    "/odm/etc/wifi",
    "/product/etc/wifi",
    "/system/etc/wifi",
    "/mnt/system/vendor",
    "/mnt/system/vendor/firmware",
    "/mnt/system/vendor/firmware_mnt",
    "/mnt/system/vendor/etc/wifi",
    "/mnt/system/vendor/bin",
    "/mnt/system/vendor/lib",
    "/mnt/system/vendor/lib64",
    "/mnt/system/odm/etc/wifi",
    "/mnt/system/product/etc/wifi",
    "/mnt/system/system/etc/wifi",
};

static const char *const wifi_scan_roots[] = {
    "/vendor",
    "/vendor/firmware",
    "/vendor/firmware_mnt",
    "/vendor/etc",
    "/vendor/bin",
    "/vendor/lib",
    "/vendor/lib64",
    "/odm/etc",
    "/product/etc",
    "/system/etc",
    "/mnt/system/vendor",
    "/mnt/system/vendor/firmware",
    "/mnt/system/vendor/firmware_mnt",
    "/mnt/system/vendor/etc",
    "/mnt/system/vendor/bin",
    "/mnt/system/vendor/lib",
    "/mnt/system/vendor/lib64",
    "/mnt/system/odm/etc",
    "/mnt/system/product/etc",
    "/mnt/system/system/etc",
};

static const char *const wifi_patterns[] = {
    "wlan",
    "wifi",
    "WCNSS",
    "wcnss",
    "cnss",
    "qca",
    "qcacld",
    "ath",
    "bdwlan",
    "qwlan",
    "wlanmdsp",
    "Data.msc",
    "wpa_supplicant",
    "hostapd",
    "android.hardware.wifi",
    "vendor.qti.hardware.wifi",
};

static void wifi_emit(struct wifiinv_sink *sink, const char *fmt, ...) {
    char line[WIFIINV_MAX_LINE];
    va_list ap;
    int len;

    va_start(ap, fmt);
    len = vsnprintf(line, sizeof(line), fmt, ap);
    va_end(ap);

    if (len < 0) {
        return;
    }
    if (sink == NULL || sink->console) {
        a90_console_printf("%s", line);
    }
}

static const char *wifi_yesno(bool value) {
    return value ? "yes" : "no";
}

static const char *wifi_refresh_relation(const struct a90_wifiinv_snapshot *snapshot) {
    if (snapshot == NULL) {
        return "unknown";
    }
    if (snapshot->wlan_ifaces > 0 ||
        snapshot->rfkill_wifi > 0 ||
        snapshot->module_matches > 0) {
        return "kernel-gates-changed";
    }
    if (snapshot->net_total == WIFIINV_BASELINE_NET_TOTAL &&
        snapshot->wlan_ifaces == WIFIINV_BASELINE_WLAN_IFACES &&
        snapshot->rfkill_total == WIFIINV_BASELINE_RFKILL_TOTAL &&
        snapshot->rfkill_wifi == WIFIINV_BASELINE_RFKILL_WIFI &&
        snapshot->module_matches == WIFIINV_BASELINE_MODULE_MATCHES &&
        snapshot->existing_paths == WIFIINV_BASELINE_DEFAULT_EXISTING_PATHS &&
        snapshot->file_matches == WIFIINV_BASELINE_DEFAULT_FILE_MATCHES) {
        return "unchanged-native-default";
    }
    if (snapshot->existing_paths >= WIFIINV_BASELINE_MOUNTED_EXISTING_PATHS &&
        snapshot->file_matches >= WIFIINV_BASELINE_MOUNTED_FILE_MATCHES) {
        return "android-candidates-visible";
    }
    return "changed-review-required";
}

static bool wifi_contains_pattern(const char *text) {
    size_t text_len;
    size_t pattern_index;

    if (text == NULL) {
        return false;
    }

    text_len = strlen(text);
    for (pattern_index = 0;
         pattern_index < sizeof(wifi_patterns) / sizeof(wifi_patterns[0]);
         pattern_index++) {
        const char *pattern = wifi_patterns[pattern_index];
        size_t pattern_len = strlen(pattern);
        size_t offset;

        if (pattern_len == 0 || pattern_len > text_len) {
            continue;
        }
        for (offset = 0; offset + pattern_len <= text_len; offset++) {
            size_t i;
            bool match = true;

            for (i = 0; i < pattern_len; i++) {
                unsigned char a = (unsigned char)text[offset + i];
                unsigned char b = (unsigned char)pattern[i];

                if (tolower(a) != tolower(b)) {
                    match = false;
                    break;
                }
            }
            if (match) {
                return true;
            }
        }
    }

    return false;
}

static const char *wifi_file_kind(mode_t mode) {
    if (S_ISDIR(mode)) {
        return "dir";
    }
    if (S_ISLNK(mode)) {
        return "link";
    }
    if (S_ISREG(mode)) {
        return "file";
    }
    if (S_ISCHR(mode)) {
        return "char";
    }
    if (S_ISBLK(mode)) {
        return "block";
    }
    return "other";
}

static void wifi_read_attr(const char *path, const char *name, char *out, size_t out_size) {
    char attr_path[PATH_MAX];

    if (out == NULL || out_size == 0) {
        return;
    }
    out[0] = '\0';
    snprintf(attr_path, sizeof(attr_path), "%s/%s", path, name);
    if (read_trimmed_text_file(attr_path, out, out_size) < 0) {
        snprintf(out, out_size, "-");
    }
}

static int wifi_emit_net(struct wifiinv_sink *sink, struct a90_wifiinv_snapshot *snapshot, bool verbose) {
    DIR *dir = opendir("/sys/class/net");
    struct dirent *entry;

    if (verbose) {
        wifi_emit(sink, "[net]\r\n");
    }
    if (dir == NULL) {
        if (verbose) {
            wifi_emit(sink, "path=/sys/class/net readable=no errno=%d error=%s\r\n", errno, strerror(errno));
        }
        return negative_errno_or(ENOENT);
    }

    while ((entry = readdir(dir)) != NULL) {
        char iface_path[PATH_MAX];
        char address[80];
        char operstate[80];
        char ifindex[80];
        bool wlan_like;

        if (entry->d_name[0] == '.') {
            continue;
        }
        snapshot->net_total++;
        wlan_like = wifi_contains_pattern(entry->d_name);
        if (wlan_like) {
            snapshot->wlan_ifaces++;
        }
        if (!verbose) {
            continue;
        }

        snprintf(iface_path, sizeof(iface_path), "/sys/class/net/%s", entry->d_name);
        wifi_read_attr(iface_path, "address", address, sizeof(address));
        wifi_read_attr(iface_path, "operstate", operstate, sizeof(operstate));
        wifi_read_attr(iface_path, "ifindex", ifindex, sizeof(ifindex));
        wifi_emit(sink,
                  "iface=%s wlan_like=%s address=%s operstate=%s ifindex=%s\r\n",
                  entry->d_name,
                  wifi_yesno(wlan_like),
                  address,
                  operstate,
                  ifindex);
    }

    closedir(dir);
    return 0;
}

static int wifi_emit_rfkill(struct wifiinv_sink *sink, struct a90_wifiinv_snapshot *snapshot, bool verbose) {
    DIR *dir = opendir("/sys/class/rfkill");
    struct dirent *entry;

    if (verbose) {
        wifi_emit(sink, "[rfkill]\r\n");
    }
    if (dir == NULL) {
        if (verbose) {
            wifi_emit(sink, "path=/sys/class/rfkill readable=no errno=%d error=%s\r\n", errno, strerror(errno));
        }
        return negative_errno_or(ENOENT);
    }

    while ((entry = readdir(dir)) != NULL) {
        char rfkill_path[PATH_MAX];
        char name[96];
        char type[96];
        char state[32];
        char soft[32];
        char hard[32];
        bool wifi_like;

        if (entry->d_name[0] == '.') {
            continue;
        }
        snapshot->rfkill_total++;
        snprintf(rfkill_path, sizeof(rfkill_path), "/sys/class/rfkill/%s", entry->d_name);
        wifi_read_attr(rfkill_path, "name", name, sizeof(name));
        wifi_read_attr(rfkill_path, "type", type, sizeof(type));
        wifi_read_attr(rfkill_path, "state", state, sizeof(state));
        wifi_read_attr(rfkill_path, "soft", soft, sizeof(soft));
        wifi_read_attr(rfkill_path, "hard", hard, sizeof(hard));
        wifi_like = wifi_contains_pattern(name) || wifi_contains_pattern(type);
        if (wifi_like) {
            snapshot->rfkill_wifi++;
        }
        if (verbose) {
            wifi_emit(sink,
                      "node=%s name=%s type=%s wifi_like=%s state=%s soft=%s hard=%s\r\n",
                      entry->d_name,
                      name,
                      type,
                      wifi_yesno(wifi_like),
                      state,
                      soft,
                      hard);
        }
    }

    closedir(dir);
    return 0;
}

static int wifi_emit_modules(struct wifiinv_sink *sink, struct a90_wifiinv_snapshot *snapshot, bool verbose) {
    FILE *file = fopen("/proc/modules", "r");
    char line[WIFIINV_MAX_LINE];

    if (verbose) {
        wifi_emit(sink, "[modules]\r\n");
    }
    if (file == NULL) {
        if (verbose) {
            wifi_emit(sink, "path=/proc/modules readable=no errno=%d error=%s\r\n", errno, strerror(errno));
        }
        return negative_errno_or(ENOENT);
    }
    snapshot->proc_modules_readable = true;

    while (fgets(line, sizeof(line), file) != NULL) {
        trim_newline(line);
        if (!wifi_contains_pattern(line)) {
            continue;
        }
        snapshot->module_matches++;
        if (verbose) {
            wifi_emit(sink, "%s\r\n", line);
        }
    }

    fclose(file);
    return 0;
}

static void wifi_emit_candidate_paths(struct wifiinv_sink *sink, struct a90_wifiinv_snapshot *snapshot, bool verbose) {
    size_t index;

    if (verbose) {
        wifi_emit(sink, "[paths]\r\n");
    }

    for (index = 0;
         index < sizeof(wifi_candidate_paths) / sizeof(wifi_candidate_paths[0]);
         index++) {
        const char *path = wifi_candidate_paths[index];
        struct stat st;

        snapshot->candidate_paths++;
        if (lstat(path, &st) == 0) {
            snapshot->existing_paths++;
            if (verbose) {
                wifi_emit(sink, "exists=yes kind=%s path=%s\r\n", wifi_file_kind(st.st_mode), path);
            }
        } else if (verbose) {
            wifi_emit(sink, "exists=no path=%s errno=%d\r\n", path, errno);
        }
    }
}

static void wifi_scan_tree(struct wifiinv_sink *sink,
                           struct a90_wifiinv_snapshot *snapshot,
                           const char *path,
                           int depth,
                           bool verbose) {
    DIR *dir;
    struct dirent *entry;

    if (depth > WIFIINV_MAX_PATH_SCAN_DEPTH) {
        return;
    }
    dir = opendir(path);
    if (dir == NULL) {
        return;
    }

    while ((entry = readdir(dir)) != NULL) {
        char child[PATH_MAX];
        struct stat st;
        bool matched;

        if (entry->d_name[0] == '.') {
            continue;
        }
        snprintf(child, sizeof(child), "%s/%s", path, entry->d_name);
        if (lstat(child, &st) < 0) {
            continue;
        }

        matched = wifi_contains_pattern(entry->d_name) || wifi_contains_pattern(child);
        if (matched) {
            snapshot->file_matches++;
            if (verbose && sink != NULL && sink->file_matches_printed < sink->file_match_limit) {
                wifi_emit(sink, "match kind=%s path=%s\r\n", wifi_file_kind(st.st_mode), child);
                sink->file_matches_printed++;
            }
        }

        if (S_ISDIR(st.st_mode)) {
            wifi_scan_tree(sink, snapshot, child, depth + 1, verbose);
        }
    }

    closedir(dir);
}

static void wifi_emit_file_scan(struct wifiinv_sink *sink, struct a90_wifiinv_snapshot *snapshot, bool verbose) {
    size_t index;

    if (verbose) {
        wifi_emit(sink, "[files]\r\n");
    }

    for (index = 0; index < sizeof(wifi_scan_roots) / sizeof(wifi_scan_roots[0]); index++) {
        struct stat st;
        const char *root = wifi_scan_roots[index];

        if (lstat(root, &st) < 0 || !S_ISDIR(st.st_mode)) {
            continue;
        }
        if (verbose) {
            wifi_emit(sink, "scan_root=%s\r\n", root);
        }
        wifi_scan_tree(sink, snapshot, root, 0, verbose);
    }

    if (verbose && sink != NULL && snapshot->file_matches > sink->file_matches_printed) {
        wifi_emit(sink,
                  "matches_truncated printed=%d total=%d\r\n",
                  sink->file_matches_printed,
                  snapshot->file_matches);
    }
}

static int wifi_collect_into(struct wifiinv_sink *sink, struct a90_wifiinv_snapshot *snapshot, bool verbose) {
    memset(snapshot, 0, sizeof(*snapshot));
    (void)wifi_emit_net(sink, snapshot, verbose);
    (void)wifi_emit_rfkill(sink, snapshot, verbose);
    (void)wifi_emit_modules(sink, snapshot, verbose);
    wifi_emit_candidate_paths(sink, snapshot, verbose);
    wifi_emit_file_scan(sink, snapshot, verbose);
    return 0;
}

int a90_wifiinv_collect(struct a90_wifiinv_snapshot *out) {
    struct wifiinv_sink sink = { .console = false, .file_match_limit = 0, .file_matches_printed = 0 };

    if (out == NULL) {
        return -EINVAL;
    }
    return wifi_collect_into(&sink, out, false);
}

int a90_wifiinv_print_summary(void) {
    struct wifiinv_sink sink = {
        .console = true,
        .file_match_limit = 0,
        .file_matches_printed = 0,
    };
    struct a90_wifiinv_snapshot snapshot;
    int rc;

    rc = wifi_collect_into(&sink, &snapshot, false);
    if (rc < 0) {
        return rc;
    }

    wifi_emit(&sink, "[wifiinv]\r\n");
    wifi_emit(&sink, "banner=%s\r\n", INIT_BANNER);
    wifi_emit(&sink, "policy=read-only no-rfkill-write no-link-up no-module-change\r\n");
    wifi_emit(&sink,
              "net total=%d wlan_like=%d\r\n",
              snapshot.net_total,
              snapshot.wlan_ifaces);
    wifi_emit(&sink,
              "rfkill total=%d wifi_like=%d\r\n",
              snapshot.rfkill_total,
              snapshot.rfkill_wifi);
    wifi_emit(&sink,
              "modules readable=%s matches=%d\r\n",
              wifi_yesno(snapshot.proc_modules_readable),
              snapshot.module_matches);
    wifi_emit(&sink,
              "paths existing=%d/%d file_matches=%d\r\n",
              snapshot.existing_paths,
              snapshot.candidate_paths,
              snapshot.file_matches);
    a90_logf("wifiinv",
             "summary wlan=%d rfkill_wifi=%d modules=%d paths=%d/%d files=%d",
             snapshot.wlan_ifaces,
             snapshot.rfkill_wifi,
             snapshot.module_matches,
             snapshot.existing_paths,
             snapshot.candidate_paths,
             snapshot.file_matches);
    return 0;
}

int a90_wifiinv_print_full(void) {
    struct wifiinv_sink sink = {
        .console = true,
        .file_match_limit = WIFIINV_MAX_FILE_MATCHES,
        .file_matches_printed = 0,
    };
    struct a90_wifiinv_snapshot snapshot;
    int rc;

    wifi_emit(&sink, "[A90 WIFI INVENTORY]\r\n");
    wifi_emit(&sink, "generated_ms=%ld\r\n", monotonic_millis());
    wifi_emit(&sink, "banner=%s\r\n", INIT_BANNER);
    wifi_emit(&sink, "policy=read-only no-rfkill-write no-link-up no-module-change\r\n");
    rc = wifi_collect_into(&sink, &snapshot, true);
    if (rc < 0) {
        return rc;
    }
    wifi_emit(&sink, "[summary]\r\n");
    wifi_emit(&sink,
              "net_total=%d wlan_like=%d rfkill_total=%d rfkill_wifi=%d module_matches=%d paths=%d/%d file_matches=%d\r\n",
              snapshot.net_total,
              snapshot.wlan_ifaces,
              snapshot.rfkill_total,
              snapshot.rfkill_wifi,
              snapshot.module_matches,
              snapshot.existing_paths,
              snapshot.candidate_paths,
              snapshot.file_matches);
    a90_logf("wifiinv",
             "full wlan=%d rfkill_wifi=%d modules=%d paths=%d/%d files=%d",
             snapshot.wlan_ifaces,
             snapshot.rfkill_wifi,
             snapshot.module_matches,
             snapshot.existing_paths,
             snapshot.candidate_paths,
             snapshot.file_matches);
    return 0;
}

int a90_wifiinv_print_refresh(void) {
    struct wifiinv_sink sink = {
        .console = true,
        .file_match_limit = 0,
        .file_matches_printed = 0,
    };
    struct a90_wifiinv_snapshot snapshot;
    const char *relation;
    int rc;

    rc = wifi_collect_into(&sink, &snapshot, false);
    if (rc < 0) {
        return rc;
    }
    relation = wifi_refresh_relation(&snapshot);

    wifi_emit(&sink, "[wifiinv refresh]\r\n");
    wifi_emit(&sink, "banner=%s\r\n", INIT_BANNER);
    wifi_emit(&sink, "policy=read-only no-rfkill-write no-link-up no-module-change no-firmware-mutation\r\n");
    wifi_emit(&sink,
              "current net=%d wlan=%d rfkill=%d wifi_rfkill=%d modules=%d paths=%d/%d files=%d\r\n",
              snapshot.net_total,
              snapshot.wlan_ifaces,
              snapshot.rfkill_total,
              snapshot.rfkill_wifi,
              snapshot.module_matches,
              snapshot.existing_paths,
              snapshot.candidate_paths,
              snapshot.file_matches);
    wifi_emit(&sink,
              "baseline_default v103/v104 net=%d wlan=%d rfkill=%d wifi_rfkill=%d modules=%d paths=%d/%d files=%d\r\n",
              WIFIINV_BASELINE_NET_TOTAL,
              WIFIINV_BASELINE_WLAN_IFACES,
              WIFIINV_BASELINE_RFKILL_TOTAL,
              WIFIINV_BASELINE_RFKILL_WIFI,
              WIFIINV_BASELINE_MODULE_MATCHES,
              WIFIINV_BASELINE_DEFAULT_EXISTING_PATHS,
              (int)(sizeof(wifi_candidate_paths) / sizeof(wifi_candidate_paths[0])),
              WIFIINV_BASELINE_DEFAULT_FILE_MATCHES);
    wifi_emit(&sink,
              "baseline_mounted v103/v104 paths=%d/%d files=%d decision=no-go\r\n",
              WIFIINV_BASELINE_MOUNTED_EXISTING_PATHS,
              (int)(sizeof(wifi_candidate_paths) / sizeof(wifi_candidate_paths[0])),
              WIFIINV_BASELINE_MOUNTED_FILE_MATCHES);
    wifi_emit(&sink, "relation=%s\r\n", relation);
    if (strcmp(relation, "kernel-gates-changed") == 0) {
        wifi_emit(&sink, "next=plan a separate approved nl80211/iw read-only probe; still no bring-up in v122\r\n");
    } else if (strcmp(relation, "android-candidates-visible") == 0) {
        wifi_emit(&sink, "next=keep bring-up blocked; identify vendor driver/firmware contract from Android/TWRP baseline\r\n");
    } else if (strcmp(relation, "unchanged-native-default") == 0) {
        wifi_emit(&sink, "next=bring-up remains blocked; native default still lacks wlan/rfkill/module gates\r\n");
    } else {
        wifi_emit(&sink, "next=review changed evidence before any Wi-Fi bring-up plan\r\n");
    }
    a90_logf("wifiinv",
             "refresh relation=%s wlan=%d rfkill_wifi=%d modules=%d paths=%d/%d files=%d",
             relation,
             snapshot.wlan_ifaces,
             snapshot.rfkill_wifi,
             snapshot.module_matches,
             snapshot.existing_paths,
             snapshot.candidate_paths,
             snapshot.file_matches);
    return 0;
}

int a90_wifiinv_print_paths(void) {
    struct wifiinv_sink sink = {
        .console = true,
        .file_match_limit = 0,
        .file_matches_printed = 0,
    };
    size_t index;

    wifi_emit(&sink, "[wifiinv paths]\r\n");
    wifi_emit(&sink, "candidate_paths:\r\n");
    for (index = 0;
         index < sizeof(wifi_candidate_paths) / sizeof(wifi_candidate_paths[0]);
         index++) {
        wifi_emit(&sink, "  %s\r\n", wifi_candidate_paths[index]);
    }
    wifi_emit(&sink, "scan_roots:\r\n");
    for (index = 0; index < sizeof(wifi_scan_roots) / sizeof(wifi_scan_roots[0]); index++) {
        wifi_emit(&sink, "  %s\r\n", wifi_scan_roots[index]);
    }
    wifi_emit(&sink, "patterns:\r\n");
    for (index = 0; index < sizeof(wifi_patterns) / sizeof(wifi_patterns[0]); index++) {
        wifi_emit(&sink, "  %s\r\n", wifi_patterns[index]);
    }
    wifi_emit(&sink, "forbidden: rfkill-write link-up module-load module-unload service-mutation\r\n");
    return 0;
}
