/*
 * A90 native init v127.
 *
 * This version hardens the auto-menu busy gate with a deny-by-default
 * allowlist for non-power menu states.
 */
#include "v127/00_prelude.inc.c"
#include "v127/10_core_log_console.inc.c"
#include "v127/20_device_display.inc.c"
#include "v127/30_status_hud.inc.c"
#include "v127/40_menu_apps.inc.c"
#include "v127/50_boot_services.inc.c"
#include "v127/60_shell_basic_commands.inc.c"
#include "v127/70_storage_android_net.inc.c"
#include "v127/80_shell_dispatch.inc.c"
#include "v127/90_main.inc.c"
