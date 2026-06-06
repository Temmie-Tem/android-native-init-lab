/* Included by stage3/linux_init/init_v80.c. Do not compile standalone. */

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdbool.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <linux/input.h>
#include <linux/reboot.h>
#include <poll.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/syscall.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/sysmacros.h>
#include <sys/wait.h>
#include <sys/utsname.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>
#include <drm/drm.h>
#include <drm/drm_fourcc.h>
#include <drm/drm_mode.h>

#define INIT_VERSION "0.8.11"
#define INIT_BUILD "v80"
#define INIT_CREATOR "made by temmie0214"
#define INIT_BANNER "A90 Linux init " INIT_VERSION " (" INIT_BUILD ")"
#define BOOT_SPLASH_SECONDS 2
#define BOOT_HUD_REFRESH_SECONDS 2
#define NATIVE_LOG_PRIMARY "/cache/native-init.log"
#define NATIVE_LOG_FALLBACK "/tmp/native-init.log"
#define NATIVE_LOG_MAX_BYTES (256 * 1024)
#define KMS_LOG_TAIL_MAX_LINES 24
#define KMS_LOG_TAIL_LINE_MAX 96
#define BOOT_TIMELINE_MAX 32
#define CONSOLE_POLL_TIMEOUT_MS 1000
#define CONSOLE_IDLE_REATTACH_MS 60000
#define DISPLAY_TEST_PAGE_COUNT 4
#define AUTO_MENU_STATE_PATH "/tmp/a90-auto-menu-active"
#define AUTO_MENU_REQUEST_PATH "/tmp/a90-auto-menu-request"
#define NETSERVICE_FLAG_PATH "/cache/native-init-netservice"
#define NETSERVICE_LOG_PATH "/cache/native-init-netservice.log"
#define NETSERVICE_USB_HELPER "/cache/bin/a90_usbnet"
#define NETSERVICE_TCPCTL_HELPER "/cache/bin/a90_tcpctl"
#define NETSERVICE_TOYBOX "/cache/bin/toybox"
#define NETSERVICE_IFNAME "ncm0"
#define NETSERVICE_DEVICE_IP "192.168.7.2"
#define NETSERVICE_NETMASK "255.255.255.0"
#define NETSERVICE_TCP_PORT "2325"
#define NETSERVICE_TCP_IDLE_SECONDS "3600"
#define NETSERVICE_TCP_MAX_CLIENTS "0"
#define CMDV1X_MAX_ARGS 32
#define SD_BLOCK_NAME "mmcblk0p1"
#define SD_MOUNT_POINT "/mnt/sdext"
#define SD_FS_TYPE "ext4"
#define SD_WORKSPACE_DIR "/mnt/sdext/a90"
#define SD_EXPECTED_UUID "c6c81408-f453-11e7-b42a-23a2c89f58bc"
#define SD_ID_FILE SD_WORKSPACE_DIR "/.a90-native-id"
#define SD_BOOT_RW_TEST_FILE SD_WORKSPACE_DIR "/tmp/.boot-rw-test"
#define SD_NATIVE_LOG_PATH SD_WORKSPACE_DIR "/logs/native-init.log"
#define CACHE_STORAGE_ROOT "/cache"
#define TMP_STORAGE_ROOT "/tmp"
#define BOOT_SPLASH_LINE_COUNT 6
#define BOOT_SPLASH_LINE_MAX 96

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef ECANCELED
#define ECANCELED 125
#endif

static int console_fd = -1;
static long last_console_reattach_ms = 0;
static pid_t adbd_pid = -1;
static pid_t hud_pid = -1;
static pid_t tcpctl_pid = -1;
static bool native_log_ready = false;
static char native_log_path[PATH_MAX] = NATIVE_LOG_FALLBACK;
static bool cache_mount_ready = false;

struct boot_storage_state {
    bool probed;
    bool sd_present;
    bool sd_mounted;
    bool sd_expected;
    bool sd_rw_ok;
    bool fallback;
    char backend[16];
    char root[PATH_MAX];
    char sd_uuid[40];
    char warning[128];
    char detail[160];
};

static struct boot_storage_state boot_storage = {
    .probed = false,
    .sd_present = false,
    .sd_mounted = false,
    .sd_expected = false,
    .sd_rw_ok = false,
    .fallback = true,
    .backend = "cache",
    .root = CACHE_STORAGE_ROOT,
    .sd_uuid = "<none>",
    .warning = "SD not probed; using /cache",
    .detail = "boot storage probe pending",
};

static char boot_splash_lines[BOOT_SPLASH_LINE_COUNT][BOOT_SPLASH_LINE_MAX] = {
    "[ KERNEL ] STOCK LINUX 4.14",
    "[ CACHE  ] WAITING",
    "[ SD     ] WAITING",
    "[ STORAGE] CACHE FALLBACK",
    "[ SERIAL ] USB ACM STARTING",
    "[ RUNTIME] HUD MENU LOADING",
};
static bool boot_splash_recorded = false;

struct boot_timeline_entry {
    long ms;
    char step[32];
    int code;
    int saved_errno;
    char detail[128];
};

static struct boot_timeline_entry boot_timeline[BOOT_TIMELINE_MAX];
static size_t boot_timeline_count = 0;

enum command_flags {
    CMD_NONE = 0,
    CMD_DISPLAY = 1 << 0,
    CMD_BLOCKING = 1 << 1,
    CMD_DANGEROUS = 1 << 2,
    CMD_BACKGROUND = 1 << 3,
    CMD_NO_DONE = 1 << 4,
};

enum cancel_kind {
    CANCEL_NONE = 0,
    CANCEL_SOFT,
    CANCEL_HARD,
};

struct shell_last_result {
    char command[64];
    int code;
    int saved_errno;
    long duration_ms;
    unsigned int flags;
};

static struct shell_last_result last_result = {
    .command = "<none>",
    .code = 0,
    .saved_errno = 0,
    .duration_ms = 0,
    .flags = CMD_NONE,
};
static unsigned long shell_protocol_seq = 0;

static long monotonic_millis(void);
static int ensure_block_node(const char *path, unsigned int major_num, unsigned int minor_num);
static void reap_tcpctl_child(void);
static bool netservice_enabled_flag(void);
static int cmd_mountsd(char **argv, int argc);
static int cmd_storage(void);

struct kms_display_state {
    int fd;
    uint32_t connector_id;
    uint32_t encoder_id;
    uint32_t crtc_id;
    uint32_t fb_id[2];
    uint32_t handle[2];
    uint32_t width;
    uint32_t height;
    uint32_t stride;
    size_t map_size;
    void *map[2];
    uint32_t current_buffer;
    struct drm_mode_modeinfo mode;
};

static struct kms_display_state kms_state = {
    .fd = -1,
    .map = { MAP_FAILED, MAP_FAILED },
};
