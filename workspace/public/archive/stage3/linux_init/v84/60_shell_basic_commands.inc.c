/* Included by stage3/linux_init/init_v84.c. Do not compile standalone. */

static int cmd_pwd(void) {
    char cwd[PATH_MAX];

    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        a90_console_printf("pwd: %s\r\n", strerror(errno));
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("%s\r\n", cwd);
    return 0;
}

static void cmd_help(void) {
    a90_console_printf("help\r\n");
    a90_console_printf("version\r\n");
    a90_console_printf("status\r\n");
    a90_console_printf("last\r\n");
    a90_console_printf("logpath\r\n");
    a90_console_printf("logcat\r\n");
    a90_console_printf("timeline\r\n");
    a90_console_printf("bootstatus\r\n");
    a90_console_printf("blocking commands: q or Ctrl-C cancels\r\n");
    a90_console_printf("uname\r\n");
    a90_console_printf("pwd\r\n");
    a90_console_printf("cd <dir>\r\n");
    a90_console_printf("ls [dir]\r\n");
    a90_console_printf("cat <file>\r\n");
    a90_console_printf("stat <path>\r\n");
    a90_console_printf("mounts\r\n");
    a90_console_printf("mountsystem [ro|rw]\r\n");
    a90_console_printf("mountsd [status|ro|rw|off|init]\r\n");
    a90_console_printf("storage\r\n");
    a90_console_printf("prepareandroid\r\n");
    a90_console_printf("inputinfo [eventX]\r\n");
    a90_console_printf("drminfo [entry]\r\n");
    a90_console_printf("fbinfo [fbX]\r\n");
    a90_console_printf("kmsprobe\r\n");
    a90_console_printf("kmssolid [color]\r\n");
    a90_console_printf("kmsframe\r\n");
    a90_console_printf("statusscreen\r\n");
    a90_console_printf("statushud\r\n");
    a90_console_printf("watchhud [sec] [count]\r\n");
    a90_console_printf("autohud [sec]\r\n");
    a90_console_printf("stophud\r\n");
    a90_console_printf("redraw\r\n");
    a90_console_printf("testpattern\r\n");
    a90_console_printf("clear\r\n");
    a90_console_printf("inputcaps <eventX>\r\n");
    a90_console_printf("readinput <eventX> [count]\r\n");
    a90_console_printf("waitkey [count]\r\n");
    a90_console_printf("inputlayout\r\n");
    a90_console_printf("waitgesture [count]\r\n");
    a90_console_printf("inputmonitor [events]\r\n");
    a90_console_printf("displaytest [0-3|colors|font|safe|layout]\r\n");
    a90_console_printf("cutoutcal [x y size]\r\n");
    a90_console_printf("menu\r\n");
    a90_console_printf("screenmenu\r\n");
    a90_console_printf("cmdv1 <command> [args...]\r\n");
    a90_console_printf("cmdv1x <len:hex-utf8-arg>...\r\n");
    a90_console_printf("blindmenu\r\n");
    a90_console_printf("mkdir <dir>\r\n");
    a90_console_printf("mknodc <path> <major> <minor>\r\n");
    a90_console_printf("mknodb <path> <major> <minor>\r\n");
    a90_console_printf("mountfs <src> <dst> <type> [ro]\r\n");
    a90_console_printf("umount <path>\r\n");
    a90_console_printf("echo <text>\r\n");
    a90_console_printf("writefile <path> <value...>\r\n");
    a90_console_printf("cpustress [sec] [workers]\r\n");
    a90_console_printf("run <path> [args...]\r\n");
    a90_console_printf("runandroid <path> [args...]\r\n");
    a90_console_printf("startadbd\r\n");
    a90_console_printf("stopadbd\r\n");
    a90_console_printf("netservice [status|start|stop|enable|disable]\r\n");
    a90_console_printf("reattach\r\n");
    a90_console_printf("usbacmreset\r\n");
    a90_console_printf("sync\r\n");
    a90_console_printf("reboot\r\n");
    a90_console_printf("recovery\r\n");
    a90_console_printf("poweroff\r\n");
}

