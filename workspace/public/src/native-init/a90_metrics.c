#include "a90_metrics.h"

#include <dirent.h>
#include <errno.h>
#include <limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "a90_util.h"

int a90_metrics_read_sysfs_long(const char *path, long *value_out) {
    char buf[128];

    if (read_trimmed_text_file(path, buf, sizeof(buf)) < 0) {
        return -1;
    }

    *value_out = strtol(buf, NULL, 10);
    return 0;
}

static int read_first_token(const char *path, char *out, size_t out_size) {
    char buf[256];
    size_t len = 0;

    if (read_trimmed_text_file(path, buf, sizeof(buf)) < 0) {
        return -1;
    }

    while (buf[len] != '\0' && buf[len] != ' ' && buf[len] != '\t' && len + 1 < out_size) {
        out[len] = buf[len];
        ++len;
    }
    out[len] = '\0';
    return 0;
}

static int read_meminfo_kb(const char *label, long *value_out) {
    FILE *fp;
    char line[256];
    size_t label_len = strlen(label);

    fp = fopen("/proc/meminfo", "r");
    if (fp == NULL) {
        return -1;
    }

    while (fgets(line, sizeof(line), fp) != NULL) {
        if (strncmp(line, label, label_len) == 0) {
            char *cursor = line + label_len;

            while (*cursor == ' ' || *cursor == '\t' || *cursor == ':') {
                ++cursor;
            }
            *value_out = strtol(cursor, NULL, 10);
            fclose(fp);
            return 0;
        }
    }

    fclose(fp);
    errno = ENOENT;
    return -1;
}

static int read_cpu_usage_percent(long *percent_out) {
    static bool have_previous = false;
    static unsigned long long previous_total = 0;
    static unsigned long long previous_idle = 0;
    FILE *fp;
    char line[256];
    unsigned long long user = 0;
    unsigned long long nice = 0;
    unsigned long long system = 0;
    unsigned long long idle = 0;
    unsigned long long iowait = 0;
    unsigned long long irq = 0;
    unsigned long long softirq = 0;
    unsigned long long steal = 0;
    unsigned long long idle_all;
    unsigned long long non_idle;
    unsigned long long total;
    unsigned long long total_delta;
    unsigned long long idle_delta;
    unsigned long long busy_delta;
    long percent;

    fp = fopen("/proc/stat", "r");
    if (fp == NULL) {
        return -1;
    }

    if (fgets(line, sizeof(line), fp) == NULL) {
        fclose(fp);
        return -1;
    }
    fclose(fp);

    if (sscanf(line, "cpu %llu %llu %llu %llu %llu %llu %llu %llu",
               &user,
               &nice,
               &system,
               &idle,
               &iowait,
               &irq,
               &softirq,
               &steal) < 4) {
        return -1;
    }

    idle_all = idle + iowait;
    non_idle = user + nice + system + irq + softirq + steal;
    total = idle_all + non_idle;

    if (!have_previous || total <= previous_total) {
        previous_total = total;
        previous_idle = idle_all;
        have_previous = true;
        return -1;
    }

    total_delta = total - previous_total;
    idle_delta = idle_all - previous_idle;
    previous_total = total;
    previous_idle = idle_all;

    if (total_delta == 0 || idle_delta > total_delta) {
        return -1;
    }

    busy_delta = total_delta - idle_delta;
    percent = (long)((busy_delta * 100ULL + total_delta / 2ULL) / total_delta);
    if (percent < 0) {
        percent = 0;
    } else if (percent > 100) {
        percent = 100;
    }

    *percent_out = percent;
    return 0;
}

static int read_gpu_busy_percent(long *percent_out) {
    char buf[64];
    long percent;

    if (read_trimmed_text_file("/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage",
                               buf,
                               sizeof(buf)) < 0) {
        return -1;
    }

    percent = strtol(buf, NULL, 10);
    if (percent < 0) {
        percent = 0;
    } else if (percent > 100) {
        percent = 100;
    }

    *percent_out = percent;
    return 0;
}

static int read_average_thermal_temp(const char *prefix_a,
                                     const char *prefix_b,
                                     long *temp_out) {
    DIR *dir;
    struct dirent *entry;
    long total = 0;
    long count = 0;

    dir = opendir("/sys/class/thermal");
    if (dir == NULL) {
        return -1;
    }

    while ((entry = readdir(dir)) != NULL) {
        char type_path[PATH_MAX];
        char temp_path[PATH_MAX];
        char type[128];
        long temp_value;

        if (strncmp(entry->d_name, "thermal_zone", 12) != 0) {
            continue;
        }

        if (snprintf(type_path, sizeof(type_path),
                     "/sys/class/thermal/%s/type", entry->d_name) >= (int)sizeof(type_path) ||
            snprintf(temp_path, sizeof(temp_path),
                     "/sys/class/thermal/%s/temp", entry->d_name) >= (int)sizeof(temp_path)) {
            continue;
        }

        if (read_trimmed_text_file(type_path, type, sizeof(type)) < 0 ||
            a90_metrics_read_sysfs_long(temp_path, &temp_value) < 0) {
            continue;
        }

        if (strncmp(type, prefix_a, strlen(prefix_a)) == 0 ||
            (prefix_b != NULL && strncmp(type, prefix_b, strlen(prefix_b)) == 0)) {
            total += temp_value;
            ++count;
        }
    }

    closedir(dir);

    if (count == 0) {
        errno = ENOENT;
        return -1;
    }

    *temp_out = total / count;
    return 0;
}

