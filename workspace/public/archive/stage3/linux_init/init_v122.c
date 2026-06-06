/*
 * A90 native init v122.
 *
 * This version moves Wi-Fi refresh evidence into a90_wifiinv.c/h.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v122/00_prelude.inc.c"
#include "v122/10_core_log_console.inc.c"
#include "v122/20_device_display.inc.c"
#include "v122/30_status_hud.inc.c"
#include "v122/40_menu_apps.inc.c"
#include "v122/50_boot_services.inc.c"
#include "v122/60_shell_basic_commands.inc.c"
#include "v122/70_storage_android_net.inc.c"
#include "v122/80_shell_dispatch.inc.c"
#include "v122/90_main.inc.c"
