/*
 * A90 native init v89.
 *
 * This version is the menu control API extraction after v88.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v89/00_prelude.inc.c"
#include "v89/10_core_log_console.inc.c"
#include "v89/20_device_display.inc.c"
#include "v89/30_status_hud.inc.c"
#include "v89/40_menu_apps.inc.c"
#include "v89/50_boot_services.inc.c"
#include "v89/60_shell_basic_commands.inc.c"
#include "v89/70_storage_android_net.inc.c"
#include "v89/80_shell_dispatch.inc.c"
#include "v89/90_main.inc.c"
