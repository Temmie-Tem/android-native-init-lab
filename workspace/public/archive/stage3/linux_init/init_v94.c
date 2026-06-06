/*
 * A90 native init v94.
 *
 * This version adds the boot selftest API after v93.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v94/00_prelude.inc.c"
#include "v94/10_core_log_console.inc.c"
#include "v94/20_device_display.inc.c"
#include "v94/30_status_hud.inc.c"
#include "v94/40_menu_apps.inc.c"
#include "v94/50_boot_services.inc.c"
#include "v94/60_shell_basic_commands.inc.c"
#include "v94/70_storage_android_net.inc.c"
#include "v94/80_shell_dispatch.inc.c"
#include "v94/90_main.inc.c"
