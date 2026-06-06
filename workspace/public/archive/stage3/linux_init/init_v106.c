/*
 * A90 native init v106.
 *
 * This version adds a read-only Wi-Fi feasibility gate.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v106/00_prelude.inc.c"
#include "v106/10_core_log_console.inc.c"
#include "v106/20_device_display.inc.c"
#include "v106/30_status_hud.inc.c"
#include "v106/40_menu_apps.inc.c"
#include "v106/50_boot_services.inc.c"
#include "v106/60_shell_basic_commands.inc.c"
#include "v106/70_storage_android_net.inc.c"
#include "v106/80_shell_dispatch.inc.c"
#include "v106/90_main.inc.c"
