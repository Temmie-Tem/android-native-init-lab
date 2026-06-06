#include "a90_app_cpustress.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "a90_config.h"
#include "a90_draw.h"
#include "a90_kms.h"
#include "a90_metrics.h"
#include "a90_run.h"
#include "a90_util.h"

static long app_cpustress_clamp_duration_ms(long duration_ms) {
    if (duration_ms < 1000L) {
        return 1000L;
    }
    if (duration_ms > 120000L) {
        return 120000L;
    }
    return duration_ms;
}

static uint32_t app_cpustress_text_scale(void) {
    struct a90_kms_info info;

    a90_kms_info(&info);
    if (info.width >= 1080) {
        return 4;
    }
    if (info.width >= 720) {
        return 3;
    }
    return 2;
}

static uint32_t app_cpustress_shrink_text_scale(const char *text,
                                                uint32_t scale,
                                                uint32_t max_width) {
    while (scale > 1 && (uint32_t)strlen(text) * scale * 6 > max_width) {
        --scale;
    }
    return scale;
}

void a90_app_cpustress_init(struct a90_app_cpustress_state *state) {
    if (state == NULL) {
        return;
    }
    memset(state, 0, sizeof(*state));
    state->pid = -1;
    state->workers = 8;
    state->duration_ms = 10000L;
}

int a90_app_cpustress_start(struct a90_app_cpustress_state *state,
                            long seconds,
                            unsigned int workers) {
    char seconds_arg[16];
    char workers_arg[16];
    char *const argv[] = {
        CPUSTRESS_HELPER,
        seconds_arg,
        workers_arg,
        NULL
    };
    struct a90_run_config config = {
        .tag = "cpustress-app",
        .argv = argv,
        .stdio_mode = A90_RUN_STDIO_NULL,
        .setsid = true,
        .ignore_hup_pipe = true,
        .kill_process_group = true,
        .stop_timeout_ms = 2000,
    };
    pid_t pid = -1;
    int seconds_value;
    int rc;

    if (state == NULL) {
        return -EINVAL;
    }

    a90_app_cpustress_stop(state);
    state->done = false;
    state->failed = false;
    state->workers = workers;
    state->duration_ms = app_cpustress_clamp_duration_ms(seconds * 1000L);
    state->deadline_ms = monotonic_millis() + state->duration_ms;
    seconds_value = (int)(state->duration_ms / 1000L);

    snprintf(seconds_arg, sizeof(seconds_arg), "%d", seconds_value);
    snprintf(workers_arg, sizeof(workers_arg), "%u", state->workers);
    rc = a90_run_spawn(&config, &pid);
    if (rc < 0) {
        state->pid = -1;
        state->done = true;
        state->failed = true;
        return rc;
    }
    state->pid = pid;
    return 0;
}

void a90_app_cpustress_stop(struct a90_app_cpustress_state *state) {
    if (state == NULL) {
        return;
    }
    if (state->pid > 0) {
        (void)a90_run_stop_pid_ex(state->pid,
                                  "cpustress-app",
                                  2000,
                                  true,
                                  NULL);
        state->pid = -1;
    }
}

void a90_app_cpustress_tick(struct a90_app_cpustress_state *state) {
    int status = 0;
    int rc;

    if (state == NULL || state->pid <= 0) {
        return;
    }

    rc = a90_run_reap_pid(state->pid, &status);
    if (rc == 1) {
        struct a90_run_result result = {
            .pid = state->pid,
            .status = status,
        };

        state->pid = -1;
        state->done = true;
        if (a90_run_result_to_rc(&result) != 0) {
            state->failed = true;
        }
        return;
    }
    if (rc < 0) {
        state->pid = -1;
        state->done = true;
        state->failed = true;
        return;
    }
    if (monotonic_millis() > state->deadline_ms + 2000L) {
        a90_app_cpustress_stop(state);
        state->done = true;
        state->failed = true;
    }
}

bool a90_app_cpustress_running(const struct a90_app_cpustress_state *state) {
    return state != NULL && state->pid > 0;
}

