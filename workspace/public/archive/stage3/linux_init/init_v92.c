/*
 * A90 native init v92.
 *
 * This version extracts shell metadata and controller policy after v91.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v92/00_prelude.inc.c"
#include "v92/10_core_log_console.inc.c"
#include "v92/20_device_display.inc.c"
#include "v92/30_status_hud.inc.c"
#include "v92/40_menu_apps.inc.c"
#include "v92/50_boot_services.inc.c"
#include "v92/60_shell_basic_commands.inc.c"
#include "v92/70_storage_android_net.inc.c"
#include "v92/80_shell_dispatch.inc.c"
#include "v92/90_main.inc.c"
