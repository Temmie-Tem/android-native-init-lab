/* Included by stage3/linux_init/init_v85.c. Do not compile standalone. */

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

    a90_console_printf("a90:%s# ", cwd);
}
