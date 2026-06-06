/*
 * A90 native init v631.
 *
 * This version splits the sibling SSCTL boot-window proof into per-node
 * bounded child attempts.
 */
#include "v319/00_prelude.inc.c"
#include "v319/10_core_log_console.inc.c"
#include "v319/20_device_display.inc.c"
#include "v319/30_status_hud.inc.c"
#include "v319/40_menu_apps.inc.c"
#include "v319/50_boot_services.inc.c"
#include "v319/60_shell_basic_commands.inc.c"
#include "v319/70_storage_android_net.inc.c"
#include "v319/80_shell_dispatch.inc.c"
#include "v631/90_main.inc.c"
