/*
 * A90 native init v111.
 *
 * This version adds a extended soak release-candidate baseline.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v111/00_prelude.inc.c"
#include "v111/10_core_log_console.inc.c"
#include "v111/20_device_display.inc.c"
#include "v111/30_status_hud.inc.c"
#include "v111/40_menu_apps.inc.c"
#include "v111/50_boot_services.inc.c"
#include "v111/60_shell_basic_commands.inc.c"
#include "v111/70_storage_android_net.inc.c"
#include "v111/80_shell_dispatch.inc.c"
#include "v111/90_main.inc.c"
