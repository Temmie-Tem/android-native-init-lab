/*
 * A90 native init v96.
 *
 * This version performs structure audit and low-risk cleanup after v95.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v96/00_prelude.inc.c"
#include "v96/10_core_log_console.inc.c"
#include "v96/20_device_display.inc.c"
#include "v96/30_status_hud.inc.c"
#include "v96/40_menu_apps.inc.c"
#include "v96/50_boot_services.inc.c"
#include "v96/60_shell_basic_commands.inc.c"
#include "v96/70_storage_android_net.inc.c"
#include "v96/80_shell_dispatch.inc.c"
#include "v96/90_main.inc.c"
