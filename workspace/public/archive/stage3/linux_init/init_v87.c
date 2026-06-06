/*
 * A90 native init v87.
 *
 * This version is the input API extraction after v86.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v87/00_prelude.inc.c"
#include "v87/10_core_log_console.inc.c"
#include "v87/20_device_display.inc.c"
#include "v87/30_status_hud.inc.c"
#include "v87/40_menu_apps.inc.c"
#include "v87/50_boot_services.inc.c"
#include "v87/60_shell_basic_commands.inc.c"
#include "v87/70_storage_android_net.inc.c"
#include "v87/80_shell_dispatch.inc.c"
#include "v87/90_main.inc.c"
