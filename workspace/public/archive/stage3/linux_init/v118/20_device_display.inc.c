/* Included by stage3/linux_init/init_v118.c. Do not compile standalone. */

static int print_input_event_info(const char *event_name) {
    char name_path[PATH_MAX];
    char dev_path[PATH_MAX];
    char name_buf[256];
    char dev_info_path[PATH_MAX];
    char dev_info[64];

    if (snprintf(name_path, sizeof(name_path),
                 "/sys/class/input/%s/device/name", event_name) >= (int)sizeof(name_path) ||
        snprintf(dev_info_path, sizeof(dev_info_path),
                 "/sys/class/input/%s/dev", event_name) >= (int)sizeof(dev_info_path)) {
        a90_console_printf("inputinfo: %s: path too long\r\n", event_name);
        return -ENAMETOOLONG;
    }

    if (read_text_file(name_path, name_buf, sizeof(name_buf)) < 0) {
        a90_console_printf("inputinfo: %s: %s\r\n", event_name, strerror(errno));
        return negative_errno_or(ENOENT);
    }
    trim_newline(name_buf);

    if (read_text_file(dev_info_path, dev_info, sizeof(dev_info)) < 0) {
        a90_console_printf("inputinfo: %s dev: %s\r\n", event_name, strerror(errno));
        return negative_errno_or(ENOENT);
    }
    trim_newline(dev_info);

    if (get_input_event_path(event_name, dev_path, sizeof(dev_path)) < 0) {
        a90_console_printf("%s  name=%s  dev=%s  node=<error:%s>\r\n",
                event_name, name_buf, dev_info, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("%s  name=%s  dev=%s  node=%s\r\n",
            event_name, name_buf, dev_info, dev_path);
    return 0;
}

static int cmd_inputinfo(char **argv, int argc) {
    if (argc >= 2) {
        char event_name[32];

        if (normalize_event_name(argv[1], event_name, sizeof(event_name)) < 0) {
            a90_console_printf("inputinfo: invalid event name\r\n");
            return -EINVAL;
        }
        return print_input_event_info(event_name);
    }

    {
        DIR *dir = opendir("/sys/class/input");
        struct dirent *entry;
        int first_error = 0;
        bool printed = false;

        if (dir == NULL) {
            a90_console_printf("inputinfo: %s\r\n", strerror(errno));
            return negative_errno_or(ENOENT);
        }

        while ((entry = readdir(dir)) != NULL) {
            if (strncmp(entry->d_name, "event", 5) == 0) {
                int result = print_input_event_info(entry->d_name);
                if (result == 0) {
                    printed = true;
                } else if (first_error == 0) {
                    first_error = result;
                }
            }
        }

        closedir(dir);
        return printed ? 0 : first_error;
    }
}

static void print_drm_entry_info(const char *entry_name) {
    char base_path[PATH_MAX];
    char path[PATH_MAX];
    char value[1024];
    char node_path[PATH_MAX];
    bool printed_header = false;

    if (snprintf(base_path, sizeof(base_path),
                 "/sys/class/drm/%s", entry_name) >= (int)sizeof(base_path)) {
        a90_console_printf("drminfo: %s: path too long\r\n", entry_name);
        return;
    }

    if (snprintf(path, sizeof(path), "%s/dev", base_path) >= (int)sizeof(path)) {
        a90_console_printf("drminfo: %s: path too long\r\n", entry_name);
        return;
    }

    if (read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        a90_console_printf("%s  dev=%s", entry_name, value);
        printed_header = true;

        if (((strncmp(entry_name, "card", 4) == 0) && strchr(entry_name, '-') == NULL) ||
            strncmp(entry_name, "renderD", 7) == 0 ||
            strncmp(entry_name, "controlD", 8) == 0) {
            if (get_char_device_path(path, "/dev/dri", entry_name,
                                     node_path, sizeof(node_path)) == 0) {
                a90_console_printf("  node=%s", node_path);
            } else {
                a90_console_printf("  node=<error:%s>", strerror(errno));
            }
        }
        a90_console_printf("\r\n");
    }

    if (snprintf(path, sizeof(path), "%s/status", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        a90_console_printf("  status=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/enabled", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        a90_console_printf("  enabled=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/dpms", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        a90_console_printf("  dpms=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/modes", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        flatten_inline_text(value);
        a90_console_printf("  modes=%s\r\n", value);
    }

    if (!printed_header) {
        a90_console_printf("%s\r\n", entry_name);
    }
}

static int cmd_drminfo(char **argv, int argc) {
    if (argc >= 2) {
        print_drm_entry_info(argv[1]);
        return 0;
    }

    {
        DIR *dir = opendir("/sys/class/drm");
        struct dirent *entry;

        if (dir == NULL) {
            a90_console_printf("drminfo: %s\r\n", strerror(errno));
            return negative_errno_or(ENOENT);
        }

        while ((entry = readdir(dir)) != NULL) {
            if (entry->d_name[0] == '.') {
                continue;
            }
            print_drm_entry_info(entry->d_name);
        }

        closedir(dir);
        return 0;
    }
}

static void print_fb_entry_info(const char *entry_name) {
    char base_path[PATH_MAX];
    char path[PATH_MAX];
    char value[1024];
    char node_path[PATH_MAX];
    bool printed_header = false;

    if (snprintf(base_path, sizeof(base_path),
                 "/sys/class/graphics/%s", entry_name) >= (int)sizeof(base_path)) {
        a90_console_printf("fbinfo: %s: path too long\r\n", entry_name);
        return;
    }

    if (snprintf(path, sizeof(path), "%s/dev", base_path) >= (int)sizeof(path)) {
        a90_console_printf("fbinfo: %s: path too long\r\n", entry_name);
        return;
    }

    if (read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        a90_console_printf("%s  dev=%s", entry_name, value);
        printed_header = true;

        if (get_char_device_path(path, "/dev/graphics", entry_name,
                                 node_path, sizeof(node_path)) == 0) {
            a90_console_printf("  node=%s", node_path);
        } else {
            a90_console_printf("  node=<error:%s>", strerror(errno));
        }
        a90_console_printf("\r\n");
    }

    if (snprintf(path, sizeof(path), "%s/name", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        a90_console_printf("  name=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/bits_per_pixel", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        a90_console_printf("  bits_per_pixel=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/virtual_size", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        a90_console_printf("  virtual_size=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/modes", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        flatten_inline_text(value);
        a90_console_printf("  modes=%s\r\n", value);
    }

    if (snprintf(path, sizeof(path), "%s/blank", base_path) < (int)sizeof(path) &&
        read_trimmed_text_file(path, value, sizeof(value)) == 0) {
        if (!printed_header) {
            a90_console_printf("%s\r\n", entry_name);
            printed_header = true;
        }
        a90_console_printf("  blank=%s\r\n", value);
    }

    if (!printed_header) {
        a90_console_printf("%s\r\n", entry_name);
    }
}

static int cmd_fbinfo(char **argv, int argc) {
    if (argc >= 2) {
        print_fb_entry_info(argv[1]);
        return 0;
    }

    {
        DIR *dir = opendir("/sys/class/graphics");
        struct dirent *entry;

        if (dir == NULL) {
            a90_console_printf("fbinfo: %s\r\n", strerror(errno));
            return negative_errno_or(ENOENT);
        }

        while ((entry = readdir(dir)) != NULL) {
            if (strncmp(entry->d_name, "fb", 2) == 0) {
                print_fb_entry_info(entry->d_name);
            }
        }

        closedir(dir);
        return 0;
    }
}