int a90_app_cpustress_draw(const struct a90_app_cpustress_state *state) {
    struct a90_metrics_snapshot snapshot;
    char online[64];
    char present[64];
    char freq0[32];
    char freq1[32];
    char freq2[32];
    char freq3[32];
    char freq4[32];
    char freq5[32];
    char freq6[32];
    char freq7[32];
    char lines[8][160];
    const char *status_word;
    long remaining_ms;
    long duration_ms;
    uint32_t scale;
    uint32_t title_scale;
    uint32_t x;
    uint32_t y;
    uint32_t card_w;
    uint32_t line_h;
    size_t index;

    if (state == NULL) {
        return -EINVAL;
    }

    duration_ms = app_cpustress_clamp_duration_ms(state->duration_ms);
    remaining_ms = state->deadline_ms - monotonic_millis();
    if (remaining_ms < 0) {
        remaining_ms = 0;
    }

    if (state->failed) {
        status_word = "FAILED";
    } else if (state->pid > 0) {
        status_word = "RUNNING";
    } else if (state->done) {
        status_word = "DONE";
    } else {
        status_word = "READY";
    }

    a90_metrics_read_snapshot(&snapshot);
    if (read_trimmed_text_file("/sys/devices/system/cpu/online",
                               online,
                               sizeof(online)) < 0) {
        strcpy(online, "?");
    }
    if (read_trimmed_text_file("/sys/devices/system/cpu/present",
                               present,
                               sizeof(present)) < 0) {
        strcpy(present, "?");
    }
    a90_metrics_read_cpu_freq_label(0, freq0, sizeof(freq0));
    a90_metrics_read_cpu_freq_label(1, freq1, sizeof(freq1));
    a90_metrics_read_cpu_freq_label(2, freq2, sizeof(freq2));
    a90_metrics_read_cpu_freq_label(3, freq3, sizeof(freq3));
    a90_metrics_read_cpu_freq_label(4, freq4, sizeof(freq4));
    a90_metrics_read_cpu_freq_label(5, freq5, sizeof(freq5));
    a90_metrics_read_cpu_freq_label(6, freq6, sizeof(freq6));
    a90_metrics_read_cpu_freq_label(7, freq7, sizeof(freq7));

    snprintf(lines[0], sizeof(lines[0]), "STATE %s  REM %ld.%03ldS",
             status_word,
             remaining_ms / 1000L,
             remaining_ms % 1000L);
    snprintf(lines[1], sizeof(lines[1]), "CPU %s  USE %s  LOAD %s",
             snapshot.cpu_temp,
             snapshot.cpu_usage,
             snapshot.loadavg);
    snprintf(lines[2], sizeof(lines[2]), "CORES ONLINE %.24s  PRESENT %.24s", online, present);
    snprintf(lines[3], sizeof(lines[3]), "FREQ 0:%s 1:%s 2:%s 3:%s",
             freq0, freq1, freq2, freq3);
    snprintf(lines[4], sizeof(lines[4]), "FREQ 4:%s 5:%s 6:%s 7:%s",
             freq4, freq5, freq6, freq7);
    snprintf(lines[5], sizeof(lines[5]), "MEM %s  PWR %s",
             snapshot.memory,
             snapshot.power_now);
    snprintf(lines[6], sizeof(lines[6]), "WORKERS %u  TEST %ldS",
             state->workers,
             duration_ms / 1000L);
    snprintf(lines[7], sizeof(lines[7]), "ANY BUTTON BACK / CANCEL");

    if (a90_kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = app_cpustress_text_scale();
    title_scale = scale + 1;
    x = a90_kms_framebuffer()->width / 18;
    if (x < scale * 4) {
        x = scale * 4;
    }
    y = a90_kms_framebuffer()->height / 10;
    card_w = a90_kms_framebuffer()->width - (x * 2);
    line_h = scale * 11;

    a90_draw_text(a90_kms_framebuffer(), x, y, "TOOLS / CPU STRESS", 0xffcc33,
                  app_cpustress_shrink_text_scale("TOOLS / CPU STRESS",
                                                  title_scale,
                                                  card_w));
    y += line_h + scale * 4;

    a90_draw_rect(a90_kms_framebuffer(), x - scale, y - scale, card_w, line_h * 9, 0x202020);
    for (index = 0; index < 8; ++index) {
        uint32_t color = 0xffffff;

        if (index == 0) {
            color = state->failed ? 0xff6666 : (state->pid > 0 ? 0x88ee88 : 0xffcc33);
        } else if (index == 7) {
            color = 0xdddddd;
        }
        a90_draw_text(a90_kms_framebuffer(), x, y + (uint32_t)index * line_h,
                      lines[index],
                      color,
                      app_cpustress_shrink_text_scale(lines[index],
                                                      scale,
                                                      card_w - scale * 2));
    }

    if (a90_kms_present("cpustress", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}
