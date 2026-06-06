/*
 * A90 native init v88.
 *
 * This version is the HUD API extraction after v87.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v88/00_prelude.inc.c"
#include "v88/10_core_log_console.inc.c"
#include "v88/20_device_display.inc.c"
#include "v88/30_status_hud.inc.c"
#include "v88/40_menu_apps.inc.c"
#include "v88/50_boot_services.inc.c"
#include "v88/60_shell_basic_commands.inc.c"
#include "v88/70_storage_android_net.inc.c"
#include "v88/80_shell_dispatch.inc.c"
#include "v88/90_main.inc.c"
