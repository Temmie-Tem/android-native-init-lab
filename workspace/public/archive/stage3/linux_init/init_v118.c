/*
 * A90 native init v118.
 *
 * This version moves shell command metadata helpers into a90_shell.c/h.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v118/00_prelude.inc.c"
#include "v118/10_core_log_console.inc.c"
#include "v118/20_device_display.inc.c"
#include "v118/30_status_hud.inc.c"
#include "v118/40_menu_apps.inc.c"
#include "v118/50_boot_services.inc.c"
#include "v118/60_shell_basic_commands.inc.c"
#include "v118/70_storage_android_net.inc.c"
#include "v118/80_shell_dispatch.inc.c"
#include "v118/90_main.inc.c"
