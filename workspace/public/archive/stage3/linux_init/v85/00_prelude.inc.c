/* Included by stage3/linux_init/init_v85.c. Do not compile standalone. */

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

#include "../a90_config.h"
#include "../a90_console.h"
#include "../a90_cmdproto.h"
#include "../a90_log.h"
#include "../a90_run.h"
#include "../a90_service.h"
#include "../a90_timeline.h"
#include "../a90_util.h"


#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef ECANCELED
#define ECANCELED 125
#endif

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

enum command_flags {
    CMD_NONE = 0,
    CMD_DISPLAY = 1 << 0,
    CMD_BLOCKING = 1 << 1,
    CMD_DANGEROUS = 1 << 2,
    CMD_BACKGROUND = 1 << 3,
    CMD_NO_DONE = 1 << 4,
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
