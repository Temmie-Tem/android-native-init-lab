/*
 * A90 native init v93.
 *
 * This version extracts storage API boundary after v92.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v93/00_prelude.inc.c"
#include "v93/10_core_log_console.inc.c"
#include "v93/20_device_display.inc.c"
#include "v93/30_status_hud.inc.c"
#include "v93/40_menu_apps.inc.c"
#include "v93/50_boot_services.inc.c"
#include "v93/60_shell_basic_commands.inc.c"
#include "v93/70_storage_android_net.inc.c"
#include "v93/80_shell_dispatch.inc.c"
#include "v93/90_main.inc.c"
