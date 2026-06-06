/*
 * A90 native init v91.
 *
 * This version externalizes CPU stress workers into a helper after v90.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v91/00_prelude.inc.c"
#include "v91/10_core_log_console.inc.c"
#include "v91/20_device_display.inc.c"
#include "v91/30_status_hud.inc.c"
#include "v91/40_menu_apps.inc.c"
#include "v91/50_boot_services.inc.c"
#include "v91/60_shell_basic_commands.inc.c"
#include "v91/70_storage_android_net.inc.c"
#include "v91/80_shell_dispatch.inc.c"
#include "v91/90_main.inc.c"
