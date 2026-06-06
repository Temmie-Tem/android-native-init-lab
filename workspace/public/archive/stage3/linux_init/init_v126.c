/*
 * A90 native init v126.
 *
 * This version hardens Batch 6 retained-source reliability: strict
 * input event names and historical rollback fixes.
 */
#include "v126/00_prelude.inc.c"
#include "v126/10_core_log_console.inc.c"
#include "v126/20_device_display.inc.c"
#include "v126/30_status_hud.inc.c"
#include "v126/40_menu_apps.inc.c"
#include "v126/50_boot_services.inc.c"
#include "v126/60_shell_basic_commands.inc.c"
#include "v126/70_storage_android_net.inc.c"
#include "v126/80_shell_dispatch.inc.c"
#include "v126/90_main.inc.c"
