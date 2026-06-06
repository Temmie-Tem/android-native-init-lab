/*
 * A90 native init v101.
 *
 * This version adds a minimal service manager view over existing long-running helpers.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v101/00_prelude.inc.c"
#include "v101/10_core_log_console.inc.c"
#include "v101/20_device_display.inc.c"
#include "v101/30_status_hud.inc.c"
#include "v101/40_menu_apps.inc.c"
#include "v101/50_boot_services.inc.c"
#include "v101/60_shell_basic_commands.inc.c"
#include "v101/70_storage_android_net.inc.c"
#include "v101/80_shell_dispatch.inc.c"
#include "v101/90_main.inc.c"
