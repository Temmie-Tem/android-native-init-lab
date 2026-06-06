#define _GNU_SOURCE

#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <time.h>
#include <unistd.h>

#define WLANBOOTCTL_VERSION "a90_wlanbootctl v2"
#define BOOT_WLAN_PATH "/sys/kernel/boot_wlan/boot_wlan"
#define SHUTDOWN_WLAN_PATH "/sys/kernel/shutdown_wlan/shutdown"
#define QCWLANSTATE_PATH "/sys/wifi/qcwlanstate"
#define WLAN_CON_MODE_PATH "/sys/module/wlan/parameters/con_mode"
#define WLAN_FWPATH_PATH "/sys/module/wlan/parameters/fwpath"
#define PROC_DEVICES_PATH "/proc/devices"
#define PROC_NET_DEV_PATH "/proc/net/dev"
#define PROC_NET_WIRELESS_PATH "/proc/net/wireless"
#define SYS_CLASS_NET "/sys/class/net"
#define SYS_CLASS_IEEE80211 "/sys/class/ieee80211"
#define DEV_WLAN_PATH "/dev/wlan"
#define SYS_CLASS_WLAN_DEV "/sys/class/wlan/wlan/dev"

static int write_all(int fd, const char *buf, size_t len) {
    size_t off = 0;

    while (off < len) {
        ssize_t nwritten = write(fd, buf + off, len - off);

        if (nwritten < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (nwritten == 0) {
            errno = EIO;
            return -1;
        }
        off += (size_t)nwritten;
    }
    return 0;
}

static int read_file_limited(const char *path, char *buf, size_t size) {
    ssize_t nread;
    int fd;

    if (size == 0) {
        errno = EINVAL;
        return -1;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -1;
    }
    nread = read(fd, buf, size - 1);
    if (nread < 0) {
        int saved_errno = errno;
        close(fd);
        errno = saved_errno;
        return -1;
    }
    close(fd);
    buf[nread] = '\0';
    return (int)nread;
}

static void sanitize_inline(char *text) {
    for (size_t i = 0; text[i] != '\0'; i++) {
        unsigned char ch = (unsigned char)text[i];

        if (ch == '\n' || ch == '\r' || ch == '\t') {
            text[i] = ' ';
        } else if (ch < 0x20 || ch == 0x7f) {
            text[i] = '_';
        }
    }
}

static void print_file_value(const char *prefix, const char *label, const char *path) {
    char buf[512];
    int nread = read_file_limited(path, buf, sizeof(buf));

    if (nread < 0) {
        printf("%s.%s.exists=0\n", prefix, label);
        printf("%s.%s.errno=%d\n", prefix, label, errno);
        return;
    }
    sanitize_inline(buf);
    printf("%s.%s.exists=1\n", prefix, label);
    printf("%s.%s.bytes=%d\n", prefix, label, nread);
    printf("%s.%s.value=%s\n", prefix, label, buf);
}

static void print_path_status(const char *prefix, const char *label, const char *path) {
    struct stat st;

    if (lstat(path, &st) < 0) {
        printf("%s.%s.exists=0\n", prefix, label);
        printf("%s.%s.errno=%d\n", prefix, label, errno);
        return;
    }
    printf("%s.%s.exists=1\n", prefix, label);
    printf("%s.%s.mode=%03o\n", prefix, label, st.st_mode & 07777);
    printf("%s.%s.uid=%ld\n", prefix, label, (long)st.st_uid);
    printf("%s.%s.gid=%ld\n", prefix, label, (long)st.st_gid);
    if (S_ISCHR(st.st_mode) || S_ISBLK(st.st_mode)) {
        printf("%s.%s.major=%u\n", prefix, label, major(st.st_rdev));
        printf("%s.%s.minor=%u\n", prefix, label, minor(st.st_rdev));
    }
    if (S_ISDIR(st.st_mode)) {
        printf("%s.%s.type=directory\n", prefix, label);
    } else if (S_ISCHR(st.st_mode)) {
        printf("%s.%s.type=char\n", prefix, label);
    } else if (S_ISLNK(st.st_mode)) {
        printf("%s.%s.type=symlink\n", prefix, label);
    } else if (S_ISREG(st.st_mode)) {
        printf("%s.%s.type=regular\n", prefix, label);
    } else {
        printf("%s.%s.type=other\n", prefix, label);
    }
}

static bool wifi_name(const char *name) {
    return strncmp(name, "wlan", 4) == 0 ||
           strncmp(name, "swlan", 5) == 0 ||
           strncmp(name, "p2p", 3) == 0 ||
           strncmp(name, "wifi-aware", 10) == 0 ||
           strncmp(name, "phy", 3) == 0;
}

static int print_matching_dir(const char *prefix, const char *label, const char *path) {
    DIR *dir = opendir(path);
    struct dirent *entry;
    int count = 0;
    int printed = 0;

    if (dir == NULL) {
        printf("%s.%s.exists=0\n", prefix, label);
        printf("%s.%s.errno=%d\n", prefix, label, errno);
        printf("%s.%s.count=0\n", prefix, label);
        printf("%s.%s.names=\n", prefix, label);
        return -1;
    }
    printf("%s.%s.exists=1\n", prefix, label);
    printf("%s.%s.names=", prefix, label);
    while ((entry = readdir(dir)) != NULL) {
        if (entry->d_name[0] == '.') {
            continue;
        }
        if (!wifi_name(entry->d_name)) {
            continue;
        }
        if (printed > 0) {
            fputc(',', stdout);
        }
        fputs(entry->d_name, stdout);
        printed++;
        count++;
    }
    fputc('\n', stdout);
    printf("%s.%s.count=%d\n", prefix, label, count);
    closedir(dir);
    return count;
}

static bool file_contains_token(const char *path, const char *token) {
    char buf[16384];
    int nread = read_file_limited(path, buf, sizeof(buf));

    return nread >= 0 && strstr(buf, token) != NULL;
}

static void print_snapshot(const char *prefix) {
    printf("%s.begin=1\n", prefix);
    print_file_value(prefix, "qcwlanstate", QCWLANSTATE_PATH);
    print_file_value(prefix, "wlan_con_mode", WLAN_CON_MODE_PATH);
    print_file_value(prefix, "wlan_fwpath", WLAN_FWPATH_PATH);
    print_file_value(prefix, "sys_class_wlan_dev", SYS_CLASS_WLAN_DEV);
    print_path_status(prefix, "boot_wlan", BOOT_WLAN_PATH);
    print_path_status(prefix, "shutdown_wlan", SHUTDOWN_WLAN_PATH);
    print_path_status(prefix, "dev_wlan", DEV_WLAN_PATH);
    print_path_status(prefix, "sys_class_net_wlan0", "/sys/class/net/wlan0");
    print_path_status(prefix, "sys_class_net_swlan0", "/sys/class/net/swlan0");
    print_matching_dir(prefix, "sys_class_net_wifi", SYS_CLASS_NET);
    print_matching_dir(prefix, "sys_class_ieee80211", SYS_CLASS_IEEE80211);
    printf("%s.proc_devices.qcwlanstate_present=%d\n",
           prefix,
           file_contains_token(PROC_DEVICES_PATH, "qcwlanstate") ? 1 : 0);
    printf("%s.proc_net_dev.wlan_present=%d\n",
           prefix,
           file_contains_token(PROC_NET_DEV_PATH, "wlan") ? 1 : 0);
    printf("%s.proc_net_wireless.wlan_present=%d\n",
           prefix,
           file_contains_token(PROC_NET_WIRELESS_PATH, "wlan") ? 1 : 0);
    printf("%s.end=1\n", prefix);
}

static int write_fixed_one(const char *path, const char *label) {
    int fd = open(path, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);

    printf("%s.write_attempted=1\n", label);
    printf("%s.path=%s\n", label, path);
    if (fd < 0) {
        printf("%s.write_rc=1\n", label);
        printf("%s.write_errno=%d\n", label, errno);
        return 1;
    }
    if (write_all(fd, "1", 1) < 0) {
        int saved_errno = errno;
        close(fd);
        printf("%s.write_rc=1\n", label);
        printf("%s.write_errno=%d\n", label, saved_errno);
        return 1;
    }
    if (close(fd) < 0) {
        printf("%s.write_rc=1\n", label);
        printf("%s.write_errno=%d\n", label, errno);
        return 1;
    }
    printf("%s.write_rc=0\n", label);
    printf("%s.write_errno=0\n", label);
    return 0;
}

static int write_fixed_text(const char *path, const char *label, const char *text, size_t len) {
    int fd = open(path, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);

    printf("%s.write_attempted=1\n", label);
    printf("%s.path=%s\n", label, path);
    if (fd < 0) {
        printf("%s.write_rc=1\n", label);
        printf("%s.write_errno=%d\n", label, errno);
        return 1;
    }
    if (write_all(fd, text, len) < 0) {
        int saved_errno = errno;
        close(fd);
        printf("%s.write_rc=1\n", label);
        printf("%s.write_errno=%d\n", label, saved_errno);
        return 1;
    }
    if (close(fd) < 0) {
        printf("%s.write_rc=1\n", label);
        printf("%s.write_errno=%d\n", label, errno);
        return 1;
    }
    printf("%s.write_rc=0\n", label);
    printf("%s.write_errno=0\n", label);
    return 0;
}

static bool parse_wlan_dev(unsigned int *major_out, unsigned int *minor_out) {
    char buf[64];
    unsigned int parsed_major;
    unsigned int parsed_minor;

    if (read_file_limited(SYS_CLASS_WLAN_DEV, buf, sizeof(buf)) < 0) {
        return false;
    }
    if (sscanf(buf, "%u:%u", &parsed_major, &parsed_minor) != 2) {
        errno = EINVAL;
        return false;
    }
    *major_out = parsed_major;
    *minor_out = parsed_minor;
    return true;
}

static bool dev_wlan_matches(unsigned int expected_major, unsigned int expected_minor) {
    struct stat st;

    if (lstat(DEV_WLAN_PATH, &st) < 0) {
        return false;
    }
    return S_ISCHR(st.st_mode) &&
           major(st.st_rdev) == expected_major &&
           minor(st.st_rdev) == expected_minor;
}

static int ensure_dev_wlan_node(const char *label) {
    unsigned int wlan_major = 0;
    unsigned int wlan_minor = 0;
    struct stat st;
    dev_t dev;
    int rc = 0;

    printf("%s.begin=1\n", label);
    printf("%s.path=%s\n", label, DEV_WLAN_PATH);
    printf("%s.source=%s\n", label, SYS_CLASS_WLAN_DEV);
    if (!parse_wlan_dev(&wlan_major, &wlan_minor)) {
        printf("%s.source_rc=1\n", label);
        printf("%s.source_errno=%d\n", label, errno);
        printf("%s.created=0\n", label);
        printf("%s.end=1\n", label);
        return 1;
    }
    printf("%s.source_rc=0\n", label);
    printf("%s.source_major=%u\n", label, wlan_major);
    printf("%s.source_minor=%u\n", label, wlan_minor);
    dev = makedev(wlan_major, wlan_minor);

    if (lstat(DEV_WLAN_PATH, &st) == 0) {
        if (!S_ISCHR(st.st_mode) ||
            major(st.st_rdev) != wlan_major ||
            minor(st.st_rdev) != wlan_minor) {
            printf("%s.existing=1\n", label);
            printf("%s.existing_match=0\n", label);
            printf("%s.created=0\n", label);
            printf("%s.end=1\n", label);
            return 1;
        }
        printf("%s.existing=1\n", label);
        printf("%s.existing_match=1\n", label);
    } else if (errno == ENOENT) {
        printf("%s.existing=0\n", label);
        if (mknod(DEV_WLAN_PATH, S_IFCHR | 0660, dev) < 0) {
            printf("%s.mknod_rc=1\n", label);
            printf("%s.mknod_errno=%d\n", label, errno);
            printf("%s.created=0\n", label);
            printf("%s.end=1\n", label);
            return 1;
        }
        printf("%s.mknod_rc=0\n", label);
        printf("%s.mknod_errno=0\n", label);
        printf("%s.created=1\n", label);
    } else {
        printf("%s.existing_probe_rc=1\n", label);
        printf("%s.existing_probe_errno=%d\n", label, errno);
        printf("%s.created=0\n", label);
        printf("%s.end=1\n", label);
        return 1;
    }

    if (chown(DEV_WLAN_PATH, 1010, 1010) < 0) {
        printf("%s.chown_rc=1\n", label);
        printf("%s.chown_errno=%d\n", label, errno);
        rc = 1;
    } else {
        printf("%s.chown_rc=0\n", label);
        printf("%s.chown_errno=0\n", label);
    }
    if (chmod(DEV_WLAN_PATH, 0660) < 0) {
        printf("%s.chmod_rc=1\n", label);
        printf("%s.chmod_errno=%d\n", label, errno);
        rc = 1;
    } else {
        printf("%s.chmod_rc=0\n", label);
        printf("%s.chmod_errno=0\n", label);
    }
    printf("%s.match_after=%d\n", label, dev_wlan_matches(wlan_major, wlan_minor) ? 1 : 0);
    print_path_status(label, "after", DEV_WLAN_PATH);
    printf("%s.end=1\n", label);
    return rc;
}

static bool parse_seconds(const char *text, int *seconds_out) {
    char *end = NULL;
    long value;

    if (text == NULL || text[0] == '\0') {
        return false;
    }
    errno = 0;
    value = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value < 0 || value > 120) {
        return false;
    }
    *seconds_out = (int)value;
    return true;
}

