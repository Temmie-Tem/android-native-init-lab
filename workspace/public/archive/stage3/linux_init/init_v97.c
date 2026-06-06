/*
 * A90 native init v97.
 *
 * This version promotes SD workspace into a runtime root after v96.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v97/00_prelude.inc.c"
#include "v97/10_core_log_console.inc.c"
#include "v97/20_device_display.inc.c"
#include "v97/30_status_hud.inc.c"
#include "v97/40_menu_apps.inc.c"
#include "v97/50_boot_services.inc.c"
#include "v97/60_shell_basic_commands.inc.c"
#include "v97/70_storage_android_net.inc.c"
#include "v97/80_shell_dispatch.inc.c"
#include "v97/90_main.inc.c"