static int cmd_uname(void) {
    struct utsname uts;

    if (uname(&uts) < 0) {
        a90_console_printf("uname: %s\r\n", strerror(errno));
        return negative_errno_or(EIO);
    }

    a90_console_printf("%s %s %s %s %s\r\n",
            uts.sysname, uts.nodename, uts.release, uts.version, uts.machine);
    return 0;
}

static void cmd_version(void) {
    struct utsname uts;

    a90_console_printf("%s\r\n", INIT_BANNER);
    a90_console_printf("%s\r\n", INIT_CREATOR);
    a90_console_printf("version: %s build=%s\r\n", INIT_VERSION, INIT_BUILD);
    if (uname(&uts) == 0) {
        a90_console_printf("kernel: %s %s %s\r\n", uts.sysname, uts.release, uts.machine);
    }
    if (kms_state.fd >= 0) {
        a90_console_printf("display: %ux%u connector=%u crtc=%u fb=%u\r\n",
                kms_state.width,
                kms_state.height,
                kms_state.connector_id,
                kms_state.crtc_id,
                kms_state.fb_id[kms_state.current_buffer]);
    } else {
        a90_console_printf("display: not initialized\r\n");
    }
}

static void cmd_status(void) {
    struct status_snapshot snapshot;
    char boot_summary[64];

    read_status_snapshot(&snapshot);
    a90_timeline_boot_summary(boot_summary, sizeof(boot_summary));

    a90_console_printf("init: %s\r\n", INIT_BANNER);
    a90_console_printf("creator: %s\r\n", INIT_CREATOR);
    a90_console_printf("boot: %s\r\n", boot_summary);
    a90_console_printf("uptime: %ss  load=%s\r\n", snapshot.uptime, snapshot.loadavg);
    a90_console_printf("battery: %s %s temp=%s voltage=%s\r\n",
            snapshot.battery_pct,
            snapshot.battery_status,
            snapshot.battery_temp,
            snapshot.battery_voltage);
    a90_console_printf("power: now=%s avg=%s\r\n", snapshot.power_now, snapshot.power_avg);
    a90_console_printf("thermal: cpu=%s %s gpu=%s %s\r\n",
            snapshot.cpu_temp,
            snapshot.cpu_usage,
            snapshot.gpu_temp,
            snapshot.gpu_usage);
    a90_console_printf("memory: %s used\r\n", snapshot.memory);
    if (kms_state.fd >= 0) {
        a90_console_printf("display: %ux%u connector=%u crtc=%u current_buffer=%u\r\n",
                kms_state.width,
                kms_state.height,
                kms_state.connector_id,
                kms_state.crtc_id,
                kms_state.current_buffer);
    } else {
        a90_console_printf("display: not initialized\r\n");
    }
    a90_console_printf("adbd: %s\r\n", adbd_pid > 0 ? "started" : "stopped");
    reap_hud_child();
    a90_console_printf("autohud: %s\r\n", hud_pid > 0 ? "running" : "stopped");
    reap_tcpctl_child();
    a90_console_printf("netservice: %s tcpctl=%s\r\n",
            netservice_enabled_flag() ? "enabled" : "disabled",
            tcpctl_pid > 0 ? "running" : "stopped");
    cmd_storage();
    cmd_mountsd((char *[]){ "mountsd", "status" }, 2);
}

static void cpustress_worker(long deadline_ms, unsigned int worker_index) {
    volatile unsigned long long accumulator =
        0x9e3779b97f4a7c15ULL ^ ((unsigned long long)getpid() << 17) ^ worker_index;

    while (monotonic_millis() < deadline_ms) {
        int index;

        for (index = 0; index < 200000; ++index) {
            accumulator ^= accumulator << 7;
            accumulator ^= accumulator >> 9;
            accumulator += 0x9e3779b97f4a7c15ULL + (unsigned long long)index;
        }
    }

    (void)accumulator;
    _exit(0);
}

static void cpustress_stop_workers(pid_t *pids, unsigned int workers) {
    unsigned int index;

    for (index = 0; index < workers; ++index) {
        if (pids[index] > 0) {
            kill(pids[index], SIGTERM);
        }
    }
    usleep(100000);
    for (index = 0; index < workers; ++index) {
        if (pids[index] > 0) {
            kill(pids[index], SIGKILL);
        }
    }
    for (index = 0; index < workers; ++index) {
        if (pids[index] > 0) {
            waitpid(pids[index], NULL, 0);
            pids[index] = -1;
        }
    }
}

