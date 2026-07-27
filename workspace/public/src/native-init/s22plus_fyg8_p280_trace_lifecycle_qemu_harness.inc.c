/* Generic-arm64 execution control for the shared P2.80 trace lifecycle. */

#define P280_QEMU_SANITY_NS 5000000000ULL
#define P280_QEMU_NR_FCNTL 25
#define P280_QEMU_F_SETFL 4

static const struct p280_event_descriptor p280_qemu_role_events[] = {
    {
        "start_in",
        "p:p280/start_in __arm64_sys_fcntl on=+16(%x0):s32\n",
        "on == 1",
    },
    {
        "parent_pm_out",
        "p:p280/parent_pm_out do_fcntl rc=%x0:s32\n",
        "common_pid > 0",
    },
    {
        "child_pm_out",
        "p:p280/child_pm_out do_fcntl rc=%x0:s32\n",
        "common_pid > 0",
    },
    {
        "start_out",
        "r:p280/start_out __arm64_sys_fcntl rc=$retval:s32\n",
        "common_pid > 0",
    },
};

static const struct p280_event_descriptor p280_qemu_bind_events[] = {
    {
        "resume_in",
        "p:p280/resume_in __arm64_sys_fcntl\n",
        "common_pid == 1",
    },
    {
        "resume_out",
        "r:p280/resume_out __arm64_sys_fcntl rc=$retval:s32\n",
        "common_pid == 1",
    },
    {
        "pull_in",
        "p:p280/pull_in do_fcntl on=%x1:s32\n",
        "common_pid == 1",
    },
    {
        "pull_out",
        "r:p280/pull_out do_fcntl rc=$retval:s32\n",
        "common_pid == 1",
    },
    {
        "run_in",
        "p:p280/run_in do_fcntl on=%x1:s32\n",
        "common_pid == 1",
    },
    {
        "run_out",
        "r:p280/run_out do_fcntl rc=$retval:s32\n",
        "common_pid == 1",
    },
};

static void p280_qemu_write(const char *value) {
    (void)p260_write_all(1, value, cstr_len(value), 0);
}

static size_t p280_qemu_decimal(
    char output[32], uint64_t value) {
    char reverse[32];
    size_t count = 0;
    do {
        reverse[count++] = (char)('0' + (value % 10U));
        value /= 10U;
    } while (value != 0U && count < sizeof(reverse));
    for (size_t index = 0; index < count; ++index) {
        output[index] = reverse[count - index - 1U];
    }
    output[count] = '\0';
    return count;
}

static __attribute__((noreturn)) void p280_qemu_fail(
    const char *stage) {
    p280_qemu_write("P280_TRACE_LIFECYCLE result=FAIL stage=");
    p280_qemu_write(stage);
    p280_qemu_write("\n");
    quiet_park();
}

static long p280_qemu_mkdir(const char *path) {
    long rc = sys_mkdirat(path, 0755);
    return rc == 0 || rc == -EEXIST ? 0 : rc;
}

static void p280_qemu_setup_console_and_paths(void) {
    if (p280_qemu_mkdir("/dev") != 0) {
        p280_qemu_fail("dev-path");
    }
    long rc = sys_mount(
        "devtmpfs",
        "/dev",
        "devtmpfs",
        MS_NOSUID | MS_NODEV,
        "mode=0755");
    if (rc != 0 && rc != -P260_EBUSY) {
        p280_qemu_fail("devtmpfs-mount");
    }
    if (
        p280_qemu_mkdir("/sys") != 0
        || p280_qemu_mkdir("/sys/kernel") != 0
        || p280_qemu_mkdir("/sys/kernel/tracing") != 0
    ) {
        p280_qemu_fail("trace-paths");
    }
}

static void p280_qemu_set_trace(const char *value) {
    size_t length = cstr_len(value);
    if (length >= sizeof(p280_trace_buffer)) {
        p280_qemu_fail("fixture-capacity");
    }
    memcpy(p280_trace_buffer, value, length);
    p280_trace_buffer[length] = '\0';
    p280_trace_length = length;
}

