/* Included by stage3/linux_init/init_v82.c. Do not compile standalone. */

static int setup_base_mounts(void) {
    ensure_dir("/proc", 0755);
    ensure_dir("/sys", 0755);
    ensure_dir("/dev", 0755);
    ensure_dir("/tmp", 0755);
    ensure_dir("/cache", 0755);
    ensure_dir("/config", 0755);
    ensure_dir("/mnt", 0755);
    ensure_dir("/dev/block", 0755);

    mount("proc", "/proc", "proc", 0, NULL);
    mount("sysfs", "/sys", "sysfs", 0, NULL);
    mount("devtmpfs", "/dev", "devtmpfs", 0, "mode=0755");
    mount("tmpfs", "/tmp", "tmpfs", 0, "mode=1777");
    ensure_char_node_exact("/dev/null", 1, 3);
    ensure_char_node_exact("/dev/zero", 1, 5);

    return 0;
}

static int mount_cache(void) {
    char node_path[PATH_MAX];

    if (get_block_device_path("sda31", node_path, sizeof(node_path)) < 0) {
        return -1;
    }

    if (mount(node_path, "/cache", "ext4", 0, NULL) == 0) {
        return 0;
    }
    return -1;
}

static int create_symlink(const char *target, const char *linkpath) {
    if (symlink(target, linkpath) == 0 || errno == EEXIST) {
        return 0;
    }
    return -1;
}

static bool path_exists(const char *path) {
    struct stat st;

    return lstat(path, &st) == 0;
}

static int ensure_block_node(const char *path, unsigned int major_num, unsigned int minor_num) {
    dev_t wanted = makedev(major_num, minor_num);

    if (mknod(path, S_IFBLK | 0600, wanted) == 0) {
        return 0;
    }
    if (errno == EEXIST) {
        struct stat st;

        if (lstat(path, &st) == 0 &&
            S_ISBLK(st.st_mode) &&
            st.st_rdev == wanted) {
            return 0;
        }

        if (unlink(path) < 0) {
            return -1;
        }
        if (mknod(path, S_IFBLK | 0600, wanted) == 0) {
            return 0;
        }
    }
    return -1;
}

static int bind_mount_dir(const char *src, const char *dst) {
    if (mount(src, dst, NULL, MS_BIND, NULL) == 0 || errno == EBUSY) {
        return 0;
    }
    return -1;
}

static int setup_acm_gadget(void) {
    if (mount("configfs", "/config", "configfs", 0, NULL) != 0 && errno != EBUSY) {
        return -1;
    }

    ensure_dir("/config/usb_gadget", 0770);
    ensure_dir("/config/usb_gadget/g1", 0770);
    ensure_dir("/config/usb_gadget/g1/strings", 0770);
    ensure_dir("/config/usb_gadget/g1/strings/0x409", 0770);
    ensure_dir("/config/usb_gadget/g1/configs", 0770);
    ensure_dir("/config/usb_gadget/g1/configs/b.1", 0770);
    ensure_dir("/config/usb_gadget/g1/configs/b.1/strings", 0770);
    ensure_dir("/config/usb_gadget/g1/configs/b.1/strings/0x409", 0770);
    ensure_dir("/config/usb_gadget/g1/functions", 0770);
    ensure_dir("/config/usb_gadget/g1/functions/acm.usb0", 0770);

    wf("/config/usb_gadget/g1/idVendor", "0x04e8");
    wf("/config/usb_gadget/g1/idProduct", "0x6861");
    wf("/config/usb_gadget/g1/bcdUSB", "0x0200");
    wf("/config/usb_gadget/g1/bcdDevice", "0x0100");
    wf("/config/usb_gadget/g1/strings/0x409/serialnumber", "RFCM90CFWXA");
    wf("/config/usb_gadget/g1/strings/0x409/manufacturer", "samsung");
    wf("/config/usb_gadget/g1/strings/0x409/product", "SM8150-ACM");
    wf("/config/usb_gadget/g1/configs/b.1/strings/0x409/configuration", "serial");
    wf("/config/usb_gadget/g1/configs/b.1/MaxPower", "900");

    if (create_symlink("/config/usb_gadget/g1/functions/acm.usb0",
                       "/config/usb_gadget/g1/configs/b.1/f1") < 0) {
        return -1;
    }

    wf("/config/usb_gadget/g1/UDC", "a600000.dwc3");
    return 0;
}

