/*
 * A90 native init v82.
 *
 * This version is the log/timeline API extraction after v81.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v82/00_prelude.inc.c"
#include "v82/10_core_log_console.inc.c"
#include "v82/20_device_display.inc.c"
#include "v82/30_status_hud.inc.c"
#include "v82/40_menu_apps.inc.c"
#include "v82/50_boot_services.inc.c"
#include "v82/60_shell_basic_commands.inc.c"
#include "v82/70_storage_android_net.inc.c"
#include "v82/80_shell_dispatch.inc.c"
#include "v82/90_main.inc.c"