static int cmd_cpustress(char **argv, int argc) {
    pid_t pids[16];
    long seconds = 10;
    long workers_long = 4;
    unsigned int workers;
    unsigned int started = 0;
    long deadline_ms;
    int exit_code = 0;
    unsigned int index;

    if (argc > 1) {
        seconds = strtol(argv[1], NULL, 10);
    }
    if (argc > 2) {
        workers_long = strtol(argv[2], NULL, 10);
    }
    if (argc > 3 || seconds < 1 || seconds > 120 || workers_long < 1 || workers_long > 16) {
        a90_console_printf("usage: cpustress [sec 1-120] [workers 1-16]\r\n");
        return -EINVAL;
    }

    workers = (unsigned int)workers_long;
    for (index = 0; index < workers; ++index) {
        pids[index] = -1;
    }

    deadline_ms = monotonic_millis() + seconds * 1000L;
    a90_console_printf("cpustress: workers=%u sec=%ld, q/Ctrl-C cancels\r\n", workers, seconds);

    for (index = 0; index < workers; ++index) {
        pid_t pid = fork();

        if (pid < 0) {
            int saved_errno = errno;
            a90_console_printf("cpustress: fork worker %u: %s\r\n", index, strerror(saved_errno));
            cpustress_stop_workers(pids, started);
            return -saved_errno;
        }
        if (pid == 0) {
            cpustress_worker(deadline_ms, index);
        }
        pids[index] = pid;
        ++started;
    }

    while (started > 0) {
        enum a90_cancel_kind cancel;

        for (index = 0; index < workers; ++index) {
            if (pids[index] > 0) {
                int status;
                pid_t got = waitpid(pids[index], &status, WNOHANG);

                if (got == pids[index]) {
                    pids[index] = -1;
                    --started;
                    if (WIFSIGNALED(status)) {
                        exit_code = -EINTR;
                    }
                }
            }
        }
        if (started == 0) {
            break;
        }

        cancel = a90_console_poll_cancel(100);
        if (cancel != CANCEL_NONE) {
            cpustress_stop_workers(pids, workers);
            return a90_console_cancelled("cpustress", cancel);
        }

        if (monotonic_millis() > deadline_ms + 2000L) {
            cpustress_stop_workers(pids, workers);
            a90_console_printf("cpustress: timeout cleanup\r\n");
            return -ETIMEDOUT;
        }
    }

    a90_console_printf("cpustress: done workers=%u sec=%ld\r\n", workers, seconds);
    return exit_code;
}

