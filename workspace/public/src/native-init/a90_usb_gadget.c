#include "a90_usb_gadget.h"

#include "a90_config.h"
#include "a90_console.h"
#include "a90_log.h"
#include "a90_util.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define A90_USB_GADGET_ROOT "/config/usb_gadget/g1"
#define A90_USB_GADGET_CONFIG A90_USB_GADGET_ROOT "/configs/b.1"
#define A90_USB_GADGET_ACM_FUNCTION A90_USB_GADGET_ROOT "/functions/acm.usb0"
#define A90_USB_GADGET_NCM_FUNCTION A90_USB_GADGET_ROOT "/functions/ncm.usb0"
#define A90_USB_GADGET_MASS_STORAGE_FUNCTION A90_USB_GADGET_ROOT "/functions/mass_storage.0"
#define A90_USB_GADGET_ACM_LINK A90_USB_GADGET_CONFIG "/f1"
#define A90_USB_GADGET_NCM_LINK A90_USB_GADGET_CONFIG "/f2"
#define A90_USB_GADGET_MASS_STORAGE_LINK A90_USB_GADGET_CONFIG "/f3"
#define A90_USB_GADGET_ADB_LINK A90_USB_GADGET_CONFIG "/f2"
#define A90_USB_GADGET_UDC_PATH A90_USB_GADGET_ROOT "/UDC"
#define A90_USB_GADGET_DEFAULT_UDC "a600000.dwc3"
#define A90_USB_STATUS_VERSION "a90-native-usb-status-v1"
#define A90_USB_RECONFIG_LOG_PATH "/cache/a90-usb-reconfigure.log"
#define A90_USB_RECONFIG_WATCHDOG_SEC 8
#define A90_USB_RECONFIG_DETACH_DELAY_USEC 1000000
#define A90_USB_RECONFIG_SETTLE_USEC 350000
#define A90_USB_MASS_STORAGE_INTERNAL_BACKING_PATH "/cache/a90-usb-mass-storage-v2323-internal.img"
#define A90_USB_MASS_STORAGE_SD_BACKING_PATH "/cache/a90-usb-mass-storage-v2323-sd.img"
#define A90_USB_MASS_STORAGE_BACKING_BYTES (8LL * 1024LL * 1024LL)
#define A90_USB_MASS_STORAGE_INTERNAL_INQUIRY_STRING "A90-LNX A90-INTERNAL    0001"
#define A90_USB_MASS_STORAGE_INTERNAL_INQUIRY_VENDOR "A90-LNX"
#define A90_USB_MASS_STORAGE_INTERNAL_INQUIRY_PRODUCT "A90-INTERNAL"
#define A90_USB_MASS_STORAGE_INTERNAL_INQUIRY_REVISION "0001"
#define A90_USB_MASS_STORAGE_INTERNAL_VOLUME_LABEL "A90INTERNAL"
#define A90_USB_MASS_STORAGE_SD_INQUIRY_STRING "A90-LNX A90-SD          0001"
#define A90_USB_MASS_STORAGE_SD_INQUIRY_VENDOR "A90-LNX"
#define A90_USB_MASS_STORAGE_SD_INQUIRY_PRODUCT "A90-SD"
#define A90_USB_MASS_STORAGE_SD_INQUIRY_REVISION "0001"
#define A90_USB_MASS_STORAGE_SD_VOLUME_LABEL "A90SD"
#define A90_USB_MASS_STORAGE_MAX_LUNS 2
#define A90_USB_FAT_BYTES_PER_SECTOR 512
#define A90_USB_FAT_TOTAL_SECTORS ((unsigned int)(A90_USB_MASS_STORAGE_BACKING_BYTES / A90_USB_FAT_BYTES_PER_SECTOR))
#define A90_USB_FAT_RESERVED_SECTORS 1
#define A90_USB_FAT_COUNT 2
#define A90_USB_FAT_ROOT_ENTRIES 512
#define A90_USB_FAT_ROOT_DIR_SECTORS 32
#define A90_USB_FAT_SECTORS_PER_FAT 64
#define A90_USB_FAT_SECTORS_PER_CLUSTER 1
#define A90_USB_FAT_ROOT_DIR_SECTOR \
    (A90_USB_FAT_RESERVED_SECTORS + (A90_USB_FAT_COUNT * A90_USB_FAT_SECTORS_PER_FAT))
#define A90_USB_MAX_FUNCTIONS 32
#define A90_USB_MAX_CONFIGS 8
#define A90_USB_MAX_CONFIG_LINKS 32
#define A90_USB_MAX_UDCS 8

struct usb_function_info {
    char name[64];
    char control_role[32];
    char links[128];
    bool linked;
    bool control;
};

struct usb_config_link_info {
    char name[64];
    char function[64];
    char control_role[32];
    bool control;
};

struct usb_config_info {
    char name[64];
    char configuration[128];
    char max_power[32];
    int link_count;
    struct usb_config_link_info links[A90_USB_MAX_CONFIG_LINKS];
};

struct usb_udc_info {
    char name[64];
    char state[64];
    char current_speed[64];
    char maximum_speed[64];
};

struct usb_inventory {
    struct a90_usb_gadget_status base;
    char id_vendor[32];
    char id_product[32];
    char bcd_usb[32];
    char bcd_device[32];
    char manufacturer[128];
    char product[128];
    bool serial_present;
    size_t serial_len;
    int function_count;
    int config_count;
    int udc_count;
    bool acm_control_present;
    bool ncm_control_present;
    struct usb_function_info functions[A90_USB_MAX_FUNCTIONS];
    struct usb_config_info configs[A90_USB_MAX_CONFIGS];
    struct usb_udc_info udcs[A90_USB_MAX_UDCS];
};

struct usb_mass_storage_lun_identity {
    int lun;
    const char *backing_path;
    const char *inquiry_string;
    const char *vendor;
    const char *product;
    const char *revision;
    const char *volume_label;
};

static const struct usb_mass_storage_lun_identity A90_USB_MASS_STORAGE_LUNS[A90_USB_MASS_STORAGE_MAX_LUNS] = {
    {
        0,
        A90_USB_MASS_STORAGE_INTERNAL_BACKING_PATH,
        A90_USB_MASS_STORAGE_INTERNAL_INQUIRY_STRING,
        A90_USB_MASS_STORAGE_INTERNAL_INQUIRY_VENDOR,
        A90_USB_MASS_STORAGE_INTERNAL_INQUIRY_PRODUCT,
        A90_USB_MASS_STORAGE_INTERNAL_INQUIRY_REVISION,
        A90_USB_MASS_STORAGE_INTERNAL_VOLUME_LABEL,
    },
    {
        1,
        A90_USB_MASS_STORAGE_SD_BACKING_PATH,
        A90_USB_MASS_STORAGE_SD_INQUIRY_STRING,
        A90_USB_MASS_STORAGE_SD_INQUIRY_VENDOR,
        A90_USB_MASS_STORAGE_SD_INQUIRY_PRODUCT,
        A90_USB_MASS_STORAGE_SD_INQUIRY_REVISION,
        A90_USB_MASS_STORAGE_SD_VOLUME_LABEL,
    },
};

static int write_file(const char *path, const char *value) {
    int fd = open(path, O_WRONLY | O_CLOEXEC);
    int saved_errno;

    if (fd < 0) {
        return -1;
    }
    if (write_all_checked(fd, value, strlen(value)) < 0) {
        saved_errno = errno;
        close(fd);
        errno = saved_errno;
        return -1;
    }
    if (close(fd) < 0) {
        return -1;
    }
    return 0;
}

