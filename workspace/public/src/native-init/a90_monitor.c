#include "a90_monitor.h"

#include "a90_console.h"
#include "a90_draw.h"
#include "a90_kms.h"
#include "a90_metrics.h"
#include "a90_sensormap.h"
#include "a90_util.h"

#include <dirent.h>
#include <errno.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define A90_MONITOR_MAX_CPUS 16U
#define A90_MONITOR_MAX_CLUSTERS 8U
#define A90_MONITOR_INVALID_LONG (-1L)

struct a90_monitor_cpu {
    unsigned int id;
    bool online;
    bool have_capacity;
    long capacity;
    long cur_khz;
    long min_khz;
    long max_khz;
    uint64_t related_mask;
    unsigned int cluster_index;
};

struct a90_monitor_cluster {
    uint64_t mask;
    unsigned int cpu_count;
    long min_khz;
    long max_khz;
    char label[16];
};

struct a90_monitor_sample {
    long timestamp_ms;
    unsigned int cpu_count;
    long cpu_usage_pct[A90_MONITOR_MAX_CPUS];
    long cpu_cur_khz[A90_MONITOR_MAX_CPUS];
    long cpu_min_khz[A90_MONITOR_MAX_CPUS];
    long cpu_max_khz[A90_MONITOR_MAX_CPUS];
    int cpu_online[A90_MONITOR_MAX_CPUS];
    long mem_total_kb;
    long mem_available_kb;
    char loadavg[48];
    long gpu_busy_pct;
    long gpu_cur_hz;
    long gpu_max_hz;
    long gpu_temp_millic;
    long battery_capacity_pct;
    long battery_temp_decic;
    long battery_voltage_uv;
    long battery_current_ua;
    long battery_power_uw;
    char battery_status[64];
    struct a90_sensormap_summary sensor_summary;
};

struct a90_monitor_history {
    struct a90_monitor_sample samples[A90_MONITOR_M0_MAX_SAMPLES];
    unsigned int head;
    unsigned int count;
};

struct a90_monitor_state {
    struct a90_monitor_cpu cpus[A90_MONITOR_MAX_CPUS];
    unsigned int cpu_count;
    struct a90_monitor_cluster clusters[A90_MONITOR_MAX_CLUSTERS];
    unsigned int cluster_count;
    bool prev_valid[A90_MONITOR_MAX_CPUS];
    unsigned long long prev_total[A90_MONITOR_MAX_CPUS];
    unsigned long long prev_idle[A90_MONITOR_MAX_CPUS];
    struct a90_monitor_history history;
    char gpu_model[64];
};

static bool monitor_is_digit(char ch) {
    return ch >= '0' && ch <= '9';
}

static int monitor_parse_cpu_dir(const char *name, unsigned int *id_out) {
    char *endptr;
    unsigned long value;

    if (strncmp(name, "cpu", 3) != 0 || !monitor_is_digit(name[3])) {
        return -EINVAL;
    }
    errno = 0;
    value = strtoul(name + 3, &endptr, 10);
    if (errno != 0 || endptr == name + 3 || *endptr != '\0' ||
        value >= A90_MONITOR_MAX_CPUS) {
        return -EINVAL;
    }
    *id_out = (unsigned int)value;
    return 0;
}

static int monitor_read_text(const char *path, char *out, size_t out_size) {
    if (read_trimmed_text_file(path, out, out_size) < 0 || out[0] == '\0') {
        return -1;
    }
    flatten_inline_text(out);
    return 0;
}

static int monitor_read_long_path(const char *path, long *out) {
    char text[64];
    char *endptr;
    long value;

    if (monitor_read_text(path, text, sizeof(text)) < 0) {
        return -1;
    }
    errno = 0;
    value = strtol(text, &endptr, 10);
    if (errno != 0 || endptr == text) {
        return -1;
    }
    *out = value;
    return 0;
}

