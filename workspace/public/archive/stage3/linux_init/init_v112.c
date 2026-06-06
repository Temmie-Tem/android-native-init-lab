/*
 * A90 native init v112.
 *
 * This version adds a USB/NCM service soak baseline.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v112/00_prelude.inc.c"
#include "v112/10_core_log_console.inc.c"
#include "v112/20_device_display.inc.c"
#include "v112/30_status_hud.inc.c"
#include "v112/40_menu_apps.inc.c"
#include "v112/50_boot_services.inc.c"
#include "v112/60_shell_basic_commands.inc.c"
#include "v112/70_storage_android_net.inc.c"
#include "v112/80_shell_dispatch.inc.c"
#include "v112/90_main.inc.c"
