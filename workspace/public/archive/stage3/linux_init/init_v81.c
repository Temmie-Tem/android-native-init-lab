/*
 * A90 native init v81.
 *
 * This version is the first true base-module extraction after v80.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v81/00_prelude.inc.c"
#include "v81/10_core_log_console.inc.c"
#include "v81/20_device_display.inc.c"
#include "v81/30_status_hud.inc.c"
#include "v81/40_menu_apps.inc.c"
#include "v81/50_boot_services.inc.c"
#include "v81/60_shell_basic_commands.inc.c"
#include "v81/70_storage_android_net.inc.c"
#include "v81/80_shell_dispatch.inc.c"
#include "v81/90_main.inc.c"
