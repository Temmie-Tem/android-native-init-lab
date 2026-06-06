/*
 * A90 native init v104.
 *
 * This version adds a read-only Wi-Fi feasibility gate.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v104/00_prelude.inc.c"
#include "v104/10_core_log_console.inc.c"
#include "v104/20_device_display.inc.c"
#include "v104/30_status_hud.inc.c"
#include "v104/40_menu_apps.inc.c"
#include "v104/50_boot_services.inc.c"
#include "v104/60_shell_basic_commands.inc.c"
#include "v104/70_storage_android_net.inc.c"
#include "v104/80_shell_dispatch.inc.c"
#include "v104/90_main.inc.c"
