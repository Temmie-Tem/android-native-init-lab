#include "a90_sensormap.h"

#include "a90_console.h"
#include "a90_util.h"

#include <dirent.h>
#include <errno.h>
#include <stdbool.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define SENSORMAP_MAX_TRIPS 12

static bool starts_with(const char *text, const char *prefix) {
    return strncmp(text, prefix, strlen(prefix)) == 0;
}

static bool path_exists(const char *path) {
    struct stat st;

    return lstat(path, &st) == 0;
}

static int read_attr_text(const char *dir, const char *name, char *out, size_t out_size) {
        char path[PATH_MAX + 64];

    if (out == NULL || out_size == 0) {
        return -EINVAL;
    }
    snprintf(path, sizeof(path), "%s/%s", dir, name);
    path[sizeof(path) - 1] = '\0';
    if (read_trimmed_text_file(path, out, out_size) < 0) {
        return -errno;
    }
    flatten_inline_text(out);
    return 0;
}

static int read_attr_long(const char *dir, const char *name, long *out) {
    char text[64];
    char *endptr;
    long value;
    int rc;

    if (out == NULL) {
        return -EINVAL;
    }
    rc = read_attr_text(dir, name, text, sizeof(text));
    if (rc < 0) {
        return rc;
    }
    errno = 0;
    value = strtol(text, &endptr, 10);
    if (errno != 0 || endptr == text) {
        return -EINVAL;
    }
    *out = value;
    return 0;
}

static int count_prefixed_entries(const char *path, const char *prefix) {
    DIR *dir;
    struct dirent *entry;
    int count = 0;

    dir = opendir(path);
    if (dir == NULL) {
        return 0;
    }
    while ((entry = readdir(dir)) != NULL) {
        if (entry->d_name[0] == '.') {
            continue;
        }
        if (starts_with(entry->d_name, prefix)) {
            ++count;
        }
    }
    closedir(dir);
    return count;
}

static const char *format_millic(long millic, char *out, size_t out_size) {
    long whole = millic / 1000;
    long frac = millic % 1000;

    if (frac < 0) {
        frac = -frac;
    }
    snprintf(out, out_size, "%ld.%03ldC", whole, frac);
    return out;
}

static void thermal_zone_path(const char *name, char *out, size_t out_size) {
    snprintf(out, out_size, "/sys/class/thermal/%s", name);
    out[out_size - 1] = '\0';
}

static int count_trip_points(const char *zone_dir) {
    int trip_count = 0;
    int index;

    for (index = 0; index < SENSORMAP_MAX_TRIPS; ++index) {
        char path[PATH_MAX + 64];

        snprintf(path, sizeof(path), "%s/trip_point_%d_temp", zone_dir, index);
        path[sizeof(path) - 1] = '\0';
        if (path_exists(path)) {
            ++trip_count;
        }
    }
    return trip_count;
}

int a90_sensormap_collect_summary(struct a90_sensormap_summary *out) {
    DIR *dir;
    struct dirent *entry;

    if (out == NULL) {
        return -EINVAL;
    }
    memset(out, 0, sizeof(*out));

    dir = opendir("/sys/class/thermal");
    if (dir != NULL) {
        while ((entry = readdir(dir)) != NULL) {
            char zone_dir[PATH_MAX];
            char type[96] = "-";
            long temp;

            if (starts_with(entry->d_name, "thermal_zone")) {
                ++out->thermal_zones;
                thermal_zone_path(entry->d_name, zone_dir, sizeof(zone_dir));
                (void)read_attr_text(zone_dir, "type", type, sizeof(type));
                if (read_attr_long(zone_dir, "temp", &temp) == 0) {
                    ++out->thermal_readable;
                    if (out->thermal_readable == 1 || temp > out->max_temp_millic) {
                        out->max_temp_millic = temp;
                        snprintf(out->max_temp_type, sizeof(out->max_temp_type), "%s", type);
                    }
                }
            } else if (starts_with(entry->d_name, "cooling_device")) {
                ++out->cooling_devices;
            }
        }
        closedir(dir);
    }

    dir = opendir("/sys/class/power_supply");
    if (dir != NULL) {
        while ((entry = readdir(dir)) != NULL) {
            char supply_dir[PATH_MAX];
            char type[96] = "";

            if (entry->d_name[0] == '.') {
                continue;
            }
            ++out->power_supplies;
            snprintf(supply_dir, sizeof(supply_dir), "/sys/class/power_supply/%s", entry->d_name);
            supply_dir[sizeof(supply_dir) - 1] = '\0';
            if (read_attr_text(supply_dir, "type", type, sizeof(type)) == 0) {
                if (strcmp(type, "Battery") == 0) {
                    ++out->power_batteries;
                }
                if (strcmp(type, "Mains") == 0 ||
                    strcmp(type, "USB") == 0 ||
                    strcmp(type, "Wireless") == 0) {
                    ++out->power_chargers;
                }
            }
        }
        closedir(dir);
    }

    return 0;
}

