/*
 * P3.17 runtime executability witness for the bounded Max77705 diagnostic.
 *
 * The provider-pre snapshot is taken by the generic module loader after the
 * five derived SPMI/PMIC modules and before msm-geni-se can instantiate the
 * target I2C consumer.  The post snapshot, command-line policy witness,
 * supplier link, and waiting_for_supplier state are captured only after the
 * inherited gadget/direct fence closes and before the diagnostic is loaded.
 */

#define P317_PLATFORM_ROOT "/sys/bus/platform/devices/"
#define P317_SPMI_ROOT "/sys/bus/spmi/devices/"
#define P317_PROVIDER_COUNT 3U
#define P317_PROVIDER_MASK 0x07U
#define P317_PROVIDER_SETTLE_POLLS 50U
#define P317_PROVIDER_SETTLE_NS 100000000LL
#define P317_PROVIDER_CHAIN_LAST_MODULE_INDEX 65U
#define P317_CMDLINE_CAPACITY 8192U

#define P317_SPMI_CONTROLLER_DT "/soc/qcom,spmi@c42d000"
#define P317_PMIC_DT \
    "/soc/qcom,spmi@c42d000/qcom,pm8350c@2"
#define P317_GPIO_DT \
    "/soc/qcom,spmi@c42d000/qcom,pm8350c@2/pinctrl@8800"

struct p317_provider_spec {
    const char *root;
    const char *of_path;
    const char *driver;
};

static const struct p317_provider_spec p317_providers[] = {
    {P317_PLATFORM_ROOT, P317_SPMI_CONTROLLER_DT, "spmi_pmic_arb"},
    {P317_SPMI_ROOT, P317_PMIC_DT, "pmic-spmi"},
    {P317_PLATFORM_ROOT, P317_GPIO_DT, "qcom-spmi-gpio"},
};

_Static_assert(
    sizeof(p317_providers) / sizeof(p317_providers[0]) ==
        P317_PROVIDER_COUNT,
    "P3.17 provider count");

static struct s22plus_max77705_p317_exec_witness g_p317_exec;

static int p317_path_suffix(
    const char *value, size_t length, const char *suffix) {
    size_t suffix_length = cstr_len(suffix);
    return length >= suffix_length
        && p260_bytes_equal(
            value + length - suffix_length, suffix, suffix_length);
}

static long p317_join_path(
    char *output, size_t capacity,
    const char *left, const char *middle, const char *right) {
    size_t cursor = 0U;
    output[0] = '\0';
    long rc = p282_copy_path_part(output, capacity, &cursor, left);
    if (rc == 0 && middle != NULL)
        rc = p282_copy_path_part(output, capacity, &cursor, middle);
    if (rc == 0 && right != NULL)
        rc = p282_copy_path_part(output, capacity, &cursor, right);
    return rc;
}

static long p317_expected_driver(
    const char *device_path, const char *expected,
    int *bound, int *wrong) {
    char path[320];
    char target[S22_P241_SYMLINK_TARGET_MAX];
    struct s22_p241_kernel_stat stat_buffer = {0};
    long rc = p317_join_path(
        path, sizeof(path), device_path, "/driver", NULL);
    if (rc != 0) return rc;
    rc = p241_newfstatat(path, &stat_buffer, AT_SYMLINK_NOFOLLOW);
    if (rc == -ENOENT) {
        *bound = 0;
        *wrong = 0;
        return 0;
    }
    if (rc != 0 || (stat_buffer.st_mode & S_IFMT) != S_IFLNK)
        return rc != 0 ? rc : -EIO;
    long amount = p241_readlinkat(path, target, sizeof(target));
    if (amount <= 0 || amount >= (long)sizeof(target))
        return amount < 0 ? amount : -EIO;
    *bound = p241_basename_equals(
        target, (size_t)amount, expected);
    *wrong = !*bound;
    return 0;
}

