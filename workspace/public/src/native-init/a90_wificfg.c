#include "a90_wificfg.h"

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "a90_console.h"
#include "a90_log.h"
#include "a90_util.h"

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#define WIFICFG_PRIMARY_ROOT "/mnt/sdext/a90/config/wifi"
#define WIFICFG_PRIMARY_AUTOCONNECT WIFICFG_PRIMARY_ROOT "/autoconnect.conf"
#define WIFICFG_PRIMARY_PROFILES WIFICFG_PRIMARY_ROOT "/profiles"
#define WIFICFG_PRIMARY_SECRET_ROOT "/mnt/sdext/a90/secrets/wifi"
#define WIFICFG_CACHE_ROOT "/cache/a90-wifi/config"
#define WIFICFG_CACHE_AUTOCONNECT WIFICFG_CACHE_ROOT "/autoconnect.conf"
#define WIFICFG_CACHE_PROFILES WIFICFG_CACHE_ROOT "/profiles"
#define WIFICFG_RUNTIME_ROOT "/cache/a90-wifi"

#define WIFICFG_MAX_TEXT 8192
#define WIFICFG_MAX_VALUE 192
#define WIFICFG_MAX_PATH 384

struct wificfg_file_info {
    bool exists;
    bool is_regular;
    bool is_dir;
    bool is_symlink;
    bool mode_owner_only;
    bool openable;
    mode_t mode;
};

struct wificfg_global_config {
    bool exists;
    bool parsed;
    bool from_primary;
    bool from_cache;
    bool version_set;
    bool autoconnect_set;
    bool default_profile_set;
    bool connect_timeout_set;
    bool dhcp_set;
    bool external_ping_set;
    bool scan_before_connect_set;
    bool retry_count_set;
    int version;
    int autoconnect;
    int connect_timeout_sec;
    int dhcp;
    int external_ping;
    int scan_before_connect;
    int retry_count;
    int invalid_lines;
    int unknown_keys;
    char default_profile[WIFICFG_MAX_VALUE];
};

struct wificfg_profile_config {
    bool exists;
    bool parsed;
    bool from_primary;
    bool from_cache;
    bool version_set;
    bool enabled_set;
    bool ssid_file_set;
    bool psk_file_set;
    bool band_set;
    bool priority_set;
    bool key_mgmt_set;
    bool inline_secret_key_seen;
    int version;
    int enabled;
    int priority;
    int invalid_lines;
    int unknown_keys;
    char ssid_file[WIFICFG_MAX_PATH];
    char psk_file[WIFICFG_MAX_PATH];
    char band[WIFICFG_MAX_VALUE];
    char key_mgmt[WIFICFG_MAX_VALUE];
};

static void wificfg_defaults(struct wificfg_global_config *config) {
    memset(config, 0, sizeof(*config));
    config->version = 1;
    config->autoconnect = 0;
    config->connect_timeout_sec = 35;
    config->dhcp = 0;
    config->external_ping = 0;
    config->scan_before_connect = 1;
    config->retry_count = 1;
}

static void wificfg_profile_defaults(struct wificfg_profile_config *profile) {
    memset(profile, 0, sizeof(*profile));
    profile->version = 1;
    profile->enabled = 1;
    profile->priority = 0;
    snprintf(profile->band, sizeof(profile->band), "%s", "any");
    snprintf(profile->key_mgmt, sizeof(profile->key_mgmt), "%s", "WPA-PSK");
}

static void wificfg_stat_path(const char *path, struct wificfg_file_info *info) {
    struct stat statbuf;

    memset(info, 0, sizeof(*info));
    if (lstat(path, &statbuf) < 0) {
        return;
    }

    info->exists = true;
    info->mode = statbuf.st_mode & 07777;
    info->is_regular = S_ISREG(statbuf.st_mode);
    info->is_dir = S_ISDIR(statbuf.st_mode);
    info->is_symlink = S_ISLNK(statbuf.st_mode);
    info->mode_owner_only = (info->mode & 0077) == 0;
}

