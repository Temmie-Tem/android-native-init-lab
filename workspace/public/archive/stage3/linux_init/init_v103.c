/*
 * A90 native init v103.
 *
 * This version adds read-only Wi-Fi inventory collection.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v103/00_prelude.inc.c"
#include "v103/10_core_log_console.inc.c"
#include "v103/20_device_display.inc.c"
#include "v103/30_status_hud.inc.c"
#include "v103/40_menu_apps.inc.c"
#include "v103/50_boot_services.inc.c"
#include "v103/60_shell_basic_commands.inc.c"
#include "v103/70_storage_android_net.inc.c"
#include "v103/80_shell_dispatch.inc.c"
#include "v103/90_main.inc.c"