static long p317_scan_provider(
    const struct p317_provider_spec *spec,
    int *present, int *bound, int *wrong, int *duplicate) {
    uint8_t buffer[S22_P241_DIRENT_BUFFER_SIZE];
    char matched_path[288] = {0};
    unsigned int matches = 0U;
    long fd = p316_dir_open(spec->root);
    if (fd < 0) return fd;
    for (;;) {
        long amount = p241_getdents64((int)fd, buffer, sizeof(buffer));
        if (amount < 0) {
            (void)sys_close((int)fd);
            return amount;
        }
        if (amount == 0) break;
        size_t cursor = 0U;
        while (cursor < (size_t)amount) {
            struct s22_p241_linux_dirent64 *entry =
                (struct s22_p241_linux_dirent64 *)(buffer + cursor);
            size_t header = offsetof(struct s22_p241_linux_dirent64, d_name);
            if (entry->d_reclen < header + 2U
                || cursor + entry->d_reclen > (size_t)amount) {
                (void)sys_close((int)fd);
                return -EIO;
            }
            size_t capacity = entry->d_reclen - header;
            size_t length = 0U;
            while (length < capacity && entry->d_name[length] != '\0')
                ++length;
            if (length == capacity || length == 0U) {
                (void)sys_close((int)fd);
                return -EIO;
            }
            if (!(length == 1U && entry->d_name[0] == '.')
                && !(length == 2U && entry->d_name[0] == '.'
                    && entry->d_name[1] == '.')) {
                char device_path[288];
                char of_node_path[320];
                char target[S22_P241_SYMLINK_TARGET_MAX];
                char name[128];
                if (length >= sizeof(name)) {
                    (void)sys_close((int)fd);
                    return -P260_EOVERFLOW;
                }
                memcpy(name, entry->d_name, length);
                name[length] = '\0';
                long rc = p317_join_path(
                    device_path, sizeof(device_path), spec->root, name, NULL);
                if (rc == 0)
                    rc = p317_join_path(
                        of_node_path, sizeof(of_node_path),
                        device_path, "/of_node", NULL);
                if (rc != 0) {
                    (void)sys_close((int)fd);
                    return rc;
                }
                long target_length = p241_readlinkat(
                    of_node_path, target, sizeof(target));
                if (target_length != -ENOENT) {
                    if (target_length <= 0
                        || target_length >= (long)sizeof(target)) {
                        (void)sys_close((int)fd);
                        return target_length < 0 ? target_length : -EIO;
                    }
                    if (p317_path_suffix(
                        target, (size_t)target_length, spec->of_path)) {
                        if (++matches == 1U)
                            memcpy(
                                matched_path, device_path,
                                cstr_len(device_path) + 1U);
                    }
                }
            }
            cursor += entry->d_reclen;
        }
    }
    long close_rc = sys_close((int)fd);
    if (close_rc != 0) return close_rc;
    *present = matches == 1U;
    *duplicate = matches > 1U;
    *bound = 0;
    *wrong = 0;
    return matches == 1U
        ? p317_expected_driver(matched_path, spec->driver, bound, wrong)
        : 0;
}

static long p317_provider_snapshot(uint8_t *present, uint8_t *bound) {
    uint8_t present_value = S22PLUS_MAX77705_P317_PROVIDER_VALID;
    uint8_t bound_value = 0U;
    for (size_t index = 0U; index < P317_PROVIDER_COUNT; ++index) {
        int exists = 0;
        int attached = 0;
        int wrong = 0;
        int duplicate = 0;
        long rc = p317_scan_provider(
            &p317_providers[index],
            &exists, &attached, &wrong, &duplicate);
        if (rc != 0) return rc;
        if (exists) present_value |= (uint8_t)(1U << index);
        if (duplicate)
            present_value |= (uint8_t)(
                1U << (S22PLUS_MAX77705_P317_PROVIDER_DUPLICATE_SHIFT +
                    index));
        if (attached) bound_value |= (uint8_t)(1U << index);
        if (wrong)
            bound_value |= (uint8_t)(
                1U << (S22PLUS_MAX77705_P317_PROVIDER_DUPLICATE_SHIFT +
                    index));
    }
    *present = present_value;
    *bound = bound_value;
    return 0;
}