static int wificfg_read_regular_text(const char *path, char *buf, size_t buf_size) {
    struct stat statbuf;
    int fd;
    ssize_t bytes_read;

    if (buf_size == 0) {
        errno = EINVAL;
        return -1;
    }
    if (lstat(path, &statbuf) < 0) {
        return -1;
    }
    if (!S_ISREG(statbuf.st_mode) || S_ISLNK(statbuf.st_mode)) {
        errno = EINVAL;
        return -1;
    }

    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -1;
    }
    bytes_read = read(fd, buf, buf_size - 1);
    close(fd);
    if (bytes_read < 0) {
        return -1;
    }
    buf[bytes_read] = '\0';
    return 0;
}

static char *wificfg_trim(char *text) {
    char *end;

    while (*text != '\0' && isspace((unsigned char)*text)) {
        ++text;
    }
    end = text + strlen(text);
    while (end > text && isspace((unsigned char)end[-1])) {
        --end;
    }
    *end = '\0';
    return text;
}

static bool wificfg_parse_boolish(const char *value, int *out) {
    if (strcmp(value, "1") == 0 ||
        strcmp(value, "true") == 0 ||
        strcmp(value, "yes") == 0 ||
        strcmp(value, "on") == 0) {
        *out = 1;
        return true;
    }
    if (strcmp(value, "0") == 0 ||
        strcmp(value, "false") == 0 ||
        strcmp(value, "no") == 0 ||
        strcmp(value, "off") == 0) {
        *out = 0;
        return true;
    }
    return false;
}

static bool wificfg_parse_int(const char *value, int min_value, int max_value, int *out) {
    char *end = NULL;
    long parsed;

    errno = 0;
    parsed = strtol(value, &end, 10);
    if (errno != 0 || end == value || *end != '\0') {
        return false;
    }
    if (parsed < min_value || parsed > max_value) {
        return false;
    }
    *out = (int)parsed;
    return true;
}

static bool wificfg_copy_value(char *destination, size_t destination_size, const char *value) {
    size_t value_len = strlen(value);

    if (destination_size == 0 || value_len >= destination_size) {
        return false;
    }
    memcpy(destination, value, value_len + 1);
    return true;
}

static bool wificfg_profile_name_valid(const char *name) {
    size_t index;

    if (name == NULL || name[0] == '\0' || strlen(name) >= 96) {
        return false;
    }
    for (index = 0; name[index] != '\0'; ++index) {
        unsigned char character = (unsigned char)name[index];

        if (!(isalnum(character) || character == '_' || character == '-' || character == '.')) {
            return false;
        }
    }
    return true;
}

static bool wificfg_path_has_prefix(const char *path, const char *prefix) {
    size_t prefix_len = strlen(prefix);

    return strncmp(path, prefix, prefix_len) == 0 &&
           (path[prefix_len] == '\0' || path[prefix_len] == '/');
}

static bool wificfg_secret_path_safe(const char *path) {
    if (path == NULL || path[0] != '/' || strstr(path, "/../") != NULL) {
        return false;
    }
    if (strstr(path, "/./") != NULL || strstr(path, "//") != NULL) {
        return false;
    }
    return wificfg_path_has_prefix(path, WIFICFG_PRIMARY_SECRET_ROOT) ||
           wificfg_path_has_prefix(path, WIFICFG_CACHE_ROOT);
}

static void wificfg_join_profile_path(char *destination,
                                      size_t destination_size,
                                      const char *root,
                                      const char *profile_name) {
    snprintf(destination, destination_size, "%s/%s.conf", root, profile_name);
}

