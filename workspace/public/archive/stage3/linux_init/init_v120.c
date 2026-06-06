/*
 * A90 native init v120.
 *
 * This version moves command group metadata into a90_shell.c/h.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v120/00_prelude.inc.c"
#include "v120/10_core_log_console.inc.c"
#include "v120/20_device_display.inc.c"
#include "v120/30_status_hud.inc.c"
#include "v120/40_menu_apps.inc.c"
#include "v120/50_boot_services.inc.c"
#include "v120/60_shell_basic_commands.inc.c"
#include "v120/70_storage_android_net.inc.c"
#include "v120/80_shell_dispatch.inc.c"
#include "v120/90_main.inc.c"
