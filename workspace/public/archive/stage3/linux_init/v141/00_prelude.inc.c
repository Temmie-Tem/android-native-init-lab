/* Included by stage3/linux_init/init_v141.c. Do not compile standalone. */

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

#include "../a90_config.h"
#include "../a90_app_about.h"
#include "../a90_app_cpustress.h"
#include "../a90_app_displaytest.h"
#include "../a90_app_inputmon.h"
#include "../a90_app_log.h"
#include "../a90_app_network.h"
#include "../a90_console.h"
#include "../a90_controller.h"
#include "../a90_cmdproto.h"
#include "../a90_diag.h"
#include "../a90_draw.h"
#include "../a90_exposure.h"
#include "../a90_hud.h"
#include "../a90_helper.h"
#include "../a90_input.h"
#include "../a90_kms.h"
#include "../a90_log.h"
#include "../a90_menu.h"
#include "../a90_metrics.h"
#include "../a90_netservice.h"
#include "../a90_pid1_guard.h"
#include "../a90_run.h"
#include "../a90_runtime.h"
#include "../a90_service.h"
#include "../a90_shell.h"
#include "../a90_selftest.h"
#include "../a90_storage.h"
#include "../a90_timeline.h"
#include "../a90_usb_gadget.h"
#include "../a90_userland.h"
#include "../a90_util.h"
#include "../a90_wififeas.h"
#include "../a90_wifiinv.h"


#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#ifndef ECANCELED
#define ECANCELED 125
#endif

static bool boot_splash_recorded = false;

static int ensure_block_node(const char *path, unsigned int major_num, unsigned int minor_num);
static void refresh_pid1_guard(void);
