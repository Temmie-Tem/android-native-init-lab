/*
 * A90 native init v107.
 *
 * This version adds a read-only Wi-Fi feasibility gate.
 * The module files are intentionally included into one translation unit so
 * existing static PID1 state and helper visibility stay unchanged.
 */

#include "v107/00_prelude.inc.c"
#include "v107/10_core_log_console.inc.c"
#include "v107/20_device_display.inc.c"
#include "v107/30_status_hud.inc.c"
#include "v107/40_menu_apps.inc.c"
#include "v107/50_boot_services.inc.c"
#include "v107/60_shell_basic_commands.inc.c"
#include "v107/70_storage_android_net.inc.c"
#include "v107/80_shell_dispatch.inc.c"
#include "v107/90_main.inc.c"
