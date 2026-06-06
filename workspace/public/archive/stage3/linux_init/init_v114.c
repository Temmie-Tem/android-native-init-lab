/*
 * A90 native init v114.
 *
 * This version adds a helper deployment visibility baseline.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v114/00_prelude.inc.c"
#include "v114/10_core_log_console.inc.c"
#include "v114/20_device_display.inc.c"
#include "v114/30_status_hud.inc.c"
#include "v114/40_menu_apps.inc.c"
#include "v114/50_boot_services.inc.c"
#include "v114/60_shell_basic_commands.inc.c"
#include "v114/70_storage_android_net.inc.c"
#include "v114/80_shell_dispatch.inc.c"
#include "v114/90_main.inc.c"
