#include "a90_benchmark.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "a90_log.h"
#include "a90_metrics.h"
#include "a90_util.h"

#define A90_BENCHMARK_LINE_MAX 1024

struct a90_benchmark_diskstats {
    unsigned long long read_sectors;
    unsigned long long write_sectors;
    int valid;
};

static int a90_benchmark_stage_valid(const char *stage) {
    const unsigned char *cursor = (const unsigned char *)stage;

    if (stage == NULL || *stage == '\0') {
        return 0;
    }
    while (*cursor != '\0') {
        if (!((*cursor >= 'a' && *cursor <= 'z') ||
              (*cursor >= '0' && *cursor <= '9') ||
              *cursor == '_')) {
            return 0;
        }
        ++cursor;
    }
    return 1;
}

static uint64_t a90_benchmark_previous_emit_duration_ms;

static int a90_benchmark_boottime_ms(uint64_t *value) {
    struct timespec ts;

    if (value == NULL || clock_gettime(CLOCK_BOOTTIME, &ts) < 0) {
        return -1;
    }
    *value = (uint64_t)ts.tv_sec * 1000ULL +
             (uint64_t)ts.tv_nsec / 1000000ULL;
    return 0;
}

static void a90_benchmark_read_raw(const char *path, char *out, size_t out_size) {
    char value[128];
    char *end = NULL;
    long long parsed;

    snprintf(out, out_size, "na");
    if (read_trimmed_text_file(path, value, sizeof(value)) < 0 || value[0] == '\0') {
        return;
    }
    errno = 0;
    parsed = strtoll(value, &end, 10);
    if (errno != 0 || end == value || *end != '\0') {
        return;
    }
    snprintf(out, out_size, "%lld", parsed);
}

static void a90_benchmark_read_cpu_khz(unsigned int cpu, char *out, size_t out_size) {
    char path[160];

    if (snprintf(path,
                 sizeof(path),
                 "/sys/devices/system/cpu/cpu%u/cpufreq/scaling_cur_freq",
                 cpu) >= (int)sizeof(path)) {
        snprintf(out, out_size, "na");
        return;
    }
    a90_benchmark_read_raw(path, out, out_size);
    if (strcmp(out, "na") == 0) {
        if (snprintf(path,
                     sizeof(path),
                     "/sys/devices/system/cpu/cpu%u/cpufreq/cpuinfo_cur_freq",
                     cpu) >= (int)sizeof(path)) {
            return;
        }
        a90_benchmark_read_raw(path, out, out_size);
    }
}

static struct a90_benchmark_diskstats a90_benchmark_read_mmc_diskstats(void) {
    struct a90_benchmark_diskstats result = {0, 0, 0};
    FILE *stream;
    char line[512];

    stream = fopen("/proc/diskstats", "r");
    if (stream == NULL) {
        return result;
    }
    while (fgets(line, sizeof(line), stream) != NULL) {
        unsigned int major_num;
        unsigned int minor_num;
        char name[64];
        unsigned long long reads_completed;
        unsigned long long reads_merged;
        unsigned long long read_sectors;
        unsigned long long read_ms;
        unsigned long long writes_completed;
        unsigned long long writes_merged;
        unsigned long long write_sectors;
        unsigned long long write_ms;

        if (sscanf(line,
                   " %u %u %63s %llu %llu %llu %llu %llu %llu %llu %llu",
                   &major_num,
                   &minor_num,
                   name,
                   &reads_completed,
                   &reads_merged,
                   &read_sectors,
                   &read_ms,
                   &writes_completed,
                   &writes_merged,
                   &write_sectors,
                   &write_ms) != 11) {
            continue;
        }
        (void)major_num;
        (void)minor_num;
        (void)reads_completed;
        (void)reads_merged;
        (void)read_ms;
        (void)writes_completed;
        (void)writes_merged;
        (void)write_ms;
        if (strcmp(name, "mmcblk0") == 0) {
            result.read_sectors = read_sectors;
            result.write_sectors = write_sectors;
            result.valid = 1;
            break;
        }
    }
    fclose(stream);
    return result;
}

