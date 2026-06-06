/*
 * A90 native init v102.
 *
 * This version adds read-only diagnostics and log bundle collection.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v102/00_prelude.inc.c"
#include "v102/10_core_log_console.inc.c"
#include "v102/20_device_display.inc.c"
#include "v102/30_status_hud.inc.c"
#include "v102/40_menu_apps.inc.c"
#include "v102/50_boot_services.inc.c"
#include "v102/60_shell_basic_commands.inc.c"
#include "v102/70_storage_android_net.inc.c"
#include "v102/80_shell_dispatch.inc.c"
#include "v102/90_main.inc.c"
