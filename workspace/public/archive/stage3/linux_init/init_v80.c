/*
 * A90 native init v80.
 *
 * This version is the first source-layout split after v79.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v80/00_prelude.inc.c"
#include "v80/10_core_log_console.inc.c"
#include "v80/20_device_display.inc.c"
#include "v80/30_status_hud.inc.c"
#include "v80/40_menu_apps.inc.c"
#include "v80/50_boot_services.inc.c"
#include "v80/60_shell_basic_commands.inc.c"
#include "v80/70_storage_android_net.inc.c"
#include "v80/80_shell_dispatch.inc.c"
#include "v80/90_main.inc.c"