static void usb_put_le16(unsigned char *buffer, size_t offset, unsigned int value) {
    buffer[offset] = (unsigned char)(value & 0xffU);
    buffer[offset + 1] = (unsigned char)((value >> 8) & 0xffU);
}

static void usb_put_le32(unsigned char *buffer, size_t offset, unsigned int value) {
    buffer[offset] = (unsigned char)(value & 0xffU);
    buffer[offset + 1] = (unsigned char)((value >> 8) & 0xffU);
    buffer[offset + 2] = (unsigned char)((value >> 16) & 0xffU);
    buffer[offset + 3] = (unsigned char)((value >> 24) & 0xffU);
}

static int usb_write_block_at(int fd, off_t offset, const unsigned char *buffer, size_t length) {
    if (lseek(fd, offset, SEEK_SET) < 0) {
        return -1;
    }
    return write_all_checked(fd, (const char *)buffer, length);
}

static void usb_log_line(const char *line) {
    int fd;

    if (line == NULL) {
        return;
    }
    fd = open(A90_USB_RECONFIG_LOG_PATH, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0600);
    if (fd < 0) {
        return;
    }
    (void)write_all_checked(fd, line, strlen(line));
    (void)write_all_checked(fd, "\n", 1);
    close(fd);
}

static int create_symlink_checked(const char *target, const char *linkpath) {
    if (symlink(target, linkpath) == 0 || errno == EEXIST) {
        return 0;
    }
    return -1;
}

static int usb_create_or_replace_symlink(const char *target, const char *linkpath) {
    char current[256];
    ssize_t current_len;

    current_len = readlink(linkpath, current, sizeof(current) - 1);
    if (current_len >= 0) {
        current[current_len] = '\0';
        if (strcmp(current, target) == 0) {
            return 0;
        }
        if (unlink(linkpath) < 0) {
            return -1;
        }
    } else if (errno != ENOENT) {
        return -1;
    }

    return symlink(target, linkpath);
}

static bool path_exists(const char *path) {
    struct stat st;

    return lstat(path, &st) == 0;
}

static bool path_is_dir(const char *path) {
    struct stat st;

    return lstat(path, &st) == 0 && S_ISDIR(st.st_mode);
}

static bool path_is_symlink(const char *path) {
    struct stat st;

    return lstat(path, &st) == 0 && S_ISLNK(st.st_mode);
}

static int ensure_configfs(void) {
    if (mount("configfs", "/config", "configfs", 0, NULL) == 0 || errno == EBUSY) {
        return 0;
    }
    return -1;
}

static const char *yesno(bool value) {
    return value ? "yes" : "no";
}

static const char *dash_if_empty(const char *value) {
    return value != NULL && value[0] != '\0' ? value : "-";
}

static bool usb_char_equal_ci(char left, char right) {
    if (left >= 'A' && left <= 'Z') {
        left = (char)(left - 'A' + 'a');
    }
    if (right >= 'A' && right <= 'Z') {
        right = (char)(right - 'A' + 'a');
    }
    return left == right;
}

static bool usb_name_contains_ci(const char *name, const char *needle) {
    size_t name_len;
    size_t needle_len;
    size_t offset;

    if (name == NULL || needle == NULL) {
        return false;
    }
    name_len = strlen(name);
    needle_len = strlen(needle);
    if (needle_len == 0 || needle_len > name_len) {
        return false;
    }
    for (offset = 0; offset + needle_len <= name_len; ++offset) {
        size_t index;
        bool matched = true;

        for (index = 0; index < needle_len; ++index) {
            if (!usb_char_equal_ci(name[offset + index], needle[index])) {
                matched = false;
                break;
            }
        }
        if (matched) {
            return true;
        }
    }
    return false;
}

static void usb_control_role_for_function(const char *function, char *out, size_t out_size) {
    const char *role = "aux";

    if (function != NULL) {
        if (usb_name_contains_ci(function, "acm")) {
            role = "control-acm";
        } else if (usb_name_contains_ci(function, "ncm")) {
            role = "control-ncm";
        }
    }
    if (out != NULL && out_size > 0) {
        snprintf(out, out_size, "%s", role);
    }
}

static bool usb_role_is_control(const char *role) {
    return role != NULL && strcmp(role, "aux") != 0;
}

static bool usb_role_is_acm(const char *role) {
    return role != NULL && strcmp(role, "control-acm") == 0;
}

static bool usb_role_is_ncm(const char *role) {
    return role != NULL && strcmp(role, "control-ncm") == 0;
}

static void usb_join_path(char *out, size_t out_size, const char *base, const char *leaf) {
    if (out == NULL || out_size == 0) {
        return;
    }
    snprintf(out, out_size, "%s/%s", base != NULL ? base : "", leaf != NULL ? leaf : "");
}

static void usb_read_value(const char *path, char *out, size_t out_size) {
    if (out == NULL || out_size == 0) {
        return;
    }
    out[0] = '\0';
    if (path == NULL || read_trimmed_text_file(path, out, out_size) < 0) {
        snprintf(out, out_size, "-");
    }
}

static void usb_read_gadget_value(const char *leaf, char *out, size_t out_size) {
    char path[256];

    usb_join_path(path, sizeof(path), A90_USB_GADGET_ROOT, leaf);
    usb_read_value(path, out, out_size);
}

static bool usb_link_points_to(const char *linkpath, const char *target_basename) {
    char target[256];
    const char *basename;
    ssize_t target_len;

    if (linkpath == NULL || target_basename == NULL) {
        return false;
    }
    target_len = readlink(linkpath, target, sizeof(target) - 1);
    if (target_len < 0) {
        return false;
    }
    target[target_len] = '\0';
    basename = strrchr(target, '/');
    if (basename != NULL) {
        ++basename;
    } else {
        basename = target;
    }
    return strcmp(basename, target_basename) == 0;
}

static void usb_copy_basename(const char *path, char *out, size_t out_size) {
    const char *base;

    if (out == NULL || out_size == 0) {
        return;
    }
    out[0] = '\0';
    if (path == NULL || path[0] == '\0') {
        snprintf(out, out_size, "-");
        return;
    }
    base = strrchr(path, '/');
    if (base != NULL) {
        ++base;
    } else {
        base = path;
    }
    snprintf(out, out_size, "%s", base);
}

static struct usb_function_info *usb_find_function(struct usb_inventory *inventory,
                                                   const char *name) {
    int index;

    if (inventory == NULL || name == NULL) {
        return NULL;
    }
    for (index = 0; index < inventory->function_count && index < A90_USB_MAX_FUNCTIONS; ++index) {
        if (strcmp(inventory->functions[index].name, name) == 0) {
            return &inventory->functions[index];
        }
    }
    return NULL;
}

static void usb_mark_control_presence(struct usb_inventory *inventory, const char *role) {
    if (inventory == NULL || role == NULL) {
        return;
    }
    if (usb_role_is_acm(role)) {
        inventory->acm_control_present = true;
    }
    if (usb_role_is_ncm(role)) {
        inventory->ncm_control_present = true;
    }
}

static void usb_collect_functions(struct usb_inventory *inventory) {
    DIR *dir;
    struct dirent *entry;

    if (inventory == NULL) {
        return;
    }
    dir = opendir(A90_USB_GADGET_ROOT "/functions");
    if (dir == NULL) {
        return;
    }
    while ((entry = readdir(dir)) != NULL) {
        char path[256];
        struct usb_function_info *function;

        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        usb_join_path(path, sizeof(path), A90_USB_GADGET_ROOT "/functions", entry->d_name);
        if (!path_is_dir(path)) {
            continue;
        }
        if (inventory->function_count >= A90_USB_MAX_FUNCTIONS) {
            ++inventory->function_count;
            continue;
        }
        function = &inventory->functions[inventory->function_count++];
        snprintf(function->name, sizeof(function->name), "%s", entry->d_name);
        usb_control_role_for_function(function->name,
                                      function->control_role,
                                      sizeof(function->control_role));
        function->control = usb_role_is_control(function->control_role);
    }
    closedir(dir);
}