static bool wificfg_parse_global_pair(struct wificfg_global_config *config,
                                      const char *key,
                                      const char *value) {
    int parsed_int;

    if (strcmp(key, "version") == 0) {
        if (!wificfg_parse_int(value, 1, 99, &parsed_int)) {
            return false;
        }
        config->version = parsed_int;
        config->version_set = true;
        return true;
    }
    if (strcmp(key, "autoconnect") == 0) {
        if (!wificfg_parse_boolish(value, &parsed_int)) {
            return false;
        }
        config->autoconnect = parsed_int;
        config->autoconnect_set = true;
        return true;
    }
    if (strcmp(key, "default_profile") == 0) {
        if (!wificfg_profile_name_valid(value) ||
            !wificfg_copy_value(config->default_profile, sizeof(config->default_profile), value)) {
            return false;
        }
        config->default_profile_set = true;
        return true;
    }
    if (strcmp(key, "connect_timeout_sec") == 0) {
        if (!wificfg_parse_int(value, 5, 180, &parsed_int)) {
            return false;
        }
        config->connect_timeout_sec = parsed_int;
        config->connect_timeout_set = true;
        return true;
    }
    if (strcmp(key, "dhcp") == 0) {
        if (!wificfg_parse_boolish(value, &parsed_int)) {
            return false;
        }
        config->dhcp = parsed_int;
        config->dhcp_set = true;
        return true;
    }
    if (strcmp(key, "external_ping") == 0) {
        if (!wificfg_parse_boolish(value, &parsed_int)) {
            return false;
        }
        config->external_ping = parsed_int;
        config->external_ping_set = true;
        return true;
    }
    if (strcmp(key, "scan_before_connect") == 0) {
        if (!wificfg_parse_boolish(value, &parsed_int)) {
            return false;
        }
        config->scan_before_connect = parsed_int;
        config->scan_before_connect_set = true;
        return true;
    }
    if (strcmp(key, "retry_count") == 0) {
        if (!wificfg_parse_int(value, 0, 5, &parsed_int)) {
            return false;
        }
        config->retry_count = parsed_int;
        config->retry_count_set = true;
        return true;
    }

    config->unknown_keys++;
    return true;
}

static bool wificfg_parse_profile_pair(struct wificfg_profile_config *profile,
                                       const char *key,
                                       const char *value) {
    int parsed_int;

    if (strcmp(key, "version") == 0) {
        if (!wificfg_parse_int(value, 1, 99, &parsed_int)) {
            return false;
        }
        profile->version = parsed_int;
        profile->version_set = true;
        return true;
    }
    if (strcmp(key, "enabled") == 0) {
        if (!wificfg_parse_boolish(value, &parsed_int)) {
            return false;
        }
        profile->enabled = parsed_int;
        profile->enabled_set = true;
        return true;
    }
    if (strcmp(key, "ssid_file") == 0) {
        if (!wificfg_copy_value(profile->ssid_file, sizeof(profile->ssid_file), value)) {
            return false;
        }
        profile->ssid_file_set = true;
        return true;
    }
    if (strcmp(key, "psk_file") == 0) {
        if (!wificfg_copy_value(profile->psk_file, sizeof(profile->psk_file), value)) {
            return false;
        }
        profile->psk_file_set = true;
        return true;
    }
    if (strcmp(key, "band") == 0) {
        if (!(strcmp(value, "2.4g") == 0 ||
              strcmp(value, "5g") == 0 ||
              strcmp(value, "6g") == 0 ||
              strcmp(value, "any") == 0) ||
            !wificfg_copy_value(profile->band, sizeof(profile->band), value)) {
            return false;
        }
        profile->band_set = true;
        return true;
    }
    if (strcmp(key, "priority") == 0) {
        if (!wificfg_parse_int(value, -1000, 1000, &parsed_int)) {
            return false;
        }
        profile->priority = parsed_int;
        profile->priority_set = true;
        return true;
    }
    if (strcmp(key, "key_mgmt") == 0) {
        if (!(strcmp(value, "WPA-PSK") == 0 ||
              strcmp(value, "SAE") == 0 ||
              strcmp(value, "WPA-PSK SAE") == 0) ||
            !wificfg_copy_value(profile->key_mgmt, sizeof(profile->key_mgmt), value)) {
            return false;
        }
        profile->key_mgmt_set = true;
        return true;
    }
    if (strcmp(key, "ssid") == 0 ||
        strcmp(key, "psk") == 0 ||
        strcmp(key, "password") == 0) {
        profile->inline_secret_key_seen = true;
        return true;
    }

    profile->unknown_keys++;
    return true;
}