static int p317_provider_ready(uint8_t present, uint8_t bound) {
    return s22plus_max77705_p317_provider_ready(present, bound);
}

static long p317_capture_preclient_provider(void) {
    for (unsigned int attempt = 0U;
         attempt < P317_PROVIDER_SETTLE_POLLS; ++attempt) {
        long rc = p317_provider_snapshot(
            &g_p317_exec.pre_present, &g_p317_exec.pre_bound);
        if (rc != 0) return rc;
        if (p317_provider_ready(
            g_p317_exec.pre_present, g_p317_exec.pre_bound))
            return 0;
        if (attempt + 1U < P317_PROVIDER_SETTLE_POLLS)
            (void)sys_nanosleep(P317_PROVIDER_SETTLE_NS);
    }
    return 0;
}

static int p317_token_prefix(
    const char *value, size_t length, const char *prefix) {
    size_t prefix_length = cstr_len(prefix);
    return length >= prefix_length
        && p260_bytes_equal(value, prefix, prefix_length);
}

static long p317_capture_policy(void) {
    char value[P317_CMDLINE_CAPACITY];
    size_t length = 0U;
    long rc = p282_read_file(
        "/proc/cmdline", value, sizeof(value), &length);
    if (rc != 0) return rc;
    if (length == 0U || value[length - 1U] != '\n') return -EIO;
    unsigned int fw = 0U;
    unsigned int strict = 0U;
    size_t cursor = 0U;
    while (cursor < length) {
        while (cursor < length &&
            (value[cursor] == ' ' || value[cursor] == '\t'
                || value[cursor] == '\n')) ++cursor;
        size_t start = cursor;
        while (cursor < length && value[cursor] != ' '
            && value[cursor] != '\t' && value[cursor] != '\n') {
            unsigned char byte = (unsigned char)value[cursor];
            if (byte < 0x21U || byte > 0x7eU) return -EIO;
            ++cursor;
        }
        if (cursor == start) continue;
        size_t token_length = cursor - start;
        if (p317_token_prefix(
            value + start, token_length, "fw_devlink=")) fw = 1U;
        if (p317_token_prefix(
            value + start, token_length, "fw_devlink.strict=")) strict = 1U;
    }
    uint8_t gadget = g_p317_exec.policy &
        S22PLUS_MAX77705_P317_POLICY_GADGET_READY;
    uint8_t state = fw && strict
        ? S22PLUS_MAX77705_P317_POLICY_BOTH_TOKENS
        : (fw ? S22PLUS_MAX77705_P317_POLICY_FW_DEVLINK_TOKEN
            : (strict ? S22PLUS_MAX77705_P317_POLICY_STRICT_TOKEN
                : S22PLUS_MAX77705_P317_POLICY_DEFAULT_ON_STRICT));
    g_p317_exec.policy = (uint8_t)(
        S22PLUS_MAX77705_P317_POLICY_VALID | gadget | state);
    return 0;
}

static long p317_capture_waiting(const char *parent_path, uint8_t *state) {
    char path[288];
    char value[4];
    size_t length = 0U;
    long rc = p317_join_path(
        path, sizeof(path), parent_path, "/waiting_for_supplier", NULL);
    if (rc != 0) return rc;
    rc = p282_read_file(path, value, sizeof(value), &length);
    if (rc == -ENOENT) {
        *state = S22PLUS_MAX77705_P317_WAITING_FILE_ABSENT;
        return 0;
    }
    if (rc != 0) return rc;
    if (length == 2U && value[1] == '\n' && value[0] == '0')
        *state = S22PLUS_MAX77705_P317_WAITING_ZERO;
    else if (length == 2U && value[1] == '\n' && value[0] == '1')
        *state = S22PLUS_MAX77705_P317_WAITING_ONE;
    else
        return -EIO;
    return 0;
}