static void usb_append_function_link(struct usb_function_info *function, const char *link_name) {
    size_t used;

    if (function == NULL || link_name == NULL || link_name[0] == '\0') {
        return;
    }
    function->linked = true;
    used = strlen(function->links);
    snprintf(function->links + used,
             sizeof(function->links) > used ? sizeof(function->links) - used : 0,
             "%s%s",
             used > 0 ? "," : "",
             link_name);
}

static void usb_collect_config_links(struct usb_inventory *inventory,
                                     struct usb_config_info *config,
                                     const char *config_path) {
    DIR *dir;
    struct dirent *entry;

    if (inventory == NULL || config == NULL || config_path == NULL) {
        return;
    }
    dir = opendir(config_path);
    if (dir == NULL) {
        return;
    }
    while ((entry = readdir(dir)) != NULL) {
        char link_path[256];
        char target[256];
        ssize_t target_len;
        struct usb_config_link_info *link;
        struct usb_function_info *function;

        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0 ||
            strcmp(entry->d_name, "strings") == 0) {
            continue;
        }
        usb_join_path(link_path, sizeof(link_path), config_path, entry->d_name);
        if (!path_is_symlink(link_path)) {
            continue;
        }
        if (config->link_count >= A90_USB_MAX_CONFIG_LINKS) {
            ++config->link_count;
            continue;
        }
        link = &config->links[config->link_count++];
        snprintf(link->name, sizeof(link->name), "%s", entry->d_name);
        target_len = readlink(link_path, target, sizeof(target) - 1);
        if (target_len < 0) {
            snprintf(link->function, sizeof(link->function), "unreadable");
        } else {
            target[target_len] = '\0';
            usb_copy_basename(target, link->function, sizeof(link->function));
        }
        usb_control_role_for_function(link->function,
                                      link->control_role,
                                      sizeof(link->control_role));
        link->control = usb_role_is_control(link->control_role);
        usb_mark_control_presence(inventory, link->control_role);
        function = usb_find_function(inventory, link->function);
        if (function != NULL) {
            usb_append_function_link(function, link->name);
        }
    }
    closedir(dir);
}

static void usb_collect_configs(struct usb_inventory *inventory) {
    DIR *dir;
    struct dirent *entry;

    if (inventory == NULL) {
        return;
    }
    dir = opendir(A90_USB_GADGET_ROOT "/configs");
    if (dir == NULL) {
        return;
    }
    while ((entry = readdir(dir)) != NULL) {
        char config_path[256];
        char value_path[256];
        struct usb_config_info *config;

        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0 ||
            strcmp(entry->d_name, "strings") == 0) {
            continue;
        }
        usb_join_path(config_path, sizeof(config_path), A90_USB_GADGET_ROOT "/configs", entry->d_name);
        if (!path_is_dir(config_path)) {
            continue;
        }
        if (inventory->config_count >= A90_USB_MAX_CONFIGS) {
            ++inventory->config_count;
            continue;
        }
        config = &inventory->configs[inventory->config_count++];
        snprintf(config->name, sizeof(config->name), "%s", entry->d_name);
        usb_join_path(value_path, sizeof(value_path), config_path, "strings/0x409/configuration");
        usb_read_value(value_path, config->configuration, sizeof(config->configuration));
        usb_join_path(value_path, sizeof(value_path), config_path, "MaxPower");
        usb_read_value(value_path, config->max_power, sizeof(config->max_power));
        usb_collect_config_links(inventory, config, config_path);
    }
    closedir(dir);
}

static void usb_collect_udcs(struct usb_inventory *inventory) {
    DIR *dir;
    struct dirent *entry;

    if (inventory == NULL) {
        return;
    }
    dir = opendir("/sys/class/udc");
    if (dir == NULL) {
        return;
    }
    while ((entry = readdir(dir)) != NULL) {
        char udc_path[256];
        char value_path[256];
        struct usb_udc_info *udc;

        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        usb_join_path(udc_path, sizeof(udc_path), "/sys/class/udc", entry->d_name);
        if (inventory->udc_count >= A90_USB_MAX_UDCS) {
            ++inventory->udc_count;
            continue;
        }
        udc = &inventory->udcs[inventory->udc_count++];
        snprintf(udc->name, sizeof(udc->name), "%s", entry->d_name);
        usb_join_path(value_path, sizeof(value_path), udc_path, "state");
        usb_read_value(value_path, udc->state, sizeof(udc->state));
        usb_join_path(value_path, sizeof(value_path), udc_path, "current_speed");
        usb_read_value(value_path, udc->current_speed, sizeof(udc->current_speed));
        usb_join_path(value_path, sizeof(value_path), udc_path, "maximum_speed");
        usb_read_value(value_path, udc->maximum_speed, sizeof(udc->maximum_speed));
    }
    closedir(dir);
}

static void usb_collect_strings(struct usb_inventory *inventory) {
    char path[256];
    char serial[128];

    if (inventory == NULL) {
        return;
    }
    usb_read_gadget_value("idVendor", inventory->id_vendor, sizeof(inventory->id_vendor));
    usb_read_gadget_value("idProduct", inventory->id_product, sizeof(inventory->id_product));
    usb_read_gadget_value("bcdUSB", inventory->bcd_usb, sizeof(inventory->bcd_usb));
    usb_read_gadget_value("bcdDevice", inventory->bcd_device, sizeof(inventory->bcd_device));
    usb_read_gadget_value("strings/0x409/manufacturer",
                          inventory->manufacturer,
                          sizeof(inventory->manufacturer));
    usb_read_gadget_value("strings/0x409/product", inventory->product, sizeof(inventory->product));
    usb_join_path(path, sizeof(path), A90_USB_GADGET_ROOT, "strings/0x409/serialnumber");
    if (read_trimmed_text_file(path, serial, sizeof(serial)) == 0) {
        inventory->serial_present = serial[0] != '\0';
        inventory->serial_len = strlen(serial);
    }
}

static int usb_collect_inventory(struct usb_inventory *inventory) {
    if (inventory == NULL) {
        return -EINVAL;
    }
    memset(inventory, 0, sizeof(*inventory));
    (void)a90_usb_gadget_status(&inventory->base);
    usb_collect_strings(inventory);
    usb_collect_functions(inventory);
    usb_collect_configs(inventory);
    usb_collect_udcs(inventory);
    return 0;
}