static int wificfg_parse_lines(char *text,
                               bool profile_mode,
                               struct wificfg_global_config *global_config,
                               struct wificfg_profile_config *profile_config) {
    char *saveptr = NULL;
    char *line = strtok_r(text, "\n", &saveptr);

    while (line != NULL) {
        char *trimmed = wificfg_trim(line);
        char *separator;
        char *key;
        char *value;
        bool parsed;

        trim_newline(trimmed);
        if (trimmed[0] == '\0' || trimmed[0] == '#' || trimmed[0] == ';') {
            line = strtok_r(NULL, "\n", &saveptr);
            continue;
        }

        separator = strchr(trimmed, '=');
        if (separator == NULL) {
            if (profile_mode) {
                profile_config->invalid_lines++;
            } else {
                global_config->invalid_lines++;
            }
            line = strtok_r(NULL, "\n", &saveptr);
            continue;
        }

        *separator = '\0';
        key = wificfg_trim(trimmed);
        value = wificfg_trim(separator + 1);
        if (key[0] == '\0') {
            if (profile_mode) {
                profile_config->invalid_lines++;
            } else {
                global_config->invalid_lines++;
            }
            line = strtok_r(NULL, "\n", &saveptr);
            continue;
        }

        parsed = profile_mode ?
            wificfg_parse_profile_pair(profile_config, key, value) :
            wificfg_parse_global_pair(global_config, key, value);
        if (!parsed) {
            if (profile_mode) {
                profile_config->invalid_lines++;
            } else {
                global_config->invalid_lines++;
            }
        }

        line = strtok_r(NULL, "\n", &saveptr);
    }

    return 0;
}

static int wificfg_load_global(struct wificfg_global_config *config) {
    char text[WIFICFG_MAX_TEXT];

    wificfg_defaults(config);
    if (wificfg_read_regular_text(WIFICFG_PRIMARY_AUTOCONNECT, text, sizeof(text)) == 0) {
        config->exists = true;
        config->from_primary = true;
        wificfg_parse_lines(text, false, config, NULL);
        config->parsed = config->invalid_lines == 0;
        return 0;
    }
    if (wificfg_read_regular_text(WIFICFG_CACHE_AUTOCONNECT, text, sizeof(text)) == 0) {
        config->exists = true;
        config->from_cache = true;
        wificfg_parse_lines(text, false, config, NULL);
        config->parsed = config->invalid_lines == 0;
        return 0;
    }
    return -ENOENT;
}

static int wificfg_load_profile(const struct wificfg_global_config *config,
                                struct wificfg_profile_config *profile,
                                char *profile_path,
                                size_t profile_path_size) {
    char text[WIFICFG_MAX_TEXT];

    wificfg_profile_defaults(profile);
    if (!config->default_profile_set ||
        !wificfg_profile_name_valid(config->default_profile)) {
        return -EINVAL;
    }

    wificfg_join_profile_path(profile_path, profile_path_size, WIFICFG_PRIMARY_PROFILES, config->default_profile);
    if (wificfg_read_regular_text(profile_path, text, sizeof(text)) == 0) {
        profile->exists = true;
        profile->from_primary = true;
        wificfg_parse_lines(text, true, NULL, profile);
        profile->parsed = profile->invalid_lines == 0;
        return 0;
    }

    wificfg_join_profile_path(profile_path, profile_path_size, WIFICFG_CACHE_PROFILES, config->default_profile);
    if (wificfg_read_regular_text(profile_path, text, sizeof(text)) == 0) {
        profile->exists = true;
        profile->from_cache = true;
        wificfg_parse_lines(text, true, NULL, profile);
        profile->parsed = profile->invalid_lines == 0;
        return 0;
    }

    return -ENOENT;
}

static const char *wificfg_source_name(const struct wificfg_global_config *config) {
    if (config->from_primary) {
        return "primary";
    }
    if (config->from_cache) {
        return "cache";
    }
    return "none";
}

static const char *wificfg_profile_source_name(const struct wificfg_profile_config *profile) {
    if (profile->from_primary) {
        return "primary";
    }
    if (profile->from_cache) {
        return "cache";
    }
    return "none";
}

static const char *wificfg_path_kind(const struct wificfg_file_info *info) {
    if (!info->exists) {
        return "missing";
    }
    if (info->is_symlink) {
        return "symlink";
    }
    if (info->is_dir) {
        return "dir";
    }
    if (info->is_regular) {
        return "file";
    }
    return "other";
}