static void a90_benchmark_calculated_power(char *out, size_t out_size) {
    char voltage[64];
    char current[64];
    char *end = NULL;
    long long voltage_uv;
    long long current_ua;

    snprintf(out, out_size, "na");
    a90_benchmark_read_raw(
        "/sys/class/power_supply/battery/voltage_now", voltage, sizeof(voltage));
    a90_benchmark_read_raw(
        "/sys/class/power_supply/battery/current_now", current, sizeof(current));
    if (strcmp(voltage, "na") == 0 || strcmp(current, "na") == 0) {
        return;
    }
    errno = 0;
    voltage_uv = strtoll(voltage, &end, 10);
    if (errno != 0 || end == voltage || *end != '\0') {
        return;
    }
    errno = 0;
    current_ua = strtoll(current, &end, 10);
    if (errno != 0 || end == current || *end != '\0') {
        return;
    }
    snprintf(out, out_size, "%lld", (voltage_uv * current_ua) / 1000000LL);
}

static void a90_benchmark_emit_internal(const char *stage, int sample_telemetry) {
    struct a90_metrics_snapshot snapshot;
    struct a90_benchmark_diskstats diskstats;
    char cpu0_khz[64];
    char cpu4_khz[64];
    char cpu7_khz[64];
    char gpu_hz[64];
    char battery_current_ua[64];
    char battery_voltage_uv[64];
    char power_now_raw[64];
    char power_avg_raw[64];
    char calculated_power_uw[64];
    char mmc_read_sectors[64];
    char mmc_write_sectors[64];
    char line[A90_BENCHMARK_LINE_MAX];
    uint64_t started_ms;
    uint64_t sampled_ms;
    uint64_t ended_ms;
    uint64_t prior_emit_duration_ms;
    int clock_ok;
    int length;

    if (!a90_benchmark_stage_valid(stage)) {
        return;
    }
    prior_emit_duration_ms = a90_benchmark_previous_emit_duration_ms;
    clock_ok = a90_benchmark_boottime_ms(&started_ms) == 0;
    if (!clock_ok) {
        started_ms = 0;
    }
    if (sample_telemetry) {
        a90_metrics_read_snapshot(&snapshot);
        a90_benchmark_read_cpu_khz(0, cpu0_khz, sizeof(cpu0_khz));
        a90_benchmark_read_cpu_khz(4, cpu4_khz, sizeof(cpu4_khz));
        a90_benchmark_read_cpu_khz(7, cpu7_khz, sizeof(cpu7_khz));
        a90_benchmark_read_raw(
            "/sys/class/kgsl/kgsl-3d0/devfreq/cur_freq", gpu_hz, sizeof(gpu_hz));
        a90_benchmark_read_raw(
            "/sys/class/power_supply/battery/current_now",
            battery_current_ua,
            sizeof(battery_current_ua));
        a90_benchmark_read_raw(
            "/sys/class/power_supply/battery/voltage_now",
            battery_voltage_uv,
            sizeof(battery_voltage_uv));
        a90_benchmark_read_raw(
            "/sys/class/power_supply/battery/power_now",
            power_now_raw,
            sizeof(power_now_raw));
        a90_benchmark_read_raw(
            "/sys/class/power_supply/battery/power_avg",
            power_avg_raw,
            sizeof(power_avg_raw));
        a90_benchmark_calculated_power(calculated_power_uw, sizeof(calculated_power_uw));
        diskstats = a90_benchmark_read_mmc_diskstats();
        if (diskstats.valid) {
            snprintf(mmc_read_sectors,
                     sizeof(mmc_read_sectors),
                     "%llu",
                     diskstats.read_sectors);
            snprintf(mmc_write_sectors,
                     sizeof(mmc_write_sectors),
                     "%llu",
                     diskstats.write_sectors);
        } else {
            snprintf(mmc_read_sectors, sizeof(mmc_read_sectors), "na");
            snprintf(mmc_write_sectors, sizeof(mmc_write_sectors), "na");
        }
    } else {
        snprintf(snapshot.cpu_temp, sizeof(snapshot.cpu_temp), "na");
        snprintf(snapshot.gpu_temp, sizeof(snapshot.gpu_temp), "na");
        snprintf(snapshot.battery_temp, sizeof(snapshot.battery_temp), "na");
        snprintf(snapshot.cpu_usage, sizeof(snapshot.cpu_usage), "na");
        snprintf(snapshot.gpu_usage, sizeof(snapshot.gpu_usage), "na");
        snprintf(snapshot.memory, sizeof(snapshot.memory), "na");
        snprintf(snapshot.loadavg, sizeof(snapshot.loadavg), "na");
        snprintf(cpu0_khz, sizeof(cpu0_khz), "na");
        snprintf(cpu4_khz, sizeof(cpu4_khz), "na");
        snprintf(cpu7_khz, sizeof(cpu7_khz), "na");
        snprintf(gpu_hz, sizeof(gpu_hz), "na");
        snprintf(battery_current_ua, sizeof(battery_current_ua), "na");
        snprintf(battery_voltage_uv, sizeof(battery_voltage_uv), "na");
        snprintf(power_now_raw, sizeof(power_now_raw), "na");
        snprintf(power_avg_raw, sizeof(power_avg_raw), "na");
        snprintf(calculated_power_uw, sizeof(calculated_power_uw), "na");
        snprintf(mmc_read_sectors, sizeof(mmc_read_sectors), "na");
        snprintf(mmc_write_sectors, sizeof(mmc_write_sectors), "na");
    }
    if (a90_benchmark_boottime_ms(&sampled_ms) < 0) {
        sampled_ms = started_ms;
        clock_ok = 0;
    }

    length = snprintf(
        line,
        sizeof(line),
        "A90BENCH schema=%s stage=%s boottime_ms=%llu clock_ok=%d "
        "telemetry_sampled=%d sample_duration_ms=%llu prior_emit_duration_ms=%llu "
        "cpu_temp_c=%s gpu_temp_c=%s battery_temp_c=%s "
        "cpu_usage_pct=%s gpu_usage_pct=%s memory_mb=%s load1=%s "
        "cpu0_khz=%s cpu4_khz=%s cpu7_khz=%s gpu_hz=%s "
        "battery_current_ua=%s battery_voltage_uv=%s "
        "power_now_raw=%s power_avg_raw=%s calculated_power_uw=%s "
        "mmc_read_sectors=%s mmc_write_sectors=%s",
        A90_BENCHMARK_SCHEMA,
        stage,
        (unsigned long long)started_ms,
        clock_ok,
        sample_telemetry ? 1 : 0,
        (unsigned long long)(sampled_ms >= started_ms ? sampled_ms - started_ms : 0),
        (unsigned long long)prior_emit_duration_ms,
        snapshot.cpu_temp,
        snapshot.gpu_temp,
        snapshot.battery_temp,
        snapshot.cpu_usage,
        snapshot.gpu_usage,
        snapshot.memory,
        snapshot.loadavg,
        cpu0_khz,
        cpu4_khz,
        cpu7_khz,
        gpu_hz,
        battery_current_ua,
        battery_voltage_uv,
        power_now_raw,
        power_avg_raw,
        calculated_power_uw,
        mmc_read_sectors,
        mmc_write_sectors);
    if (length < 0 || (size_t)length >= sizeof(line)) {
        return;
    }
    a90_logf("benchmark", "%s", line);
    if (clock_ok && a90_benchmark_boottime_ms(&ended_ms) == 0 &&
        ended_ms >= started_ms) {
        a90_benchmark_previous_emit_duration_ms = ended_ms - started_ms;
    } else {
        a90_benchmark_previous_emit_duration_ms = 0;
    }
}

void a90_benchmark_mark(const char *stage) {
    a90_benchmark_emit_internal(stage, 0);
}

void a90_benchmark_emit(const char *stage) {
    a90_benchmark_emit_internal(stage, 1);
}