static void usb_print_inventory(const struct usb_inventory *inventory) {
    int config_index;
    int function_index;
    int udc_index;
    bool control_ok;

    if (inventory == NULL) {
        return;
    }
    control_ok = inventory->acm_control_present && inventory->ncm_control_present;
    a90_console_printf("[usb status]\r\n");
    a90_console_printf("version=%s\r\n", A90_USB_STATUS_VERSION);
    a90_console_printf("read_only=1\r\n");
    a90_console_printf("configfs.root=%s\r\n", A90_USB_GADGET_ROOT);
    a90_console_printf("configfs.present=%d\r\n", inventory->base.configfs_mounted ? 1 : 0);
    a90_console_printf("gadget.present=%d\r\n", inventory->base.gadget_dir ? 1 : 0);
    a90_console_printf("gadget.udc_path=%s\r\n", A90_USB_GADGET_UDC_PATH);
    a90_console_printf("gadget.udc=%s\r\n", dash_if_empty(inventory->base.udc));
    a90_console_printf("gadget.bound=%d\r\n", inventory->base.udc_bound ? 1 : 0);
    a90_console_printf("idVendor=%s\r\n", dash_if_empty(inventory->id_vendor));
    a90_console_printf("idProduct=%s\r\n", dash_if_empty(inventory->id_product));
    a90_console_printf("bcdUSB=%s\r\n", dash_if_empty(inventory->bcd_usb));
    a90_console_printf("bcdDevice=%s\r\n", dash_if_empty(inventory->bcd_device));
    a90_console_printf("strings.manufacturer=%s\r\n", dash_if_empty(inventory->manufacturer));
    a90_console_printf("strings.product=%s\r\n", dash_if_empty(inventory->product));
    a90_console_printf("strings.serialnumber.present=%d\r\n", inventory->serial_present ? 1 : 0);
    a90_console_printf("strings.serialnumber.redacted=1\r\n");
    a90_console_printf("strings.serialnumber.length=%zu\r\n", inventory->serial_len);
    a90_console_printf("udc.count=%d\r\n", inventory->udc_count);
    for (udc_index = 0; udc_index < inventory->udc_count && udc_index < A90_USB_MAX_UDCS; ++udc_index) {
        const struct usb_udc_info *udc = &inventory->udcs[udc_index];

        a90_console_printf("udc.%d.name=%s\r\n", udc_index, dash_if_empty(udc->name));
        a90_console_printf("udc.%d.bound_here=%d\r\n",
                           udc_index,
                           strcmp(udc->name, inventory->base.udc) == 0 ? 1 : 0);
        a90_console_printf("udc.%d.state=%s\r\n", udc_index, dash_if_empty(udc->state));
        a90_console_printf("udc.%d.current_speed=%s\r\n",
                           udc_index,
                           dash_if_empty(udc->current_speed));
        a90_console_printf("udc.%d.maximum_speed=%s\r\n",
                           udc_index,
                           dash_if_empty(udc->maximum_speed));
    }
    a90_console_printf("config.count=%d\r\n", inventory->config_count);
    for (config_index = 0;
         config_index < inventory->config_count && config_index < A90_USB_MAX_CONFIGS;
         ++config_index) {
        const struct usb_config_info *config = &inventory->configs[config_index];
        int link_index;

        a90_console_printf("config.%d.name=%s\r\n", config_index, dash_if_empty(config->name));
        a90_console_printf("config.%d.configuration=%s\r\n",
                           config_index,
                           dash_if_empty(config->configuration));
        a90_console_printf("config.%d.max_power=%s\r\n", config_index, dash_if_empty(config->max_power));
        a90_console_printf("config.%d.link_count=%d\r\n", config_index, config->link_count);
        for (link_index = 0;
             link_index < config->link_count && link_index < A90_USB_MAX_CONFIG_LINKS;
             ++link_index) {
            const struct usb_config_link_info *link = &config->links[link_index];

            a90_console_printf("config.%d.link.%d.name=%s\r\n",
                               config_index,
                               link_index,
                               dash_if_empty(link->name));
            a90_console_printf("config.%d.link.%d.function=%s\r\n",
                               config_index,
                               link_index,
                               dash_if_empty(link->function));
            a90_console_printf("config.%d.link.%d.control=%d\r\n",
                               config_index,
                               link_index,
                               link->control ? 1 : 0);
            a90_console_printf("config.%d.link.%d.control_role=%s\r\n",
                               config_index,
                               link_index,
                               dash_if_empty(link->control_role));
        }
    }
    a90_console_printf("function.count=%d\r\n", inventory->function_count);
    for (function_index = 0;
         function_index < inventory->function_count && function_index < A90_USB_MAX_FUNCTIONS;
         ++function_index) {
        const struct usb_function_info *function = &inventory->functions[function_index];

        a90_console_printf("function.%d.name=%s\r\n", function_index, dash_if_empty(function->name));
        a90_console_printf("function.%d.linked=%d\r\n", function_index, function->linked ? 1 : 0);
        a90_console_printf("function.%d.links=%s\r\n", function_index, dash_if_empty(function->links));
        a90_console_printf("function.%d.control=%d\r\n", function_index, function->control ? 1 : 0);
        a90_console_printf("function.%d.control_role=%s\r\n",
                           function_index,
                           dash_if_empty(function->control_role));
        if (strcmp(function->name, "mass_storage.0") == 0) {
            int lun_index;

            a90_console_printf("function.%d.mass_storage.lun.count=%d\r\n",
                               function_index,
                               A90_USB_MASS_STORAGE_MAX_LUNS);
            for (lun_index = 0; lun_index < A90_USB_MASS_STORAGE_MAX_LUNS; ++lun_index) {
                const struct usb_mass_storage_lun_identity *lun = &A90_USB_MASS_STORAGE_LUNS[lun_index];
                char lun_path[256];
                char attr_path[320];
                char file[256];
                char ro[32];
                char removable[32];
                char cdrom[32];
                char inquiry_string[64];
                bool lun_present;
                bool file_present;

                snprintf(lun_path,
                         sizeof(lun_path),
                         "%s/lun.%d",
                         A90_USB_GADGET_MASS_STORAGE_FUNCTION,
                         lun->lun);
                lun_present = path_is_dir(lun_path);
                if (lun_present) {
                    snprintf(attr_path, sizeof(attr_path), "%s/file", lun_path);
                    usb_read_value(attr_path, file, sizeof(file));
                    snprintf(attr_path, sizeof(attr_path), "%s/ro", lun_path);
                    usb_read_value(attr_path, ro, sizeof(ro));
                    snprintf(attr_path, sizeof(attr_path), "%s/removable", lun_path);
                    usb_read_value(attr_path, removable, sizeof(removable));
                    snprintf(attr_path, sizeof(attr_path), "%s/cdrom", lun_path);
                    usb_read_value(attr_path, cdrom, sizeof(cdrom));
                    snprintf(attr_path, sizeof(attr_path), "%s/inquiry_string", lun_path);
                    usb_read_value(attr_path, inquiry_string, sizeof(inquiry_string));
                } else {
                    snprintf(file, sizeof(file), "-");
                    snprintf(ro, sizeof(ro), "-");
                    snprintf(removable, sizeof(removable), "-");
                    snprintf(cdrom, sizeof(cdrom), "-");
                    snprintf(inquiry_string, sizeof(inquiry_string), "-");
                }
                file_present = file[0] != '\0' && strcmp(file, "-") != 0;
                if (lun->lun == 0) {
                    a90_console_printf("function.%d.mass_storage.file.present=%d\r\n",
                                       function_index,
                                       file_present ? 1 : 0);
                    a90_console_printf("function.%d.mass_storage.file.path=%s\r\n",
                                       function_index,
                                       file_present ? file : "-");
                    a90_console_printf("function.%d.mass_storage.ro=%s\r\n",
                                       function_index,
                                       dash_if_empty(ro));
                    a90_console_printf("function.%d.mass_storage.removable=%s\r\n",
                                       function_index,
                                       dash_if_empty(removable));
                    a90_console_printf("function.%d.mass_storage.cdrom=%s\r\n",
                                       function_index,
                                       dash_if_empty(cdrom));
                    a90_console_printf("function.%d.mass_storage.inquiry_string=%s\r\n",
                                       function_index,
                                       dash_if_empty(inquiry_string));
                }
                a90_console_printf("function.%d.mass_storage.lun.%d.present=%d\r\n",
                                   function_index,
                                   lun->lun,
                                   lun_present ? 1 : 0);
                a90_console_printf("function.%d.mass_storage.lun.%d.file.present=%d\r\n",
                                   function_index,
                                   lun->lun,
                                   file_present ? 1 : 0);
                a90_console_printf("function.%d.mass_storage.lun.%d.file.path=%s\r\n",
                                   function_index,
                                   lun->lun,
                                   file_present ? file : "-");
                a90_console_printf("function.%d.mass_storage.lun.%d.ro=%s\r\n",
                                   function_index,
                                   lun->lun,
                                   dash_if_empty(ro));
                a90_console_printf("function.%d.mass_storage.lun.%d.removable=%s\r\n",
                                   function_index,
                                   lun->lun,
                                   dash_if_empty(removable));
                a90_console_printf("function.%d.mass_storage.lun.%d.cdrom=%s\r\n",
                                   function_index,
                                   lun->lun,
                                   dash_if_empty(cdrom));
                a90_console_printf("function.%d.mass_storage.lun.%d.inquiry_string=%s\r\n",
                                   function_index,
                                   lun->lun,
                                   dash_if_empty(inquiry_string));
                a90_console_printf("function.%d.mass_storage.lun.%d.inquiry.vendor=%s\r\n",
                                   function_index,
                                   lun->lun,
                                   lun->vendor);
                a90_console_printf("function.%d.mass_storage.lun.%d.inquiry.product=%s\r\n",
                                   function_index,
                                   lun->lun,
                                   lun->product);
                a90_console_printf("function.%d.mass_storage.lun.%d.inquiry.revision=%s\r\n",
                                   function_index,
                                   lun->lun,
                                   lun->revision);
                a90_console_printf("function.%d.mass_storage.lun.%d.volume_label=%s\r\n",
                                   function_index,
                                   lun->lun,
                                   lun->volume_label);
            }
        }
    }
    a90_console_printf("control.acm.present=%d\r\n", inventory->acm_control_present ? 1 : 0);
    a90_console_printf("control.ncm.present=%d\r\n", inventory->ncm_control_present ? 1 : 0);
    a90_console_printf("control.ok=%d\r\n", control_ok ? 1 : 0);
    a90_console_printf("control.required=NCM+ACM\r\n");
    a90_console_printf("mutation_attempted=0\r\n");
    a90_console_printf("read_only=1\r\n");
    a90_console_printf("decision=%s\r\n",
                       control_ok ? "usb-status-control-topology-read" :
                                    "usb-status-control-topology-incomplete");
    a90_console_printf("summary.bound=%s control_acm=%s control_ncm=%s functions=%d configs=%d udcs=%d\r\n",
                       yesno(inventory->base.udc_bound),
                       yesno(inventory->acm_control_present),
                       yesno(inventory->ncm_control_present),
                       inventory->function_count,
                       inventory->config_count,
                       inventory->udc_count);
}