void a90_sensormap_summary_text(char *out, size_t out_size) {
    struct a90_sensormap_summary summary;
    char temp[32];

    if (out == NULL || out_size == 0) {
        return;
    }
    if (a90_sensormap_collect_summary(&summary) < 0) {
        snprintf(out, out_size, "sensormap=error");
        return;
    }

    snprintf(out, out_size,
             "sensormap=thermal=%d readable=%d cooling=%d max=%s:%s power=%d batteries=%d chargers=%d",
             summary.thermal_zones,
             summary.thermal_readable,
             summary.cooling_devices,
             summary.max_temp_type[0] ? summary.max_temp_type : "-",
             summary.thermal_readable > 0 ? format_millic(summary.max_temp_millic, temp, sizeof(temp)) : "-",
             summary.power_supplies,
             summary.power_batteries,
             summary.power_chargers);
    out[out_size - 1] = '\0';
}

int a90_sensormap_print_summary(void) {
    char summary[256];

    a90_sensormap_summary_text(summary, sizeof(summary));
    a90_console_printf("%s\r\n", summary);
    return 0;
}

int a90_sensormap_print_thermal(void) {
    DIR *dir;
    struct dirent *entry;

    a90_console_printf("[thermal zones]\r\n");
    dir = opendir("/sys/class/thermal");
    if (dir == NULL) {
        a90_console_printf("thermal: open failed errno=%d\r\n", errno);
        return -errno;
    }
    while ((entry = readdir(dir)) != NULL) {
        char zone_dir[PATH_MAX];
        char type[96] = "-";
        char temp_text[32] = "-";
        long temp;
        int trip_count;
        int index;

        if (!starts_with(entry->d_name, "thermal_zone")) {
            continue;
        }
        thermal_zone_path(entry->d_name, zone_dir, sizeof(zone_dir));
        (void)read_attr_text(zone_dir, "type", type, sizeof(type));
        if (read_attr_long(zone_dir, "temp", &temp) == 0) {
            (void)format_millic(temp, temp_text, sizeof(temp_text));
        }
        trip_count = count_trip_points(zone_dir);
        a90_console_printf("%s type=%s temp=%s trips=%d", entry->d_name, type, temp_text, trip_count);
        for (index = 0; index < trip_count && index < 3; ++index) {
            char attr[64];
            char trip_type[64] = "-";
            long trip_temp;
            char trip_temp_text[32] = "-";

            snprintf(attr, sizeof(attr), "trip_point_%d_type", index);
            (void)read_attr_text(zone_dir, attr, trip_type, sizeof(trip_type));
            snprintf(attr, sizeof(attr), "trip_point_%d_temp", index);
            if (read_attr_long(zone_dir, attr, &trip_temp) == 0) {
                (void)format_millic(trip_temp, trip_temp_text, sizeof(trip_temp_text));
            }
            a90_console_printf(" trip%d=%s:%s", index, trip_type, trip_temp_text);
        }
        a90_console_printf("\r\n");
    }
    closedir(dir);

    a90_console_printf("[cooling devices]\r\n");
    dir = opendir("/sys/class/thermal");
    if (dir == NULL) {
        return 0;
    }
    while ((entry = readdir(dir)) != NULL) {
            char device_dir[PATH_MAX];
        char type[96] = "-";
        char cur_state[32] = "-";
        char max_state[32] = "-";

        if (!starts_with(entry->d_name, "cooling_device")) {
            continue;
        }
        snprintf(device_dir, sizeof(device_dir), "/sys/class/thermal/%s", entry->d_name);
        device_dir[sizeof(device_dir) - 1] = '\0';
        (void)read_attr_text(device_dir, "type", type, sizeof(type));
        (void)read_attr_text(device_dir, "cur_state", cur_state, sizeof(cur_state));
        (void)read_attr_text(device_dir, "max_state", max_state, sizeof(max_state));
        a90_console_printf("%s type=%s cur=%s max=%s\r\n", entry->d_name, type, cur_state, max_state);
    }
    closedir(dir);
    return 0;
}

