/*
 * A90 native init v109.
 *
 * This version adds a post-v108 structure audit baseline.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v109/00_prelude.inc.c"
#include "v109/10_core_log_console.inc.c"
#include "v109/20_device_display.inc.c"
#include "v109/30_status_hud.inc.c"
#include "v109/40_menu_apps.inc.c"
#include "v109/50_boot_services.inc.c"
#include "v109/60_shell_basic_commands.inc.c"
#include "v109/70_storage_android_net.inc.c"
#include "v109/80_shell_dispatch.inc.c"
#include "v109/90_main.inc.c"
