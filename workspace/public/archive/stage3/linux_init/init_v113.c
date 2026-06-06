/*
 * A90 native init v113.
 *
 * This version adds a runtime package layout baseline.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v113/00_prelude.inc.c"
#include "v113/10_core_log_console.inc.c"
#include "v113/20_device_display.inc.c"
#include "v113/30_status_hud.inc.c"
#include "v113/40_menu_apps.inc.c"
#include "v113/50_boot_services.inc.c"
#include "v113/60_shell_basic_commands.inc.c"
#include "v113/70_storage_android_net.inc.c"
#include "v113/80_shell_dispatch.inc.c"
#include "v113/90_main.inc.c"
