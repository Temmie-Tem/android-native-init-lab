/*
 * A90 native init v132.
 *
 * This version removes legacy per-version changelog routes and keeps
 * ABOUT/changelog rendering on the shared changelog table.
 */
#include "v132/00_prelude.inc.c"
#include "v132/10_core_log_console.inc.c"
#include "v132/20_device_display.inc.c"
#include "v132/30_status_hud.inc.c"
#include "v132/40_menu_apps.inc.c"
#include "v132/50_boot_services.inc.c"
#include "v132/60_shell_basic_commands.inc.c"
#include "v132/70_storage_android_net.inc.c"
#include "v132/80_shell_dispatch.inc.c"
#include "v132/90_main.inc.c"