static void wificfg_print_path_info(const char *label, const char *path, bool show_path) {
    struct wificfg_file_info info;

    wificfg_stat_path(path, &info);
    if (show_path) {
        a90_console_printf("%s.path=%s\r\n", label, path);
    }
    a90_console_printf("%s.kind=%s\r\n", label, wificfg_path_kind(&info));
    if (info.exists) {
        a90_console_printf("%s.mode=0%03o\r\n", label, (unsigned int)info.mode);
        a90_console_printf("%s.owner_only=%d\r\n", label, info.mode_owner_only ? 1 : 0);
    }
}

static bool wificfg_secret_status(const char *label, const char *path, bool configured) {
    struct wificfg_file_info info;
    bool safe_path;
    bool usable;

    a90_console_printf("%s.configured=%d\r\n", label, configured ? 1 : 0);
    if (!configured) {
        a90_console_printf("%s.present=0\r\n", label);
        a90_console_printf("%s.path_safe=0\r\n", label);
        a90_console_printf("%s.mode_ok=0\r\n", label);
        return false;
    }

    safe_path = wificfg_secret_path_safe(path);
    a90_console_printf("%s.path_safe=%d\r\n", label, safe_path ? 1 : 0);
    if (!safe_path) {
        a90_console_printf("%s.present=0\r\n", label);
        a90_console_printf("%s.mode_ok=0\r\n", label);
        return false;
    }

    wificfg_stat_path(path, &info);
    usable = info.exists && info.is_regular && !info.is_symlink && info.mode_owner_only;
    a90_console_printf("%s.present=%d\r\n", label, info.exists ? 1 : 0);
    if (info.exists) {
        a90_console_printf("%s.kind=%s\r\n", label, wificfg_path_kind(&info));
        a90_console_printf("%s.mode=0%03o\r\n", label, (unsigned int)info.mode);
    }
    a90_console_printf("%s.mode_ok=%d\r\n", label, usable ? 1 : 0);
    return usable;
}

static const char *wificfg_decision(const struct wificfg_global_config *config,
                                    const struct wificfg_profile_config *profile,
                                    bool profile_loaded,
                                    bool ssid_usable,
                                    bool psk_usable) {
    if (!config->exists) {
        return "wifi-config-no-autoconnect-config";
    }
    if (!config->parsed) {
        return "wifi-config-invalid-global";
    }
    if (config->autoconnect == 0) {
        return "wifi-config-disabled";
    }
    if (config->external_ping != 0) {
        return "wifi-config-external-ping-blocked";
    }
    if (!config->default_profile_set) {
        return "wifi-config-needs-default-profile";
    }
    if (!profile_loaded) {
        return "wifi-config-missing-profile";
    }
    if (!profile->parsed) {
        return "wifi-config-invalid-profile";
    }
    if (profile->inline_secret_key_seen) {
        return "wifi-config-inline-secret-blocked";
    }
    if (profile->enabled == 0) {
        return "wifi-config-profile-disabled";
    }
    if (!ssid_usable || !psk_usable) {
        return "wifi-config-secret-not-ready";
    }
    return "wifi-config-ready";
}

