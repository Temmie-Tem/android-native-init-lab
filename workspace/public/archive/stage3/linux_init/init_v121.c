/*
 * A90 native init v121.
 *
 * This version moves PID1 guard checks into a90_pid1_guard.c/h.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v121/00_prelude.inc.c"
#include "v121/10_core_log_console.inc.c"
#include "v121/20_device_display.inc.c"
#include "v121/30_status_hud.inc.c"
#include "v121/40_menu_apps.inc.c"
#include "v121/50_boot_services.inc.c"
#include "v121/60_shell_basic_commands.inc.c"
#include "v121/70_storage_android_net.inc.c"
#include "v121/80_shell_dispatch.inc.c"
#include "v121/90_main.inc.c"