static int cmd_ls(const char *path) {
    DIR *dir;
    struct dirent *entry;
    int first_error = 0;

    dir = opendir(path);
    if (dir == NULL) {
        a90_console_printf("ls: %s: %s\r\n", path, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    while ((entry = readdir(dir)) != NULL) {
        char full[PATH_MAX];
        struct stat st;
        char type = '?';

        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }

        if (snprintf(full, sizeof(full), "%s/%s", path, entry->d_name) >= (int)sizeof(full)) {
            continue;
        }

        if (lstat(full, &st) == 0) {
            if (S_ISDIR(st.st_mode)) {
                type = 'd';
            } else if (S_ISLNK(st.st_mode)) {
                type = 'l';
            } else if (S_ISCHR(st.st_mode)) {
                type = 'c';
            } else if (S_ISBLK(st.st_mode)) {
                type = 'b';
            } else if (S_ISREG(st.st_mode)) {
                type = '-';
            }
            a90_console_printf("%c %8ld %s\r\n", type, (long)st.st_size, entry->d_name);
        } else {
            a90_console_printf("? ???????? %s\r\n", entry->d_name);
            if (first_error == 0) {
                first_error = negative_errno_or(EIO);
            }
        }
    }

    closedir(dir);
    return first_error;
}

static int cmd_cat(const char *path) {
    char buf[512];
    int fd = open(path, O_RDONLY);

    if (fd < 0) {
        a90_console_printf("cat: %s: %s\r\n", path, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    while (1) {
        ssize_t rd = read(fd, buf, sizeof(buf));
        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            a90_console_printf("cat: %s: %s\r\n", path, strerror(errno));
            close(fd);
            return negative_errno_or(EIO);
        }
        if (rd == 0) {
            break;
        }
        a90_console_write(buf, (size_t)rd);
    }

    close(fd);
    a90_console_printf("\r\n");
    return 0;
}

static int cmd_logpath(void) {
    a90_console_printf("log: path=%s ready=%s max=%d\r\n",
            a90_log_path(),
            a90_log_ready() ? "yes" : "no",
            NATIVE_LOG_MAX_BYTES);
    return a90_log_ready() ? 0 : -EIO;
}

static int cmd_logcat(void) {
    if (!a90_log_ready()) {
        a90_console_printf("logcat: log is not ready\r\n");
        return -ENOENT;
    }
    return cmd_cat(a90_log_path());
}

static int cmd_timeline(void) {
    size_t count = a90_timeline_count();
    size_t index;

    a90_console_printf("timeline: count=%ld max=%d\r\n",
            (long)count,
            BOOT_TIMELINE_MAX);

    for (index = 0; index < count && index < BOOT_TIMELINE_MAX; ++index) {
        const struct a90_timeline_entry *entry = a90_timeline_entry_at(index);

        if (entry == NULL) {
            continue;
        }

        a90_console_printf("%02ld %8ldms %-18s rc=%d errno=%d %s\r\n",
                (long)index,
                entry->ms,
                entry->step,
                entry->code,
                entry->saved_errno,
                entry->detail);
    }

    return count > 0 ? 0 : -ENOENT;
}

static int cmd_bootstatus(void) {
    char summary[64];
    size_t count = a90_timeline_count();

    a90_timeline_boot_summary(summary, sizeof(summary));
    a90_console_printf("boot: %s\r\n", summary);
    a90_console_printf("timeline_entries: %ld/%d\r\n",
            (long)count,
            BOOT_TIMELINE_MAX);
    return count > 0 ? 0 : -ENOENT;
}

static int cmd_stat(const char *path) {
    struct stat st;

    if (lstat(path, &st) < 0) {
        a90_console_printf("stat: %s: %s\r\n", path, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("mode=0%o uid=%ld gid=%ld size=%ld\r\n",
            st.st_mode & 07777, (long)st.st_uid, (long)st.st_gid, (long)st.st_size);
    if (S_ISBLK(st.st_mode) || S_ISCHR(st.st_mode)) {
        a90_console_printf("rdev=%u:%u\r\n", major(st.st_rdev), minor(st.st_rdev));
    }
    return 0;
}

static int cmd_mounts(void) {
    return cmd_cat("/proc/mounts");
}

static int cmd_mountsystem(bool read_only) {
    unsigned long flags = read_only ? MS_RDONLY : 0;
    char node_path[PATH_MAX];

    ensure_dir("/mnt", 0755);
    ensure_dir("/mnt/system", 0755);

    if (get_block_device_path("sda28", node_path, sizeof(node_path)) < 0) {
        a90_console_printf("mountsystem: mknod failed: %s\r\n", strerror(errno));
        return negative_errno_or(EIO);
    }

    if (mount(node_path, "/mnt/system", "ext4", flags, NULL) < 0) {
        if (errno == EBUSY) {
            a90_console_printf("mountsystem: already mounted\r\n");
            return 0;
        } else {
            a90_console_printf("mountsystem: %s\r\n", strerror(errno));
        }
        return negative_errno_or(EIO);
    }

    a90_console_printf("mountsystem: /mnt/system ready (%s)\r\n", read_only ? "ro" : "rw");
    return 0;
}

static bool mount_line_for_path(const char *path,
                                char *out,
                                size_t out_size,
                                bool *read_only_out) {
    FILE *fp;
    char line[512];

    if (out_size > 0) {
        out[0] = '\0';
    }
    if (read_only_out != NULL) {
        *read_only_out = false;
    }
    fp = fopen("/proc/mounts", "r");
    if (fp == NULL) {
        return false;
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        char src[160];
        char dst[160];
        char type[64];
        char opts[192];

        if (sscanf(line, "%159s %159s %63s %191s", src, dst, type, opts) != 4) {
            continue;
        }
        if (strcmp(dst, path) == 0) {
            if (out_size > 0) {
                snprintf(out, out_size, "%s", line);
            }
            if (read_only_out != NULL) {
                char opt_copy[192];
                char *token;
                char *saveptr = NULL;

                snprintf(opt_copy, sizeof(opt_copy), "%s", opts);
                for (token = strtok_r(opt_copy, ",", &saveptr);
                     token != NULL;
                     token = strtok_r(NULL, ",", &saveptr)) {
                    if (strcmp(token, "ro") == 0) {
                        *read_only_out = true;
                        break;
                    }
                }
            }
            fclose(fp);
            return true;
        }
    }
    fclose(fp);
    return false;
}

static int read_ext4_uuid(const char *node_path, char *out, size_t out_size) {
    unsigned char uuid[16];
    ssize_t rd;
    int fd;

    if (out_size < 37) {
        errno = ENOSPC;
        return -1;
    }
    fd = open(node_path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    rd = pread(fd, uuid, sizeof(uuid), 1024 + 0x68);
    close(fd);
    if (rd != (ssize_t)sizeof(uuid)) {
        errno = EIO;
        return -1;
    }
    snprintf(out,
             out_size,
             "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
             uuid[0], uuid[1], uuid[2], uuid[3],
             uuid[4], uuid[5],
             uuid[6], uuid[7],
             uuid[8], uuid[9],
             uuid[10], uuid[11], uuid[12], uuid[13], uuid[14], uuid[15]);
    return 0;
}

static int write_text_file_sync(const char *path, const char *value) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);

    if (fd < 0) {
        return -1;
    }
    if (write_all_checked(fd, value, strlen(value)) < 0 ||
        fsync(fd) < 0) {
        int saved_errno = errno;

        close(fd);
        errno = saved_errno;
        return -1;
    }
    if (close(fd) < 0) {
        return -1;
    }
    return 0;
}

static int ensure_sd_workspace(void) {
    static const char *dirs[] = {
        SD_WORKSPACE_DIR,
        SD_WORKSPACE_DIR "/bin",
        SD_WORKSPACE_DIR "/logs",
        SD_WORKSPACE_DIR "/tmp",
        SD_WORKSPACE_DIR "/rootfs",
        SD_WORKSPACE_DIR "/images",
        SD_WORKSPACE_DIR "/backups",
    };
    size_t index;

    for (index = 0; index < SCREEN_MENU_COUNT(dirs); ++index) {
        if (ensure_dir(dirs[index], 0755) < 0) {
            int saved_errno = errno;

            a90_console_printf("mountsd: mkdir %s: %s\r\n", dirs[index], strerror(saved_errno));
            return -saved_errno;
        }
    }
    return 0;
}

static int ensure_sd_identity_marker(const char *uuid) {
    char marker[96];
    int saved_errno;

    if (read_trimmed_text_file(SD_ID_FILE, marker, sizeof(marker)) == 0) {
        if (strcmp(marker, uuid) == 0) {
            return 0;
        }
        errno = ESTALE;
        return -1;
    }

    saved_errno = errno;
    if (saved_errno != ENOENT) {
        errno = saved_errno;
        return -1;
    }
    if (write_text_file_sync(SD_ID_FILE, uuid) < 0) {
        return -1;
    }
    return 0;
}

static int sd_write_read_probe(void) {
    char payload[128];
    char readback[128];

    snprintf(payload,
             sizeof(payload),
             "boot-rw-test %s %s %ld",
             INIT_VERSION,
             INIT_BUILD,
             monotonic_millis());
    if (write_text_file_sync(SD_BOOT_RW_TEST_FILE, payload) < 0) {
        return -1;
    }
    sync();
    if (read_trimmed_text_file(SD_BOOT_RW_TEST_FILE, readback, sizeof(readback)) < 0) {
        return -1;
    }
    unlink(SD_BOOT_RW_TEST_FILE);
    if (strcmp(payload, readback) != 0) {
        errno = EIO;
        return -1;
    }
    return 0;
}
