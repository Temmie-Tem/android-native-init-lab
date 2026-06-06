/*
 * A90 native init v95.
 *
 * This version extracts USB gadget and netservice APIs after v94.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v95/00_prelude.inc.c"
#include "v95/10_core_log_console.inc.c"
#include "v95/20_device_display.inc.c"
#include "v95/30_status_hud.inc.c"
#include "v95/40_menu_apps.inc.c"
#include "v95/50_boot_services.inc.c"
#include "v95/60_shell_basic_commands.inc.c"
#include "v95/70_storage_android_net.inc.c"
#include "v95/80_shell_dispatch.inc.c"
#include "v95/90_main.inc.c"
