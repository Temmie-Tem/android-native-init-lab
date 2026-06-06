/*
 * A90 native init v83.
 *
 * This version is the console API extraction after v82.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v83/00_prelude.inc.c"
#include "v83/10_core_log_console.inc.c"
#include "v83/20_device_display.inc.c"
#include "v83/30_status_hud.inc.c"
#include "v83/40_menu_apps.inc.c"
#include "v83/50_boot_services.inc.c"
#include "v83/60_shell_basic_commands.inc.c"
#include "v83/70_storage_android_net.inc.c"
#include "v83/80_shell_dispatch.inc.c"
#include "v83/90_main.inc.c"
