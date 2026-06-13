#include "a90_usb_gadget.h"

#include "a90_config.h"
#include "a90_console.h"
#include "a90_log.h"
#include "a90_util.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <unistd.h>

#define A90_USB_GADGET_ROOT "/config/usb_gadget/g1"
#define A90_USB_GADGET_CONFIG A90_USB_GADGET_ROOT "/configs/b.1"
#define A90_USB_GADGET_ACM_FUNCTION A90_USB_GADGET_ROOT "/functions/acm.usb0"
#define A90_USB_GADGET_ACM_LINK A90_USB_GADGET_CONFIG "/f1"
#define A90_USB_GADGET_ADB_LINK A90_USB_GADGET_CONFIG "/f2"
#define A90_USB_GADGET_UDC_PATH A90_USB_GADGET_ROOT "/UDC"
#define A90_USB_GADGET_DEFAULT_UDC "a600000.dwc3"
#define A90_USB_STATUS_VERSION "a90-native-usb-status-v1"
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

static int create_symlink_checked(const char *target, const char *linkpath) {
    if (symlink(target, linkpath) == 0 || errno == EEXIST) {
        return 0;
    }
    return -1;
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
    write_file(A90_USB_GADGET_ROOT "/strings/0x409/serialnumber", "RFCM90CFWXA");
    write_file(A90_USB_GADGET_ROOT "/strings/0x409/manufacturer", "samsung");
    write_file(A90_USB_GADGET_ROOT "/strings/0x409/product", "SM8150-ACM");
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
    a90_console_printf("usage: usb [status]\r\n");
    return -EINVAL;
}