static long p317_capture_supplier(
    const char *parent_path, uint8_t *state) {
    uint8_t buffer[S22_P241_DIRENT_BUFFER_SIZE];
    unsigned int total = 0U;
    unsigned int exact = 0U;
    long fd = p316_dir_open(parent_path);
    if (fd < 0) return fd;
    for (;;) {
        long amount = p241_getdents64((int)fd, buffer, sizeof(buffer));
        if (amount < 0) {
            (void)sys_close((int)fd);
            return amount;
        }
        if (amount == 0) break;
        size_t cursor = 0U;
        while (cursor < (size_t)amount) {
            struct s22_p241_linux_dirent64 *entry =
                (struct s22_p241_linux_dirent64 *)(buffer + cursor);
            size_t header = offsetof(struct s22_p241_linux_dirent64, d_name);
            if (entry->d_reclen < header + 2U
                || cursor + entry->d_reclen > (size_t)amount) {
                (void)sys_close((int)fd);
                return -EIO;
            }
            size_t capacity = entry->d_reclen - header;
            size_t length = 0U;
            while (length < capacity && entry->d_name[length] != '\0')
                ++length;
            if (length == capacity || length == 0U) {
                (void)sys_close((int)fd);
                return -EIO;
            }
            if (p316_name_has_prefix(
                entry->d_name, length, "supplier:")) {
                char name[160];
                char supplier_path[352];
                char link_path[384];
                char target[S22_P241_SYMLINK_TARGET_MAX];
                if (length >= sizeof(name)) {
                    (void)sys_close((int)fd);
                    return -P260_EOVERFLOW;
                }
                memcpy(name, entry->d_name, length);
                name[length] = '\0';
                long rc = p317_join_path(
                    supplier_path, sizeof(supplier_path),
                    parent_path, "/", name);
                if (rc == 0)
                    rc = p317_join_path(
                        link_path, sizeof(link_path),
                        supplier_path, "/of_node", NULL);
                if (rc != 0) {
                    (void)sys_close((int)fd);
                    return rc;
                }
                ++total;
                long target_length = p241_readlinkat(
                    link_path, target, sizeof(target));
                if (target_length > 0
                    && target_length < (long)sizeof(target)
                    && p317_path_suffix(
                        target, (size_t)target_length, P317_GPIO_DT))
                    ++exact;
                else if (target_length < 0 && target_length != -ENOENT) {
                    (void)sys_close((int)fd);
                    return target_length;
                }
            }
            cursor += entry->d_reclen;
        }
    }
    long close_rc = sys_close((int)fd);
    if (close_rc != 0) return close_rc;
    *state = total == 0U
        ? S22PLUS_MAX77705_P317_SUPPLIER_LINK_ABSENT
        : (total == 1U && exact == 1U
            ? S22PLUS_MAX77705_P317_SUPPLIER_EXACT_ONE
            : S22PLUS_MAX77705_P317_SUPPLIER_FOREIGN_OR_MULTIPLE);
    return 0;
}

static long p317_capture_post_provider(void) {
    return p317_provider_snapshot(
        &g_p317_exec.post_present, &g_p317_exec.post_bound);
}

