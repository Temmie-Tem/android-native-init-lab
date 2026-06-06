#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

static volatile sig_atomic_t stop_requested;

static void handle_signal(int signo) {
    (void)signo;
    stop_requested = 1;
}

static long monotonic_ms(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0) {
        return 0;
    }
    return (long)(ts.tv_sec * 1000L) + (long)(ts.tv_nsec / 1000000L);
}

static int read_text(const char *path, char *buf, size_t size) {
    int fd;
    ssize_t rd;

    if (size == 0) {
        errno = EINVAL;
        return -1;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    rd = read(fd, buf, size - 1);
    close(fd);
    if (rd < 0) {
        return -1;
    }
    buf[rd] = '\0';
    while (rd > 0 && (buf[rd - 1] == '\n' || buf[rd - 1] == '\r')) {
        buf[--rd] = '\0';
    }
    return 0;
}

static long read_long_path(const char *path, long fallback) {
    char buf[64];
    char *end = NULL;
    long value;

    if (read_text(path, buf, sizeof(buf)) < 0) {
        return fallback;
    }
    errno = 0;
    value = strtol(buf, &end, 10);
    if (errno != 0 || end == buf) {
        return fallback;
    }
    return value;
}

static long read_first_long(const char *const *paths, long fallback) {
    size_t index;

    for (index = 0; paths[index] != NULL; ++index) {
        long value = read_long_path(paths[index], fallback);

        if (value != fallback) {
            return value;
        }
    }
    return fallback;
}

static double temp_to_c(long raw) {
    if (raw < 0) {
        return -1.0;
    }
    if (raw > 1000) {
        return (double)raw / 1000.0;
    }
    return (double)raw / 10.0;
}

static void read_status_string(const char *path, char *out, size_t size) {
    if (read_text(path, out, size) < 0) {
        snprintf(out, size, "unknown");
    }
}

static void read_mem(long *used_mb, long *total_mb) {
    FILE *file = fopen("/proc/meminfo", "r");
    char key[64];
    char unit[32];
    long value;
    long total_kb = -1;
    long available_kb = -1;

    if (file == NULL) {
        *used_mb = -1;
        *total_mb = -1;
        return;
    }
    while (fscanf(file, "%63s %ld %31s", key, &value, unit) == 3) {
        if (strcmp(key, "MemTotal:") == 0) {
            total_kb = value;
        } else if (strcmp(key, "MemAvailable:") == 0) {
            available_kb = value;
        }
    }
    fclose(file);
    if (total_kb < 0 || available_kb < 0) {
        *used_mb = -1;
        *total_mb = total_kb >= 0 ? total_kb / 1024 : -1;
        return;
    }
    *used_mb = (total_kb - available_kb) / 1024;
    *total_mb = total_kb / 1024;
}

static double read_load1(void) {
    FILE *file = fopen("/proc/loadavg", "r");
    double load1 = -1.0;

    if (file == NULL) {
        return -1.0;
    }
    if (fscanf(file, "%lf", &load1) != 1) {
        load1 = -1.0;
    }
    fclose(file);
    return load1;
}

static double read_uptime_seconds(void) {
    FILE *file = fopen("/proc/uptime", "r");
    double uptime = -1.0;

    if (file == NULL) {
        return -1.0;
    }
    if (fscanf(file, "%lf", &uptime) != 1) {
        uptime = -1.0;
    }
    fclose(file);
    return uptime;
}

static void json_string(FILE *file, const char *text) {
    const unsigned char *p = (const unsigned char *)text;

    fputc('"', file);
    for (; *p != '\0'; ++p) {
        if (*p == '"' || *p == '\\') {
            fputc('\\', file);
            fputc(*p, file);
        } else if (*p >= 0x20 && *p < 0x7f) {
            fputc(*p, file);
        } else {
            fputc('?', file);
        }
    }
    fputc('"', file);
}

static void write_event(FILE *file,
                        const char *session,
                        const char *event,
                        unsigned long seq,
                        int interval_sec) {
    fprintf(file,
            "{\"type\":\"%s\",\"session\":",
            event);
    json_string(file, session);
    fprintf(file,
            ",\"seq\":%lu,\"ts_ms\":%ld,\"interval_sec\":%d}\n",
            seq,
            monotonic_ms(),
            interval_sec);
    fflush(file);
    fsync(fileno(file));
}

static void write_sample(FILE *file,
                         const char *session,
                         unsigned long seq,
                         int interval_sec) {
    static const char *const cpu_temp_paths[] = {
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/class/thermal/thermal_zone1/temp",
        "/sys/class/thermal/thermal_zone2/temp",
        NULL,
    };
    static const char *const gpu_temp_paths[] = {
        "/sys/class/thermal/thermal_zone10/temp",
        "/sys/class/thermal/thermal_zone11/temp",
        "/sys/class/thermal/thermal_zone12/temp",
        "/sys/class/thermal/thermal_zone3/temp",
        NULL,
    };
    char battery_status[64];
    long mem_used_mb;
    long mem_total_mb;
    long battery_pct;
    long battery_temp_raw;
    long voltage_uv;
    long current_ua;
    long cpu_temp_raw;
    long gpu_temp_raw;
    double uptime_sec;
    double load1;
    double power_w = -1.0;

    read_status_string("/sys/class/power_supply/battery/status",
                       battery_status,
                       sizeof(battery_status));
    battery_pct = read_long_path("/sys/class/power_supply/battery/capacity", -1);
    battery_temp_raw = read_long_path("/sys/class/power_supply/battery/temp", -1);
    voltage_uv = read_long_path("/sys/class/power_supply/battery/voltage_now", -1);
    current_ua = read_long_path("/sys/class/power_supply/battery/current_now", -1);
    if (voltage_uv > 0 && current_ua != -1) {
        double current_abs = current_ua < 0 ? -(double)current_ua : (double)current_ua;

        power_w = ((double)voltage_uv / 1000000.0) * (current_abs / 1000000.0);
    }
    cpu_temp_raw = read_first_long(cpu_temp_paths, -1);
    gpu_temp_raw = read_first_long(gpu_temp_paths, -1);
    read_mem(&mem_used_mb, &mem_total_mb);
    uptime_sec = read_uptime_seconds();
    load1 = read_load1();

    fprintf(file,
            "{\"type\":\"sample\",\"session\":");
    json_string(file, session);
    fprintf(file,
            ",\"seq\":%lu"
            ",\"ts_ms\":%ld"
            ",\"interval_sec\":%d"
            ",\"uptime_sec\":%.3f"
            ",\"battery_pct\":%ld"
            ",\"battery_status\":",
            seq,
            monotonic_ms(),
            interval_sec,
            uptime_sec,
            battery_pct);
    json_string(file, battery_status);
    fprintf(file,
            ",\"battery_temp_c\":%.1f"
            ",\"voltage_uv\":%ld"
            ",\"current_ua\":%ld"
            ",\"power_w\":%.3f"
            ",\"cpu_temp_c\":%.1f"
            ",\"gpu_temp_c\":%.1f"
            ",\"mem_used_mb\":%ld"
            ",\"mem_total_mb\":%ld"
            ",\"load1\":%.2f"
            "}\n",
            temp_to_c(battery_temp_raw),
            voltage_uv,
            current_ua,
            power_w,
            temp_to_c(cpu_temp_raw),
            temp_to_c(gpu_temp_raw),
            mem_used_mb,
            mem_total_mb,
            load1);
    fflush(file);
    fsync(fileno(file));
}

static int open_output_file(const char *path) {
    struct stat st;
    int fd;
    int saved_errno;

    fd = open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        return -1;
    }
    if (fstat(fd, &st) < 0) {
        saved_errno = errno;
        close(fd);
        errno = saved_errno;
        return -1;
    }
    if (!S_ISREG(st.st_mode)) {
        close(fd);
        errno = EINVAL;
        return -1;
    }
    if (fchmod(fd, 0600) < 0) {
        saved_errno = errno;
        close(fd);
        errno = saved_errno;
        return -1;
    }
    return fd;
}

