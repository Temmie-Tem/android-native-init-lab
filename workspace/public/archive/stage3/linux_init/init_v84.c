/*
 * A90 native init v84.
 *
 * This version is the cmdproto API extraction after v83.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v84/00_prelude.inc.c"
#include "v84/10_core_log_console.inc.c"
#include "v84/20_device_display.inc.c"
#include "v84/30_status_hud.inc.c"
#include "v84/40_menu_apps.inc.c"
#include "v84/50_boot_services.inc.c"
#include "v84/60_shell_basic_commands.inc.c"
#include "v84/70_storage_android_net.inc.c"
#include "v84/80_shell_dispatch.inc.c"
#include "v84/90_main.inc.c"