static __attribute__((noreturn)) void p317_publish(
    int tty_fd, const struct p316_diag_observation *observation) {
    uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE];
    uint16_t detail = 0U;
    int rc = s22plus_max77705_p317_encode_envelope(
        &observation->binding, &g_p317_exec,
        observation->semantic_kind, observation->semantic_code,
        observation->observer_site, observation->observer_error_class,
        observation->result_valid ? &observation->result : NULL,
        observation->result_valid ? &observation->summary : NULL,
        envelope, &detail);
    if (rc != 0)
        p290_fail_next(P313_DETAIL_TERMINAL_DOMAIN_CONTRADICTION);
    p316_bypass_to_pair();
    long publish_rc = s22_max77705_checkpoint_payload_progress_position(
        &g_checkpoint, 105U, S22PLUS_MAX77705_A_DETAIL, envelope);
    if (publish_rc == 0)
        publish_rc = s22_max77705_checkpoint_payload_terminal_position(
            &g_checkpoint, 106U, detail, envelope + 64U);
    if (publish_rc != 0) p292_park_after_checkpoint_error(publish_rc);
    if (tty_fd >= 0) (void)p260_write_banner(tty_fd);
    p290_park_after_confirmed_publication();
}

static __attribute__((noreturn)) void p317_fail_observer(
    int tty_fd, unsigned int observer_site, long operation_error,
    const struct p316_diag_observation *prior) {
    struct p316_diag_observation observation = {0};
    if (prior != NULL) observation = *prior;
    if (observer_site < S22PLUS_MAX77705_OBSERVER_SITE_OVERRIDE_PREPARE
        || observer_site > S22PLUS_MAX77705_P317_OBSERVER_SITE_WAITING)
        observer_site = S22PLUS_MAX77705_OBSERVER_SITE_RESULT_POLICY;
    if (prior == NULL)
        observation.binding.loader_state =
            S22PLUS_MAX77705_LOADER_NOT_STARTED;
    observation.semantic_kind = S22PLUS_MAX77705_SEMANTIC_TERMINAL;
    observation.semantic_code =
        S22PLUS_MAX77705_TERMINAL_SYNC_CONTRADICTION;
    observation.result_valid = 0U;
    observation.observer_site = (uint8_t)observer_site;
    observation.observer_error_class =
        p316_observer_error_class(operation_error);
    p317_publish(tty_fd, &observation);
}

static __attribute__((noreturn)) void p317_fail_precondition(
    int tty_fd, uint8_t semantic_code,
    const struct p316_diag_observation *prior) {
    struct p316_diag_observation observation = {0};
    if (prior != NULL) observation = *prior;
    else observation.binding.loader_state =
        S22PLUS_MAX77705_LOADER_NOT_STARTED;
    observation.semantic_kind = S22PLUS_MAX77705_SEMANTIC_TERMINAL;
    observation.semantic_code = semantic_code;
    observation.result_valid = 0U;
    observation.observer_site = S22PLUS_MAX77705_OBSERVER_SITE_NONE;
    observation.observer_error_class =
        S22PLUS_MAX77705_OBSERVER_ERROR_NONE;
    p317_publish(tty_fd, &observation);
}