int a90_wificfg_print_status(void) {
    struct wificfg_global_config config;
    struct wificfg_profile_config profile;
    char profile_path[WIFICFG_MAX_PATH] = "";
    int config_rc;
    int profile_rc;
    bool ssid_usable = false;
    bool psk_usable = false;

    config_rc = wificfg_load_global(&config);
    profile_rc = wificfg_load_profile(&config, &profile, profile_path, sizeof(profile_path));

    a90_console_printf("[wifi config]\r\n");
    wificfg_print_path_info("primary_config_root", WIFICFG_PRIMARY_ROOT, true);
    wificfg_print_path_info("primary_secret_root", WIFICFG_PRIMARY_SECRET_ROOT, true);
    wificfg_print_path_info("cache_config_root", WIFICFG_CACHE_ROOT, true);
    wificfg_print_path_info("runtime_root", WIFICFG_RUNTIME_ROOT, true);
    a90_console_printf("active_config_source=%s\r\n", wificfg_source_name(&config));
    a90_console_printf("autoconnect_config_present=%d\r\n", config.exists ? 1 : 0);
    a90_console_printf("autoconnect_config_valid=%d\r\n", config.exists && config.parsed ? 1 : 0);
    a90_console_printf("autoconnect_config_rc=%d\r\n", config_rc);
    a90_console_printf("version=%d%s\r\n", config.version, config.version_set ? "" : " default");
    a90_console_printf("autoconnect=%d%s\r\n", config.autoconnect, config.autoconnect_set ? "" : " default");
    a90_console_printf("default_profile_set=%d\r\n", config.default_profile_set ? 1 : 0);
    if (config.default_profile_set) {
        a90_console_printf("default_profile=%s\r\n", config.default_profile);
    }
    a90_console_printf("connect_timeout_sec=%d%s\r\n",
                       config.connect_timeout_sec,
                       config.connect_timeout_set ? "" : " default");
    a90_console_printf("dhcp=%d%s\r\n", config.dhcp, config.dhcp_set ? "" : " default");
    a90_console_printf("external_ping=%d%s\r\n",
                       config.external_ping,
                       config.external_ping_set ? "" : " default");
    a90_console_printf("scan_before_connect=%d%s\r\n",
                       config.scan_before_connect,
                       config.scan_before_connect_set ? "" : " default");
    a90_console_printf("retry_count=%d%s\r\n", config.retry_count, config.retry_count_set ? "" : " default");
    a90_console_printf("global_invalid_lines=%d\r\n", config.invalid_lines);
    a90_console_printf("global_unknown_keys=%d\r\n", config.unknown_keys);

    a90_console_printf("profile_source=%s\r\n", wificfg_profile_source_name(&profile));
    a90_console_printf("profile_present=%d\r\n", profile.exists ? 1 : 0);
    a90_console_printf("profile_valid=%d\r\n", profile.exists && profile.parsed ? 1 : 0);
    a90_console_printf("profile_rc=%d\r\n", profile_rc);
    if (profile.exists) {
        wificfg_print_path_info("profile_file", profile_path, false);
        a90_console_printf("profile_enabled=%d%s\r\n", profile.enabled, profile.enabled_set ? "" : " default");
        a90_console_printf("profile_band=%s%s\r\n", profile.band, profile.band_set ? "" : " default");
        a90_console_printf("profile_priority=%d%s\r\n", profile.priority, profile.priority_set ? "" : " default");
        a90_console_printf("profile_key_mgmt=%s%s\r\n", profile.key_mgmt, profile.key_mgmt_set ? "" : " default");
        a90_console_printf("profile_inline_secret_key_seen=%d\r\n", profile.inline_secret_key_seen ? 1 : 0);
        a90_console_printf("profile_invalid_lines=%d\r\n", profile.invalid_lines);
        a90_console_printf("profile_unknown_keys=%d\r\n", profile.unknown_keys);
        ssid_usable = wificfg_secret_status("ssid_file", profile.ssid_file, profile.ssid_file_set);
        psk_usable = wificfg_secret_status("psk_file", profile.psk_file, profile.psk_file_set);
    } else {
        a90_console_printf("profile_enabled=0\r\n");
        a90_console_printf("profile_inline_secret_key_seen=0\r\n");
        a90_console_printf("ssid_file.configured=0\r\n");
        a90_console_printf("ssid_file.present=0\r\n");
        a90_console_printf("psk_file.configured=0\r\n");
        a90_console_printf("psk_file.present=0\r\n");
    }

    a90_console_printf("secret_values_logged=0\r\n");
    a90_console_printf("decision=%s\r\n",
                       wificfg_decision(&config, &profile, profile_rc == 0, ssid_usable, psk_usable));
    a90_logf("wificfg",
             "status source=%s autoconnect=%d profile_present=%d decision=%s",
             wificfg_source_name(&config),
             config.autoconnect,
             profile.exists ? 1 : 0,
             wificfg_decision(&config, &profile, profile_rc == 0, ssid_usable, psk_usable));
    return 0;
}

int a90_wificfg_cmd(char **argv, int argc) {
    if (argc == 3 &&
        argv != NULL &&
        argv[1] != NULL &&
        argv[2] != NULL &&
        strcmp(argv[1], "config") == 0 &&
        strcmp(argv[2], "status") == 0) {
        return a90_wificfg_print_status();
    }

    a90_console_printf("usage: wifi config status\r\n");
    return -EINVAL;
}
