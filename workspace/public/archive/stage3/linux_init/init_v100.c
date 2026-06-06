/*
 * A90 native init v100.
 *
 * This version adds an explicit-token custom TCP remote shell over USB NCM.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v100/00_prelude.inc.c"
#include "v100/10_core_log_console.inc.c"
#include "v100/20_device_display.inc.c"
#include "v100/30_status_hud.inc.c"
#include "v100/40_menu_apps.inc.c"
#include "v100/50_boot_services.inc.c"
#include "v100/60_shell_basic_commands.inc.c"
#include "v100/70_storage_android_net.inc.c"
#include "v100/80_shell_dispatch.inc.c"
#include "v100/90_main.inc.c"