static int observe_seconds(int seconds) {
    for (int i = 0; i <= seconds; i++) {
        char prefix[64];

        snprintf(prefix, sizeof(prefix), "wlanboot.observe.%03d", i);
        print_snapshot(prefix);
        fflush(stdout);
        if (i < seconds) {
            sleep(1);
        }
    }
    return 0;
}

static int boot_observe(int seconds) {
    int rc;

    printf("wlanboot.begin=1\n");
    printf("wlanboot.version=%s\n", WLANBOOTCTL_VERSION);
    printf("wlanboot.operation=boot-observe\n");
    printf("wlanboot.scan_connect_linkup=0\n");
    printf("wlanboot.credentials=0\n");
    printf("wlanboot.dhcp_routing=0\n");
    printf("wlanboot.external_ping=0\n");
    printf("wlanboot.shutdown_executed=0\n");
    print_snapshot("wlanboot.before");
    rc = write_fixed_one(BOOT_WLAN_PATH, "wlanboot.boot_wlan");
    observe_seconds(seconds);
    print_snapshot("wlanboot.after");
    printf("wlanboot.result=%s\n", rc == 0 ? "boot-write-executed" : "boot-write-failed");
    printf("wlanboot.end=1\n");
    return rc;
}

static int shutdown_observe(int seconds) {
    int rc;

    printf("wlanboot.begin=1\n");
    printf("wlanboot.version=%s\n", WLANBOOTCTL_VERSION);
    printf("wlanboot.operation=shutdown-observe\n");
    printf("wlanboot.scan_connect_linkup=0\n");
    printf("wlanboot.credentials=0\n");
    printf("wlanboot.dhcp_routing=0\n");
    printf("wlanboot.external_ping=0\n");
    print_snapshot("wlanboot.before");
    rc = write_fixed_one(SHUTDOWN_WLAN_PATH, "wlanboot.shutdown_wlan");
    observe_seconds(seconds);
    print_snapshot("wlanboot.after");
    printf("wlanboot.result=%s\n", rc == 0 ? "shutdown-write-executed" : "shutdown-write-failed");
    printf("wlanboot.end=1\n");
    return rc;
}

