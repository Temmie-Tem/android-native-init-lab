#ifndef A90_METRICS_H
#define A90_METRICS_H

#include <stddef.h>

struct a90_metrics_snapshot {
    char battery_status[64];
    char battery_pct[32];
    char battery_temp[32];
    char battery_voltage[32];
    char cpu_temp[32];
    char cpu_usage[16];
    char gpu_temp[32];
    char gpu_usage[16];
    char memory[64];
    char loadavg[32];
    char uptime[32];
    char power_now[32];
    char power_avg[32];
};

int a90_metrics_read_sysfs_long(const char *path, long *value_out);
void a90_metrics_read_snapshot(struct a90_metrics_snapshot *snapshot);
void a90_metrics_read_cpu_freq_label(unsigned int cpu, char *out, size_t out_size);

#endif
