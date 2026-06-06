/* Included by stage3/linux_init/init_v80.c. Do not compile standalone. */

int main(void) {
    timeline_record(0, 0, "init-start", "%s", INIT_BANNER);
    setup_base_mounts();
    native_log_select(NATIVE_LOG_FALLBACK);
    native_logf("boot", "%s start", INIT_BANNER);
    native_logf("boot", "base mounts ready");
    timeline_record(0, 0, "base-mounts", "proc/sys/dev/tmpfs requested");
    klogf("<6>A90v80: base mounts ready\n");
    prepare_early_display_environment();
    boot_splash_set_line(1, "[ CACHE  ] MOUNTING /cache");
    boot_splash_set_line(2, "[ SD     ] WAITING FOR PROBE");
    boot_auto_frame();
    native_logf("boot", "early display/input nodes prepared");
    timeline_record(0, 0, "early-nodes", "display/input/graphics nodes prepared");
    timeline_probe_boot_resources();
    klogf("<6>A90v80: early display/input nodes prepared\n");

    if (mount_cache() == 0) {
        cache_mount_ready = true;
        boot_splash_set_line(1, "[ CACHE  ] OK /cache");
        native_log_select(NATIVE_LOG_PRIMARY);
        timeline_replay_to_log("cache");
        native_logf("boot", "%s start", INIT_BANNER);
        native_logf("boot", "base mounts ready");
        native_logf("boot", "early display/input nodes prepared");
        native_logf("boot", "cache mounted log=%s", native_log_current_path());
        timeline_record(0, 0, "cache-mount", "/cache mounted log=%s", native_log_current_path());
        mark_step("1_cache_ok_v80\n");
        klogf("<6>A90v80: cache mounted\n");
    } else {
        int saved_errno = errno;

        cache_mount_ready = false;
        boot_splash_set_line(1, "[ CACHE  ] WARN MOUNT FAIL");
        native_logf("boot", "cache mount failed errno=%d error=%s log=%s",
                    saved_errno, strerror(saved_errno), native_log_current_path());
        timeline_record(-saved_errno,
                        saved_errno,
                        "cache-mount",
                        "/cache failed: %s log=%s",
                        strerror(saved_errno),
                        native_log_current_path());
        klogf("<6>A90v80: cache mount failed (%d)\n", saved_errno);
    }
    boot_auto_frame();
    boot_storage_probe();

    if (setup_acm_gadget() == 0) {
        mark_step("2_gadget_ok_v80\n");
        boot_splash_set_line(4, "[ SERIAL ] ACM GADGET OK");
        native_logf("boot", "ACM gadget configured");
        timeline_record(0, 0, "usb-gadget", "ACM gadget configured");
        klogf("<6>A90v80: ACM gadget configured\n");
    } else {
        int saved_errno = errno;

        boot_splash_set_line(4, "[ SERIAL ] FAIL ACM GADGET");
        boot_auto_frame();
        native_logf("boot", "ACM gadget failed errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        timeline_record(-saved_errno,
                        saved_errno,
                        "usb-gadget",
                        "ACM gadget failed: %s",
                        strerror(saved_errno));
        klogf("<6>A90v80: ACM gadget failed (%d)\n", saved_errno);
        while (1) {
            sleep(60);
        }
    }

    if (wait_for_tty_gs0() == 0) {
        mark_step("3_tty_ready_v80\n");
        boot_splash_set_line(4, "[ SERIAL ] TTYGS0 READY");
        boot_splash_set_line(5, "[ RUNTIME] HUD MENU LOADING");
        native_logf("boot", "ttyGS0 ready");
        timeline_record(0, 0, "ttyGS0", "/dev/ttyGS0 ready");
        klogf("<6>A90v80: ttyGS0 ready\n");
        boot_auto_frame();
        sleep(BOOT_SPLASH_SECONDS);
    } else {
        int saved_errno = errno;

        boot_splash_set_line(4, "[ SERIAL ] FAIL TTYGS0");
        boot_auto_frame();
        native_logf("boot", "ttyGS0 missing errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        timeline_record(-saved_errno,
                        saved_errno,
                        "ttyGS0",
                        "/dev/ttyGS0 missing: %s",
                        strerror(saved_errno));
        klogf("<6>A90v80: ttyGS0 missing (%d)\n", saved_errno);
        while (1) {
            sleep(60);
        }
    }

    if (attach_console() == 0) {
        mark_step("4_console_attached_v80\n");
        boot_splash_set_line(5, "[ RUNTIME] SHELL READY");
        native_logf("boot", "console attached");
        timeline_record(0, 0, "console", "serial console attached");
        drain_console_input(250, 1500);
        cprintf("\r\n# %s\r\n", INIT_BANNER);
        cprintf("# USB ACM serial console ready.\r\n");
        if (start_auto_hud(BOOT_HUD_REFRESH_SECONDS, false) == 0) {
            native_logf("boot", "autohud started refresh=%d", BOOT_HUD_REFRESH_SECONDS);
            timeline_record(0, 0, "autohud", "started refresh=%d", BOOT_HUD_REFRESH_SECONDS);
            cprintf("# Boot display: splash %ds -> autohud %ds.\r\n",
                    BOOT_SPLASH_SECONDS,
                    BOOT_HUD_REFRESH_SECONDS);
        } else {
            int saved_errno = errno;

            native_logf("boot", "autohud start failed errno=%d error=%s",
                        saved_errno, strerror(saved_errno));
            timeline_record(-saved_errno,
                            saved_errno,
                            "autohud",
                            "start failed: %s",
                            strerror(saved_errno));
            cprintf("# Boot display: autohud start failed.\r\n");
        }
        if (netservice_enabled_flag()) {
            int net_rc;

            cprintf("# Netservice: enabled, starting NCM/tcpctl.\r\n");
            net_rc = netservice_start();
            if (net_rc == 0) {
                mark_step("5_netservice_ok_v80\n");
                cprintf("# Netservice: NCM %s %s, tcpctl port %s.\r\n",
                        NETSERVICE_IFNAME,
                        NETSERVICE_DEVICE_IP,
                        NETSERVICE_TCP_PORT);
                klogf("<6>A90v80: netservice started\n");
            } else {
                int net_errno = -net_rc;

                if (net_errno < 0) {
                    net_errno = EIO;
                }
                cprintf("# Netservice: start failed rc=%d errno=%d (%s).\r\n",
                        net_rc,
                        net_errno,
                        strerror(net_errno));
                native_logf("boot", "netservice failed rc=%d errno=%d error=%s",
                            net_rc, net_errno, strerror(net_errno));
                timeline_record(net_rc,
                                net_errno,
                                "netservice",
                                "start failed: %s",
                                strerror(net_errno));
                klogf("<6>A90v80: netservice failed (%d)\n", net_errno);
            }
        } else {
            native_logf("boot", "netservice disabled flag=%s", NETSERVICE_FLAG_PATH);
        }
        native_logf("boot", "entering shell");
        timeline_record(0, 0, "shell", "interactive shell ready");
        shell_loop();
    } else {
        int saved_errno = errno;
        native_logf("boot", "console attach failed errno=%d error=%s",
                    saved_errno, strerror(saved_errno));
        timeline_record(-saved_errno,
                        saved_errno,
                        "console",
                        "attach failed: %s",
                        strerror(saved_errno));
        klogf("<6>A90v80: console attach failed (%d)\n", saved_errno);
    }

    while (1) {
        sleep(60);
    }
}
