/* Included by stage3/linux_init/init_v631.c. Do not compile standalone. */

static void storage_boot_set_line(void *ctx, int line, const char *text) {
    (void)ctx;
    boot_splash_set_line((size_t)line, "%s", text);
}

static void storage_boot_draw_frame(void *ctx) {
    (void)ctx;
    boot_auto_frame();
}

static void selftest_boot_set_line(void *ctx, int line, const char *text) {
    (void)ctx;
    boot_splash_set_line((size_t)line, "%s", text);
}

static void selftest_boot_draw_frame(void *ctx) {
    (void)ctx;
    boot_auto_frame();
}


#define A90_V631_SIBLING_SSCTL_FLAG "/cache/native-init-sibling-ssctl-v631"
#define A90_V631_SIBLING_SSCTL_LOG "/cache/native-init-sibling-ssctl-v631.log"
#define A90_V631_SIBLING_SSCTL_TIMEOUT_MS 5000

static int v631_append_ssctl_log(const char *fmt, ...) {
    int fd;
    int rc;
    va_list ap;

    fd = open(A90_V631_SIBLING_SSCTL_LOG,
              O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return -1;
    }

    va_start(ap, fmt);
    rc = vdprintf(fd, fmt, ap);
    va_end(ap);
    close(fd);
    return rc < 0 ? -1 : 0;
}

static bool v631_sibling_ssctl_flag_armed(void) {
    char state[32];

    if (read_trimmed_text_file(A90_V631_SIBLING_SSCTL_FLAG,
                               state,
                               sizeof(state)) < 0) {
        a90_logf("wifi-v631", "sibling ssctl disabled flag=%s errno=%d error=%s",
                 A90_V631_SIBLING_SSCTL_FLAG,
                 errno,
                 strerror(errno));
        klogf("<6>A90v631: sibling ssctl disabled flag=%s\n",
              A90_V631_SIBLING_SSCTL_FLAG);
        return false;
    }

    if (strcmp(state, "run") != 0) {
        a90_logf("wifi-v631", "sibling ssctl ignored flag=%s state=%.16s",
                 A90_V631_SIBLING_SSCTL_FLAG,
                 state);
        klogf("<6>A90v631: sibling ssctl ignored state=%.16s\n", state);
        return false;
    }

    if (unlink(A90_V631_SIBLING_SSCTL_FLAG) < 0 && errno != ENOENT) {
        a90_logf("wifi-v631", "sibling ssctl flag unlink warning errno=%d error=%s",
                 errno,
                 strerror(errno));
    }
    sync();
    return true;
}

static int v631_write_sysfs_once(const char *path) {
    int fd;
    int saved_errno;

    fd = open(path, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }

    if (write_all_checked(fd, "1\n", 2) < 0) {
        saved_errno = errno;
        close(fd);
        return -saved_errno;
    }

    if (close(fd) < 0) {
        return -errno;
    }
    return 0;
}

static void v631_sibling_ssctl_child(const char *label, const char *path) {
    int rc;

    (void)v631_append_ssctl_log("node %s child start path=%s\n", label, path);
    rc = v631_write_sysfs_once(path);
    if (rc < 0) {
        (void)v631_append_ssctl_log("node %s write rc=%d errno=%d error=%s\n",
                                   label,
                                   rc,
                                   -rc,
                                   strerror(-rc));
        klogf("<6>A90v631: sibling ssctl node=%s write failed rc=%d\n",
              label,
              rc);
        _exit(1);
    }

    (void)v631_append_ssctl_log("node %s write rc=0\n", label);
    klogf("<6>A90v631: sibling ssctl node=%s write ok\n", label);
    _exit(0);
}

static int v631_wait_child_timeout(pid_t pid,
                                   int timeout_ms,
                                   int *status_out,
                                   bool *reaped_out) {
    long deadline = monotonic_millis() + timeout_ms;
    int status;

    if (reaped_out != NULL) {
        *reaped_out = false;
    }
    while (monotonic_millis() < deadline) {
        pid_t rc = waitpid(pid, &status, WNOHANG);

        if (rc == pid) {
            if (status_out != NULL) {
                *status_out = status;
            }
            if (reaped_out != NULL) {
                *reaped_out = true;
            }
            return 0;
        }
        if (rc < 0) {
            return -errno;
        }
        usleep(100000);
    }

    (void)kill(pid, SIGKILL);
    deadline = monotonic_millis() + 1000;
    while (monotonic_millis() < deadline) {
        pid_t rc = waitpid(pid, &status, WNOHANG);

        if (rc == pid) {
            if (status_out != NULL) {
                *status_out = status;
            }
            if (reaped_out != NULL) {
                *reaped_out = true;
            }
            return -ETIMEDOUT;
        }
        if (rc < 0) {
            return -errno;
        }
        usleep(100000);
    }
    return -ETIMEDOUT;
}

