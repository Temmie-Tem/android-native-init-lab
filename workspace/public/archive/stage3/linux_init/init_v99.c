/*
 * A90 native init v99.
 *
 * This version evaluates optional BusyBox/toybox userland on the v97 runtime root.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v99/00_prelude.inc.c"
#include "v99/10_core_log_console.inc.c"
#include "v99/20_device_display.inc.c"
#include "v99/30_status_hud.inc.c"
#include "v99/40_menu_apps.inc.c"
#include "v99/50_boot_services.inc.c"
#include "v99/60_shell_basic_commands.inc.c"
#include "v99/70_storage_android_net.inc.c"
#include "v99/80_shell_dispatch.inc.c"
#include "v99/90_main.inc.c"