static void usb_redirect_stdio_to_null(void) {
    int fd = open("/dev/null", O_RDWR | O_CLOEXEC);

    a90_console_silence_child();
    if (fd < 0) {
        return;
    }
    dup2(fd, STDIN_FILENO);
    dup2(fd, STDOUT_FILENO);
    dup2(fd, STDERR_FILENO);
    if (fd > STDERR_FILENO) {
        close(fd);
    }
}

static void usb_reconfig_marker_path(char *out, size_t out_size) {
    if (out == NULL || out_size == 0) {
        return;
    }
    snprintf(out, out_size, "/cache/a90-usb-reconfig-%ld.done", (long)getpid());
}

static void usb_current_or_default_udc(char *out, size_t out_size) {
    if (out == NULL || out_size == 0) {
        return;
    }
    if (read_trimmed_text_file(A90_USB_GADGET_UDC_PATH, out, out_size) < 0 || out[0] == '\0') {
        snprintf(out, out_size, "%s", A90_USB_GADGET_DEFAULT_UDC);
    }
}

static void usb_write_best_effort(const char *path, const char *value) {
    int saved_errno;

    if (write_file(path, value) == 0) {
        return;
    }
    saved_errno = errno;
    a90_logf("usb", "best-effort write failed path=%s errno=%d", path, saved_errno);
    errno = saved_errno;
}