static int devnode_observe(int seconds) {
    int rc;

    printf("wlanboot.begin=1\n");
    printf("wlanboot.version=%s\n", WLANBOOTCTL_VERSION);
    printf("wlanboot.operation=devnode-observe\n");
    printf("wlanboot.scan_connect_linkup=0\n");
    printf("wlanboot.credentials=0\n");
    printf("wlanboot.dhcp_routing=0\n");
    printf("wlanboot.external_ping=0\n");
    printf("wlanboot.driver_state_on_executed=0\n");
    printf("wlanboot.shutdown_executed=0\n");
    print_snapshot("wlanboot.before");
    rc = ensure_dev_wlan_node("wlanboot.dev_wlan_node");
    observe_seconds(seconds);
    print_snapshot("wlanboot.after");
    printf("wlanboot.result=%s\n", rc == 0 ? "devnode-ready" : "devnode-failed");
    printf("wlanboot.end=1\n");
    return rc;
}

static int devnode_on_observe(int seconds) {
    int rc;
    int write_rc = 1;

    printf("wlanboot.begin=1\n");
    printf("wlanboot.version=%s\n", WLANBOOTCTL_VERSION);
    printf("wlanboot.operation=devnode-on-observe\n");
    printf("wlanboot.scan_connect_linkup=0\n");
    printf("wlanboot.credentials=0\n");
    printf("wlanboot.dhcp_routing=0\n");
    printf("wlanboot.external_ping=0\n");
    printf("wlanboot.driver_state_on_executed=1\n");
    printf("wlanboot.shutdown_executed=0\n");
    print_snapshot("wlanboot.before");
    rc = ensure_dev_wlan_node("wlanboot.dev_wlan_node");
    if (rc == 0) {
        write_rc = write_fixed_text(DEV_WLAN_PATH, "wlanboot.dev_wlan_on", "ON", 3);
    }
    observe_seconds(seconds);
    print_snapshot("wlanboot.after");
    if (rc != 0) {
        printf("wlanboot.result=devnode-failed\n");
    } else if (write_rc != 0) {
        printf("wlanboot.result=driver-state-on-write-failed\n");
    } else {
        printf("wlanboot.result=driver-state-on-written\n");
    }
    printf("wlanboot.end=1\n");
    return rc != 0 ? rc : write_rc;
}

