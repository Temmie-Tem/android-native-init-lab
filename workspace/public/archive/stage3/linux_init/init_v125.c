/*
 * A90 native init v125.
 *
 * This version hardens Batch 4 log/diagnostic privacy: private
 * diagnostics, fallback log storage, and opt-in HUD log tail.
 */
#include "v125/00_prelude.inc.c"
#include "v125/10_core_log_console.inc.c"
#include "v125/20_device_display.inc.c"
#include "v125/30_status_hud.inc.c"
#include "v125/40_menu_apps.inc.c"
#include "v125/50_boot_services.inc.c"
#include "v125/60_shell_basic_commands.inc.c"
#include "v125/70_storage_android_net.inc.c"
#include "v125/80_shell_dispatch.inc.c"
#include "v125/90_main.inc.c"
