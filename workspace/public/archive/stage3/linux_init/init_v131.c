/*
 * A90 native init v131.
 *
 * This version uses timer-based hold-repeat scrolling so long menu/changelog
 * screens do not depend on kernel EV_KEY repeat events.
 */
#include "v131/00_prelude.inc.c"
#include "v131/10_core_log_console.inc.c"
#include "v131/20_device_display.inc.c"
#include "v131/30_status_hud.inc.c"
#include "v131/40_menu_apps.inc.c"
#include "v131/50_boot_services.inc.c"
#include "v131/60_shell_basic_commands.inc.c"
#include "v131/70_storage_android_net.inc.c"
#include "v131/80_shell_dispatch.inc.c"
#include "v131/90_main.inc.c"
