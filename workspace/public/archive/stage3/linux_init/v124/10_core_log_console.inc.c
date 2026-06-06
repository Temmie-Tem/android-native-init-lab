/* Included by stage3/linux_init/init_v124.c. Do not compile standalone. */

static void wf(const char *path, const char *value) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        return;
    }
    write_all(fd, value, strlen(value));
    close(fd);
}

static void klogf(const char *fmt, ...) {
    char buf[512];
    va_list ap;
    int fd;
    int len;

    va_start(ap, fmt);
    len = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);

    if (len <= 0) {
        return;
    }
    if ((size_t)len >= sizeof(buf)) {
        len = (int)sizeof(buf) - 1;
    }

    fd = open("/dev/kmsg", O_WRONLY);
    if (fd < 0) {
        return;
    }
    write_all(fd, buf, (size_t)len);
    close(fd);
}

static void boot_splash_set_line(size_t index, const char *fmt, ...) {
    va_list ap;
    char line[BOOT_SPLASH_LINE_MAX];

    if (index >= BOOT_SPLASH_LINE_COUNT) {
        return;
    }
    va_start(ap, fmt);
    vsnprintf(line, sizeof(line), fmt, ap);
    va_end(ap);
    a90_hud_boot_splash_set_line(index, "%s", line);
}

static void mark_step(const char *value) {
    wf("/cache/v5_step", value);
    sync();
}

static int parse_dev_numbers(const char *dev_info,
                             unsigned int *major_num,
                             unsigned int *minor_num) {
    if (sscanf(dev_info, "%u:%u", major_num, minor_num) != 2) {
        errno = EINVAL;
        return -1;
    }
    return 0;
}

static int ensure_char_node(const char *path, unsigned int major_num, unsigned int minor_num) {
    if (mknod(path, S_IFCHR | 0600, makedev(major_num, minor_num)) < 0 && errno != EEXIST) {
        return -1;
    }
    return 0;
}

static int get_char_device_path(const char *sysfs_dev_path,
                                const char *dev_dir,
                                const char *node_name,
                                char *out,
                                size_t out_size) {
    char dev_info[64];
    unsigned int major_num;
    unsigned int minor_num;

    if (read_trimmed_text_file(sysfs_dev_path, dev_info, sizeof(dev_info)) < 0) {
        return -1;
    }

    if (parse_dev_numbers(dev_info, &major_num, &minor_num) < 0) {
        return -1;
    }

    if (ensure_dir(dev_dir, 0755) < 0) {
        return -1;
    }

    if (snprintf(out, out_size, "%s/%s", dev_dir, node_name) >= (int)out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }

    if (ensure_char_node(out, major_num, minor_num) < 0) {
        return -1;
    }

    return 0;
}

static int get_block_device_path(const char *block_name, char *out, size_t out_size) {
    char dev_info_path[PATH_MAX];
    char dev_info[64];
    unsigned int major_num;
    unsigned int minor_num;

    if (snprintf(dev_info_path, sizeof(dev_info_path),
                 "/sys/class/block/%s/dev", block_name) >= (int)sizeof(dev_info_path)) {
        errno = ENAMETOOLONG;
        return -1;
    }

    if (read_trimmed_text_file(dev_info_path, dev_info, sizeof(dev_info)) < 0) {
        return -1;
    }

    if (parse_dev_numbers(dev_info, &major_num, &minor_num) < 0) {
        return -1;
    }

    if (ensure_dir("/dev/block", 0755) < 0) {
        return -1;
    }

    if (snprintf(out, out_size, "/dev/block/%s", block_name) >= (int)out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }

    if (ensure_block_node(out, major_num, minor_num) < 0) {
        return -1;
    }

    return 0;
}

static int normalize_event_name(const char *arg, char *out, size_t out_size) {
    if (strncmp(arg, "event", 5) == 0) {
        if (snprintf(out, out_size, "%s", arg) >= (int)out_size) {
            errno = ENAMETOOLONG;
            return -1;
        }
        return 0;
    }

    if (snprintf(out, out_size, "event%s", arg) >= (int)out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    return 0;
}

static int get_input_event_path(const char *event_name, char *out, size_t out_size) {
    char dev_info_path[PATH_MAX];

    if (snprintf(dev_info_path, sizeof(dev_info_path),
                 "/sys/class/input/%s/dev", event_name) >= (int)sizeof(dev_info_path)) {
        errno = ENAMETOOLONG;
        return -1;
    }

    return get_char_device_path(dev_info_path, "/dev/input", event_name, out, out_size);
}

static void prepare_input_nodes(void) {
    DIR *dir = opendir("/sys/class/input");
    struct dirent *entry;
    char path[PATH_MAX];

    if (dir == NULL) {
        return;
    }

    while ((entry = readdir(dir)) != NULL) {
        if (strncmp(entry->d_name, "event", 5) != 0) {
            continue;
        }
        get_input_event_path(entry->d_name, path, sizeof(path));
    }

    closedir(dir);
}

static void prepare_drm_nodes(void) {
    DIR *dir = opendir("/sys/class/drm");
    struct dirent *entry;
    char dev_info_path[PATH_MAX];
    char out[PATH_MAX];

    if (dir == NULL) {
        return;
    }

    while ((entry = readdir(dir)) != NULL) {
        const char *name = entry->d_name;

        if (name[0] == '.') {
            continue;
        }

        if (!(((strncmp(name, "card", 4) == 0) && strchr(name, '-') == NULL) ||
              strncmp(name, "renderD", 7) == 0 ||
              strncmp(name, "controlD", 8) == 0)) {
            continue;
        }

        if (snprintf(dev_info_path, sizeof(dev_info_path),
                     "/sys/class/drm/%s/dev", name) >= (int)sizeof(dev_info_path)) {
            continue;
        }

        get_char_device_path(dev_info_path, "/dev/dri", name, out, sizeof(out));
    }

    closedir(dir);
}

static void prepare_graphics_nodes(void) {
    DIR *dir = opendir("/sys/class/graphics");
    struct dirent *entry;
    char dev_info_path[PATH_MAX];
    char out[PATH_MAX];

    if (dir == NULL) {
        return;
    }

    while ((entry = readdir(dir)) != NULL) {
        if (strncmp(entry->d_name, "fb", 2) != 0) {
            continue;
        }

        if (snprintf(dev_info_path, sizeof(dev_info_path),
                     "/sys/class/graphics/%s/dev", entry->d_name) >= (int)sizeof(dev_info_path)) {
            continue;
        }

        get_char_device_path(dev_info_path, "/dev/graphics", entry->d_name, out, sizeof(out));
    }

    closedir(dir);
}

static void prepare_early_display_environment(void) {
    wf("/sys/class/backlight/panel0-backlight/brightness", "200");
    prepare_drm_nodes();
    prepare_graphics_nodes();
    prepare_input_nodes();
}
