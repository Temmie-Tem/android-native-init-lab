/*
 * A90 native init v135.
 *
 * This version adds a machine-checkable controller policy matrix for
 * menu-visible and power-page command safety decisions.
 */
#include "v135/00_prelude.inc.c"
#include "v135/10_core_log_console.inc.c"
#include "v135/20_device_display.inc.c"
#include "v135/30_status_hud.inc.c"
#include "v135/40_menu_apps.inc.c"
#include "v135/50_boot_services.inc.c"
#include "v135/60_shell_basic_commands.inc.c"
#include "v135/70_storage_android_net.inc.c"
#include "v135/80_shell_dispatch.inc.c"
#include "v135/90_main.inc.c"
