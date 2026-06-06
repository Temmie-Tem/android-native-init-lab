/*
 * A90 native init v119.
 *
 * This version moves menu route helpers into a90_menu.c/h.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v119/00_prelude.inc.c"
#include "v119/10_core_log_console.inc.c"
#include "v119/20_device_display.inc.c"
#include "v119/30_status_hud.inc.c"
#include "v119/40_menu_apps.inc.c"
#include "v119/50_boot_services.inc.c"
#include "v119/60_shell_basic_commands.inc.c"
#include "v119/70_storage_android_net.inc.c"
#include "v119/80_shell_dispatch.inc.c"
#include "v119/90_main.inc.c"