static int attach_console(void) {
    int fd;
    struct termios tio;

    fd = open("/dev/ttyGS0", O_RDWR | O_NOCTTY);
    if (fd < 0) {
        return -1;
    }

    if (tcgetattr(fd, &tio) == 0) {
        tio.c_iflag = IGNBRK;
        tio.c_oflag = 0;
        tio.c_cflag &= ~(CSIZE | PARENB | CSTOPB | CRTSCTS);
        tio.c_cflag |= CS8 | CREAD | CLOCAL;
        tio.c_lflag = 0;
        tio.c_cc[VMIN] = 1;
        tio.c_cc[VTIME] = 0;
        cfsetispeed(&tio, B115200);
        cfsetospeed(&tio, B115200);
        tcsetattr(fd, TCSANOW, &tio);
        tcflush(fd, TCIOFLUSH);
    }

    console_fd = fd;
    dup2(fd, STDIN_FILENO);
    dup2(fd, STDOUT_FILENO);
    dup2(fd, STDERR_FILENO);

    return 0;
}

static void drain_console_input(unsigned int quiet_ms, unsigned int max_ms) {
    long started_ms = monotonic_millis();
    long quiet_started_ms = started_ms;

    while (1) {
        struct pollfd pfd;
        long now_ms = monotonic_millis();
        char ch;

        if (now_ms - started_ms >= (long)max_ms) {
            return;
        }
        if (now_ms - quiet_started_ms >= (long)quiet_ms) {
            return;
        }

        pfd.fd = STDIN_FILENO;
        pfd.events = POLLIN;
        pfd.revents = 0;

        if (poll(&pfd, 1, 20) <= 0 || (pfd.revents & POLLIN) == 0) {
            continue;
        }

        if (read(STDIN_FILENO, &ch, 1) == 1) {
            quiet_started_ms = monotonic_millis();
        }
    }
}

static long console_monotonic_millis(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0) {
        return 0;
    }

    return (long)(ts.tv_sec * 1000L) + (long)(ts.tv_nsec / 1000000L);
}

static int reattach_console(const char *reason, bool announce) {
    int old_fd = console_fd;
    long now_ms = console_monotonic_millis();
    bool quiet_success = (strcmp(reason, "idle-timeout") == 0);

    if (now_ms > 0 &&
        last_console_reattach_ms > 0 &&
        now_ms - last_console_reattach_ms < 500) {
        return 0;
    }
    last_console_reattach_ms = now_ms;

    if (!quiet_success) {
        a90_logf("console", "reattach requested reason=%s old_fd=%d",
                    reason, old_fd);
        klogf("<6>A90v82: console reattach requested reason=%s old_fd=%d\n",
              reason, old_fd);
    }

    if (old_fd >= 0) {
        close(old_fd);
    }
    console_fd = -1;

    if (wait_for_tty_gs0() < 0) {
        int saved_errno = errno;
        a90_logf("console", "reattach wait failed reason=%s errno=%d error=%s",
                    reason, saved_errno, strerror(saved_errno));
        klogf("<6>A90v82: console reattach wait failed (%d)\n", saved_errno);
        errno = saved_errno;
        return -1;
    }

    if (attach_console() < 0) {
        int saved_errno = errno;
        a90_logf("console", "reattach open failed reason=%s errno=%d error=%s",
                    reason, saved_errno, strerror(saved_errno));
        klogf("<6>A90v82: console reattach open failed (%d)\n", saved_errno);
        errno = saved_errno;
        return -1;
    }

    drain_console_input(50, 200);
    if (!quiet_success) {
        a90_logf("console", "reattach ok reason=%s fd=%d", reason, console_fd);
        klogf("<6>A90v82: console reattached reason=%s fd=%d\n", reason, console_fd);
    }
    if (announce) {
        cprintf("\r\n# serial console reattached: %s\r\n", reason);
    }
    return 0;
}

