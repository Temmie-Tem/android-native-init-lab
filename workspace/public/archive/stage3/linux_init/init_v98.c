/*
 * A90 native init v98.
 *
 * This version adds helper inventory and manifest checks on the v97 runtime root.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v98/00_prelude.inc.c"
#include "v98/10_core_log_console.inc.c"
#include "v98/20_device_display.inc.c"
#include "v98/30_status_hud.inc.c"
#include "v98/40_menu_apps.inc.c"
#include "v98/50_boot_services.inc.c"
#include "v98/60_shell_basic_commands.inc.c"
#include "v98/70_storage_android_net.inc.c"
#include "v98/80_shell_dispatch.inc.c"
#include "v98/90_main.inc.c"
