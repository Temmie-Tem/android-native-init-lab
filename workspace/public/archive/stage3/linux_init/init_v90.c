/*
 * A90 native init v90.
 *
 * This version is the metrics API extraction after v89.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v90/00_prelude.inc.c"
#include "v90/10_core_log_console.inc.c"
#include "v90/20_device_display.inc.c"
#include "v90/30_status_hud.inc.c"
#include "v90/40_menu_apps.inc.c"
#include "v90/50_boot_services.inc.c"
#include "v90/60_shell_basic_commands.inc.c"
#include "v90/70_storage_android_net.inc.c"
#include "v90/80_shell_dispatch.inc.c"
#include "v90/90_main.inc.c"
