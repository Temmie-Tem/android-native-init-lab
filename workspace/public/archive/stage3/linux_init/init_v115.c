/*
 * A90 native init v115.
 *
 * This version hardens remote shell audit and host validation paths.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v115/00_prelude.inc.c"
#include "v115/10_core_log_console.inc.c"
#include "v115/20_device_display.inc.c"
#include "v115/30_status_hud.inc.c"
#include "v115/40_menu_apps.inc.c"
#include "v115/50_boot_services.inc.c"
#include "v115/60_shell_basic_commands.inc.c"
#include "v115/70_storage_android_net.inc.c"
#include "v115/80_shell_dispatch.inc.c"
#include "v115/90_main.inc.c"