static int v631_run_sibling_ssctl_node(const char *label, const char *path) {
    pid_t pid;
    int status = 0;
    int rc;
    bool reaped = false;

    (void)v631_append_ssctl_log("node %s parent start path=%s timeout_ms=%d\n",
                               label,
                               path,
                               A90_V631_SIBLING_SSCTL_TIMEOUT_MS);
    a90_timeline_record(0, 0, "wifi-v631-ssctl", "%s start", label);
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;

        (void)v631_append_ssctl_log("node %s fork failed errno=%d error=%s\n",
                                   label,
                                   saved_errno,
                                   strerror(saved_errno));
        a90_timeline_record(-saved_errno,
                            saved_errno,
                            "wifi-v631-ssctl",
                            "%s fork failed",
                            label);
        return -saved_errno;
    }

    if (pid == 0) {
        v631_sibling_ssctl_child(label, path);
    }

    rc = v631_wait_child_timeout(pid,
                                 A90_V631_SIBLING_SSCTL_TIMEOUT_MS,
                                 &status,
                                 &reaped);
    (void)v631_append_ssctl_log("node %s parent rc=%d status=0x%x reaped=%d\n",
                               label,
                               rc,
                               status,
                               reaped ? 1 : 0);
    if (rc == 0) {
        int node_rc = WIFEXITED(status) ? WEXITSTATUS(status) : EIO;

        a90_timeline_record(node_rc == 0 ? 0 : -EIO,
                            node_rc,
                            "wifi-v631-ssctl",
                            "%s status=0x%x",
                            label,
                            status);
        klogf("<6>A90v631: sibling ssctl node=%s status=0x%x\n",
              label,
              status);
        return node_rc == 0 ? 0 : -EIO;
    }

    a90_timeline_record(rc,
                        -rc,
                        "wifi-v631-ssctl",
                        "%s wait failed reaped=%d",
                        label,
                        reaped ? 1 : 0);
    klogf("<6>A90v631: sibling ssctl node=%s wait failed rc=%d reaped=%d\n",
          label,
          rc,
          reaped ? 1 : 0);
    if (!reaped) {
        return -ECHILD;
    }
    return rc;
}

static void v631_run_sibling_ssctl_once(void) {
    static const struct {
        const char *label;
        const char *path;
    } nodes[] = {
        { "adsp", "/sys/kernel/boot_adsp/boot" },
        { "cdsp", "/sys/kernel/boot_cdsp/boot" },
        { "slpi", "/sys/kernel/boot_slpi/boot" },
    };
    size_t index;
    int failures = 0;
    int timeouts = 0;

    if (!v631_sibling_ssctl_flag_armed()) {
        return;
    }

    boot_splash_set_line(5, "[ WIFI   ] V631 SSCTL PROOF");
    boot_auto_frame();
    a90_console_printf("# V631 sibling SSCTL proof: armed one-shot.\r\n");
    a90_logf("wifi-v631", "sibling ssctl proof armed timeout_ms=%d",
             A90_V631_SIBLING_SSCTL_TIMEOUT_MS);
    a90_timeline_record(0, 0, "wifi-v631-ssctl", "armed one-shot");
    klogf("<6>A90v631: sibling ssctl proof armed\n");

    for (index = 0; index < sizeof(nodes) / sizeof(nodes[0]); ++index) {
        int node_rc = v631_run_sibling_ssctl_node(nodes[index].label, nodes[index].path);

        if (node_rc != 0) {
            ++failures;
        }
        if (node_rc == -ETIMEDOUT) {
            ++timeouts;
        }
        if (node_rc == -ECHILD) {
            (void)v631_append_ssctl_log("proof stop unreaped node=%s\n",
                                       nodes[index].label);
            break;
        }
    }

    a90_console_printf("# V631 sibling SSCTL proof: failures=%d timeouts=%d.\r\n",
                       failures,
                       timeouts);
    a90_logf("wifi-v631", "sibling ssctl proof complete failures=%d timeouts=%d",
             failures,
             timeouts);
    a90_timeline_record(failures == 0 ? 0 : -EIO,
                        failures,
                        "wifi-v631-ssctl",
                        "complete failures=%d timeouts=%d",
                        failures,
                        timeouts);
    klogf("<6>A90v631: sibling ssctl proof complete failures=%d timeouts=%d\n",
          failures,
          timeouts);
}

