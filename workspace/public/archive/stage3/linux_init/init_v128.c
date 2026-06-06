/*
 * A90 native init v128.
 *
 * This version relaxes the hardened auto-menu busy gate with explicit
 * read-only subcommand policy while preserving deny-by-default mutations.
 */
#include "v128/00_prelude.inc.c"
#include "v128/10_core_log_console.inc.c"
#include "v128/20_device_display.inc.c"
#include "v128/30_status_hud.inc.c"
#include "v128/40_menu_apps.inc.c"
#include "v128/50_boot_services.inc.c"
#include "v128/60_shell_basic_commands.inc.c"
#include "v128/70_storage_android_net.inc.c"
#include "v128/80_shell_dispatch.inc.c"
#include "v128/90_main.inc.c"