static void format_temp_tenths(char *out, size_t out_size, long milli_c) {
    long tenths = milli_c / 100;
    long whole = tenths / 10;
    long frac = tenths % 10;

    if (frac < 0) {
        frac = -frac;
    }

    snprintf(out, out_size, "%ld.%ldC", whole, frac);
}

static void format_milliwatts_as_watts(char *out, size_t out_size, long milliwatts) {
    long tenths = milliwatts / 100;
    long whole = tenths / 10;
    long frac = tenths % 10;

    if (frac < 0) {
        frac = -frac;
    }

    snprintf(out, out_size, "%ld.%ldW", whole, frac);
}

void a90_metrics_read_snapshot(struct a90_metrics_snapshot *snapshot) {
    long value;
    long mem_total_kb;
    long mem_avail_kb;

    strcpy(snapshot->battery_status, "?");
    strcpy(snapshot->battery_pct, "?");
    strcpy(snapshot->battery_temp, "?");
    strcpy(snapshot->battery_voltage, "?");
    strcpy(snapshot->cpu_temp, "?");
    strcpy(snapshot->cpu_usage, "?");
    strcpy(snapshot->gpu_temp, "?");
    strcpy(snapshot->gpu_usage, "?");
    strcpy(snapshot->memory, "?");
    strcpy(snapshot->loadavg, "?");
    strcpy(snapshot->uptime, "?");
    strcpy(snapshot->power_now, "?");
    strcpy(snapshot->power_avg, "?");

    if (a90_metrics_read_sysfs_long("/sys/class/power_supply/battery/capacity", &value) == 0) {
        snprintf(snapshot->battery_pct, sizeof(snapshot->battery_pct), "%ld%%", value);
    }
    if (read_trimmed_text_file("/sys/class/power_supply/battery/status",
                               snapshot->battery_status,
                               sizeof(snapshot->battery_status)) < 0) {
        strcpy(snapshot->battery_status, "?");
    }
    if (a90_metrics_read_sysfs_long("/sys/class/power_supply/battery/temp", &value) == 0) {
        format_temp_tenths(snapshot->battery_temp, sizeof(snapshot->battery_temp), value * 100);
    }
    if (a90_metrics_read_sysfs_long("/sys/class/power_supply/battery/voltage_now", &value) == 0) {
        snprintf(snapshot->battery_voltage, sizeof(snapshot->battery_voltage), "%ldmV", value / 1000);
    }
    if (a90_metrics_read_sysfs_long("/sys/class/power_supply/battery/power_now", &value) == 0) {
        format_milliwatts_as_watts(snapshot->power_now, sizeof(snapshot->power_now), value);
    }
    if (a90_metrics_read_sysfs_long("/sys/class/power_supply/battery/power_avg", &value) == 0) {
        format_milliwatts_as_watts(snapshot->power_avg, sizeof(snapshot->power_avg), value);
    }
    if (read_average_thermal_temp("cpu-", "cpuss", &value) == 0) {
        format_temp_tenths(snapshot->cpu_temp, sizeof(snapshot->cpu_temp), value);
    }
    if (read_cpu_usage_percent(&value) == 0) {
        snprintf(snapshot->cpu_usage, sizeof(snapshot->cpu_usage), "%ld%%", value);
    }
    if (read_average_thermal_temp("gpuss", NULL, &value) == 0) {
        format_temp_tenths(snapshot->gpu_temp, sizeof(snapshot->gpu_temp), value);
    }
    if (read_gpu_busy_percent(&value) == 0) {
        snprintf(snapshot->gpu_usage, sizeof(snapshot->gpu_usage), "%ld%%", value);
    }
    if (read_meminfo_kb("MemTotal", &mem_total_kb) == 0 &&
        read_meminfo_kb("MemAvailable", &mem_avail_kb) == 0) {
        snprintf(snapshot->memory, sizeof(snapshot->memory), "%ld/%ldMB",
                 (mem_total_kb - mem_avail_kb) / 1024,
                 mem_total_kb / 1024);
    }
    read_first_token("/proc/loadavg", snapshot->loadavg, sizeof(snapshot->loadavg));
    read_first_token("/proc/uptime", snapshot->uptime, sizeof(snapshot->uptime));
}

void a90_metrics_read_cpu_freq_label(unsigned int cpu, char *out, size_t out_size) {
    char path[PATH_MAX];
    long khz;

    snprintf(out, out_size, "?");
    if (snprintf(path, sizeof(path),
                 "/sys/devices/system/cpu/cpu%u/cpufreq/scaling_cur_freq",
                 cpu) >= (int)sizeof(path)) {
        return;
    }
    if (a90_metrics_read_sysfs_long(path, &khz) < 0) {
        if (snprintf(path, sizeof(path),
                     "/sys/devices/system/cpu/cpu%u/cpufreq/cpuinfo_cur_freq",
                     cpu) >= (int)sizeof(path) ||
            a90_metrics_read_sysfs_long(path, &khz) < 0) {
            return;
        }
    }
    if (khz >= 1000000) {
        long tenths = (khz + 50000) / 100000;

        snprintf(out, out_size, "%ld.%ldG", tenths / 10, tenths % 10);
    } else {
        snprintf(out, out_size, "%ldM", (khz + 500) / 1000);
    }
}