static void p280_qemu_parser_fixtures(void) {
    struct p280_trace_control bind_control = {
        .events = p280_bind_events,
        .event_count = P280_BIND_EVENT_COUNT,
    };
    struct p280_bind_result bind_result = {0};

    p280_qemu_set_trace(
        "x-1 [000] d..2 1: pull_in: on=1\n"
        "x-1 [000] d..2 2: pull_out: rc=0\n");
    struct p280_trace_record no_run_records[P280_RECORD_CAPACITY];
    size_t no_run_count = 0;
    long no_run_rc = p280_parse_trace_records(
        &bind_control, no_run_records, &no_run_count);
    if (no_run_rc == -EINVAL) {
        p280_qemu_fail("parser-no-run-einval");
    }
    if (no_run_rc == -P260_EPROTO) {
        p280_qemu_fail("parser-no-run-eproto");
    }
    if (no_run_rc != 0) {
        p280_qemu_fail("parser-no-run-other");
    }
    if (
        no_run_count != 2U
        || no_run_records[0].event_index != 2U
        || no_run_records[1].event_index != 3U
    ) {
        p280_qemu_fail("parser-no-run-shape");
    }
    if (p280_parse_bind_result(&bind_control, &bind_result) != 0) {
        p280_qemu_fail("parser-no-run-parse");
    }
    if (
        bind_result.classification
        != P280_BIND_PULLUP_WITHOUT_RUN_STOP
    ) {
        p280_qemu_fail("parser-no-run-class");
    }

    p280_qemu_set_trace(
        "x-1 [000] d..2 1: pull_in: on=1\n"
        "x-1 [000] d..2 2: resume_in:\n"
        "x-1 [000] d..2 3: run_in: on=1\n"
        "x-1 [000] d..2 4: run_out: rc=-110\n"
        "x-1 [000] d..2 5: resume_out: rc=0\n"
        "x-1 [000] d..2 6: pull_out: rc=0\n");
    if (p280_parse_bind_result(&bind_control, &bind_result) != 0) {
        p280_qemu_fail("parser-nested-run-parse");
    }
    if (
        bind_result.classification
        != P280_BIND_NESTED_RUN_STOP_FAILURE
    ) {
        p280_qemu_fail("parser-nested-run-class");
    }

    p280_qemu_set_trace(
        "x-1 [000] d..2 1: run_in: on=1\n"
        "x-1 [000] d..2 2: run_out: rc=0\n"
        "x-1 [000] d..2 3: pull_in: on=1\n"
        "x-1 [000] d..2 4: pull_out: rc=0\n");
    if (p280_parse_bind_result(&bind_control, &bind_result) == 0) {
        p280_qemu_fail("parser-order");
    }

    struct p280_trace_record records[P280_RECORD_CAPACITY];
    size_t count = 0;
    p280_qemu_set_trace(
        "x-1 [000] d..2 1: pull_in: on=1junk\n");
    if (p280_parse_trace_records(&bind_control, records, &count) == 0) {
        p280_qemu_fail("parser-field");
    }
    p280_qemu_set_trace(
        "x-1 [000] d..2 1: unknown: on=1\n");
    if (p280_parse_trace_records(&bind_control, records, &count) == 0) {
        p280_qemu_fail("parser-unknown");
    }
    p280_qemu_set_trace(
        "x-1 [000] d..2 1: pull_in: on=1");
    if (p280_parse_trace_records(&bind_control, records, &count) == 0) {
        p280_qemu_fail("parser-truncated");
    }
}

static uint64_t p280_qemu_elapsed_ns(
    const struct timespec64 *start,
    const struct timespec64 *end) {
    if (p241_timespec_before(end, start)) {
        p280_qemu_fail("clock-order");
    }
    uint64_t seconds = (uint64_t)(end->tv_sec - start->tv_sec);
    int64_t nanoseconds = end->tv_nsec - start->tv_nsec;
    if (nanoseconds < 0) {
        --seconds;
        nanoseconds += 1000000000LL;
    }
    return seconds * 1000000000ULL + (uint64_t)nanoseconds;
}

