/*
 * A90 native init v124.
 *
 * This version hardens Batch 2 runtime/helper trust: verified helper
 * preference, no-follow storage probes/logs, and safer host helper install.
 */
#include "v124/00_prelude.inc.c"
#include "v124/10_core_log_console.inc.c"
#include "v124/20_device_display.inc.c"
#include "v124/30_status_hud.inc.c"
#include "v124/40_menu_apps.inc.c"
#include "v124/50_boot_services.inc.c"
#include "v124/60_shell_basic_commands.inc.c"
#include "v124/70_storage_android_net.inc.c"
#include "v124/80_shell_dispatch.inc.c"
#include "v124/90_main.inc.c"