static void sleep_interval(int interval_sec) {
    int remaining;

    for (remaining = interval_sec * 10; remaining > 0 && !stop_requested; --remaining) {
        struct timespec req;

        req.tv_sec = 0;
        req.tv_nsec = 100000000L;
        nanosleep(&req, NULL);
    }
}

int main(int argc, char **argv) {
    const char *path;
    const char *session;
    int interval_sec;
    FILE *file;
    int fd;
    unsigned long seq = 0;

    if (argc != 4) {
        fprintf(stderr, "usage: a90_longsoak <path> <interval_sec> <session>\n");
        return 2;
    }
    path = argv[1];
    interval_sec = atoi(argv[2]);
    session = argv[3];
    if (interval_sec < 1) {
        interval_sec = 60;
    }

    signal(SIGTERM, handle_signal);
    signal(SIGINT, handle_signal);
    signal(SIGHUP, SIG_IGN);
    signal(SIGPIPE, SIG_IGN);

    fd = open_output_file(path);
    if (fd < 0) {
        fprintf(stderr, "a90_longsoak: open %s: %s\n", path, strerror(errno));
        return 1;
    }
    file = fdopen(fd, "a");
    if (file == NULL) {
        int saved_errno = errno;

        close(fd);
        errno = saved_errno;
        fprintf(stderr, "a90_longsoak: open %s: %s\n", path, strerror(errno));
        return 1;
    }
    write_event(file, session, "start", seq, interval_sec);
    while (!stop_requested) {
        write_sample(file, session, ++seq, interval_sec);
        sleep_interval(interval_sec);
    }
    write_event(file, session, "stop", seq, interval_sec);
    fclose(file);
    return 0;
}