static void usage(FILE *out) {
    fprintf(out, "%s\n", WLANBOOTCTL_VERSION);
    fprintf(out, "usage: a90_wlanbootctl status|observe <seconds>|boot-observe <seconds>|shutdown-observe <seconds>|devnode-observe <seconds>|devnode-on-observe <seconds>\n");
    fprintf(out, "fixed writes only: %s, %s, and %s\n", BOOT_WLAN_PATH, SHUTDOWN_WLAN_PATH, DEV_WLAN_PATH);
}

int main(int argc, char **argv) {
    int seconds = 0;

    if (argc == 2 && strcmp(argv[1], "status") == 0) {
        printf("wlanboot.version=%s\n", WLANBOOTCTL_VERSION);
        print_snapshot("wlanboot.status");
        return 0;
    }
    if (argc == 3 && strcmp(argv[1], "observe") == 0 && parse_seconds(argv[2], &seconds)) {
        printf("wlanboot.version=%s\n", WLANBOOTCTL_VERSION);
        return observe_seconds(seconds);
    }
    if (argc == 3 && strcmp(argv[1], "boot-observe") == 0 && parse_seconds(argv[2], &seconds)) {
        return boot_observe(seconds);
    }
    if (argc == 3 && strcmp(argv[1], "shutdown-observe") == 0 && parse_seconds(argv[2], &seconds)) {
        return shutdown_observe(seconds);
    }
    if (argc == 3 && strcmp(argv[1], "devnode-observe") == 0 && parse_seconds(argv[2], &seconds)) {
        return devnode_observe(seconds);
    }
    if (argc == 3 && strcmp(argv[1], "devnode-on-observe") == 0 && parse_seconds(argv[2], &seconds)) {
        return devnode_on_observe(seconds);
    }
    usage(argc == 1 ? stdout : stderr);
    return argc == 1 ? 0 : 2;
}