static ssize_t read_line(char *buf, size_t buf_size) {
    static char pending_newline = '\0';
    static long last_idle_reattach_ms = 0;
    size_t pos = 0;

    while (pos + 1 < buf_size) {
        struct pollfd pfd;
        int poll_rc;
        char ch;
        ssize_t rd;

        pfd.fd = STDIN_FILENO;
        pfd.events = POLLIN | POLLHUP | POLLERR | POLLNVAL;
        pfd.revents = 0;

        poll_rc = poll(&pfd, 1, CONSOLE_POLL_TIMEOUT_MS);
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (poll_rc == 0) {
            long now_ms = console_monotonic_millis();

            if (now_ms > 0 &&
                now_ms - last_idle_reattach_ms >= CONSOLE_IDLE_REATTACH_MS) {
                last_idle_reattach_ms = now_ms;
                if (reattach_console("idle-timeout", false) == 0) {
                    pending_newline = '\0';
                }
            }
            continue;
        }

        if ((pfd.revents & (POLLHUP | POLLERR | POLLNVAL)) != 0) {
            if (reattach_console("poll-fault", true) < 0) {
                return -1;
            }
            pending_newline = '\0';
            continue;
        }
        if ((pfd.revents & POLLIN) == 0) {
            continue;
        }

        rd = read(STDIN_FILENO, &ch, 1);

        if (rd < 0) {
            if (errno == EINTR) {
                continue;
            }
            if (reattach_console("read-error", true) == 0) {
                pending_newline = '\0';
                continue;
            }
            return -1;
        }
        if (rd == 0) {
            if (reattach_console("read-eof", true) == 0) {
                pending_newline = '\0';
            }
            continue;
        }

        if (pending_newline != '\0' && ch == pending_newline) {
            pending_newline = '\0';
            continue;
        }
        pending_newline = '\0';

        if (ch == '\r' || ch == '\n') {
            pending_newline = (ch == '\r') ? '\n' : '\r';
            write_all(console_fd, "\r\n", 2);
            break;
        }

        if (ch == 0x7f || ch == 0x08) {
            if (pos > 0) {
                pos--;
                write_all(console_fd, "\b \b", 3);
            }
            continue;
        }

        if (ch == 0x03) {
            write_all(console_fd, "^C\r\n", 4);
            pos = 0;
            break;
        }

        if (ch == 0x15) {
            while (pos > 0) {
                --pos;
                write_all(console_fd, "\b \b", 3);
            }
            continue;
        }

        if (ch == 0x1b) {
            consume_escape_sequence();
            continue;
        }

        if ((unsigned char)ch < 0x20) {
            continue;
        }

        buf[pos++] = ch;
        write_all(console_fd, &ch, 1);
    }

    buf[pos] = '\0';
    return (ssize_t)pos;
}

static int split_args(char *line, char **argv, int argv_max) {
    int argc = 0;
    char *cursor = line;

    while (*cursor != '\0' && argc < argv_max - 1) {
        while (*cursor == ' ' || *cursor == '\t') {
            ++cursor;
        }
        if (*cursor == '\0') {
            break;
        }
        if (*cursor == '#') {
            break;
        }

        argv[argc++] = cursor;

        while (*cursor != '\0' && *cursor != ' ' && *cursor != '\t') {
            ++cursor;
        }
        if (*cursor == '\0') {
            break;
        }
        *cursor++ = '\0';
    }

    argv[argc] = NULL;
    return argc;
}

static int hex_digit_value(char ch) {
    if (ch >= '0' && ch <= '9') {
        return ch - '0';
    }
    if (ch >= 'a' && ch <= 'f') {
        return ch - 'a' + 10;
    }
    if (ch >= 'A' && ch <= 'F') {
        return ch - 'A' + 10;
    }
    return -1;
}