static int usb_ensure_control_base_unbound(void) {
    if (ensure_configfs() < 0) {
        return negative_errno_or(EIO);
    }
    if (ensure_dir("/config/usb_gadget", 0770) < 0 ||
        ensure_dir(A90_USB_GADGET_ROOT, 0770) < 0 ||
        ensure_dir(A90_USB_GADGET_ROOT "/strings", 0770) < 0 ||
        ensure_dir(A90_USB_GADGET_ROOT "/strings/0x409", 0770) < 0 ||
        ensure_dir(A90_USB_GADGET_ROOT "/configs", 0770) < 0 ||
        ensure_dir(A90_USB_GADGET_CONFIG, 0770) < 0 ||
        ensure_dir(A90_USB_GADGET_CONFIG "/strings", 0770) < 0 ||
        ensure_dir(A90_USB_GADGET_CONFIG "/strings/0x409", 0770) < 0 ||
        ensure_dir(A90_USB_GADGET_ROOT "/functions", 0770) < 0 ||
        ensure_dir(A90_USB_GADGET_ACM_FUNCTION, 0770) < 0 ||
        ensure_dir(A90_USB_GADGET_NCM_FUNCTION, 0770) < 0) {
        return negative_errno_or(EIO);
    }

    usb_write_best_effort(A90_USB_GADGET_ROOT "/idVendor", "0x04e8");
    usb_write_best_effort(A90_USB_GADGET_ROOT "/idProduct", "0x6861");
    usb_write_best_effort(A90_USB_GADGET_ROOT "/bcdDevice", "0x0100");
    usb_write_best_effort(A90_USB_GADGET_ROOT "/strings/0x409/manufacturer", "A90 NativeInit");
    usb_write_best_effort(A90_USB_GADGET_ROOT "/strings/0x409/product", "A90 Linux (ARM)");
    usb_write_best_effort(A90_USB_GADGET_CONFIG "/strings/0x409/configuration", "serial");
    usb_write_best_effort(A90_USB_GADGET_CONFIG "/MaxPower", "900");

    usb_write_best_effort(A90_USB_GADGET_NCM_FUNCTION "/dev_addr", "02:11:22:33:44:56");
    usb_write_best_effort(A90_USB_GADGET_NCM_FUNCTION "/host_addr", "02:11:22:33:44:55");
    usb_write_best_effort(A90_USB_GADGET_NCM_FUNCTION "/qmult", "5");

    if (usb_create_or_replace_symlink(A90_USB_GADGET_ACM_FUNCTION, A90_USB_GADGET_ACM_LINK) < 0 ||
        usb_create_or_replace_symlink(A90_USB_GADGET_NCM_FUNCTION, A90_USB_GADGET_NCM_LINK) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int usb_ensure_mass_storage_function_ready(void) {
    if (ensure_dir(A90_USB_GADGET_MASS_STORAGE_FUNCTION, 0770) < 0) {
        return negative_errno_or(EIO);
    }
    if (!path_is_dir(A90_USB_GADGET_MASS_STORAGE_FUNCTION "/lun.0")) {
        errno = ENOENT;
        return -ENOENT;
    }
    return 0;
}

static void usb_mass_storage_lun_path(int lun, char *out, size_t out_size) {
    snprintf(out, out_size, "%s/lun.%d", A90_USB_GADGET_MASS_STORAGE_FUNCTION, lun);
}

static void usb_mass_storage_lun_attr_path(int lun, const char *attr, char *out, size_t out_size) {
    snprintf(out, out_size, "%s/lun.%d/%s", A90_USB_GADGET_MASS_STORAGE_FUNCTION, lun, attr);
}

static int usb_ensure_mass_storage_lun_ready(int lun) {
    char path[256];

    usb_mass_storage_lun_path(lun, path, sizeof(path));
    if (path_is_dir(path)) {
        return 0;
    }
    if (mkdir(path, 0770) == 0 || errno == EEXIST) {
        return 0;
    }
    return negative_errno_or(EIO);
}

static int usb_ensure_named_mass_storage_luns_ready(void) {
    int lun_index;
    int rc = usb_ensure_mass_storage_function_ready();

    if (rc < 0) {
        return rc;
    }
    for (lun_index = 0; lun_index < A90_USB_MASS_STORAGE_MAX_LUNS; ++lun_index) {
        rc = usb_ensure_mass_storage_lun_ready(A90_USB_MASS_STORAGE_LUNS[lun_index].lun);
        if (rc < 0) {
            return rc;
        }
    }
    return 0;
}

static int usb_clear_mass_storage_medium(void) {
    int lun_index;

    for (lun_index = 0; lun_index < A90_USB_MASS_STORAGE_MAX_LUNS; ++lun_index) {
        const struct usb_mass_storage_lun_identity *lun = &A90_USB_MASS_STORAGE_LUNS[lun_index];
        char lun_path[256];
        char file_path[320];

        usb_mass_storage_lun_path(lun->lun, lun_path, sizeof(lun_path));
        if (!path_is_dir(lun_path)) {
            continue;
        }
        usb_mass_storage_lun_attr_path(lun->lun, "file", file_path, sizeof(file_path));
        if (write_file(file_path, "\n") < 0) {
            return negative_errno_or(EIO);
        }
    }
    return 0;
}

static int usb_configure_mass_storage_function(bool expose_backing) {
    int lun_index;
    int rc = usb_ensure_named_mass_storage_luns_ready();

    if (rc < 0) {
        return rc;
    }
    rc = usb_clear_mass_storage_medium();
    if (rc < 0) {
        return rc;
    }
    usb_write_best_effort(A90_USB_GADGET_MASS_STORAGE_FUNCTION "/stall", "1");
    for (lun_index = 0; lun_index < A90_USB_MASS_STORAGE_MAX_LUNS; ++lun_index) {
        const struct usb_mass_storage_lun_identity *lun = &A90_USB_MASS_STORAGE_LUNS[lun_index];
        char attr_path[320];

        usb_mass_storage_lun_attr_path(lun->lun, "removable", attr_path, sizeof(attr_path));
        usb_write_best_effort(attr_path, "1");
        usb_mass_storage_lun_attr_path(lun->lun, "ro", attr_path, sizeof(attr_path));
        usb_write_best_effort(attr_path, "1");
        usb_mass_storage_lun_attr_path(lun->lun, "cdrom", attr_path, sizeof(attr_path));
        usb_write_best_effort(attr_path, "0");
        usb_mass_storage_lun_attr_path(lun->lun, "nofua", attr_path, sizeof(attr_path));
        usb_write_best_effort(attr_path, "1");
        usb_mass_storage_lun_attr_path(lun->lun, "inquiry_string", attr_path, sizeof(attr_path));
        if (write_file(attr_path, lun->inquiry_string) < 0) {
            return negative_errno_or(EIO);
        }
        if (expose_backing) {
            usb_mass_storage_lun_attr_path(lun->lun, "file", attr_path, sizeof(attr_path));
            if (write_file(attr_path, lun->backing_path) < 0) {
                return negative_errno_or(EIO);
            }
        }
    }
    return 0;
}

static void usb_copy_fat_label(unsigned char *dest, const char *label) {
    size_t label_len = strlen(label);

    memset(dest, ' ', 11);
    if (label_len > 11) {
        label_len = 11;
    }
    memcpy(dest, label, label_len);
}

static void usb_prepare_fat_boot_sector(unsigned char *sector, const char *label, unsigned int serial) {
    memset(sector, 0, A90_USB_FAT_BYTES_PER_SECTOR);
    sector[0] = 0xeb;
    sector[1] = 0x3c;
    sector[2] = 0x90;
    memcpy(sector + 3, "MSDOS5.0", 8);
    usb_put_le16(sector, 11, A90_USB_FAT_BYTES_PER_SECTOR);
    sector[13] = A90_USB_FAT_SECTORS_PER_CLUSTER;
    usb_put_le16(sector, 14, A90_USB_FAT_RESERVED_SECTORS);
    sector[16] = A90_USB_FAT_COUNT;
    usb_put_le16(sector, 17, A90_USB_FAT_ROOT_ENTRIES);
    usb_put_le16(sector, 19, A90_USB_FAT_TOTAL_SECTORS);
    sector[21] = 0xf8;
    usb_put_le16(sector, 22, A90_USB_FAT_SECTORS_PER_FAT);
    usb_put_le16(sector, 24, 63);
    usb_put_le16(sector, 26, 255);
    usb_put_le32(sector, 28, 0);
    usb_put_le32(sector, 32, 0);
    sector[36] = 0x80;
    sector[38] = 0x29;
    usb_put_le32(sector, 39, serial);
    usb_copy_fat_label(sector + 43, label);
    memcpy(sector + 54, "FAT16   ", 8);
    sector[510] = 0x55;
    sector[511] = 0xaa;
}

static void usb_prepare_fat_sector_zero(unsigned char *sector) {
    memset(sector, 0, A90_USB_FAT_BYTES_PER_SECTOR);
    sector[0] = 0xf8;
    sector[1] = 0xff;
    sector[2] = 0xff;
    sector[3] = 0xff;
}

static void usb_prepare_fat_root_dir(unsigned char *sector, const char *label) {
    memset(sector, 0, A90_USB_FAT_BYTES_PER_SECTOR);
    usb_copy_fat_label(sector, label);
    sector[11] = 0x08;
}

static int usb_create_mass_storage_backing_file(const struct usb_mass_storage_lun_identity *lun,
                                                unsigned int serial) {
    unsigned char sector[A90_USB_FAT_BYTES_PER_SECTOR];
    off_t fat_primary_offset = A90_USB_FAT_RESERVED_SECTORS * A90_USB_FAT_BYTES_PER_SECTOR;
    off_t fat_secondary_offset =
        (A90_USB_FAT_RESERVED_SECTORS + A90_USB_FAT_SECTORS_PER_FAT) *
        A90_USB_FAT_BYTES_PER_SECTOR;
    off_t root_dir_offset = A90_USB_FAT_ROOT_DIR_SECTOR * A90_USB_FAT_BYTES_PER_SECTOR;
    int fd;
    int saved_errno;

    fd = open(lun->backing_path,
              O_RDWR | O_CREAT | O_TRUNC | O_CLOEXEC,
              0600);
    if (fd < 0) {
        return negative_errno_or(EIO);
    }
    if (ftruncate(fd, (off_t)A90_USB_MASS_STORAGE_BACKING_BYTES) < 0) {
        saved_errno = errno;
        close(fd);
        errno = saved_errno;
        return negative_errno_or(EIO);
    }

    usb_prepare_fat_boot_sector(sector, lun->volume_label, serial);
    if (usb_write_block_at(fd, 0, sector, sizeof(sector)) < 0) {
        saved_errno = errno;
        close(fd);
        errno = saved_errno;
        return negative_errno_or(EIO);
    }
    usb_prepare_fat_sector_zero(sector);
    if (usb_write_block_at(fd, fat_primary_offset, sector, sizeof(sector)) < 0 ||
        usb_write_block_at(fd, fat_secondary_offset, sector, sizeof(sector)) < 0) {
        saved_errno = errno;
        close(fd);
        errno = saved_errno;
        return negative_errno_or(EIO);
    }
    usb_prepare_fat_root_dir(sector, lun->volume_label);
    if (usb_write_block_at(fd, root_dir_offset, sector, sizeof(sector)) < 0 ||
        fsync(fd) < 0) {
        saved_errno = errno;
        close(fd);
        errno = saved_errno;
        return negative_errno_or(EIO);
    }
    if (close(fd) < 0) {
        return negative_errno_or(EIO);
    }
    (void)chmod(lun->backing_path, 0600);
    return 0;
}

static int usb_create_mass_storage_backing_files(void) {
    int lun_index;

    for (lun_index = 0; lun_index < A90_USB_MASS_STORAGE_MAX_LUNS; ++lun_index) {
        int rc = usb_create_mass_storage_backing_file(&A90_USB_MASS_STORAGE_LUNS[lun_index],
                                                      0xA902323U + (unsigned int)lun_index);
        if (rc < 0) {
            return rc;
        }
    }
    return 0;
}

static int usb_restore_known_good_control(const char *udc) {
    const char *target_udc = (udc != NULL && udc[0] != '\0') ? udc : A90_USB_GADGET_DEFAULT_UDC;
    int rc;

    usb_log_line("restore: begin");
    (void)a90_usb_gadget_unbind();
    usleep(A90_USB_RECONFIG_SETTLE_USEC);
    (void)unlink(A90_USB_GADGET_MASS_STORAGE_LINK);
    (void)usb_clear_mass_storage_medium();
    rc = usb_ensure_control_base_unbound();
    if (rc < 0) {
        a90_logf("usb", "restore control base failed rc=%d", rc);
        return rc;
    }
    if (write_file(A90_USB_GADGET_UDC_PATH, target_udc) < 0) {
        rc = negative_errno_or(EIO);
        a90_logf("usb", "restore bind failed rc=%d", rc);
        return rc;
    }
    usb_log_line("restore: rebound control-only");
    return 0;
}

static pid_t usb_spawn_reconfig_watchdog(const char *done_path, const char *udc) {
    pid_t pid = fork();

    if (pid < 0) {
        return -1;
    }
    if (pid == 0) {
        char saved_udc[64];

        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        usb_redirect_stdio_to_null();
        snprintf(saved_udc, sizeof(saved_udc), "%s", udc != NULL && udc[0] != '\0' ? udc : A90_USB_GADGET_DEFAULT_UDC);
        sleep(A90_USB_RECONFIG_WATCHDOG_SEC);
        if (done_path != NULL && path_exists(done_path)) {
            _exit(0);
        }
        usb_log_line("watchdog: marker missing, restoring known-good control gadget");
        (void)usb_restore_known_good_control(saved_udc);
        _exit(0);
    }
    return pid;
}

static void usb_mark_reconfig_done(const char *done_path) {
    int fd;

    if (done_path == NULL) {
        return;
    }
    fd = open(done_path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (fd < 0) {
        return;
    }
    (void)write_all_checked(fd, "done\n", 5);
    close(fd);
}

static bool usb_inventory_control_ok(void) {
    struct usb_inventory inventory;

    if (usb_collect_inventory(&inventory) < 0) {
        return false;
    }
    return inventory.base.udc_bound &&
           inventory.acm_control_present &&
           inventory.ncm_control_present &&
           usb_link_points_to(A90_USB_GADGET_ACM_LINK, "acm.usb0") &&
           usb_link_points_to(A90_USB_GADGET_NCM_LINK, "ncm.usb0");
}

static int usb_run_mass_storage_reconfigure(bool add_mass_storage, bool expose_backing) {
    char udc[64];
    char done_path[128];
    pid_t watchdog;
    int rc;

    usb_current_or_default_udc(udc, sizeof(udc));
    usb_reconfig_marker_path(done_path, sizeof(done_path));
    (void)unlink(done_path);

    if (add_mass_storage) {
        rc = usb_ensure_mass_storage_function_ready();
        if (rc < 0) {
            a90_logf("usb", "mass_storage prepare failed rc=%d", rc);
            return rc;
        }
        if (expose_backing) {
            rc = usb_create_mass_storage_backing_files();
            if (rc < 0) {
                a90_logf("usb", "mass_storage backing create failed rc=%d", rc);
                return rc;
            }
        }
    }

    watchdog = usb_spawn_reconfig_watchdog(done_path, udc);
    if (watchdog < 0) {
        return negative_errno_or(EIO);
    }

    usb_log_line(add_mass_storage ? (expose_backing ? "worker: expose mass_storage begin" :
                                                      "worker: add mass_storage begin") :
                                    "worker: remove mass_storage begin");
    rc = a90_usb_gadget_unbind();
    if (rc < 0) {
        (void)usb_restore_known_good_control(udc);
        usb_mark_reconfig_done(done_path);
        return rc;
    }
    usleep(A90_USB_RECONFIG_SETTLE_USEC);

    if (add_mass_storage) {
        rc = usb_configure_mass_storage_function(expose_backing);
        if (rc == 0) {
            rc = usb_ensure_control_base_unbound();
        }
        if (rc == 0) {
            rc = usb_create_or_replace_symlink(A90_USB_GADGET_MASS_STORAGE_FUNCTION,
                                               A90_USB_GADGET_MASS_STORAGE_LINK) == 0 ?
                         0 :
                         negative_errno_or(EIO);
        }
    } else {
        (void)unlink(A90_USB_GADGET_MASS_STORAGE_LINK);
        (void)usb_clear_mass_storage_medium();
        rc = usb_ensure_control_base_unbound();
    }

    if (rc < 0) {
        (void)usb_restore_known_good_control(udc);
        usb_mark_reconfig_done(done_path);
        return rc;
    }

    if (write_file(A90_USB_GADGET_UDC_PATH, udc) < 0) {
        rc = negative_errno_or(EIO);
        (void)usb_restore_known_good_control(udc);
        usb_mark_reconfig_done(done_path);
        return rc;
    }
    usleep(A90_USB_RECONFIG_SETTLE_USEC);

    if (!usb_inventory_control_ok()) {
        (void)usb_restore_known_good_control(udc);
        usb_mark_reconfig_done(done_path);
        return -EIO;
    }
    if (add_mass_storage && !usb_link_points_to(A90_USB_GADGET_MASS_STORAGE_LINK, "mass_storage.0")) {
        (void)usb_restore_known_good_control(udc);
        usb_mark_reconfig_done(done_path);
        return -EIO;
    }

    usb_log_line(add_mass_storage ? (expose_backing ? "worker: expose mass_storage rebound" :
                                                      "worker: add mass_storage rebound") :
                                    "worker: remove mass_storage rebound");
    usb_mark_reconfig_done(done_path);
    return 0;
}

static int usb_start_mass_storage_reconfigure(bool add_mass_storage, bool expose_backing) {
    const char *action = add_mass_storage ? (expose_backing ? "expose" : "add") : "remove";
    pid_t pid;

    if (!usb_inventory_control_ok()) {
        a90_console_printf("usb.mass_storage.decision=preflight-control-incomplete\r\n");
        a90_console_printf("usb.mass_storage.mutation_attempted=0\r\n");
        return -EIO;
    }

    pid = fork();
    if (pid < 0) {
        return negative_errno_or(EAGAIN);
    }
    if (pid == 0) {
        int rc;

        signal(SIGHUP, SIG_IGN);
        signal(SIGPIPE, SIG_IGN);
        setsid();
        usb_redirect_stdio_to_null();
        usleep(A90_USB_RECONFIG_DETACH_DELAY_USEC);
        rc = usb_run_mass_storage_reconfigure(add_mass_storage, expose_backing);
        _exit(rc == 0 ? 0 : 1);
    }

    a90_console_printf("usb.mass_storage.action=%s\r\n", action);
    a90_console_printf("usb.mass_storage.detached_pid=%ld\r\n", (long)pid);
    a90_console_printf("usb.mass_storage.expected_usb_disconnect=1\r\n");
    a90_console_printf("usb.mass_storage.control_required=NCM+ACM\r\n");
    a90_console_printf("usb.mass_storage.watchdog_sec=%d\r\n", A90_USB_RECONFIG_WATCHDOG_SEC);
    a90_console_printf("usb.mass_storage.host_enumeration_required=parked\r\n");
    if (expose_backing) {
        a90_console_printf("usb.mass_storage.persona=readonly-backing\r\n");
        a90_console_printf("usb.mass_storage.lun.count=%d\r\n", A90_USB_MASS_STORAGE_MAX_LUNS);
        a90_console_printf("usb.mass_storage.lun.0.backing_file=%s\r\n",
                           A90_USB_MASS_STORAGE_LUNS[0].backing_path);
        a90_console_printf("usb.mass_storage.lun.0.model=%s\r\n",
                           A90_USB_MASS_STORAGE_LUNS[0].product);
        a90_console_printf("usb.mass_storage.lun.0.volume_label=%s\r\n",
                           A90_USB_MASS_STORAGE_LUNS[0].volume_label);
        a90_console_printf("usb.mass_storage.lun.1.backing_file=%s\r\n",
                           A90_USB_MASS_STORAGE_LUNS[1].backing_path);
        a90_console_printf("usb.mass_storage.lun.1.model=%s\r\n",
                           A90_USB_MASS_STORAGE_LUNS[1].product);
        a90_console_printf("usb.mass_storage.lun.1.volume_label=%s\r\n",
                           A90_USB_MASS_STORAGE_LUNS[1].volume_label);
        a90_console_printf("usb.mass_storage.backing_bytes=%lld\r\n",
                           (long long)A90_USB_MASS_STORAGE_BACKING_BYTES);
        a90_console_printf("usb.mass_storage.read_only=1\r\n");
    }
    a90_console_printf("usb.mass_storage.decision=scheduled\r\n");
    return 0;
}

int a90_usb_gadget_unbind(void) {
    if (write_file(A90_USB_GADGET_UDC_PATH, "") < 0) {
        if (errno == EBUSY) {
            a90_logf("usb", "UDC unbind busy; continuing");
            return 0;
        }
        return negative_errno_or(EIO);
    }
    return 0;
}

int a90_usb_gadget_bind_default_udc(void) {
    if (write_file(A90_USB_GADGET_UDC_PATH, A90_USB_GADGET_DEFAULT_UDC) < 0) {
        if (errno == EBUSY) {
            a90_logf("usb", "UDC already busy/bound; continuing");
            return 0;
        }
        return negative_errno_or(EIO);
    }
    return 0;
}

int a90_usb_gadget_setup_acm(void) {
    if (ensure_configfs() < 0) {
        return negative_errno_or(EIO);
    }

    ensure_dir("/config/usb_gadget", 0770);
    ensure_dir(A90_USB_GADGET_ROOT, 0770);
    ensure_dir(A90_USB_GADGET_ROOT "/strings", 0770);
    ensure_dir(A90_USB_GADGET_ROOT "/strings/0x409", 0770);
    ensure_dir(A90_USB_GADGET_ROOT "/configs", 0770);
    ensure_dir(A90_USB_GADGET_CONFIG, 0770);
    ensure_dir(A90_USB_GADGET_CONFIG "/strings", 0770);
    ensure_dir(A90_USB_GADGET_CONFIG "/strings/0x409", 0770);
    ensure_dir(A90_USB_GADGET_ROOT "/functions", 0770);
    ensure_dir(A90_USB_GADGET_ACM_FUNCTION, 0770);

    write_file(A90_USB_GADGET_ROOT "/idVendor", "0x04e8");
    write_file(A90_USB_GADGET_ROOT "/idProduct", "0x6861");
    write_file(A90_USB_GADGET_ROOT "/bcdUSB", "0x0200");
    write_file(A90_USB_GADGET_ROOT "/bcdDevice", "0x0100");
    write_file(A90_USB_GADGET_ROOT "/strings/0x409/serialnumber", "A90NATIVE001");
    write_file(A90_USB_GADGET_ROOT "/strings/0x409/manufacturer", "A90 NativeInit");
    write_file(A90_USB_GADGET_ROOT "/strings/0x409/product", "A90 Linux (ARM)");
    write_file(A90_USB_GADGET_CONFIG "/strings/0x409/configuration", "serial");
    write_file(A90_USB_GADGET_CONFIG "/MaxPower", "900");

    if (create_symlink_checked(A90_USB_GADGET_ACM_FUNCTION, A90_USB_GADGET_ACM_LINK) < 0) {
        return negative_errno_or(EIO);
    }

    return a90_usb_gadget_bind_default_udc();
}

int a90_usb_gadget_reset_acm(void) {
    int rc;

    rc = a90_usb_gadget_unbind();
    if (rc < 0) {
        return rc;
    }
    usleep(300000);
    unlink(A90_USB_GADGET_ADB_LINK);
    return a90_usb_gadget_setup_acm();
}

int a90_usb_gadget_status(struct a90_usb_gadget_status *out) {
    char udc[sizeof(out->udc)];

    if (out == NULL) {
        return -EINVAL;
    }

    memset(out, 0, sizeof(*out));
    out->configfs_mounted = path_exists("/config/usb_gadget");
    out->gadget_dir = path_exists(A90_USB_GADGET_ROOT);
    out->acm_function = path_exists(A90_USB_GADGET_ACM_FUNCTION);
    out->acm_link = path_is_symlink(A90_USB_GADGET_ACM_LINK);
    out->adb_link = path_is_symlink(A90_USB_GADGET_ADB_LINK);
    if (read_trimmed_text_file(A90_USB_GADGET_UDC_PATH, udc, sizeof(udc)) == 0) {
        snprintf(out->udc, sizeof(out->udc), "%s", udc);
        out->udc_bound = out->udc[0] != '\0';
    }
    return 0;
}

int a90_usb_gadget_print_status(void) {
    struct usb_inventory inventory;
    int rc;

    rc = usb_collect_inventory(&inventory);
    if (rc < 0) {
        return rc;
    }
    usb_print_inventory(&inventory);
    return 0;
}

int a90_usb_gadget_cmd(char **argv, int argc) {
    if (argv == NULL || argc < 1) {
        return -EINVAL;
    }
    if (argc == 1 || (argc == 2 && argv[1] != NULL && strcmp(argv[1], "status") == 0)) {
        return a90_usb_gadget_print_status();
    }
    if (argc == 3 && argv[1] != NULL && argv[2] != NULL &&
        strcmp(argv[1], "mass-storage") == 0) {
        if (strcmp(argv[2], "add") == 0) {
            return usb_start_mass_storage_reconfigure(true, false);
        }
        if (strcmp(argv[2], "expose") == 0) {
            return usb_start_mass_storage_reconfigure(true, true);
        }
        if (strcmp(argv[2], "remove") == 0) {
            return usb_start_mass_storage_reconfigure(false, false);
        }
    }
    a90_console_printf("usage: usb [status|mass-storage add|mass-storage expose|mass-storage remove]\r\n");
    return -EINVAL;
}