static int monitor_read_cpu_attr_text(unsigned int cpu,
                                      const char *name,
                                      char *out,
                                      size_t out_size) {
    char path[PATH_MAX];

    if (snprintf(path, sizeof(path),
                 "/sys/devices/system/cpu/cpu%u/%s", cpu, name) >= (int)sizeof(path)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    return monitor_read_text(path, out, out_size);
}

static int monitor_read_cpu_attr_long(unsigned int cpu,
                                      const char *name,
                                      long *out) {
    char path[PATH_MAX];

    if (snprintf(path, sizeof(path),
                 "/sys/devices/system/cpu/cpu%u/%s", cpu, name) >= (int)sizeof(path)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    return monitor_read_long_path(path, out);
}

static bool monitor_parse_cpu_list_mask(const char *text, uint64_t *mask_out) {
    const char *cursor = text;
    uint64_t mask = 0;
    bool any = false;

    while (*cursor != '\0') {
        char *endptr;
        unsigned long first;
        unsigned long last;
        unsigned long item;

        while (*cursor == ' ' || *cursor == '\t' || *cursor == ',') {
            ++cursor;
        }
        if (*cursor == '\0') {
            break;
        }
        if (!monitor_is_digit(*cursor)) {
            return false;
        }
        errno = 0;
        first = strtoul(cursor, &endptr, 10);
        if (errno != 0 || endptr == cursor || first >= 64UL) {
            return false;
        }
        cursor = endptr;
        last = first;
        if (*cursor == '-') {
            ++cursor;
            if (!monitor_is_digit(*cursor)) {
                return false;
            }
            errno = 0;
            last = strtoul(cursor, &endptr, 10);
            if (errno != 0 || endptr == cursor || last >= 64UL || last < first) {
                return false;
            }
            cursor = endptr;
        }
        for (item = first; item <= last; ++item) {
            mask |= 1ULL << item;
        }
        any = true;
    }

    if (!any) {
        return false;
    }
    *mask_out = mask;
    return true;
}

static void monitor_format_cpu_mask(uint64_t mask, char *out, size_t out_size) {
    size_t used = 0;
    unsigned int cpu = 0;
    bool first_token = true;

    if (out_size == 0) {
        return;
    }
    out[0] = '\0';
    while (cpu < 64U) {
        unsigned int start;
        unsigned int end;
        int written;

        if ((mask & (1ULL << cpu)) == 0) {
            ++cpu;
            continue;
        }
        start = cpu;
        end = cpu;
        while (end + 1U < 64U && (mask & (1ULL << (end + 1U))) != 0) {
            ++end;
        }
        if (end == start) {
            written = snprintf(out + used,
                               used < out_size ? out_size - used : 0,
                               "%s%u",
                               first_token ? "" : ",",
                               start);
        } else {
            written = snprintf(out + used,
                               used < out_size ? out_size - used : 0,
                               "%s%u-%u",
                               first_token ? "" : ",",
                               start,
                               end);
        }
        if (written < 0) {
            out[out_size - 1] = '\0';
            return;
        }
        if ((size_t)written >= (used < out_size ? out_size - used : 0)) {
            out[out_size - 1] = '\0';
            return;
        }
        used += (size_t)written;
        first_token = false;
        cpu = end + 1U;
    }
    if (first_token) {
        snprintf(out, out_size, "-");
    }
}

static void monitor_sort_u32(unsigned int *values, unsigned int count) {
    unsigned int i;

    for (i = 1; i < count; ++i) {
        unsigned int value = values[i];
        unsigned int j = i;

        while (j > 0 && values[j - 1U] > value) {
            values[j] = values[j - 1U];
            --j;
        }
        values[j] = value;
    }
}

static int monitor_read_meminfo_kb(const char *label, long *value_out) {
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

static int monitor_discover_cpu_ids(unsigned int *ids, unsigned int *count_out) {
    DIR *dir;
    struct dirent *entry;
    unsigned int count = 0;

    dir = opendir("/sys/devices/system/cpu");
    if (dir == NULL) {
        return -1;
    }

    while ((entry = readdir(dir)) != NULL) {
        unsigned int id;

        if (monitor_parse_cpu_dir(entry->d_name, &id) < 0) {
            continue;
        }
        if (count < A90_MONITOR_MAX_CPUS) {
            ids[count++] = id;
        }
    }
    closedir(dir);

    monitor_sort_u32(ids, count);
    *count_out = count;
    return count > 0 ? 0 : -1;
}

static unsigned int monitor_find_or_add_cluster(struct a90_monitor_state *state,
                                                uint64_t mask,
                                                long min_khz,
                                                long max_khz) {
    unsigned int index;

    for (index = 0; index < state->cluster_count; ++index) {
        if (state->clusters[index].mask == mask) {
            if (min_khz >= 0 &&
                (state->clusters[index].min_khz < 0 || min_khz < state->clusters[index].min_khz)) {
                state->clusters[index].min_khz = min_khz;
            }
            if (max_khz > state->clusters[index].max_khz) {
                state->clusters[index].max_khz = max_khz;
            }
            return index;
        }
    }

    if (state->cluster_count >= A90_MONITOR_MAX_CLUSTERS) {
        return A90_MONITOR_MAX_CLUSTERS - 1U;
    }

    index = state->cluster_count++;
    memset(&state->clusters[index], 0, sizeof(state->clusters[index]));
    state->clusters[index].mask = mask;
    state->clusters[index].min_khz = min_khz;
    state->clusters[index].max_khz = max_khz;
    snprintf(state->clusters[index].label,
             sizeof(state->clusters[index].label),
             "Cluster%u",
             index);
    return index;
}

static void monitor_assign_cluster_labels(struct a90_monitor_state *state) {
    unsigned int rank[A90_MONITOR_MAX_CLUSTERS];
    unsigned int i;

    for (i = 0; i < state->cluster_count; ++i) {
        rank[i] = i;
    }
    for (i = 1; i < state->cluster_count; ++i) {
        unsigned int value = rank[i];
        unsigned int j = i;

        while (j > 0 &&
               state->clusters[rank[j - 1U]].max_khz > state->clusters[value].max_khz) {
            rank[j] = rank[j - 1U];
            --j;
        }
        rank[j] = value;
    }

    if (state->cluster_count == 3U) {
        snprintf(state->clusters[rank[0]].label, sizeof(state->clusters[rank[0]].label), "Silver");
        snprintf(state->clusters[rank[1]].label, sizeof(state->clusters[rank[1]].label), "Gold");
        snprintf(state->clusters[rank[2]].label, sizeof(state->clusters[rank[2]].label), "Prime");
    } else if (state->cluster_count == 2U) {
        snprintf(state->clusters[rank[0]].label, sizeof(state->clusters[rank[0]].label), "Low");
        snprintf(state->clusters[rank[1]].label, sizeof(state->clusters[rank[1]].label), "High");
    } else {
        for (i = 0; i < state->cluster_count; ++i) {
            snprintf(state->clusters[rank[i]].label,
                     sizeof(state->clusters[rank[i]].label),
                     "Cluster%u",
                     i);
        }
    }
}

static int monitor_discover_topology(struct a90_monitor_state *state) {
    unsigned int ids[A90_MONITOR_MAX_CPUS];
    unsigned int count = 0;
    unsigned int index;

    memset(state, 0, sizeof(*state));
    state->gpu_model[0] = '\0';
    (void)monitor_read_text("/sys/class/kgsl/kgsl-3d0/gpu_model",
                            state->gpu_model,
                            sizeof(state->gpu_model));

    if (monitor_discover_cpu_ids(ids, &count) < 0) {
        return -1;
    }

    state->cpu_count = count;
    for (index = 0; index < count; ++index) {
        struct a90_monitor_cpu *cpu = &state->cpus[index];
        char related[128];
        long online = 1;

        cpu->id = ids[index];
        cpu->online = true;
        cpu->capacity = A90_MONITOR_INVALID_LONG;
        cpu->cur_khz = A90_MONITOR_INVALID_LONG;
        cpu->min_khz = A90_MONITOR_INVALID_LONG;
        cpu->max_khz = A90_MONITOR_INVALID_LONG;
        cpu->related_mask = 1ULL << cpu->id;
        cpu->cluster_index = 0;

        if (monitor_read_cpu_attr_long(cpu->id, "online", &online) == 0) {
            cpu->online = online != 0;
        }
        (void)monitor_read_cpu_attr_long(cpu->id,
                                         "cpufreq/scaling_cur_freq",
                                         &cpu->cur_khz);
        (void)monitor_read_cpu_attr_long(cpu->id,
                                         "cpufreq/scaling_min_freq",
                                         &cpu->min_khz);
        if (monitor_read_cpu_attr_long(cpu->id,
                                       "cpufreq/cpuinfo_max_freq",
                                       &cpu->max_khz) < 0) {
            (void)monitor_read_cpu_attr_long(cpu->id,
                                             "cpufreq/scaling_max_freq",
                                             &cpu->max_khz);
        }
        if (monitor_read_cpu_attr_long(cpu->id, "cpu_capacity", &cpu->capacity) == 0) {
            cpu->have_capacity = true;
        }
        if (monitor_read_cpu_attr_text(cpu->id,
                                       "cpufreq/related_cpus",
                                       related,
                                       sizeof(related)) == 0) {
            uint64_t mask;

            if (monitor_parse_cpu_list_mask(related, &mask)) {
                cpu->related_mask = mask;
            }
        }
        cpu->cluster_index = monitor_find_or_add_cluster(state,
                                                         cpu->related_mask,
                                                         cpu->min_khz,
                                                         cpu->max_khz);
    }

    for (index = 0; index < state->cluster_count; ++index) {
        unsigned int cpu_index;
        unsigned int cluster_cpu_count = 0;

        for (cpu_index = 0; cpu_index < state->cpu_count; ++cpu_index) {
            if ((state->clusters[index].mask & (1ULL << state->cpus[cpu_index].id)) != 0) {
                ++cluster_cpu_count;
            }
        }
        state->clusters[index].cpu_count = cluster_cpu_count;
    }

    monitor_assign_cluster_labels(state);
    return 0;
}

static int monitor_find_cpu_index(const struct a90_monitor_state *state,
                                  unsigned int cpu_id) {
    unsigned int index;

    for (index = 0; index < state->cpu_count; ++index) {
        if (state->cpus[index].id == cpu_id) {
            return (int)index;
        }
    }
    return -1;
}

static int monitor_read_proc_cpu_stats(const struct a90_monitor_state *state,
                                       unsigned long long *total_out,
                                       unsigned long long *idle_out,
                                       bool *valid_out) {
    FILE *fp;
    char line[512];
    unsigned int index;

    for (index = 0; index < state->cpu_count; ++index) {
        total_out[index] = 0;
        idle_out[index] = 0;
        valid_out[index] = false;
    }

    fp = fopen("/proc/stat", "r");
    if (fp == NULL) {
        return -1;
    }

    while (fgets(line, sizeof(line), fp) != NULL) {
        unsigned int cpu_id;
        unsigned long long user = 0;
        unsigned long long nice = 0;
        unsigned long long system = 0;
        unsigned long long idle = 0;
        unsigned long long iowait = 0;
        unsigned long long irq = 0;
        unsigned long long softirq = 0;
        unsigned long long steal = 0;
        int cpu_index;

        if (sscanf(line, "cpu%u %llu %llu %llu %llu %llu %llu %llu %llu",
                   &cpu_id,
                   &user,
                   &nice,
                   &system,
                   &idle,
                   &iowait,
                   &irq,
                   &softirq,
                   &steal) < 5) {
            continue;
        }
        cpu_index = monitor_find_cpu_index(state, cpu_id);
        if (cpu_index < 0) {
            continue;
        }
        idle_out[cpu_index] = idle + iowait;
        total_out[cpu_index] = user + nice + system + idle + iowait + irq + softirq + steal;
        valid_out[cpu_index] = true;
    }

    fclose(fp);
    return 0;
}

static void monitor_history_push(struct a90_monitor_history *history,
                                 const struct a90_monitor_sample *sample) {
    history->samples[history->head] = *sample;
    history->head = (history->head + 1U) % A90_MONITOR_M0_MAX_SAMPLES;
    if (history->count < A90_MONITOR_M0_MAX_SAMPLES) {
        ++history->count;
    }
}

static const struct a90_monitor_sample *monitor_history_latest(
        const struct a90_monitor_history *history) {
    unsigned int index;

    if (history->count == 0) {
        return NULL;
    }
    index = (history->head + A90_MONITOR_M0_MAX_SAMPLES - 1U) %
            A90_MONITOR_M0_MAX_SAMPLES;
    return &history->samples[index];
}

static long monitor_percent_from_delta(unsigned long long total_delta,
                                       unsigned long long idle_delta) {
    unsigned long long busy_delta;
    long percent;

    if (total_delta == 0 || idle_delta > total_delta) {
        return A90_MONITOR_INVALID_LONG;
    }
    busy_delta = total_delta - idle_delta;
    percent = (long)((busy_delta * 100ULL + total_delta / 2ULL) / total_delta);
    if (percent < 0) {
        percent = 0;
    } else if (percent > 100) {
        percent = 100;
    }
    return percent;
}

static void monitor_sleep_ms(unsigned int interval_ms) {
    struct timespec request;

    request.tv_sec = (time_t)(interval_ms / 1000U);
    request.tv_nsec = (long)(interval_ms % 1000U) * 1000000L;
    while (nanosleep(&request, &request) < 0 && errno == EINTR) {
    }
}

static int monitor_take_sample(struct a90_monitor_state *state,
                               struct a90_monitor_sample *sample) {
    unsigned long long total[A90_MONITOR_MAX_CPUS];
    unsigned long long idle[A90_MONITOR_MAX_CPUS];
    bool valid[A90_MONITOR_MAX_CPUS];
    unsigned int index;

    memset(sample, 0, sizeof(*sample));
    sample->timestamp_ms = monotonic_millis();
    sample->cpu_count = state->cpu_count;
    sample->mem_total_kb = A90_MONITOR_INVALID_LONG;
    sample->mem_available_kb = A90_MONITOR_INVALID_LONG;
    sample->gpu_busy_pct = A90_MONITOR_INVALID_LONG;
    sample->gpu_cur_hz = A90_MONITOR_INVALID_LONG;
    sample->gpu_max_hz = A90_MONITOR_INVALID_LONG;
    sample->gpu_temp_millic = A90_MONITOR_INVALID_LONG;
    sample->battery_capacity_pct = A90_MONITOR_INVALID_LONG;
    sample->battery_temp_decic = A90_MONITOR_INVALID_LONG;
    sample->battery_voltage_uv = A90_MONITOR_INVALID_LONG;
    sample->battery_current_ua = A90_MONITOR_INVALID_LONG;
    sample->battery_power_uw = A90_MONITOR_INVALID_LONG;
    snprintf(sample->loadavg, sizeof(sample->loadavg), "?");
    snprintf(sample->battery_status, sizeof(sample->battery_status), "?");

    for (index = 0; index < A90_MONITOR_MAX_CPUS; ++index) {
        sample->cpu_usage_pct[index] = A90_MONITOR_INVALID_LONG;
        sample->cpu_cur_khz[index] = A90_MONITOR_INVALID_LONG;
        sample->cpu_min_khz[index] = A90_MONITOR_INVALID_LONG;
        sample->cpu_max_khz[index] = A90_MONITOR_INVALID_LONG;
        sample->cpu_online[index] = -1;
    }

    if (monitor_read_proc_cpu_stats(state, total, idle, valid) == 0) {
        for (index = 0; index < state->cpu_count; ++index) {
            if (valid[index] && state->prev_valid[index] &&
                total[index] >= state->prev_total[index] &&
                idle[index] >= state->prev_idle[index]) {
                sample->cpu_usage_pct[index] =
                    monitor_percent_from_delta(total[index] - state->prev_total[index],
                                               idle[index] - state->prev_idle[index]);
            }
            if (valid[index]) {
                state->prev_total[index] = total[index];
                state->prev_idle[index] = idle[index];
                state->prev_valid[index] = true;
            }
        }
    }

    for (index = 0; index < state->cpu_count; ++index) {
        struct a90_monitor_cpu *cpu = &state->cpus[index];
        long online = cpu->online ? 1 : 0;

        (void)monitor_read_cpu_attr_long(cpu->id, "online", &online);
        cpu->online = online != 0;
        sample->cpu_online[index] = cpu->online ? 1 : 0;
        (void)monitor_read_cpu_attr_long(cpu->id,
                                         "cpufreq/scaling_cur_freq",
                                         &cpu->cur_khz);
        sample->cpu_cur_khz[index] = cpu->cur_khz;
        sample->cpu_min_khz[index] = cpu->min_khz;
        sample->cpu_max_khz[index] = cpu->max_khz;
    }

    (void)monitor_read_meminfo_kb("MemTotal", &sample->mem_total_kb);
    (void)monitor_read_meminfo_kb("MemAvailable", &sample->mem_available_kb);
    (void)monitor_read_text("/proc/loadavg", sample->loadavg, sizeof(sample->loadavg));

    (void)monitor_read_long_path("/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage",
                                 &sample->gpu_busy_pct);
    (void)monitor_read_long_path("/sys/class/kgsl/kgsl-3d0/devfreq/cur_freq",
                                 &sample->gpu_cur_hz);
    if (monitor_read_long_path("/sys/class/kgsl/kgsl-3d0/devfreq/max_freq",
                               &sample->gpu_max_hz) < 0) {
        (void)monitor_read_long_path("/sys/class/kgsl/kgsl-3d0/max_gpuclk",
                                     &sample->gpu_max_hz);
    }
    (void)monitor_read_long_path("/sys/class/kgsl/kgsl-3d0/temp",
                                 &sample->gpu_temp_millic);

    (void)monitor_read_text("/sys/class/power_supply/battery/status",
                            sample->battery_status,
                            sizeof(sample->battery_status));
    (void)monitor_read_long_path("/sys/class/power_supply/battery/capacity",
                                 &sample->battery_capacity_pct);
    (void)monitor_read_long_path("/sys/class/power_supply/battery/temp",
                                 &sample->battery_temp_decic);
    (void)monitor_read_long_path("/sys/class/power_supply/battery/voltage_now",
                                 &sample->battery_voltage_uv);
    (void)monitor_read_long_path("/sys/class/power_supply/battery/current_now",
                                 &sample->battery_current_ua);
    (void)monitor_read_long_path("/sys/class/power_supply/battery/power_now",
                                 &sample->battery_power_uw);

    (void)a90_sensormap_collect_summary(&sample->sensor_summary);
    monitor_history_push(&state->history, sample);
    return 0;
}

static void monitor_print_cluster(const struct a90_monitor_state *state,
                                  const struct a90_monitor_sample *sample,
                                  unsigned int cluster_index,
                                  unsigned int rank) {
    const struct a90_monitor_cluster *cluster = &state->clusters[cluster_index];
    char cpus[96];
    long usage_sum = 0;
    long freq_sum = 0;
    unsigned int usage_count = 0;
    unsigned int freq_count = 0;
    unsigned int cpu_index;

    monitor_format_cpu_mask(cluster->mask, cpus, sizeof(cpus));
    for (cpu_index = 0; cpu_index < state->cpu_count; ++cpu_index) {
        const struct a90_monitor_cpu *cpu = &state->cpus[cpu_index];

        if ((cluster->mask & (1ULL << cpu->id)) == 0) {
            continue;
        }
        if (sample->cpu_usage_pct[cpu_index] >= 0) {
            usage_sum += sample->cpu_usage_pct[cpu_index];
            ++usage_count;
        }
        if (sample->cpu_cur_khz[cpu_index] >= 0) {
            freq_sum += sample->cpu_cur_khz[cpu_index];
            ++freq_count;
        }
    }

    a90_console_printf("gpu.m0.monitor.cluster.%u.label=%s\r\n", rank, cluster->label);
    a90_console_printf("gpu.m0.monitor.cluster.%u.cpus=%s\r\n", rank, cpus);
    a90_console_printf("gpu.m0.monitor.cluster.%u.cpu_count=%u\r\n",
                       rank,
                       cluster->cpu_count);
    a90_console_printf("gpu.m0.monitor.cluster.%u.min_khz=%ld\r\n",
                       rank,
                       cluster->min_khz);
    a90_console_printf("gpu.m0.monitor.cluster.%u.max_khz=%ld\r\n",
                       rank,
                       cluster->max_khz);
    a90_console_printf("gpu.m0.monitor.cluster.%u.cur_avg_khz=%ld\r\n",
                       rank,
                       freq_count > 0 ? freq_sum / (long)freq_count : A90_MONITOR_INVALID_LONG);
    a90_console_printf("gpu.m0.monitor.cluster.%u.usage_avg_pct=%ld\r\n",
                       rank,
                       usage_count > 0 ? usage_sum / (long)usage_count : A90_MONITOR_INVALID_LONG);
}

static void monitor_print_ranked_clusters(const struct a90_monitor_state *state,
                                          const struct a90_monitor_sample *sample) {
    unsigned int rank[A90_MONITOR_MAX_CLUSTERS];
    unsigned int i;

    for (i = 0; i < state->cluster_count; ++i) {
        rank[i] = i;
    }
    for (i = 1; i < state->cluster_count; ++i) {
        unsigned int value = rank[i];
        unsigned int j = i;

        while (j > 0 &&
               state->clusters[rank[j - 1U]].max_khz > state->clusters[value].max_khz) {
            rank[j] = rank[j - 1U];
            --j;
        }
        rank[j] = value;
    }

    for (i = 0; i < state->cluster_count; ++i) {
        monitor_print_cluster(state, sample, rank[i], i);
    }
}

static unsigned int monitor_capacity_readable_count(const struct a90_monitor_state *state) {
    unsigned int count = 0;
    unsigned int index;

    for (index = 0; index < state->cpu_count; ++index) {
        if (state->cpus[index].have_capacity) {
            ++count;
        }
    }
    return count;
}

static void monitor_format_freq(char *out, size_t out_size, long khz) {
    if (khz < 0) {
        snprintf(out, out_size, "?");
    } else if (khz >= 1000000L) {
        long tenths = (khz + 50000L) / 100000L;

        snprintf(out, out_size, "%ld.%ldG", tenths / 10L, tenths % 10L);
    } else {
        snprintf(out, out_size, "%ldM", (khz + 500L) / 1000L);
    }
}

static void monitor_format_hz(char *out, size_t out_size, long hz) {
    if (hz < 0) {
        snprintf(out, out_size, "?");
    } else if (hz >= 1000000000L) {
        long tenths = (hz + 50000000L) / 100000000L;

        snprintf(out, out_size, "%ld.%ldG", tenths / 10L, tenths % 10L);
    } else {
        snprintf(out, out_size, "%ldM", (hz + 500000L) / 1000000L);
    }
}

static void monitor_format_millic(char *out, size_t out_size, long millic) {
    long tenths;
    long whole;
    long frac;

    if (millic < -100000L) {
        snprintf(out, out_size, "?");
        return;
    }
    tenths = millic / 100L;
    whole = tenths / 10L;
    frac = tenths % 10L;
    if (frac < 0) {
        frac = -frac;
    }
    snprintf(out, out_size, "%ld.%ldC", whole, frac);
}

static void monitor_format_decic(char *out, size_t out_size, long decic) {
    long whole;
    long frac;

    if (decic < -1000L) {
        snprintf(out, out_size, "?");
        return;
    }
    whole = decic / 10L;
    frac = decic % 10L;
    if (frac < 0) {
        frac = -frac;
    }
    snprintf(out, out_size, "%ld.%ldC", whole, frac);
}

static long monitor_clamp_percent(long value) {
    if (value < 0) {
        return 0;
    }
    if (value > 100) {
        return 100;
    }
    return value;
}

static void monitor_draw_bar(struct a90_fb *fb,
                             uint32_t x,
                             uint32_t y,
                             uint32_t width,
                             uint32_t height,
                             long percent,
                             uint32_t fill,
                             uint32_t bg) {
    uint32_t filled = (uint32_t)((monitor_clamp_percent(percent) * (long)width) / 100L);

    a90_draw_rect(fb, x, y, width, height, bg);
    if (filled > 0) {
        a90_draw_rect(fb, x, y, filled, height, fill);
    }
    a90_draw_rect_outline(fb, x, y, width, height, 2U, 0x36424c);
}

static void monitor_draw_metric_pair(struct a90_fb *fb,
                                     uint32_t x,
                                     uint32_t y,
                                     uint32_t width,
                                     const char *label,
                                     const char *value,
                                     uint32_t accent,
                                     uint32_t scale) {
    a90_draw_text_fit(fb, x, y, label, 0x9ca8b5, scale, width);
    a90_draw_text_fit(fb, x, y + scale * 10U, value, accent, scale + 1U, width);
}

static void monitor_draw_cluster_row(const struct a90_monitor_state *state,
                                     const struct a90_monitor_sample *sample,
                                     struct a90_fb *fb,
                                     unsigned int cluster_index,
                                     uint32_t x,
                                     uint32_t y,
                                     uint32_t width,
                                     uint32_t scale,
                                     uint32_t accent) {
    const struct a90_monitor_cluster *cluster = &state->clusters[cluster_index];
    char cpus[64];
    char freq[24];
    char line[128];
    long usage_sum = 0;
    long freq_sum = 0;
    unsigned int usage_count = 0;
    unsigned int freq_count = 0;
    unsigned int cpu_index;
    uint32_t bar_x;
    uint32_t bar_w;

    monitor_format_cpu_mask(cluster->mask, cpus, sizeof(cpus));
    for (cpu_index = 0; cpu_index < state->cpu_count; ++cpu_index) {
        const struct a90_monitor_cpu *cpu = &state->cpus[cpu_index];

        if ((cluster->mask & (1ULL << cpu->id)) == 0) {
            continue;
        }
        if (sample->cpu_usage_pct[cpu_index] >= 0) {
            usage_sum += sample->cpu_usage_pct[cpu_index];
            ++usage_count;
        }
        if (sample->cpu_cur_khz[cpu_index] >= 0) {
            freq_sum += sample->cpu_cur_khz[cpu_index];
            ++freq_count;
        }
    }

    monitor_format_freq(freq,
                        sizeof(freq),
                        freq_count > 0 ? freq_sum / (long)freq_count : A90_MONITOR_INVALID_LONG);
    snprintf(line,
             sizeof(line),
             "%s CPU %s  %s  %ld%%",
             cluster->label,
             cpus,
             freq,
             usage_count > 0 ? usage_sum / (long)usage_count : A90_MONITOR_INVALID_LONG);

    a90_draw_text_fit(fb, x, y, line, 0xffffff, scale, width);
    bar_x = x;
    bar_w = width;
    monitor_draw_bar(fb,
                     bar_x,
                     y + scale * 11U,
                     bar_w,
                     scale * 4U,
                     usage_count > 0 ? usage_sum / (long)usage_count : 0,
                     accent,
                     0x131923);
}

static void monitor_draw_cpu_grid(const struct a90_monitor_state *state,
                                  const struct a90_monitor_sample *sample,
                                  struct a90_fb *fb,
                                  uint32_t x,
                                  uint32_t y,
                                  uint32_t width,
                                  uint32_t scale) {
    uint32_t col_gap = scale * 4U;
    uint32_t row_gap = scale * 4U;
    uint32_t cell_w = (width - col_gap) / 2U;
    uint32_t cell_h = scale * 14U;
    unsigned int index;

    for (index = 0; index < state->cpu_count; ++index) {
        char freq[24];
        char line[96];
        uint32_t col = index % 2U;
        uint32_t row = index / 2U;
        uint32_t cell_x = x + col * (cell_w + col_gap);
        uint32_t cell_y = y + row * (cell_h + row_gap);
        long usage = sample->cpu_usage_pct[index] >= 0 ? sample->cpu_usage_pct[index] : 0;
        uint32_t fill = 0x66ddff;

        if (strcmp(state->clusters[state->cpus[index].cluster_index].label, "Silver") == 0) {
            fill = 0x88ee88;
        } else if (strcmp(state->clusters[state->cpus[index].cluster_index].label, "Gold") == 0) {
            fill = 0xffcc33;
        } else if (strcmp(state->clusters[state->cpus[index].cluster_index].label, "Prime") == 0) {
            fill = 0xff7777;
        }

        monitor_format_freq(freq, sizeof(freq), sample->cpu_cur_khz[index]);
        snprintf(line,
                 sizeof(line),
                 "CPU%u %s %ld%%",
                 state->cpus[index].id,
                 freq,
                 sample->cpu_usage_pct[index]);
        a90_draw_text_fit(fb, cell_x, cell_y, line, 0xdce6f0, scale, cell_w);
        monitor_draw_bar(fb,
                         cell_x,
                         cell_y + scale * 8U,
                         cell_w,
                         scale * 4U,
                         usage,
                         fill,
                         0x111722);
    }
}

static int monitor_prepare_state_for_display(struct a90_monitor_state *state,
                                             struct a90_monitor_sample *sample,
                                             unsigned int samples,
                                             unsigned int interval_ms) {
    unsigned int index;

    if (monitor_discover_topology(state) < 0) {
        return -1;
    }
    for (index = 0; index < samples; ++index) {
        (void)monitor_take_sample(state, sample);
        if (index + 1U < samples && interval_ms > 0) {
            monitor_sleep_ms(interval_ms);
        }
    }
    return monitor_history_latest(&state->history) != NULL ? 0 : -1;
}

static int monitor_draw_dashboard(const struct a90_monitor_state *state,
                                  const struct a90_monitor_sample *sample) {
    struct a90_fb *fb;
    uint32_t width;
    uint32_t height;
    uint32_t margin;
    uint32_t scale;
    uint32_t title_scale;
    uint32_t y;
    uint32_t section_h;
    uint32_t gap;
    uint32_t content_w;
    char line[160];
    char gpu_freq[24];
    char gpu_temp[24];
    char bat_temp[24];
    char mem_line[64];
    char therm_line[96];
    unsigned int cluster_index;

    if (a90_kms_begin_frame(0x061018) < 0) {
        return negative_errno_or(ENODEV);
    }
    fb = a90_kms_framebuffer();
    if (fb == NULL) {
        return -ENODEV;
    }

    width = fb->width;
    height = fb->height;
    margin = width / 18U;
    if (margin < 32U) {
        margin = 32U;
    }
    scale = width >= 1000U ? 4U : 3U;
    title_scale = scale + 2U;
    gap = scale * 6U;
    content_w = width - margin * 2U;
    y = margin;

    a90_draw_rect(fb, 0, 0, width, height, 0x061018);
    a90_draw_rect(fb, 0, 0, width, scale * 5U, 0x66ddff);
    a90_draw_rect(fb, 0, height - scale * 5U, width, scale * 5U, 0xffcc33);

    a90_draw_text_fit(fb,
                      margin,
                      y,
                      "A90 SYSTEM MONITOR",
                      0xffffff,
                      title_scale,
                      content_w);
    y += title_scale * 10U;
    snprintf(line,
             sizeof(line),
             "READ ONLY M1 STATIC DASHBOARD  SAMPLES %u  HISTORY %u",
             A90_MONITOR_M0_DEFAULT_SAMPLES,
             state->history.count);
    a90_draw_text_fit(fb, margin, y, line, 0x9ca8b5, scale, content_w);
    y += scale * 14U + gap;

    a90_draw_text_fit(fb, margin, y, "HW INFO", 0xffcc33, scale + 1U, content_w);
    y += scale * 12U;
    section_h = scale * 24U;
    a90_draw_rect(fb, margin, y, content_w, section_h, 0x101820);
    a90_draw_rect_outline(fb, margin, y, content_w, section_h, 2U, 0x304050);
    monitor_format_hz(gpu_freq, sizeof(gpu_freq), sample->gpu_cur_hz);
    monitor_format_millic(gpu_temp, sizeof(gpu_temp), sample->gpu_temp_millic);
    monitor_format_decic(bat_temp, sizeof(bat_temp), sample->battery_temp_decic);
    snprintf(mem_line,
             sizeof(mem_line),
             "%ld/%ldMB",
             sample->mem_total_kb >= 0 && sample->mem_available_kb >= 0 ?
             (sample->mem_total_kb - sample->mem_available_kb) / 1024L : A90_MONITOR_INVALID_LONG,
             sample->mem_total_kb >= 0 ? sample->mem_total_kb / 1024L : A90_MONITOR_INVALID_LONG);
    monitor_draw_metric_pair(fb, margin + scale * 4U, y + scale * 4U,
                             content_w / 4U, "GPU", gpu_freq, 0x66ddff, scale);
    snprintf(line, sizeof(line), "%ld%% %s", sample->gpu_busy_pct, gpu_temp);
    monitor_draw_metric_pair(fb, margin + content_w / 4U, y + scale * 4U,
                             content_w / 4U, "GPU LOAD", line, 0x88ee88, scale);
    snprintf(line, sizeof(line), "%ld%% %s", sample->battery_capacity_pct, bat_temp);
    monitor_draw_metric_pair(fb, margin + content_w / 2U, y + scale * 4U,
                             content_w / 4U, "BATTERY", line, 0xffcc33, scale);
    monitor_draw_metric_pair(fb, margin + (content_w * 3U) / 4U, y + scale * 4U,
                             content_w / 4U - scale * 4U, "MEMORY", mem_line, 0xffffff, scale);
    y += section_h + gap;

    a90_draw_text_fit(fb, margin, y, "CPU CLUSTERS", 0xffcc33, scale + 1U, content_w);
    y += scale * 12U;
    for (cluster_index = 0; cluster_index < state->cluster_count; ++cluster_index) {
        uint32_t color = 0x66ddff;

        if (strcmp(state->clusters[cluster_index].label, "Silver") == 0) {
            color = 0x88ee88;
        } else if (strcmp(state->clusters[cluster_index].label, "Gold") == 0) {
            color = 0xffcc33;
        } else if (strcmp(state->clusters[cluster_index].label, "Prime") == 0) {
            color = 0xff7777;
        }
        monitor_draw_cluster_row(state,
                                 sample,
                                 fb,
                                 cluster_index,
                                 margin,
                                 y,
                                 content_w,
                                 scale,
                                 color);
        y += scale * 20U;
    }
    y += gap;

    a90_draw_text_fit(fb, margin, y, "PER CORE", 0xffcc33, scale + 1U, content_w);
    y += scale * 12U;
    monitor_draw_cpu_grid(state, sample, fb, margin, y, content_w, scale);
    y += scale * 74U + gap;

    a90_draw_text_fit(fb, margin, y, "DOOM INFO", 0xffcc33, scale + 1U, content_w);
    y += scale * 12U;
    a90_draw_rect(fb, margin, y, content_w, scale * 28U, 0x101820);
    a90_draw_rect_outline(fb, margin, y, content_w, scale * 28U, 2U, 0x304050);
    snprintf(line,
             sizeof(line),
             "ENGINE V3317  INPUT UDP NCM  AUDIO NATIVE SFX  DISPLAY KMS");
    a90_draw_text_fit(fb, margin + scale * 4U, y + scale * 4U, line, 0xdce6f0, scale, content_w - scale * 8U);
    snprintf(therm_line,
             sizeof(therm_line),
             "THERMAL %d/%d MAX %s",
             sample->sensor_summary.thermal_readable,
             sample->sensor_summary.thermal_zones,
             sample->sensor_summary.max_temp_type[0] ? sample->sensor_summary.max_temp_type : "-");
    a90_draw_text_fit(fb, margin + scale * 4U, y + scale * 14U, therm_line, 0x9ca8b5, scale, content_w - scale * 8U);

    a90_draw_text_fit(fb,
                      margin,
                      height - margin - scale * 10U,
                      "BRIDGE hide/q TO EXIT  READS ONLY  NO POWER WRITES",
                      0xffffff,
                      scale,
                      content_w);

    return a90_kms_present("gpu-m1-monitor-dashboard", true);
}

int a90_monitor_m0_sampler_probe(unsigned int samples, unsigned int interval_ms) {
    struct a90_monitor_state state;
    struct a90_monitor_sample sample;
    const struct a90_monitor_sample *latest;
    unsigned int index;
    long started_ms = monotonic_millis();

    if (samples < A90_MONITOR_M0_MIN_SAMPLES) {
        samples = A90_MONITOR_M0_MIN_SAMPLES;
    } else if (samples > A90_MONITOR_M0_MAX_SAMPLES) {
        samples = A90_MONITOR_M0_MAX_SAMPLES;
    }
    if (interval_ms > A90_MONITOR_M0_MAX_INTERVAL_MS) {
        interval_ms = A90_MONITOR_M0_MAX_INTERVAL_MS;
    }

    a90_console_printf("gpu.m0.monitor.scope=read-only-sysfs-proc-sampler\r\n");
    a90_console_printf("gpu.m0.monitor.samples_requested=%u\r\n", samples);
    a90_console_printf("gpu.m0.monitor.interval_ms=%u\r\n", interval_ms);
    a90_console_printf("gpu.m0.monitor.power_write_attempted=0\r\n");
    a90_console_printf("gpu.m0.monitor.kms_present_attempted=0\r\n");

    if (monitor_discover_topology(&state) < 0) {
        a90_console_printf("gpu.m0.monitor.result=cpu-discovery-failed\r\n");
        a90_console_printf("gpu.m0.monitor.errno=%d\r\n", errno);
        return -errno;
    }

    a90_console_printf("gpu.m0.monitor.cpu.count=%u\r\n", state.cpu_count);
    a90_console_printf("gpu.m0.monitor.cpu.capacity_readable_count=%u\r\n",
                       monitor_capacity_readable_count(&state));
    a90_console_printf("gpu.m0.monitor.cluster.count=%u\r\n", state.cluster_count);
    a90_console_printf("gpu.m0.monitor.cluster.detect_source=cpufreq-related-cpus-plus-max-freq\r\n");
    a90_console_printf("gpu.m0.monitor.gpu.model=%s\r\n",
                       state.gpu_model[0] != '\0' ? state.gpu_model : "?");

    for (index = 0; index < samples; ++index) {
        (void)monitor_take_sample(&state, &sample);
        if (index + 1U < samples && interval_ms > 0) {
            monitor_sleep_ms(interval_ms);
        }
    }

    latest = monitor_history_latest(&state.history);
    if (latest == NULL) {
        a90_console_printf("gpu.m0.monitor.result=no-samples\r\n");
        return -EIO;
    }

    a90_console_printf("gpu.m0.monitor.history.capacity=%u\r\n", A90_MONITOR_M0_MAX_SAMPLES);
    a90_console_printf("gpu.m0.monitor.history.count=%u\r\n", state.history.count);
    a90_console_printf("gpu.m0.monitor.history.head=%u\r\n", state.history.head);
    a90_console_printf("gpu.m0.monitor.last.timestamp_ms=%ld\r\n", latest->timestamp_ms);

    monitor_print_ranked_clusters(&state, latest);

    for (index = 0; index < state.cpu_count; ++index) {
        const struct a90_monitor_cpu *cpu = &state.cpus[index];

        a90_console_printf("gpu.m0.monitor.cpu.%u.id=%u\r\n", index, cpu->id);
        a90_console_printf("gpu.m0.monitor.cpu.%u.cluster=%s\r\n",
                           index,
                           state.clusters[cpu->cluster_index].label);
        a90_console_printf("gpu.m0.monitor.cpu.%u.online=%d\r\n",
                           index,
                           latest->cpu_online[index]);
        a90_console_printf("gpu.m0.monitor.cpu.%u.cur_khz=%ld\r\n",
                           index,
                           latest->cpu_cur_khz[index]);
        a90_console_printf("gpu.m0.monitor.cpu.%u.min_khz=%ld\r\n",
                           index,
                           latest->cpu_min_khz[index]);
        a90_console_printf("gpu.m0.monitor.cpu.%u.max_khz=%ld\r\n",
                           index,
                           latest->cpu_max_khz[index]);
        a90_console_printf("gpu.m0.monitor.cpu.%u.usage_pct=%ld\r\n",
                           index,
                           latest->cpu_usage_pct[index]);
        a90_console_printf("gpu.m0.monitor.cpu.%u.capacity=%ld\r\n",
                           index,
                           cpu->have_capacity ? cpu->capacity : A90_MONITOR_INVALID_LONG);
    }

    a90_console_printf("gpu.m0.monitor.mem.total_kb=%ld\r\n", latest->mem_total_kb);
    a90_console_printf("gpu.m0.monitor.mem.available_kb=%ld\r\n", latest->mem_available_kb);
    a90_console_printf("gpu.m0.monitor.mem.used_kb=%ld\r\n",
                       latest->mem_total_kb >= 0 && latest->mem_available_kb >= 0 ?
                       latest->mem_total_kb - latest->mem_available_kb :
                       A90_MONITOR_INVALID_LONG);
    a90_console_printf("gpu.m0.monitor.loadavg=%s\r\n", latest->loadavg);

    a90_console_printf("gpu.m0.monitor.gpu.busy_pct=%ld\r\n", latest->gpu_busy_pct);
    a90_console_printf("gpu.m0.monitor.gpu.cur_hz=%ld\r\n", latest->gpu_cur_hz);
    a90_console_printf("gpu.m0.monitor.gpu.max_hz=%ld\r\n", latest->gpu_max_hz);
    a90_console_printf("gpu.m0.monitor.gpu.temp_millic=%ld\r\n", latest->gpu_temp_millic);

    a90_console_printf("gpu.m0.monitor.thermal.zones=%d\r\n",
                       latest->sensor_summary.thermal_zones);
    a90_console_printf("gpu.m0.monitor.thermal.readable=%d\r\n",
                       latest->sensor_summary.thermal_readable);
    a90_console_printf("gpu.m0.monitor.thermal.cooling_devices=%d\r\n",
                       latest->sensor_summary.cooling_devices);
    a90_console_printf("gpu.m0.monitor.thermal.max_type=%s\r\n",
                       latest->sensor_summary.max_temp_type[0] ?
                       latest->sensor_summary.max_temp_type : "-");
    a90_console_printf("gpu.m0.monitor.thermal.max_millic=%ld\r\n",
                       latest->sensor_summary.max_temp_millic);

    a90_console_printf("gpu.m0.monitor.power.supplies=%d\r\n",
                       latest->sensor_summary.power_supplies);
    a90_console_printf("gpu.m0.monitor.power.batteries=%d\r\n",
                       latest->sensor_summary.power_batteries);
    a90_console_printf("gpu.m0.monitor.power.chargers=%d\r\n",
                       latest->sensor_summary.power_chargers);
    a90_console_printf("gpu.m0.monitor.battery.status=%s\r\n", latest->battery_status);
    a90_console_printf("gpu.m0.monitor.battery.capacity_pct=%ld\r\n",
                       latest->battery_capacity_pct);
    a90_console_printf("gpu.m0.monitor.battery.temp_decic=%ld\r\n",
                       latest->battery_temp_decic);
    a90_console_printf("gpu.m0.monitor.battery.voltage_uv=%ld\r\n",
                       latest->battery_voltage_uv);
    a90_console_printf("gpu.m0.monitor.battery.current_ua=%ld\r\n",
                       latest->battery_current_ua);
    a90_console_printf("gpu.m0.monitor.battery.power_uw=%ld\r\n",
                       latest->battery_power_uw);

    a90_console_printf("gpu.m0.monitor.elapsed_ms=%ld\r\n",
                       monotonic_millis() - started_ms);
    a90_console_printf("gpu.m0.monitor.result=sampler-pass\r\n");
    return 0;
}

int a90_monitor_m1_dashboard_probe(unsigned int samples,
                                    unsigned int interval_ms,
                                    unsigned int hold_ms) {
    struct a90_monitor_state state;
    struct a90_monitor_sample sample;
    const struct a90_monitor_sample *latest;
    struct a90_kms_info kms_info;
    long started_ms = monotonic_millis();
    int present_rc;

    if (samples < A90_MONITOR_M0_MIN_SAMPLES) {
        samples = A90_MONITOR_M0_MIN_SAMPLES;
    } else if (samples > A90_MONITOR_M0_MAX_SAMPLES) {
        samples = A90_MONITOR_M0_MAX_SAMPLES;
    }
    if (interval_ms > A90_MONITOR_M0_MAX_INTERVAL_MS) {
        interval_ms = A90_MONITOR_M0_MAX_INTERVAL_MS;
    }
    if (hold_ms > A90_MONITOR_M1_MAX_HOLD_MS) {
        hold_ms = A90_MONITOR_M1_MAX_HOLD_MS;
    }

    a90_console_printf("gpu.m1.monitor.scope=static-dashboard-existing-draw-primitives\r\n");
    a90_console_printf("gpu.m1.monitor.samples_requested=%u\r\n", samples);
    a90_console_printf("gpu.m1.monitor.interval_ms=%u\r\n", interval_ms);
    a90_console_printf("gpu.m1.monitor.hold_ms=%u\r\n", hold_ms);
    a90_console_printf("gpu.m1.monitor.power_write_attempted=0\r\n");
    a90_console_printf("gpu.m1.monitor.kgsl_submit_attempted=0\r\n");
    a90_console_printf("gpu.m1.monitor.kms_present_attempted=1\r\n");

    if (monitor_prepare_state_for_display(&state, &sample, samples, interval_ms) < 0) {
        a90_console_printf("gpu.m1.monitor.result=sampler-failed\r\n");
        a90_console_printf("gpu.m1.monitor.errno=%d\r\n", errno);
        return -errno;
    }
    latest = monitor_history_latest(&state.history);
    if (latest == NULL) {
        a90_console_printf("gpu.m1.monitor.result=no-samples\r\n");
        return -EIO;
    }

    present_rc = monitor_draw_dashboard(&state, latest);
    a90_kms_info(&kms_info);

    a90_console_printf("gpu.m1.monitor.cpu.count=%u\r\n", state.cpu_count);
    a90_console_printf("gpu.m1.monitor.cluster.count=%u\r\n", state.cluster_count);
    a90_console_printf("gpu.m1.monitor.history.count=%u\r\n", state.history.count);
    a90_console_printf("gpu.m1.monitor.gpu.model=%s\r\n",
                       state.gpu_model[0] != '\0' ? state.gpu_model : "?");
    a90_console_printf("gpu.m1.monitor.fb.initialized=%d\r\n", kms_info.initialized ? 1 : 0);
    a90_console_printf("gpu.m1.monitor.fb.width=%u\r\n", kms_info.width);
    a90_console_printf("gpu.m1.monitor.fb.height=%u\r\n", kms_info.height);
    a90_console_printf("gpu.m1.monitor.fb.stride=%u\r\n", kms_info.stride);
    a90_console_printf("gpu.m1.monitor.present_rc=%d\r\n", present_rc);
    if (present_rc < 0) {
        a90_console_printf("gpu.m1.monitor.result=kms-present-failed\r\n");
        return present_rc;
    }

    if (hold_ms > 0) {
        long hold_started_ms = monotonic_millis();

        monitor_sleep_ms(hold_ms);
        a90_console_printf("gpu.m1.monitor.hold_elapsed_ms=%ld\r\n",
                           monotonic_millis() - hold_started_ms);
    }

    a90_console_printf("gpu.m1.monitor.elapsed_ms=%ld\r\n",
                       monotonic_millis() - started_ms);
    a90_console_printf("gpu.m1.monitor.result=dashboard-presented\r\n");
    return 0;
}