static uint64_t p280_qemu_run_phase(
    const struct p280_event_descriptor *events,
    size_t event_count) {
    struct timespec64 start = {0};
    struct timespec64 end = {0};
    if (p241_clock_gettime(&start) != 0) {
        p280_qemu_fail("phase-clock-start");
    }
    struct p280_trace_control control;
    long setup_rc = p280_trace_setup(&control, events, event_count);
    if (setup_rc == P280_DETAIL_TRACE_CONTROL_UNAVAILABLE) {
        p280_qemu_fail("phase-setup-control");
    }
    if (setup_rc == P280_DETAIL_TRACE_REGISTRATION_UNAVAILABLE) {
        p280_qemu_fail("phase-setup-registration");
    }
    if (setup_rc == P280_DETAIL_TRACE_CLEANUP_UNVERIFIED) {
        p280_qemu_fail("phase-setup-cleanup");
    }
    if (setup_rc != 0) {
        p280_qemu_fail("phase-setup-other");
    }
    long fcntl_rc = syscall6(
        P280_QEMU_NR_FCNTL,
        2,
        P280_QEMU_F_SETFL,
        1,
        0,
        0,
        0);
    if (fcntl_rc != 0) {
        p280_trace_deadline_disable(&control);
        p280_qemu_fail("control-fcntl");
    }
    long quality = 0;
    if (p280_trace_finish(&control, &quality) != 0 || quality != 0) {
        p280_qemu_fail("phase-finish");
    }
    struct p280_trace_record records[P280_RECORD_CAPACITY];
    size_t count = 0;
    long parse_rc = p280_parse_trace_records(&control, records, &count);
    if (parse_rc != 0 || count != event_count) {
        p280_qemu_write("P280_TRACE_LIFECYCLE trace-begin\n");
        p280_qemu_write(p280_trace_buffer);
        p280_qemu_write("P280_TRACE_LIFECYCLE trace-end\n");
        p280_qemu_fail(
            parse_rc != 0 ? "phase-record-parse" : "phase-record-count");
    }
    uint8_t seen[P280_BIND_EVENT_COUNT] = {0};
    for (size_t index = 0; index < count; ++index) {
        if (
            records[index].pid != 1
            || records[index].event_index >= event_count
            || seen[records[index].event_index]
        ) {
            p280_qemu_fail("phase-record-shape");
        }
        seen[records[index].event_index] = 1;
    }
    if (p241_clock_gettime(&end) != 0) {
        p280_qemu_fail("phase-clock-end");
    }
    uint64_t elapsed = p280_qemu_elapsed_ns(&start, &end);
    if (elapsed >= P280_QEMU_SANITY_NS) {
        p280_qemu_fail("phase-sanity-budget");
    }
    return elapsed;
}

__attribute__((noreturn)) void _start(void) {
    p280_qemu_write("P280_TRACE_LIFECYCLE state=pid1-entry\n");
    p280_qemu_setup_console_and_paths();
    if (sys_getpid() != 1) {
        p280_qemu_fail("pid1");
    }
    p280_qemu_parser_fixtures();
    uint64_t role_ns = p280_qemu_run_phase(
        p280_qemu_role_events,
        sizeof(p280_qemu_role_events) / sizeof(p280_qemu_role_events[0]));
    uint64_t bind_ns = p280_qemu_run_phase(
        p280_qemu_bind_events,
        sizeof(p280_qemu_bind_events) / sizeof(p280_qemu_bind_events[0]));
    char role_text[32];
    char bind_text[32];
    (void)p280_qemu_decimal(role_text, role_ns);
    (void)p280_qemu_decimal(bind_text, bind_ns);
    p280_qemu_write(
        "P280_TRACE_LIFECYCLE result=PASS role_events=4 bind_events=6 "
        "role_ns=");
    p280_qemu_write(role_text);
    p280_qemu_write(" bind_ns=");
    p280_qemu_write(bind_text);
    p280_qemu_write(" parser=ok cleanup=ok nmissed=0\n");
    quiet_park();
}