static __attribute__((noreturn)) void p317_run(void) {
    (void)p316_run;
    p260_derive_identity();
    long rc = p260_mount_configfs();
    if (rc != 0) fail_at(P260_CONFIG_STAGE, 0U, rc);
    p260_progress(P260_CONFIG_STAGE);
    rc = p260_create_gadget();
    if (rc != 0) fail_at(P260_GADGET_STAGE, 0U, rc);
    p260_progress(P260_GADGET_STAGE);
    unsigned int major_number = 0U;
    unsigned int minor_number = 0U;
    rc = p260_wait_tty_dev(&major_number, &minor_number);
    if (rc != 0) fail_at(P260_TTY_CLASS_STAGE, 0U, rc);
    p260_progress(P260_TTY_CLASS_STAGE);
    rc = p260_prepare_tty_node(major_number, minor_number);
    int tty_fd = -1;
    if (rc == 0) rc = p260_open_raw_tty(&tty_fd);
    if (rc != 0) fail_at(P260_TTY_RAW_STAGE, 0U, rc);
    p260_progress(P260_TTY_RAW_STAGE);

    p290_progress_position(S22_P313_POSITION_BANNER_DEFERRED, 0U);
    uint16_t role_warning = 0U;
    rc = p282_phase_role(&role_warning, tty_fd);
    if (rc != 0 || role_warning != 0U || !g_p313_role_qscratch_valid
        || ((g_p313_role_qscratch >> 20U) & 1U) == 0U
        || ((g_p313_role_qscratch >> 28U) & 1U) == 0U)
        p290_fail_next(rc != 0 ? rc : P313_DETAIL_ROLE_QSCRATCH_VALUE);
    p290_progress_position(S22_P313_POSITION_ROLE_READY, 0U);

    struct p282_trace_control direct_control = {0};
    rc = p282_trace_setup(P282_PHASE_BIND, &direct_control);
    if (rc != 0) p290_fail_next(p313_setup_detail(rc));
    p290_progress_position(S22_P313_POSITION_DIRECT_OBSERVER_READY, 0U);
    rc = p260_bind_udc();
    if (rc != 0) p298_fail_with_trace(&direct_control, rc);
    p290_progress_position(S22_P313_POSITION_DIRECT_BIND_RETURNED, 0U);

    rc = p282_trace_read_snapshot(&direct_control, 0);
    struct p282_bind_trace_result direct_initial = {0};
    if (rc == 0)
        rc = p300_parse_bind_stream(&direct_control, &direct_initial, 0);
    if (rc != 0 || p298_start_result_detail(&direct_initial) != 0)
        p298_fail_with_trace(&direct_control,
            rc != 0 ? rc : P313_DETAIL_DIRECT_STREAM_INTEGRITY);
    p290_progress_position(S22_P313_POSITION_DIRECT_START_CLASSIFIED, 0U);
    p290_progress_position(S22_P313_POSITION_DIRECT_FENCE_STARTED, 0U);
    unsigned int direct_state = 0U;
    unsigned int direct_speed = 0U;
    int direct_configured = 0;
    rc = p313_wait_state_window(P282_FINAL_DEADLINE_SEC,
        &direct_state, &direct_speed, &direct_configured);
    if (rc != 0) p298_fail_with_trace(&direct_control, rc);
    struct p282_bind_trace_result direct = {0};
    long direct_detail = p313_finish_direct(&direct_control, &direct);
    p290_progress_position(S22_P313_POSITION_DIRECT_FENCE_CLOSED, 0U);
    if (direct_detail != 0) p290_fail_next(direct_detail);
    if (!direct_configured && !direct.connect_done_seen
        && !p313_direct_known_baseline(&direct))
        p290_fail_next(P313_DIRECT_NONBASELINE_ACTIVITY);
    p290_progress_position(S22_P313_POSITION_BRANCH_SELECTED, 0U);
    g_p317_exec.policy |= S22PLUS_MAX77705_P317_POLICY_GADGET_READY;

    rc = p317_capture_policy();
    if (rc != 0) p317_fail_observer(
        tty_fd, S22PLUS_MAX77705_P317_OBSERVER_SITE_CMDLINE, rc, NULL);
    if ((g_p317_exec.policy & S22PLUS_MAX77705_P317_POLICY_STATE_MASK) !=
        S22PLUS_MAX77705_P317_POLICY_DEFAULT_ON_STRICT)
        p317_fail_precondition(
            tty_fd,
            S22PLUS_MAX77705_P317_TERMINAL_POLICY_PRECONDITION,
            NULL);
    if (!p317_provider_ready(
        g_p317_exec.pre_present, g_p317_exec.pre_bound))
        p317_fail_precondition(
            tty_fd,
            S22PLUS_MAX77705_P317_TERMINAL_EXEC_CONTRADICTION,
            NULL);

    rc = p316_verify_substrate_bindings();
    if (rc != 0) p317_fail_observer(
        tty_fd, S22PLUS_MAX77705_OBSERVER_SITE_SUBSTRATE_VERIFY, rc, NULL);
    p290_progress_position(P316_POSITION_SUBSTRATE_VERIFIED, 0U);
    struct p316_i2c_topology topology = {0};
    rc = p316_scan_i2c_topology(&topology);
    if (rc != 0) p317_fail_observer(
        tty_fd, S22PLUS_MAX77705_OBSERVER_SITE_PRE_TOPOLOGY, rc, NULL);
    p290_progress_position(P316_POSITION_TOPOLOGY_VERIFIED, 0U);

    rc = p317_capture_post_provider();
    if (rc != 0) p317_fail_observer(
        tty_fd, S22PLUS_MAX77705_P317_OBSERVER_SITE_PROVIDER_POST, rc, NULL);
    if (!p317_provider_ready(
        g_p317_exec.post_present, g_p317_exec.post_bound))
        p317_fail_precondition(
            tty_fd,
            S22PLUS_MAX77705_P317_TERMINAL_PROVIDER_POSTCONDITION,
            NULL);
    uint8_t waiting_state = S22PLUS_MAX77705_P317_WAITING_UNAVAILABLE;
    rc = p317_capture_waiting(topology.parent_path, &waiting_state);
    if (rc != 0) p317_fail_observer(
        tty_fd, S22PLUS_MAX77705_P317_OBSERVER_SITE_WAITING, rc, NULL);
    g_p317_exec.link_waiting = waiting_state;
    uint8_t supplier_state = S22PLUS_MAX77705_P317_SUPPLIER_UNAVAILABLE;
    rc = p317_capture_supplier(topology.parent_path, &supplier_state);
    if (rc != 0) p317_fail_observer(
        tty_fd, S22PLUS_MAX77705_P317_OBSERVER_SITE_SUPPLIER, rc, NULL);
    g_p317_exec.link_waiting = (uint8_t)(
        S22PLUS_MAX77705_P317_LINK_VALID | waiting_state |
        (supplier_state << S22PLUS_MAX77705_P317_SUPPLIER_SHIFT));
    uint8_t supplier = (g_p317_exec.link_waiting &
        S22PLUS_MAX77705_P317_SUPPLIER_MASK) >>
        S22PLUS_MAX77705_P317_SUPPLIER_SHIFT;
    uint8_t waiting = g_p317_exec.link_waiting &
        S22PLUS_MAX77705_P317_WAITING_MASK;
    if (supplier != S22PLUS_MAX77705_P317_SUPPLIER_LINK_ABSENT
        && supplier != S22PLUS_MAX77705_P317_SUPPLIER_EXACT_ONE)
        p317_fail_precondition(
            tty_fd,
            S22PLUS_MAX77705_P317_TERMINAL_SUPPLIER_PRECONDITION,
            NULL);
    if (waiting != S22PLUS_MAX77705_P317_WAITING_ZERO)
        p317_fail_precondition(
            tty_fd,
            S22PLUS_MAX77705_P317_TERMINAL_WAITING_PRECONDITION,
            NULL);

    p290_progress_position(P316_POSITION_DIAGNOSTIC_DISPATCHED, 0U);
    struct p316_diag_observation observation = {0};
    rc = p316_observe_diagnostic(tty_fd, &topology, &observation);
    if (rc != 0) p317_fail_observer(
        tty_fd,
        observation.observer_site != S22PLUS_MAX77705_OBSERVER_SITE_NONE
            ? observation.observer_site
            : S22PLUS_MAX77705_OBSERVER_SITE_LATE_LOADER,
        rc, &observation);
    p290_progress_position(P316_POSITION_DIAGNOSTIC_RETURNED, 0U);
    p290_progress_position(P316_POSITION_BINDING_CAPTURED, 0U);
    p290_progress_position(P316_POSITION_RESULT_PARSED, 0U);
    p290_progress_position(P316_POSITION_RESULT_CLASSIFIED, 0U);
    p290_progress_position(P316_POSITION_ENVELOPE_READY, 0U);
    p317_publish(tty_fd, &observation);
}