static int parse_cmdv1x_token(const char *token,
                              char *buf,
                              size_t buf_size,
                              size_t *buf_pos,
                              char **arg_out) {
    const char *cursor = token;
    const char *hex;
    size_t length = 0;
    size_t hex_len;
    size_t index;

    if (*cursor < '0' || *cursor > '9') {
        return -EINVAL;
    }
    while (*cursor >= '0' && *cursor <= '9') {
        size_t digit = (size_t)(*cursor - '0');

        if (length > (SIZE_MAX - digit) / 10) {
            return -EOVERFLOW;
        }
        length = length * 10 + digit;
        ++cursor;
    }
    if (*cursor != ':') {
        return -EINVAL;
    }

    hex = cursor + 1;
    hex_len = strlen(hex);
    if (length > SIZE_MAX / 2 || hex_len != length * 2) {
        return -EINVAL;
    }
    if (length + 1 > buf_size || *buf_pos > buf_size - length - 1) {
        return -E2BIG;
    }

    *arg_out = buf + *buf_pos;
    for (index = 0; index < length; ++index) {
        int high = hex_digit_value(hex[index * 2]);
        int low = hex_digit_value(hex[index * 2 + 1]);
        unsigned int value;

        if (high < 0 || low < 0) {
            return -EINVAL;
        }
        value = (unsigned int)((high << 4) | low);
        if (value == 0) {
            return -EINVAL;
        }
        buf[(*buf_pos)++] = (char)value;
    }
    buf[(*buf_pos)++] = '\0';
    return 0;
}

static int decode_cmdv1x_args(char **tokens,
                              int token_count,
                              char **argv,
                              int argv_max,
                              char *buf,
                              size_t buf_size) {
    int index;
    size_t buf_pos = 0;

    if (token_count <= 0 || token_count >= argv_max) {
        return -EINVAL;
    }

    for (index = 0; index < token_count; ++index) {
        int result = parse_cmdv1x_token(tokens[index],
                                        buf,
                                        buf_size,
                                        &buf_pos,
                                        &argv[index]);

        if (result < 0) {
            argv[0] = NULL;
            return result;
        }
    }

    argv[token_count] = NULL;
    if (argv[0][0] == '\0') {
        return -EINVAL;
    }
    return token_count;
}

static const char *skip_shell_space(const char *line) {
    while (*line == ' ' || *line == '\t') {
        ++line;
    }
    return line;
}

static bool is_at_noise_tail_char(char ch) {
    if (ch == ' ' || ch == '\t') {
        return true;
    }
    if (ch >= 'A' && ch <= 'Z') {
        return true;
    }
    if (ch >= '0' && ch <= '9') {
        return true;
    }
    switch (ch) {
    case '+':
    case '-':
    case '&':
    case '=':
    case '?':
    case '#':
    case '*':
    case '/':
    case '\\':
    case '.':
    case ',':
    case ';':
    case ':':
    case '^':
    case '!':
    case '%':
    case '(':
    case ')':
    case '[':
    case ']':
    case '<':
    case '>':
        return true;
    default:
        return false;
    }
}

static bool is_unsolicited_at_fragment_noise(const char *line) {
    const char *cursor = skip_shell_space(line);
    size_t length = 0;

    if (*cursor == '\0') {
        return false;
    }

    while (*cursor != '\0') {
        if (*cursor != 'A' && *cursor != 'T') {
            return false;
        }
        ++length;
        if (length > 8) {
            return false;
        }
        ++cursor;
    }

    return true;
}

static bool is_unsolicited_at_noise(const char *line) {
    const char *cursor = skip_shell_space(line);

    if (cursor[0] != 'A' || cursor[1] != 'T') {
        return false;
    }

    cursor += 2;
    if (*cursor == '\0') {
        return true;
    }

    while (*cursor != '\0') {
        if (!is_at_noise_tail_char(*cursor)) {
            return false;
        }
        ++cursor;
    }

    return true;
}

static void print_prompt(void) {
    char cwd[PATH_MAX];

    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        strcpy(cwd, "/");
    }

    cprintf("a90:%s# ", cwd);
}