static void print_power_attr(const char *supply_dir, const char *name) {
    char value[96];

    if (read_attr_text(supply_dir, name, value, sizeof(value)) == 0) {
        a90_console_printf(" %s=%s", name, value);
    }
}

int a90_sensormap_print_power(void) {
    static const char *const attrs[] = {
        "type",
        "status",
        "online",
        "present",
        "health",
        "capacity",
        "temp",
        "voltage_now",
        "current_now",
        "power_now",
        "power_avg",
        "charge_now",
        "charge_counter",
    };
    DIR *dir;
    struct dirent *entry;

    a90_console_printf("[power_supply]\r\n");
    dir = opendir("/sys/class/power_supply");
    if (dir == NULL) {
        a90_console_printf("power_supply: open failed errno=%d\r\n", errno);
        return -errno;
    }
    while ((entry = readdir(dir)) != NULL) {
        char supply_dir[PATH_MAX];
        size_t index;

        if (entry->d_name[0] == '.') {
            continue;
        }
        snprintf(supply_dir, sizeof(supply_dir), "/sys/class/power_supply/%s", entry->d_name);
        supply_dir[sizeof(supply_dir) - 1] = '\0';
        a90_console_printf("%s", entry->d_name);
        for (index = 0; index < sizeof(attrs) / sizeof(attrs[0]); ++index) {
            print_power_attr(supply_dir, attrs[index]);
        }
        a90_console_printf("\r\n");
    }
    closedir(dir);
    return 0;
}

int a90_sensormap_print_full(void) {
    int rc;

    rc = a90_sensormap_print_summary();
    if (rc < 0) {
        return rc;
    }
    rc = a90_sensormap_print_thermal();
    if (rc < 0) {
        return rc;
    }
    return a90_sensormap_print_power();
}

int a90_sensormap_print_paths(void) {
    a90_console_printf("[sensormap paths]\r\n");
    a90_console_printf("/sys/class/thermal: zones=%d cooling=%d\r\n",
                       count_prefixed_entries("/sys/class/thermal", "thermal_zone"),
                       count_prefixed_entries("/sys/class/thermal", "cooling_device"));
    a90_console_printf("/sys/class/power_supply: supplies=%d\r\n",
                       count_prefixed_entries("/sys/class/power_supply", ""));
    return 0;
}

int a90_sensormap_cmd(char **argv, int argc) {
    const char *mode = argc > 1 ? argv[1] : "summary";

    if (argc > 2) {
        a90_console_printf("usage: sensormap [summary|thermal|power|full|paths]\r\n");
        return -EINVAL;
    }
    if (strcmp(mode, "summary") == 0 || strcmp(mode, "status") == 0) {
        return a90_sensormap_print_summary();
    }
    if (strcmp(mode, "thermal") == 0) {
        return a90_sensormap_print_thermal();
    }
    if (strcmp(mode, "power") == 0) {
        return a90_sensormap_print_power();
    }
    if (strcmp(mode, "full") == 0) {
        return a90_sensormap_print_full();
    }
    if (strcmp(mode, "paths") == 0) {
        return a90_sensormap_print_paths();
    }

    a90_console_printf("usage: sensormap [summary|thermal|power|full|paths]\r\n");
    return -EINVAL;
}
