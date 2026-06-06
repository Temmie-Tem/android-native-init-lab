/*
 * A90 native init v110.
 *
 * This version adds a menu/app controller cleanup baseline.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v110/00_prelude.inc.c"
#include "v110/10_core_log_console.inc.c"
#include "v110/20_device_display.inc.c"
#include "v110/30_status_hud.inc.c"
#include "v110/40_menu_apps.inc.c"
#include "v110/50_boot_services.inc.c"
#include "v110/60_shell_basic_commands.inc.c"
#include "v110/70_storage_android_net.inc.c"
#include "v110/80_shell_dispatch.inc.c"
#include "v110/90_main.inc.c"