int main(void) {
    static const struct a90_storage_boot_hooks storage_hooks = {
        .set_line = storage_boot_set_line,
        .draw_frame = storage_boot_draw_frame,
    };
    static const struct a90_selftest_boot_hooks selftest_hooks = {
        .set_line = selftest_boot_set_line,
        .draw_frame = selftest_boot_draw_frame,
    };

    a90_timeline_record(0, 0, "init-start", "%s", INIT_BANNER);
    setup_base_mounts();
    a90_log_select_or_fallback(NATIVE_LOG_FALLBACK);
    a90_logf("boot", "%s start", INIT_BANNER);
    a90_logf("boot", "base mounts ready");
    a90_timeline_record(0, 0, "base-mounts", "proc/sys/dev/tmpfs requested");
    klogf("<6>A90v631: base mounts ready\n");
    prepare_early_display_environment();
    boot_splash_set_line(1, "[ CACHE  ] MOUNTING /cache");
    boot_splash_set_line(2, "[ SD     ] WAITING FOR PROBE");
    boot_auto_frame();
    a90_logf("boot", "early display/input nodes prepared");
    a90_timeline_record(0, 0, "early-nodes", "display/input/graphics nodes prepared");
    a90_timeline_probe_boot_resources();
    klogf("<6>A90v631: early display/input nodes prepared\n");

    if (a90_storage_mount_cache() == 0) {
        a90_storage_set_cache_ready(true);
        boot_splash_set_line(1, "[ CACHE  ] OK /cache");
        a90_log_select_or_fallback(NATIVE_LOG_PRIMARY);
        a90_timeline_replay_to_log("cache");
        a90_logf("boot", "%s start", INIT_BANNER);
        a90_logf("boot", "base mounts ready");
        a90_logf("boot", "early display/input nodes prepared");
        a90_logf("boot", "cache mounted log=%s", a90_log_path());
        a90_timeline_record(0, 0, "cache-mount", "/cache mounted log=%s", a90_log_path());
        mark_step("1_cache_ok_v631\n");
        klogf("<6>A90v631: cache mounted\n");
    } else {
        int saved_errno = errno;

        a90_storage_set_cache_ready(false);
        boot_splash_set_line(1, "[ CACHE  ] WARN MOUNT FAIL");
        a90_logf("boot", "cache mount failed errno=%d error=%s log=%s",
                    saved_errno, strerror(saved_errno), a90_log_path());
        a90_timeline_record(-saved_errno,
                        saved_errno,
                        "cache-mount",
                        "/cache failed: %s log=%s",
                        strerror(saved_errno),
                        a90_log_path());
        klogf("<6>A90v631: cache mount failed (%d)\n", saved_errno);
    }
    boot_auto_frame();
    a90_storage_probe_boot(&storage_hooks, NULL);
    {
        struct a90_storage_status storage_status;
        int runtime_rc;

        if (a90_storage_get_status(&storage_status) == 0) {
            runtime_rc = a90_runtime_init(&storage_status);
        } else {
            runtime_rc = a90_runtime_init(NULL);
        }

        if (runtime_rc == 0) {
            boot_splash_set_line(4,
                    a90_runtime_using_fallback() ?
                    "[ RUNTIME] CACHE ROOT READY" :
                    "[ RUNTIME] SD ROOT READY");
            klogf("<6>A90v631: runtime root ready %s\n", a90_runtime_root());
        } else {
            int runtime_errno = -runtime_rc;

            if (runtime_errno <= 0) {
                runtime_errno = EIO;
            }
            boot_splash_set_line(4, "[ RUNTIME] WARN FALLBACK");
            klogf("<6>A90v631: runtime root warning (%d)\n", runtime_errno);
        }
        boot_auto_frame();
    }

    if (a90_helper_scan() == 0) {
        char helper_summary[96];

        a90_helper_summary(helper_summary, sizeof(helper_summary));
        boot_splash_set_line(5, "[ HELPERS] INVENTORY READY");
        a90_logf("boot", "helper inventory ready %s", helper_summary);
        klogf("<6>A90v631: helper inventory ready %s\n", helper_summary);
    } else {
        char helper_summary[96];

        a90_helper_summary(helper_summary, sizeof(helper_summary));
        boot_splash_set_line(5, "[ HELPERS] WARN SEE SELFTEST");
        a90_logf("boot", "helper inventory warning %s", helper_summary);
        klogf("<6>A90v631: helper inventory warning %s\n", helper_summary);
    }
    boot_auto_frame();

    if (a90_userland_scan() == 0) {
        char userland_summary[96];

        a90_userland_summary(userland_summary, sizeof(userland_summary));
        boot_splash_set_line(5, "[USERLAND] INVENTORY READY");
        a90_logf("boot", "userland inventory ready %s", userland_summary);
        klogf("<6>A90v631: userland inventory ready %s\n", userland_summary);
    } else {
        char userland_summary[96];

        a90_userland_summary(userland_summary, sizeof(userland_summary));
        boot_splash_set_line(5, "[USERLAND] OPTIONAL MISSING");
        a90_logf("boot", "userland inventory warning %s", userland_summary);
        klogf("<6>A90v631: userland inventory warning %s\n", userland_summary);
    }
    boot_auto_frame();

    if (a90_usb_gadget_setup_acm() == 0) {
        mark_step("2_gadget_ok_v631\n");
        boot_splash_set_line(4, "[ SERIAL ] ACM GADGET OK");
        a90_logf("boot", "ACM gadget configured");
        a90_timeline_record(0, 0, "usb-gadget", "ACM gadget configured");
        klogf("<6>A90v631: ACM gadget configured\n");
        (void)a90_selftest_run_boot(&selftest_hooks, NULL);
        {
            char guard_summary[96];

            refresh_pid1_guard();
            a90_pid1_guard_summary(guard_summary, sizeof(guard_summary));
            boot_splash_set_line(5,
                    a90_pid1_guard_has_failures() ?
                    "[ GUARD ] WARN SEE STATUS" :
                    "[ GUARD ] PID1 CHECK OK");
            boot_auto_frame();
            a90_logf("boot", "pid1 guard %s", guard_summary);
            a90_timeline_record(a90_pid1_guard_has_failures() ? -EIO : 0,
                            a90_pid1_guard_has_failures() ? EIO : 0,
                            "pid1-guard",
                            "%s",
                            guard_summary);
            klogf("<6>A90v631: pid1 guard %s\n", guard_summary);
        }
    } else {
        int saved_errno = errno;

        boot_splash_set_line(4, "[ SERIAL ] FAIL ACM GADGET");
        boot_auto_frame();
        a90_logf("boot", "ACM gadget failed errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        a90_timeline_record(-saved_errno,
                        saved_errno,
                        "usb-gadget",
                        "ACM gadget failed: %s",
                        strerror(saved_errno));
        klogf("<6>A90v631: ACM gadget failed (%d)\n", saved_errno);
        while (1) {
            sleep(60);
        }
    }

    if (a90_console_wait_tty() == 0) {
        mark_step("3_tty_ready_v631\n");
        boot_splash_set_line(4, "[ SERIAL ] TTYGS0 READY");
        boot_splash_set_line(5, "[ RUNTIME] HUD MENU LOADING");
        a90_logf("boot", "ttyGS0 ready");
        a90_timeline_record(0, 0, "ttyGS0", "/dev/ttyGS0 ready");
        klogf("<6>A90v631: ttyGS0 ready\n");
        boot_auto_frame();
        sleep(BOOT_SPLASH_SECONDS);
    } else {
        int saved_errno = errno;

        boot_splash_set_line(4, "[ SERIAL ] FAIL TTYGS0");
        boot_auto_frame();
        a90_logf("boot", "ttyGS0 missing errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        a90_timeline_record(-saved_errno,
                        saved_errno,
                        "ttyGS0",
                        "/dev/ttyGS0 missing: %s",
                        strerror(saved_errno));
        klogf("<6>A90v631: ttyGS0 missing (%d)\n", saved_errno);
        while (1) {
            sleep(60);
        }
    }

    if (a90_console_attach() == 0) {
        mark_step("4_console_attached_v631\n");
        boot_splash_set_line(5, "[ RUNTIME] SHELL READY");
        a90_logf("boot", "console attached");
        a90_timeline_record(0, 0, "console", "serial console attached");
        a90_console_drain_input(250, 1500);
        a90_console_printf("\r\n# %s\r\n", INIT_BANNER);
        a90_console_printf("# USB ACM serial console ready.\r\n");
        v631_run_sibling_ssctl_once();
        if (start_auto_hud(BOOT_HUD_REFRESH_SECONDS, false) == 0) {
            a90_logf("boot", "autohud started refresh=%d", BOOT_HUD_REFRESH_SECONDS);
            a90_timeline_record(0, 0, "autohud", "started refresh=%d", BOOT_HUD_REFRESH_SECONDS);
            a90_console_printf("# Boot display: splash %ds -> autohud %ds.\r\n",
                    BOOT_SPLASH_SECONDS,
                    BOOT_HUD_REFRESH_SECONDS);
        } else {
            int saved_errno = errno;

            a90_logf("boot", "autohud start failed errno=%d error=%s",
                        saved_errno, strerror(saved_errno));
            a90_timeline_record(-saved_errno,
                            saved_errno,
                            "autohud",
                            "start failed: %s",
                            strerror(saved_errno));
            a90_console_printf("# Boot display: autohud start failed.\r\n");
        }
        if (a90_netservice_enabled()) {
            int net_rc;

            a90_console_printf("# Netservice: enabled, starting NCM/tcpctl.\r\n");
            net_rc = a90_netservice_start();
            if (net_rc == 0) {
                mark_step("5_netservice_ok_v631\n");
                a90_console_printf("# Netservice: NCM %s %s, tcpctl port %s.\r\n",
                        NETSERVICE_IFNAME,
                        NETSERVICE_DEVICE_IP,
                        NETSERVICE_TCP_PORT);
                klogf("<6>A90v631: netservice started\n");
            } else {
                int net_errno = -net_rc;

                if (net_errno < 0) {
                    net_errno = EIO;
                }
                a90_console_printf("# Netservice: start failed rc=%d errno=%d (%s).\r\n",
                        net_rc,
                        net_errno,
                        strerror(net_errno));
                a90_logf("boot", "netservice failed rc=%d errno=%d error=%s",
                            net_rc, net_errno, strerror(net_errno));
                a90_timeline_record(net_rc,
                                net_errno,
                                "netservice",
                                "start failed: %s",
                                strerror(net_errno));
                klogf("<6>A90v631: netservice failed (%d)\n", net_errno);
            }
        } else {
            a90_logf("boot", "netservice disabled flag=%s", NETSERVICE_FLAG_PATH);
        }
        if (rshell_enabled()) {
            int rshell_rc;

            a90_console_printf("# Remote shell: enabled, starting token TCP shell.\r\n");
            rshell_rc = rshell_start_service(false);
            if (rshell_rc == 0) {
                mark_step("6_rshell_ok_v631\n");
                a90_console_printf("# Remote shell: %s:%s ready.\r\n",
                        A90_RSHELL_BIND_ADDR,
                        A90_RSHELL_PORT);
                klogf("<6>A90v631: rshell started\n");
            } else {
                int rshell_errno = -rshell_rc;

                if (rshell_errno <= 0) {
                    rshell_errno = EIO;
                }
                a90_console_printf("# Remote shell: start failed rc=%d errno=%d (%s).\r\n",
                        rshell_rc,
                        rshell_errno,
                        strerror(rshell_errno));
                a90_logf("boot", "rshell failed rc=%d errno=%d error=%s",
                            rshell_rc, rshell_errno, strerror(rshell_errno));
                a90_timeline_record(rshell_rc,
                                rshell_errno,
                                "rshell",
                                "start failed: %s",
                                strerror(rshell_errno));
                klogf("<6>A90v631: rshell failed (%d)\n", rshell_errno);
            }
        } else {
            a90_logf("boot", "rshell disabled");
        }
        a90_logf("boot", "entering shell");
        a90_timeline_record(0, 0, "shell", "interactive shell ready");
        shell_loop();
    } else {
        int saved_errno = errno;
        a90_logf("boot", "console attach failed errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        a90_timeline_record(-saved_errno,
                        saved_errno,
                        "console",
                        "attach failed: %s",
                        strerror(saved_errno));
        klogf("<6>A90v631: console attach failed (%d)\n", saved_errno);
    }

    while (1) {
        sleep(60);
    }
}
