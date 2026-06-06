/*
 * A90 native init v117.
 *
 * This version anchors the v117-v122 PID1 slimdown planning cycle.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v117/00_prelude.inc.c"
#include "v117/10_core_log_console.inc.c"
#include "v117/20_device_display.inc.c"
#include "v117/30_status_hud.inc.c"
#include "v117/40_menu_apps.inc.c"
#include "v117/50_boot_services.inc.c"
#include "v117/60_shell_basic_commands.inc.c"
#include "v117/70_storage_android_net.inc.c"
#include "v117/80_shell_dispatch.inc.c"
#include "v117/90_main.inc.c"
